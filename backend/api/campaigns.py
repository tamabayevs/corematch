"""
CoreMatch — Campaigns Blueprint
CRUD for HR interview campaigns. All endpoints require JWT auth.
"""
import uuid
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
campaigns_bp = Blueprint("campaigns", __name__)

# ──────────────────────────────────────────────────────────────
# Validation helpers
# ──────────────────────────────────────────────────────────────

MIN_QUESTIONS = 3
MAX_QUESTIONS = 7
MIN_RECORDING_SECONDS = 60
MAX_RECORDING_SECONDS = 180
VALID_EXPIRY_DAYS = (7, 14, 30)
VALID_LANGUAGES = ("en", "ar", "both")


def _validate_questions(questions: list) -> list[str]:
    """Validate question list. Returns list of error strings."""
    errors = []
    if not isinstance(questions, list):
        errors.append("questions must be an array")
        return errors
    if len(questions) < MIN_QUESTIONS:
        errors.append(f"Minimum {MIN_QUESTIONS} questions required")
    if len(questions) > MAX_QUESTIONS:
        errors.append(f"Maximum {MAX_QUESTIONS} questions allowed")
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            errors.append(f"Question {i+1} must be an object")
            continue
        if not q.get("text", "").strip():
            errors.append(f"Question {i+1} text is required")
        think_time = q.get("think_time_seconds", 30)
        if not isinstance(think_time, int) or not (0 <= think_time <= 120):
            errors.append(f"Question {i+1} think_time_seconds must be 0-120")
    return errors


def _normalize_question(q: dict, index: int) -> dict:
    """Normalize a question object, adding defaults and a stable ID."""
    return {
        "id": q.get("id") or str(uuid.uuid4()),
        "text": q.get("text", "").strip(),
        "think_time_seconds": int(q.get("think_time_seconds", 30)),
    }


def _format_campaign(row) -> dict:
    """Format a DB row into a campaign dict."""
    return {
        "id": str(row[0]),
        "name": row[1],
        "job_title": row[2],
        "job_description": row[3],
        "language": row[4],
        "questions": row[5],
        "invite_expiry_days": row[6],
        "allow_retakes": row[7],
        "max_recording_seconds": row[8],
        "status": row[9],
        "created_at": row[10].isoformat() if row[10] else None,
        "updated_at": row[11].isoformat() if row[11] else None,
        "candidate_count": row[12] if len(row) > 12 else None,
        "submitted_count": row[13] if len(row) > 13 else None,
    }


# ──────────────────────────────────────────────────────────────
# GET /api/campaigns
# ──────────────────────────────────────────────────────────────

@campaigns_bp.route("", methods=["GET"])
@require_auth
def list_campaigns():
    """List all campaigns for the current HR user."""
    status_filter = request.args.get("status")  # optional: 'active' | 'closed' | 'archived'

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                if status_filter and status_filter in ("active", "closed", "archived"):
                    cur.execute(
                        """
                        SELECT c.id, c.name, c.job_title, c.job_description, c.language,
                               c.questions, c.invite_expiry_days, c.allow_retakes,
                               c.max_recording_seconds, c.status, c.created_at, c.updated_at,
                               COUNT(cand.id) as candidate_count,
                               COUNT(cand.id) FILTER (WHERE cand.status = 'submitted') as submitted_count
                        FROM campaigns c
                        LEFT JOIN candidates cand ON cand.campaign_id = c.id
                        WHERE c.user_id = %s AND c.status = %s
                        GROUP BY c.id
                        ORDER BY c.created_at DESC
                        """,
                        (g.current_user["id"], status_filter),
                    )
                else:
                    cur.execute(
                        """
                        SELECT c.id, c.name, c.job_title, c.job_description, c.language,
                               c.questions, c.invite_expiry_days, c.allow_retakes,
                               c.max_recording_seconds, c.status, c.created_at, c.updated_at,
                               COUNT(cand.id) as candidate_count,
                               COUNT(cand.id) FILTER (WHERE cand.status = 'submitted') as submitted_count
                        FROM campaigns c
                        LEFT JOIN candidates cand ON cand.campaign_id = c.id
                        WHERE c.user_id = %s AND c.status != 'archived'
                        GROUP BY c.id
                        ORDER BY c.created_at DESC
                        """,
                        (g.current_user["id"],),
                    )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("List campaigns error: %s", str(e))
        return jsonify({"error": "Failed to fetch campaigns"}), 500

    return jsonify({"campaigns": [_format_campaign(row) for row in rows]})


