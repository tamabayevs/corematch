"""
Flow 4: Edge Cases & Error Handling
Expired invite, already submitted, invalid token, upload without consent,
duplicate invite, wrong password, token refresh, too few/many questions,
invalid file type, empty file, bad question_index, invite to closed campaign,
PDPL erase, weak password, invalid email.
"""
import io
import json
import datetime
import pytest
from unittest.mock import patch
from tests.helpers import FlowHelpers, TestData


class TestEdgeCases:

    def _setup_invited_candidate(self, client):
        """Helper: signup HR, create campaign, invite candidate, return token."""
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        token = h.get_invite_token_from_db()
        return h, token, campaign_id

    # ── Invite edge cases ──

    def test_expired_invite_returns_410(self, client):
        """Accessing an expired invite link should return 410 Gone."""
        h, token, _ = self._setup_invited_candidate(client)

        # Force-expire the invite in DB
        from database.connection import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE candidates SET invite_expires_at = NOW() - INTERVAL '1 day' WHERE invite_token = %s",
                    (token,),
                )

        res = h.get_invite(token)
        assert res.status_code == 410
        data = res.get_json()
        assert data["error"] == "invitation_expired"
        assert "job_title" in data

    def test_already_submitted_returns_409(self, client):
        """Accessing a submitted candidate's invite returns 409."""
        h, token, _ = self._setup_invited_candidate(client)

        # Force status to 'submitted'
        from database.connection import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE candidates SET status = 'submitted' WHERE invite_token = %s",
                    (token,),
                )

        res = h.get_invite(token)
        assert res.status_code == 409
        data = res.get_json()
        assert data["error"] == "already_submitted"

    def test_invalid_token_returns_404(self, client):
        """A random UUID token returns 404."""
        h = FlowHelpers(client)
        res = h.get_invite("00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404

    def test_upload_without_consent_returns_403(self, client):
        """Uploading a video before recording consent returns 403."""
        h, token, _ = self._setup_invited_candidate(client)
        # Skip consent → try upload
        res = h.upload_video_multipart(token, 0)
        assert res.status_code == 403

    def test_duplicate_invite_returns_409(self, client):
        """Inviting the same email to the same campaign twice returns 409."""
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]

        # First invite succeeds
        res1 = h.invite_candidate(campaign_id)
        assert res1.status_code == 201

        # Second invite to same email+campaign fails
        res2 = h.invite_candidate(campaign_id)
        assert res2.status_code == 409

    # ── Auth edge cases ──

    def test_wrong_password_returns_401(self, client):
        """Login with wrong password returns 401."""
        h = FlowHelpers(client)
        h.signup_user()
        res = h.login_user(password="WrongPassword999")
        assert res.status_code == 401

    def test_token_refresh(self, client):
        """Refresh endpoint returns new access token from refresh cookie."""
        h = FlowHelpers(client)
        signup_res = h.signup_user()
        assert signup_res.status_code == 201

        # Refresh should work with the cookie set during signup
        res = client.post("/api/auth/refresh")
        assert res.status_code == 200
        data = res.get_json()
        assert "access_token" in data

    def test_expired_jwt_returns_401(self, client):
        """An expired JWT token returns 401."""
        h = FlowHelpers(client)
        h.signup_user()

        # Create an expired token
        from api.middleware import get_jwt_secret, JWT_ALGORITHM
        import jwt as pyjwt
        expired_token = pyjwt.encode(
            {
                "sub": "some-user-id",
                "email": "test@test.com",
                "iat": datetime.datetime.utcnow() - datetime.timedelta(hours=1),
                "exp": datetime.datetime.utcnow() - datetime.timedelta(minutes=30),
                "type": "access",
            },
            get_jwt_secret(),
            algorithm=JWT_ALGORITHM,
        )

        res = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert res.status_code == 401

    # ── Campaign validation edge cases ──

    def test_too_few_questions_returns_400(self, client):
        """Creating a campaign with fewer than 3 questions returns 400."""
        h = FlowHelpers(client)
        h.signup_user()
        questions = [
            {"text": "Q1", "think_time_seconds": 30},
            {"text": "Q2", "think_time_seconds": 30},
        ]
        res = h.create_campaign(questions=questions)
        assert res.status_code == 400

    def test_too_many_questions_returns_400(self, client):
        """Creating a campaign with more than 7 questions returns 400."""
        h = FlowHelpers(client)
        h.signup_user()
        questions = [
            {"text": f"Question {i}", "think_time_seconds": 30}
            for i in range(8)
        ]
        res = h.create_campaign(questions=questions)
        assert res.status_code == 400

    # ── Upload validation edge cases ──

    def test_invalid_file_type_returns_400(self, client):
        """Uploading a non-video file type returns 400."""
        h, token, _ = self._setup_invited_candidate(client)
        h.record_consent(token)

        data = {
            "video": (io.BytesIO(b"not a video file"), "test.txt", "text/plain"),
            "question_index": "0",
            "duration_seconds": "10.0",
        }
        res = client.post(
            f"/api/public/video-upload/{token}",
            data=data,
            content_type="multipart/form-data",
        )
        assert res.status_code == 400

    def test_empty_file_returns_400(self, client):
        """Uploading an empty video file returns 400."""
        h, token, _ = self._setup_invited_candidate(client)
        h.record_consent(token)

        data = {
            "video": (io.BytesIO(b""), "empty.webm", "video/webm"),
            "question_index": "0",
            "duration_seconds": "10.0",
        }
        res = client.post(
            f"/api/public/video-upload/{token}",
            data=data,
            content_type="multipart/form-data",
        )
        assert res.status_code == 400

    def test_bad_question_index_returns_400(self, client):
        """Uploading with an out-of-range question_index returns 400."""
        h, token, _ = self._setup_invited_candidate(client)
        h.record_consent(token)
        res = h.upload_video_multipart(token, 99)
        assert res.status_code == 400

    def test_invite_to_closed_campaign_returns_400(self, client):
        """Inviting a candidate to a closed campaign returns 400."""
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]

        # Close the campaign
        client.put(
            f"/api/campaigns/{campaign_id}",
            json={"status": "closed"},
            headers=h._auth_headers(),
        )

        # Try inviting
        res = h.invite_candidate(
            campaign_id,
            email="another@gmail.com",
            full_name="Another Candidate",
        )
        assert res.status_code == 400

    # ── PDPL Erase ──

    def test_pdpl_erase(self, client):
        """Erasing a candidate anonymizes PII and deletes videos."""
        h, token, campaign_id = self._setup_invited_candidate(client)
        h.record_consent(token)
        h.upload_video_multipart(token, 0)

        candidate_id = h.get_candidate_id_from_db()
        res = h.erase_candidate(candidate_id)
        assert res.status_code == 200

        # Verify anonymization
        from database.connection import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT email, full_name, status FROM candidates WHERE id = %s",
                    (candidate_id,),
                )
                row = cur.fetchone()
                assert row[0] == "erased@erased.invalid"
                assert row[1] == "[Erased]"
                assert row[2] == "erased"

    # ── Auth validation edge cases ──

    def test_weak_password_signup(self, client):
        """Signing up with a weak password returns 400."""
        h = FlowHelpers(client)
        res = h.signup_user(password="weak")
        assert res.status_code == 400
        data = res.get_json()
        assert "details" in data

    def test_invalid_email_signup(self, client):
        """Signing up with an invalid email returns 400."""
        h = FlowHelpers(client)
        res = h.signup_user(email="not-an-email")
        assert res.status_code == 400
