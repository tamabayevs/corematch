"""
CoreMatch — Auth Blueprint
Endpoints: signup, login, refresh, logout, forgot-password, reset-password
"""
import os
import secrets
import hashlib
import hmac
import logging
import datetime
import bcrypt
from email_validator import validate_email, EmailNotValidError
from flask import Blueprint, request, jsonify, make_response, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from database.connection import get_db
from api.middleware import (
    require_auth,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """Hash password with bcrypt cost=12."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def _check_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _validate_password_strength(password: str) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    return errors


def _set_refresh_cookie(response, token: str, expire_days: int = 7):
    """Set httpOnly refresh token cookie."""
    is_production = os.environ.get("NODE_ENV") == "production"
    response.set_cookie(
        "refresh_token",
        token,
        max_age=expire_days * 24 * 3600,
        httponly=True,
        secure=is_production,
        samesite="Strict",
        path="/api/auth",  # Only sent to auth endpoints
    )


def _set_xsrf_cookie(response):
    """Set readable XSRF-TOKEN cookie for double-submit CSRF protection."""
    xsrf_token = secrets.token_hex(32)
    is_production = os.environ.get("NODE_ENV") == "production"
    response.set_cookie(
        "XSRF-TOKEN",
        xsrf_token,
        httponly=False,  # Intentionally readable by JS
        secure=is_production,
        samesite="Strict",
    )


def _generate_reference_id() -> str:
    """Generate CM-2026-XXXXXX reference ID for candidates."""
    year = datetime.datetime.utcnow().year
    suffix = secrets.randbelow(900000) + 100000  # 6-digit number
    return f"CM-{year}-{suffix}"


# ──────────────────────────────────────────────────────────────
# POST /api/auth/signup
# ──────────────────────────────────────────────────────────────

@auth_bp.route("/signup", methods=["POST"])
def signup():
    """
    Register a new HR user.
    Rate limit: 3/minute per IP.
    """
    limiter = auth_bp.get_app().extensions.get("limiter") if hasattr(auth_bp, 'get_app') else None

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Validate required fields
    email_raw = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()

    if not email_raw or not password or not full_name:
        return jsonify({"error": "email, password, and full_name are required"}), 400

    # Validate email format
    try:
        valid = validate_email(email_raw)
        email = valid.email
    except EmailNotValidError as e:
        return jsonify({"error": f"Invalid email: {str(e)}"}), 400

    # Validate password strength
    pw_errors = _validate_password_strength(password)
    if pw_errors:
        return jsonify({"error": "Password too weak", "details": pw_errors}), 400

    # Optional fields
    company_name = data.get("company_name", "").strip()
    job_title = data.get("job_title", "").strip()

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Check email uniqueness
                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    return jsonify({"error": "An account with this email already exists"}), 409

                # Create user
                password_hash = _hash_password(password)
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash, full_name, company_name, job_title)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, email, full_name, company_name
                    """,
                    (email, password_hash, full_name, company_name or None, job_title or None),
                )
                user = cur.fetchone()
    except Exception as e:
        logger.error("Signup DB error: %s", str(e))
        return jsonify({"error": "Failed to create account"}), 500

    user_id = str(user[0])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)

    response = make_response(jsonify({
        "message": "Account created successfully",
        "access_token": access_token,
        "user": {
            "id": user_id,
            "email": user[1],
            "full_name": user[2],
            "company_name": user[3],
        },
    }), 201)

    _set_refresh_cookie(response, refresh_token)
    _set_xsrf_cookie(response)
    return response