# ──────────────────────────────────────────────────────────────
# POST /api/campaigns
# ──────────────────────────────────────────────────────────────

@campaigns_bp.route("", methods=["POST"])
@require_auth
def create_campaign():
    """Create a new interview campaign."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Required fields
    name = data.get("name", "").strip()
    job_title = data.get("job_title", "").strip()
    questions_raw = data.get("questions", [])

    if not name:
        return jsonify({"error": "Campaign name is required"}), 400
    if not job_title:
        return jsonify({"error": "Job title is required"}), 400

    # Validate questions
    q_errors = _validate_questions(questions_raw)
    if q_errors:
        return jsonify({"error": "Invalid questions", "details": q_errors}), 400

    questions = [_normalize_question(q, i) for i, q in enumerate(questions_raw)]

    # Optional fields with defaults
    language = data.get("language", "en")
    if language not in VALID_LANGUAGES:
        return jsonify({"error": f"language must be one of {VALID_LANGUAGES}"}), 400

    invite_expiry_days = int(data.get("invite_expiry_days", 7))
    if invite_expiry_days not in VALID_EXPIRY_DAYS:
        return jsonify({"error": f"invite_expiry_days must be one of {VALID_EXPIRY_DAYS}"}), 400

    allow_retakes = bool(data.get("allow_retakes", True))
    max_recording_seconds = int(data.get("max_recording_seconds", 120))
    if not (MIN_RECORDING_SECONDS <= max_recording_seconds <= MAX_RECORDING_SECONDS):
        return jsonify({"error": f"max_recording_seconds must be {MIN_RECORDING_SECONDS}-{MAX_RECORDING_SECONDS}"}), 400

    job_description = data.get("job_description", "").strip() or None

    import json
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO campaigns
                    (user_id, name, job_title, job_description, language, questions,
                     invite_expiry_days, allow_retakes, max_recording_seconds)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                    RETURNING id, name, job_title, job_description, language, questions,
                              invite_expiry_days, allow_retakes, max_recording_seconds,
                              status, created_at, updated_at
                    """,
                    (
                        g.current_user["id"], name, job_title, job_description,
                        language, json.dumps(questions),
                        invite_expiry_days, allow_retakes, max_recording_seconds,
                    ),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Create campaign DB error: %s", str(e))
        return jsonify({"error": "Failed to create campaign"}), 500

    return jsonify({"campaign": _format_campaign(row)}), 201


# ──────────────────────────────────────────────────────────────
# GET /api/campaigns/:id
# ──────────────────────────────────────────────────────────────

@campaigns_bp.route("/<campaign_id>", methods=["GET"])
@require_auth
def get_campaign(campaign_id):
    """Get a single campaign. Only accessible by the campaign owner."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.id, c.name, c.job_title, c.job_description, c.language,
                           c.questions, c.invite_expiry_days, c.allow_retakes,
                           c.max_recording_seconds, c.status, c.created_at, c.updated_at,
                           COUNT(cand.id) as candidate_count,
                           COUNT(cand.id) FILTER (WHERE cand.status = 'submitted') as submitted_count
                    FROM campaigns c
                    LEFT JOIN candidates cand ON cand.campaign_id = c.id
                    WHERE c.id = %s AND c.user_id = %s
                    GROUP BY c.id
                    """,
                    (campaign_id, g.current_user["id"]),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Get campaign DB error: %s", str(e))
        return jsonify({"error": "Failed to fetch campaign"}), 500

    if not row:
        return jsonify({"error": "Campaign not found"}), 404

    return jsonify({"campaign": _format_campaign(row)})


# ──────────────────────────────────────────────────────────────
# PUT /api/campaigns/:id
# ──────────────────────────────────────────────────────────────

