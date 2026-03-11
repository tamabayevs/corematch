"""
Flow 5: Full Lifecycle (Golden Path)
HR signup → create campaign → invite → candidate consents → uploads 3 videos →
submits → worker processes (mocked Groq) → HR views scores → HR sets decision → audit log verified.
"""
import json
import pytest
from tests.helpers import FlowHelpers, TestData


class TestFullLifecycle:

    def test_golden_path(self, client, mock_rq_enqueue, mock_groq_client, mock_ffmpeg, email_capture):
        """Complete end-to-end flow from HR signup to decision."""
        h = FlowHelpers(client)

        # ── HR: Signup ──
        signup_res = h.signup_user()
        assert signup_res.status_code == 201
        access_token = signup_res.get_json()["access_token"]

        # ── HR: Create campaign ──
        create_res = h.create_campaign()
        assert create_res.status_code == 201
        campaign = create_res.get_json()["campaign"]
        campaign_id = campaign["id"]
        assert campaign["job_title"] == TestData.JOB_TITLE
        assert len(campaign["questions"]) == 3

        # ── HR: Invite candidate ──
        invite_res = h.invite_candidate(campaign_id)
        assert invite_res.status_code == 201
        candidate_data = invite_res.get_json()["candidate"]
        assert candidate_data["status"] == "invited"

        # Verify invitation email was captured
        invitation_emails = [e for e in email_capture.sent if e["type"] == "candidate_invitation"]
        assert len(invitation_emails) == 1

        # ── Candidate: Access invite ──
        token = h.get_invite_token_from_db()
        invite_info = h.get_invite(token)
        assert invite_info.status_code == 200
        data = invite_info.get_json()
        assert data["campaign"]["job_title"] == TestData.JOB_TITLE
        assert len(data["questions"]) == 3

        # ── Candidate: Record consent ──
        consent_res = h.record_consent(token)
        assert consent_res.status_code == 200
        assert consent_res.get_json()["consent_given"] is True

        # ── Candidate: Upload 3 videos ──
        for i in range(3):
            upload_res = h.upload_video_multipart(token, i)
            assert upload_res.status_code == 201

        # Final upload should indicate all_uploaded
        final_data = upload_res.get_json()
        assert final_data["all_uploaded"] is True
        assert final_data["uploaded_count"] == 3

        # RQ enqueue was called (auto-trigger on last upload)
        assert mock_rq_enqueue.enqueue.called

        # ── Worker: Process candidate (synchronous call, mocked AI) ──
        candidate_id = h.get_candidate_id_from_db()
        from workers.video_processor import process_candidate
        summary = process_candidate(candidate_id)

        assert summary["processed"] == 3
        assert summary["failed"] == 0
        assert summary["overall_score"] is not None
        assert summary["tier"] in ("strong_proceed", "consider", "likely_pass")

        # Verify confirmation email sent to candidate
        confirmations = [e for e in email_capture.sent if e["type"] == "candidate_confirmation"]
        assert len(confirmations) == 1
        assert confirmations[0]["to_email"] == TestData.CANDIDATE_EMAIL

        # Verify HR notification email sent
        hr_notifications = [e for e in email_capture.sent if e["type"] == "hr_notification"]
        assert len(hr_notifications) == 1
        assert hr_notifications[0]["to_email"] == TestData.HR_EMAIL

        # ── HR: View candidate scores ──
        detail_res = h.get_candidate(candidate_id)
        assert detail_res.status_code == 200
        candidate_detail = detail_res.get_json()["candidate"]
        assert candidate_detail["overall_score"] is not None
        assert candidate_detail["tier"] is not None
        assert len(candidate_detail["video_answers"]) == 3

        # Verify each video answer has scores
        for answer in candidate_detail["video_answers"]:
            assert answer["processing_status"] == "complete"
            assert answer["transcript"] is not None
            assert answer["scores"] is not None
            assert answer["scores"]["content"] is not None

        # ── HR: Set decision ──
        decision_res = h.set_decision(candidate_id, "shortlisted", note="Great candidate!")
        assert decision_res.status_code == 200

        # Verify decision persisted
        detail_after = h.get_candidate(candidate_id)
        candidate_after = detail_after.get_json()["candidate"]
        assert candidate_after["hr_decision"] == "shortlisted"
        assert candidate_after["hr_decision_note"] == "Great candidate!"

        # ── Verify audit log ──
        from database.connection import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT action FROM audit_log ORDER BY created_at ASC"
                )
                actions = [row[0] for row in cur.fetchall()]

        assert "candidate.invited" in actions
        assert "candidate.consent_given" in actions
        assert "candidate.submitted" in actions
        assert "candidate.processed" in actions
        assert "candidate.shortlisted" in actions