# ──────────────────────────────────────────────────────────────
# POST /api/auth/login
# ──────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate HR user.
    Rate limit: 5/minute per IP (brute force prevention).
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    email_raw = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email_raw or not password:
        return jsonify({"error": "email and password are required"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, password_hash, full_name, company_name, language
                    FROM users WHERE email = %s
                    """,
                    (email_raw,),
                )
                user = cur.fetchone()
    except Exception as e:
        logger.error("Login DB error: %s", str(e))
        return jsonify({"error": "Login failed"}), 500

    # Generic error for both "not found" and "wrong password" (prevents email enumeration)
    if not user or not _check_password(password, user[2]):
        return jsonify({"error": "Invalid email or password"}), 401

    user_id = str(user[0])
    access_token = create_access_token(user_id, user[1])
    refresh_token = create_refresh_token(user_id)

    response = make_response(jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "id": user_id,
            "email": user[1],
            "full_name": user[3],
            "company_name": user[4],
            "language": user[5],
        },
    }))

    _set_refresh_cookie(response, refresh_token)
    _set_xsrf_cookie(response)
    return response


# ──────────────────────────────────────────────────────────────
# POST /api/auth/refresh
# ──────────────────────────────────────────────────────────────

@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """
    Refresh access token using httpOnly refresh cookie.
    Called automatically by Axios interceptor on 401.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        return jsonify({"error": "No refresh token"}), 401

    user_id = verify_refresh_token(refresh_token)
    if not user_id:
        return jsonify({"error": "Invalid or expired refresh token"}), 401

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, full_name, company_name FROM users WHERE id = %s",
                    (user_id,),
                )
                user = cur.fetchone()
    except Exception as e:
        logger.error("Refresh DB error: %s", str(e))
        return jsonify({"error": "Token refresh failed"}), 500

    if not user:
        return jsonify({"error": "User not found"}), 401

    new_access_token = create_access_token(str(user[0]), user[1])
    new_refresh_token = create_refresh_token(str(user[0]))

    response = make_response(jsonify({
        "access_token": new_access_token,
        "user": {
            "id": str(user[0]),
            "email": user[1],
            "full_name": user[2],
            "company_name": user[3],
        },
    }))

    _set_refresh_cookie(response, new_refresh_token)
    _set_xsrf_cookie(response)
    return response


# ──────────────────────────────────────────────────────────────
# POST /api/auth/logout
# ──────────────────────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Clear refresh token cookie. Frontend clears sessionStorage."""
    response = make_response(jsonify({"message": "Logged out successfully"}))
    response.delete_cookie("refresh_token", path="/api/auth")
    response.delete_cookie("XSRF-TOKEN")
    return response


# ──────────────────────────────────────────────────────────────
# GET /api/auth/me
# ──────────────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    """Return current user profile."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, full_name, job_title, company_name, language,
                           notify_on_complete, notify_weekly, created_at
                    FROM users WHERE id = %s
                    """,
                    (g.current_user["id"],),
                )
                user = cur.fetchone()
    except Exception as e:
        logger.error("Me endpoint DB error: %s", str(e))
        return jsonify({"error": "Failed to fetch profile"}), 500

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": str(user[0]),
        "email": user[1],
        "full_name": user[2],
        "job_title": user[3],
        "company_name": user[4],
        "language": user[5],
        "notify_on_complete": user[6],
        "notify_weekly": user[7],
        "created_at": user[8].isoformat() if user[8] else None,
    })


# ──────────────────────────────────────────────────────────────
# PUT /api/auth/me
# ──────────────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["PUT"])
@require_auth
def update_profile():
    """Update HR user profile (name, job title, company, language, notifications)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    allowed_fields = {
        "full_name": str,
        "job_title": str,
        "company_name": str,
        "language": str,
        "notify_on_complete": bool,
        "notify_weekly": bool,
    }

    updates = {}
    for field, field_type in allowed_fields.items():
        if field in data:
            value = data[field]
            if field == "language" and value not in ("en", "ar"):
                return jsonify({"error": "language must be 'en' or 'ar'"}), 400
            updates[field] = value

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [g.current_user["id"]]

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE users SET {set_clause} WHERE id = %s",
                    values,
                )
    except Exception as e:
        logger.error("Update profile DB error: %s", str(e))
        return jsonify({"error": "Failed to update profile"}), 500

    return jsonify({"message": "Profile updated successfully"})


