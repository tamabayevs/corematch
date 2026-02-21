"""
CoreMatch — Auth Middleware
JWT verification for HR endpoints.
Invite token validation for public (candidate) endpoints.
"""
import os
import logging
import functools
import jwt
from flask import request, jsonify, g
from database.connection import get_db

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"


def get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is not set")
    return secret


# ──────────────────────────────────────────────────────────────
# HR Authentication — JWT
# ──────────────────────────────────────────────────────────────

def require_auth(f):
    """
    Decorator: Requires a valid JWT access token in Authorization header.
    Sets g.current_user = {id, email, full_name, company_name}
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header[7:]  # Strip "Bearer "

        try:
            payload = jwt.decode(
                token,
                get_jwt_secret(),
                algorithms=[JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT token: %s", str(e))
            return jsonify({"error": "Invalid token"}), 401

        user_id = payload.get("sub")
        if not user_id:
            return jsonify({"error": "Invalid token payload"}), 401

        # Load user from DB to ensure they still exist and get fresh data
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, full_name, company_name, language
                    FROM users WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()

        if not row:
            return jsonify({"error": "User not found"}), 401

        g.current_user = {
            "id": str(row[0]),
            "email": row[1],
            "full_name": row[2],
            "company_name": row[3],
            "language": row[4],
        }
        return f(*args, **kwargs)

    return decorated


def create_access_token(user_id: str, email: str) -> str:
    """
    Create a short-lived JWT access token (15 minutes).
    Stored in sessionStorage on the frontend.
    """
    import datetime
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """
    Create a long-lived JWT refresh token (7 days).
    Stored in httpOnly cookie on the frontend.
    """
    import datetime
    payload = {
        "sub": user_id,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
        "type": "refresh",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def verify_refresh_token(token: str):
    """
    Verify a refresh token and return the user_id (sub) or None.
    """
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None


# ──────────────────────────────────────────────────────────────
# Candidate Authentication — Invite Token
# ──────────────────────────────────────────────────────────────

def require_invite_token(f):
    """
    Decorator: Validates invite token from URL path.
    Sets g.candidate = {...full candidate row...}
    Sets g.campaign = {...campaign info...}
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        import datetime

        # Token comes from URL parameter
        token = kwargs.get("token") or request.view_args.get("token")
        if not token:
            return jsonify({"error": "Missing invite token"}), 401

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        c.id, c.campaign_id, c.email, c.full_name, c.phone,
                        c.invite_token, c.questions_snapshot, c.invite_expires_at,
                        c.status, c.consent_given, c.overall_score, c.reference_id,
                        camp.id as camp_id, camp.name as camp_name,
                        camp.job_title, camp.job_description, camp.language,
                        camp.max_recording_seconds, camp.allow_retakes,
                        u.company_name, u.email as hr_email
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    JOIN users u ON camp.user_id = u.id
                    WHERE c.invite_token = %s
                    """,
                    (token,),
                )
                row = cur.fetchone()

        if not row:
            return jsonify({"error": "Invalid or expired invitation link"}), 404

        candidate = {
            "id": str(row[0]),
            "campaign_id": str(row[1]),
            "email": row[2],
            "full_name": row[3],
            "phone": row[4],
            "invite_token": row[5],
            "questions_snapshot": row[6],
            "invite_expires_at": row[7],
            "status": row[8],
            "consent_given": row[9],
            "overall_score": float(row[10]) if row[10] else None,
            "reference_id": row[11],
        }

        campaign = {
            "id": str(row[12]),
            "name": row[13],
            "job_title": row[14],
            "job_description": row[15],
            "language": row[16],
            "max_recording_seconds": row[17],
            "allow_retakes": row[18],
            "company_name": row[19],
            "hr_email": row[20],
        }

        # Check if link has expired
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        expires_at = row[7]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)

        if now > expires_at:
            return jsonify({
                "error": "invitation_expired",
                "message": "This interview link has expired",
                "job_title": campaign["job_title"],
                "company_name": campaign["company_name"],
                "hr_email": campaign["hr_email"],
            }), 410  # 410 Gone

        # Check if already submitted
        if candidate["status"] == "submitted":
            return jsonify({
                "error": "already_submitted",
                "message": "You have already completed this interview",
                "submitted_at": str(candidate["invite_expires_at"]),
                "reference_id": candidate["reference_id"],
                "job_title": campaign["job_title"],
                "company_name": campaign["company_name"],
            }), 409  # 409 Conflict

        g.candidate = candidate
        g.campaign = campaign
        return f(*args, **kwargs)

    return decorated


# ──────────────────────────────────────────────────────────────
# CSRF Protection — Double Submit Cookie Pattern
# ──────────────────────────────────────────────────────────────

def require_csrf(f):
    """
    Decorator: Validates XSRF-TOKEN cookie matches X-XSRF-Token header.
    Apply to all state-changing endpoints that use cookie auth.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        cookie_token = request.cookies.get("XSRF-TOKEN")
        header_token = request.headers.get("X-XSRF-Token")

        if not cookie_token or not header_token:
            return jsonify({"error": "CSRF token missing"}), 403

        import hmac
        if not hmac.compare_digest(cookie_token, header_token):
            return jsonify({"error": "CSRF token mismatch"}), 403

        return f(*args, **kwargs)

    return decorated