@campaigns_bp.route("/<campaign_id>", methods=["PUT"])
@require_auth
def update_campaign(campaign_id):
    """
    Update an existing campaign.
    NOTE: Question changes only affect NEW invitations.
    Existing invitations keep their questions_snapshot.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Verify ownership and current state
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, status FROM campaigns WHERE id = %s AND user_id = %s",
                    (campaign_id, g.current_user["id"]),
                )
                existing = cur.fetchone()
    except Exception as e:
        logger.error("Update campaign check error: %s", str(e))
        return jsonify({"error": "Failed to verify campaign"}), 500

    if not existing:
        return jsonify({"error": "Campaign not found"}), 404

    import json
    updates = {}
    errors = []

    if "name" in data:
        name = data["name"].strip()
        if not name:
            errors.append("Campaign name cannot be empty")
        else:
            updates["name"] = name

    if "job_title" in data:
        jt = data["job_title"].strip()
        if not jt:
            errors.append("Job title cannot be empty")
        else:
            updates["job_title"] = jt

    if "job_description" in data:
        updates["job_description"] = data["job_description"].strip() or None

    if "language" in data:
        if data["language"] not in VALID_LANGUAGES:
            errors.append(f"language must be one of {VALID_LANGUAGES}")
        else:
            updates["language"] = data["language"]

    if "questions" in data:
        q_errors = _validate_questions(data["questions"])
        if q_errors:
            errors.extend(q_errors)
        else:
            updates["questions"] = json.dumps(
                [_normalize_question(q, i) for i, q in enumerate(data["questions"])]
            )

    if "invite_expiry_days" in data:
        expiry = int(data["invite_expiry_days"])
        if expiry not in VALID_EXPIRY_DAYS:
            errors.append(f"invite_expiry_days must be one of {VALID_EXPIRY_DAYS}")
        else:
            updates["invite_expiry_days"] = expiry

    if "allow_retakes" in data:
        updates["allow_retakes"] = bool(data["allow_retakes"])

    if "max_recording_seconds" in data:
        mrs = int(data["max_recording_seconds"])
        if not (MIN_RECORDING_SECONDS <= mrs <= MAX_RECORDING_SECONDS):
            errors.append(f"max_recording_seconds must be {MIN_RECORDING_SECONDS}-{MAX_RECORDING_SECONDS}")
        else:
            updates["max_recording_seconds"] = mrs

    if "status" in data:
        if data["status"] not in ("active", "closed", "archived"):
            errors.append("status must be 'active', 'closed', or 'archived'")
        else:
            updates["status"] = data["status"]

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    # Handle JSONB field for questions
    set_parts = []
    values = []
    for k, v in updates.items():
        if k == "questions":
            set_parts.append(f"{k} = %s::jsonb")
        else:
            set_parts.append(f"{k} = %s")
        values.append(v)

    values.append(campaign_id)
    values.append(g.current_user["id"])

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE campaigns SET {", ".join(set_parts)}
                    WHERE id = %s AND user_id = %s
                    RETURNING id, name, job_title, job_description, language, questions,
                              invite_expiry_days, allow_retakes, max_recording_seconds,
                              status, created_at, updated_at
                    """,
                    values,
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Update campaign DB error: %s", str(e))
        return jsonify({"error": "Failed to update campaign"}), 500

    if not row:
        return jsonify({"error": "Campaign not found"}), 404

    return jsonify({
        "campaign": _format_campaign(row),
        "message": "Campaign updated. Note: question changes only apply to future invitations.",
    })


# ──────────────────────────────────────────────────────────────
# POST /api/campaigns/:id/invite
# Rate limit: 50/hour per user
# ──────────────────────────────────────────────────────────────