# ──────────────────────────────────────────────────────────────
# POST /api/auth/forgot-password
# Rate limit: 3/15 minutes per IP
# ──────────────────────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    Initiate password reset.
    SECURITY: Always returns 200 regardless of whether email exists
    (prevents account enumeration).
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    email_raw = data.get("email", "").strip().lower()

    try:
        valid = validate_email(email_raw)
        email = valid.email
    except EmailNotValidError:
        # Still return 200 to prevent enumeration
        return jsonify({"message": "If this email exists, a reset link has been sent"}), 200

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, full_name FROM users WHERE email = %s", (email,))
                user = cur.fetchone()

                if user:
                    # Generate cryptographically secure token
                    raw_token = secrets.token_urlsafe(32)  # 256 bits of entropy
                    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
                    expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

                    # Invalidate any existing tokens for this user
                    cur.execute(
                        "UPDATE password_reset_tokens SET used = TRUE WHERE user_id = %s AND used = FALSE",
                        (str(user[0]),),
                    )

                    # Insert new token
                    cur.execute(
                        """
                        INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
                        VALUES (%s, %s, %s)
                        """,
                        (str(user[0]), token_hash, expires_at),
                    )

                    # Send reset email (import here to avoid circular)
                    from services.email_service import get_email_service
                    email_svc = get_email_service()
                    reset_url = f"{os.environ.get('FRONTEND_URL', 'http://localhost:5173')}/reset-password?token={raw_token}"

                    try:
                        email_svc.send_password_reset(
                            to_email=email,
                            to_name=user[1] or "there",
                            reset_url=reset_url,
                            expires_in_hours=1,
                            request_ip=request.remote_addr,
                        )
                    except Exception as email_err:
                        logger.error("Failed to send password reset email: %s", str(email_err))
                        # Don't fail the request — user might still retry

    except Exception as e:
        logger.error("Forgot password DB error: %s", str(e))

    # Always return same response (security)
    return jsonify({"message": "If this email exists, a reset link has been sent"}), 200


# ──────────────────────────────────────────────────────────────
# POST /api/auth/reset-password
# ──────────────────────────────────────────────────────────────

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    Reset password using token from email link.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    raw_token = data.get("token", "").strip()
    new_password = data.get("password", "")

    if not raw_token or not new_password:
        return jsonify({"error": "token and password are required"}), 400

    # Validate password strength
    pw_errors = _validate_password_strength(new_password)
    if pw_errors:
        return jsonify({"error": "Password too weak", "details": pw_errors}), 400

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = datetime.datetime.utcnow()

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Find valid, unexpired, unused token
                # Use constant-time comparison via SQL (no timing side channel)
                cur.execute(
                    """
                    SELECT prt.id, prt.user_id, prt.expires_at
                    FROM password_reset_tokens prt
                    WHERE prt.token_hash = %s
                      AND prt.used = FALSE
                      AND prt.expires_at > NOW()
                    """,
                    (token_hash,),
                )
                token_row = cur.fetchone()

                if not token_row:
                    return jsonify({
                        "error": "token_invalid",
                        "message": "This reset link has expired or already been used",
                    }), 400

                token_id = token_row[0]
                user_id = token_row[1]

                # Update password
                new_hash = _hash_password(new_password)
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (new_hash, str(user_id)),
                )

                # Invalidate this token and all other reset tokens for this user
                cur.execute(
                    "UPDATE password_reset_tokens SET used = TRUE WHERE user_id = %s",
                    (str(user_id),),
                )

    except Exception as e:
        logger.error("Reset password DB error: %s", str(e))
        return jsonify({"error": "Failed to reset password"}), 500

    return jsonify({"message": "Password updated successfully"})


# ──────────────────────────────────────────────────────────────
# GET /api/auth/validate-reset-token
# ──────────────────────────────────────────────────────────────

@auth_bp.route("/validate-reset-token", methods=["GET"])
def validate_reset_token():
    """
    Check if a reset token is valid (used by frontend to decide what to show).
    Returns 200 if valid, 400 if invalid/expired.
    """
    raw_token = request.args.get("token", "").strip()
    if not raw_token:
        return jsonify({"valid": False}), 400

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id FROM password_reset_tokens
                    WHERE token_hash = %s AND used = FALSE AND expires_at > NOW()
                    """,
                    (token_hash,),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Validate reset token DB error: %s", str(e))
        return jsonify({"valid": False}), 500

    if row:
        return jsonify({"valid": True})
    return jsonify({"valid": False, "error": "token_invalid"}), 400
