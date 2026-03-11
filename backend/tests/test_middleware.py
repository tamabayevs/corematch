"""
Flow 7: Middleware
require_auth sets g.current_user, rejects invalid token;
require_invite_token sets g.candidate/g.campaign, returns 410/409;
CSRF validation.
"""
import datetime
import pytest
from tests.helpers import FlowHelpers, TestData


class TestMiddleware:

    def test_require_auth_sets_current_user(self, client):
        """require_auth sets g.current_user with correct data."""
        h = FlowHelpers(client)
        h.signup_user()
        res = h.get_me()
        assert res.status_code == 200
        data = res.get_json()
        assert data["email"] == TestData.HR_EMAIL
        assert data["full_name"] == TestData.HR_NAME

    def test_require_auth_rejects_no_token(self, client):
        """Accessing protected endpoint without token returns 401."""
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_require_auth_rejects_invalid_token(self, client):
        """An invalid JWT string returns 401."""
        res = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert res.status_code == 401

    def test_require_invite_token_sets_candidate(self, client):
        """require_invite_token sets g.candidate and g.campaign."""
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        token = h.get_invite_token_from_db()

        res = h.get_invite(token)
        assert res.status_code == 200
        data = res.get_json()
        assert data["candidate"]["full_name"] == TestData.CANDIDATE_NAME
        assert data["campaign"]["job_title"] == TestData.JOB_TITLE

    def test_require_invite_token_returns_410_expired(self, client):
        """Expired invite token returns 410 with campaign info."""
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        token = h.get_invite_token_from_db()

        # Expire the invite
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
        assert "company_name" in data
        assert "hr_email" in data

    def test_require_invite_token_returns_409_submitted(self, client):
        """Submitted candidate's token returns 409 with reference_id."""
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        token = h.get_invite_token_from_db()

        # Mark as submitted
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
        assert "reference_id" in data