@campaigns_bp.route("/<campaign_id>/invite", methods=["POST"])
@require_auth
def invite_candidate(campaign_id):
    """
    Invite a candidate to a campaign.
    Creates a candidate record with a unique invite_token.
    Sends invitation email (and SMS if phone provided).
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Validate required fields
    full_name = data.get("full_name", "").strip()
    email_raw = data.get("email", "").strip().lower()

    if not full_name or not email_raw:
        return jsonify({"error": "full_name and email are required"}), 400

    # Validate email
    from email_validator import validate_email, EmailNotValidError
    try:
        valid = validate_email(email_raw)
        email = valid.email
    except EmailNotValidError:
        return jsonify({"error": "Invalid email address"}), 400

    phone = data.get("phone", "").strip() or None

    # Verify campaign ownership and that it's active
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, job_title, job_description, questions,
                           invite_expiry_days, language, max_recording_seconds, allow_retakes,
                           status
                    FROM campaigns
                    WHERE id = %s AND user_id = %s
                    """,
                    (campaign_id, g.current_user["id"]),
                )
                campaign = cur.fetchone()
    except Exception as e:
        logger.error("Invite candidate — campaign lookup error: %s", str(e))
        return jsonify({"error": "Failed to verify campaign"}), 500

    if not campaign:
        return jsonify({"error": "Campaign not found"}), 404

    if campaign[9] != "active":
        return jsonify({"error": "Cannot invite to a closed or archived campaign"}), 400

    # Check for duplicate invite in this campaign
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, status FROM candidates
                    WHERE campaign_id = %s AND email = %s
                    """,
                    (campaign_id, email),
                )
                existing = cur.fetchone()
    except Exception as e:
        logger.error("Invite candidate — duplicate check error: %s", str(e))
        return jsonify({"error": "Failed to check for existing invitation"}), 500

    if existing and existing[1] in ("invited", "started"):
        return jsonify({"error": "This candidate has already been invited to this campaign"}), 409

    import datetime
    import json

    invite_token = str(uuid.uuid4())
    invite_expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=campaign[5])

    # Snapshot the current questions at time of invitation
    questions_snapshot = campaign[4]  # Already JSONB from DB
    if isinstance(questions_snapshot, str):
        import json
        questions_snapshot = json.loads(questions_snapshot)

    # Generate reference ID
    year = datetime.datetime.utcnow().year
    import secrets
    suffix = secrets.randbelow(900000) + 100000
    reference_id = f"CM-{year}-{suffix}"

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO candidates
                    (campaign_id, email, full_name, phone, invite_token,
                     questions_snapshot, invite_expires_at, reference_id)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                    RETURNING id, email, full_name, invite_token, status, reference_id, created_at
                    """,
                    (
                        campaign_id, email, full_name, phone, invite_token,
                        json.dumps(questions_snapshot), invite_expires_at, reference_id,
                    ),
                )
                candidate = cur.fetchone()

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "candidate.invited", "candidate",
                        str(candidate[0]),
                        json.dumps({"campaign_id": campaign_id, "email": email}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Invite candidate — insert error: %s", str(e))
        return jsonify({"error": "Failed to create invitation"}), 500

    # Send invitation email
    import os
    from services.email_service import get_email_service
    from services.sms_service import get_sms_service

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    interview_url = f"{frontend_url}/interview/{invite_token}/welcome"
    short_link = f"{os.environ.get('BACKEND_URL', 'http://localhost:5000')}/s/{invite_token}"

    try:
        email_svc = get_email_service()
        email_svc.send_candidate_invitation(
            to_email=email,
            to_name=full_name,
            company_name=g.current_user.get("company_name", "the company"),
            job_title=campaign[2],
            interview_url=interview_url,
            expires_at=invite_expires_at,
            question_count=len(questions_snapshot),
        )
    except Exception as e:
        logger.error("Failed to send invitation email: %s", str(e))
        # Don't fail the whole request — candidate was created

    # Send SMS if phone provided and SMS is enabled
    if phone and os.environ.get("SMS_ENABLED", "false").lower() == "true":
        try:
            sms_svc = get_sms_service()
            sms_svc.send_candidate_invitation(
                to_phone=phone,
                company_name=g.current_user.get("company_name", "the company"),
                job_title=campaign[2],
                short_link=short_link,
            )
        except Exception as e:
            logger.error("Failed to send invitation SMS: %s", str(e))

    return jsonify({
        "message": "Invitation sent successfully",
        "candidate": {
            "id": str(candidate[0]),
            "email": candidate[1],
            "full_name": candidate[2],
            "invite_token": candidate[3],
            "status": candidate[4],
            "reference_id": candidate[5],
        },
    }), 201
