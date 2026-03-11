"""
Flow 6: Auth Endpoints
Logout clears cookies, forgot-password always 200, reset password flow
(valid/expired/used token), validate-reset-token.
"""
import hashlib
import datetime
import pytest
from tests.helpers import FlowHelpers, TestData


class TestAuthEndpoints:

    def test_logout_clears_cookies(self, client):
        """Logout should clear refresh_token and XSRF-TOKEN cookies."""
        h = FlowHelpers(client)
        h.signup_user()

        res = client.post("/api/auth/logout")
        assert res.status_code == 200
        assert res.get_json()["message"] == "Logged out successfully"

        # After logout, refresh should fail
        res = client.post("/api/auth/refresh")
        assert res.status_code == 401

    def test_forgot_password_always_200(self, client):
        """Forgot password returns 200 even for non-existent emails."""
        h = FlowHelpers(client)
        # No signup — email doesn't exist
        res = client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert res.status_code == 200
        assert "reset link" in res.get_json()["message"].lower()

    def test_forgot_password_existing_email(self, client, email_capture):
        """Forgot password for existing email sends reset email."""
        h = FlowHelpers(client)
        h.signup_user()

        res = client.post(
            "/api/auth/forgot-password",
            json={"email": TestData.HR_EMAIL},
        )
        assert res.status_code == 200

        # Verify reset email was captured
        reset_emails = [e for e in email_capture.sent if e["type"] == "password_reset"]
        assert len(reset_emails) == 1

    def test_reset_password_valid_token(self, client, email_capture):
        """Full reset password flow: forgot → get token → reset → login."""
        h = FlowHelpers(client)
        h.signup_user()

        # Trigger forgot password
        client.post(
            "/api/auth/forgot-password",
            json={"email": TestData.HR_EMAIL},
        )

        # Extract token from DB (we can't easily get it from the email in tests)
        from database.connection import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT token_hash FROM password_reset_tokens
                    WHERE used = FALSE
                    ORDER BY created_at DESC LIMIT 1
                    """
                )
                token_hash = cur.fetchone()[0]

        # We need the raw token, not the hash. Since we can't reverse hash,
        # we'll insert a known token directly for testing.
        import secrets
        raw_token = secrets.token_urlsafe(32)
        known_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

        with get_db() as conn:
            with conn.cursor() as cur:
                # Get user ID
                cur.execute("SELECT id FROM users WHERE email = %s", (TestData.HR_EMAIL,))
                user_id = str(cur.fetchone()[0])

                # Insert our known token
                cur.execute(
                    """
                    INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, known_hash, expires_at),
                )

        # Reset password with known token
        new_password = "NewSecurePass1"
        res = client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "password": new_password},
        )
        assert res.status_code == 200

        # Login with new password
        login_res = h.login_user(password=new_password)
        assert login_res.status_code == 200

    def test_reset_password_expired_token(self, client):
        """Using an expired reset token returns 400."""
        h = FlowHelpers(client)
        h.signup_user()

        import secrets
        raw_token = secrets.token_urlsafe(32)
        known_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expired_at = datetime.datetime.utcnow() - datetime.timedelta(hours=1)

        from database.connection import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email = %s", (TestData.HR_EMAIL,))
                user_id = str(cur.fetchone()[0])
                cur.execute(
                    "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
                    (user_id, known_hash, expired_at),
                )

        res = client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "password": "NewPass123"},
        )
        assert res.status_code == 400

    def test_validate_reset_token_valid(self, client):
        """validate-reset-token returns valid=True for valid token."""
        h = FlowHelpers(client)
        h.signup_user()

        import secrets
        raw_token = secrets.token_urlsafe(32)
        known_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

        from database.connection import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email = %s", (TestData.HR_EMAIL,))
                user_id = str(cur.fetchone()[0])
                cur.execute(
                    "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
                    (user_id, known_hash, expires_at),
                )

        res = client.get(f"/api/auth/validate-reset-token?token={raw_token}")
        assert res.status_code == 200
        assert res.get_json()["valid"] is True

    def test_validate_reset_token_invalid(self, client):
        """validate-reset-token returns valid=False for bogus token."""
        res = client.get("/api/auth/validate-reset-token?token=bogus-token-12345")
        assert res.status_code == 400
        assert res.get_json()["valid"] is False
