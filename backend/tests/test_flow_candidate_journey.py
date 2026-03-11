"""
Flow 2: Candidate Journey
Access invite → consent → upload videos → submit
"""
import pytest
from tests.helpers import FlowHelpers, TestData


class TestCandidateJourney:

    def _setup_invited_candidate(self, client):
        """Helper: signup HR, create campaign, invite candidate, return token."""
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        token = h.get_invite_token_from_db()
        return h, token

    def test_access_invite(self, client):
        h, token = self._setup_invited_candidate(client)
        res = h.get_invite(token)
        assert res.status_code == 200
        data = res.get_json()
        assert data["candidate"]["full_name"] == TestData.CANDIDATE_NAME
        assert data["campaign"]["job_title"] == TestData.JOB_TITLE
        assert len(data["questions"]) == 3

    def test_record_consent(self, client):
        h, token = self._setup_invited_candidate(client)
        res = h.record_consent(token)
        assert res.status_code == 200
        assert res.get_json()["consent_given"] is True

    def test_consent_idempotent(self, client):
        h, token = self._setup_invited_candidate(client)
        h.record_consent(token)
        res = h.record_consent(token)
        assert res.status_code == 200
        assert "already" in res.get_json()["message"].lower()

    def test_upload_video_q0(self, client):
        h, token = self._setup_invited_candidate(client)
        h.record_consent(token)
        res = h.upload_video_multipart(token, 0)
        assert res.status_code == 201
        data = res.get_json()
        assert data["question_index"] == 0
        assert data["uploaded_count"] == 1
        assert data["all_uploaded"] is False

    def test_upload_all_videos(self, client):
        h, token = self._setup_invited_candidate(client)
        h.record_consent(token)
        for i in range(3):
            res = h.upload_video_multipart(token, i)
            assert res.status_code == 201
        data = res.get_json()
        assert data["uploaded_count"] == 3
        assert data["all_uploaded"] is True

    def test_upload_triggers_processing(self, client, mock_rq_enqueue):
        h, token = self._setup_invited_candidate(client)
        h.record_consent(token)
        for i in range(3):
            res = h.upload_video_multipart(token, i)
        data = res.get_json()
        assert data["all_uploaded"] is True
        # RQ enqueue was called
        assert mock_rq_enqueue.enqueue.called

    def test_explicit_submit_after_auto_trigger_returns_409(self, client):
        """After all uploads auto-trigger submission, explicit submit returns 409."""
        h, token = self._setup_invited_candidate(client)
        h.record_consent(token)
        for i in range(3):
            h.upload_video_multipart(token, i)
        # Auto-trigger sets status='submitted', so require_invite_token returns 409
        res = h.submit_interview(token)
        assert res.status_code == 409

    def test_submit_partial(self, client):
        h, token = self._setup_invited_candidate(client)
        h.record_consent(token)
        h.upload_video_multipart(token, 0)  # Only 1 of 3
        res = h.submit_interview(token, submit_partial=True)
        assert res.status_code in (200, 201)
        data = res.get_json()
        assert data.get("partial") is True or data.get("message")
