"""
CoreMatch — Campaign Templates Blueprint
CRUD for reusable interview templates. All endpoints require JWT auth.
System templates are read-only and available to all users.
"""
import uuid
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
templates_bp = Blueprint("templates", __name__)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _format_template(row) -> dict:
    """Format a DB row into a template dict."""
    return {
        "id": str(row[0]),
        "user_id": str(row[1]) if row[1] else None,
        "name": row[2],
        "description": row[3],
        "questions": row[4],
        "language": row[5],
        "invite_expiry_days": row[6],
        "allow_retakes": row[7],
        "max_recording_seconds": row[8],
        "is_system": row[9],
        "created_at": row[10].isoformat() if row[10] else None,
        "updated_at": row[11].isoformat() if row[11] else None,
    }


TEMPLATE_SELECT_COLS = """
    id, user_id, name, description, questions, language,
    invite_expiry_days, allow_retakes, max_recording_seconds,
    is_system, created_at, updated_at
"""


# ──────────────────────────────────────────────────────────────
# GET /api/templates
# List all templates (user's own + system templates)
# ──────────────────────────────────────────────────────────────

@templates_bp.route("/templates", methods=["GET"])
@require_auth
def list_templates():
    """
    List all templates available to the current user.
    Includes system templates and the user's own custom templates.
    Optional query param: is_system=true|false to filter.
    """
    is_system_filter = request.args.get("is_system")

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                if is_system_filter == "true":
                    cur.execute(
                        f"""
                        SELECT {TEMPLATE_SELECT_COLS}
                        FROM campaign_templates
                        WHERE is_system = TRUE
                        ORDER BY created_at ASC
                        """,
                    )
                elif is_system_filter == "false":
                    cur.execute(
                        f"""
                        SELECT {TEMPLATE_SELECT_COLS}
                        FROM campaign_templates
                        WHERE user_id = %s AND is_system = FALSE
                        ORDER BY created_at DESC
                        """,
                        (g.current_user["id"],),
                    )
                else:
                    cur.execute(
                        f"""
                        SELECT {TEMPLATE_SELECT_COLS}
                        FROM campaign_templates
                        WHERE is_system = TRUE OR user_id = %s
                        ORDER BY is_system DESC, created_at DESC
                        """,
                        (g.current_user["id"],),
                    )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("List templates error: %s", str(e))
        return jsonify({"error": "Failed to fetch templates"}), 500

    return jsonify({"templates": [_format_template(row) for row in rows]})


# ──────────────────────────────────────────────────────────────
# POST /api/templates
# Create a custom template
# ──────────────────────────────────────────────────────────────

@templates_bp.route("/templates", methods=["POST"])
@require_auth
def create_template():
    """Create a new custom campaign template."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Template name is required"}), 400

    questions = data.get("questions", [])
    if not isinstance(questions, list):
        return jsonify({"error": "questions must be an array"}), 400

    # Normalize questions — assign IDs if missing
    normalized = []
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            return jsonify({"error": f"Question {i+1} must be an object"}), 400
        if not (q.get("text") or "").strip():
            return jsonify({"error": f"Question {i+1} text is required"}), 400
        normalized.append({
            "id": q.get("id") or str(uuid.uuid4()),
            "text": q["text"].strip(),
            "think_time_seconds": int(q.get("think_time_seconds", 30)),
        })

    description = (data.get("description") or "").strip() or None
    language = data.get("language", "en")
    if language not in ("en", "ar", "both"):
        return jsonify({"error": "language must be 'en', 'ar', or 'both'"}), 400

    invite_expiry_days = int(data.get("invite_expiry_days", 7))
    allow_retakes = bool(data.get("allow_retakes", True))
    max_recording_seconds = int(data.get("max_recording_seconds", 120))

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO campaign_templates
                    (user_id, name, description, questions, language,
                     invite_expiry_days, allow_retakes, max_recording_seconds, is_system)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s, FALSE)
                    RETURNING {TEMPLATE_SELECT_COLS}
                    """,
                    (
                        g.current_user["id"], name, description,
                        json.dumps(normalized), language,
                        invite_expiry_days, allow_retakes, max_recording_seconds,
                    ),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Create template DB error: %s", str(e))
        return jsonify({"error": "Failed to create template"}), 500

    return jsonify({"template": _format_template(row)}), 201


# ──────────────────────────────────────────────────────────────
# PUT /api/templates/:id
# Update a custom template (not system templates)
# ──────────────────────────────────────────────────────────────

@templates_bp.route("/templates/<template_id>", methods=["PUT"])
@require_auth
def update_template(template_id):
    """Update a custom template. System templates cannot be modified."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Verify ownership and that it's not a system template
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, is_system, user_id FROM campaign_templates WHERE id = %s",
                    (template_id,),
                )
                existing = cur.fetchone()
    except Exception as e:
        logger.error("Update template check error: %s", str(e))
        return jsonify({"error": "Failed to verify template"}), 500

    if not existing:
        return jsonify({"error": "Template not found"}), 404

    if existing[1]:  # is_system
        return jsonify({"error": "System templates cannot be modified"}), 403

    if str(existing[2]) != g.current_user["id"]:
        return jsonify({"error": "Template not found"}), 404

    # Build update fields
    updates = {}
    errors = []

    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            errors.append("Template name cannot be empty")
        else:
            updates["name"] = name

    if "description" in data:
        updates["description"] = (data["description"] or "").strip() or None

    if "questions" in data:
        questions = data["questions"]
        if not isinstance(questions, list):
            errors.append("questions must be an array")
        else:
            normalized = []
            for i, q in enumerate(questions):
                if not isinstance(q, dict):
                    errors.append(f"Question {i+1} must be an object")
                    continue
                if not (q.get("text") or "").strip():
                    errors.append(f"Question {i+1} text is required")
                    continue
                normalized.append({
                    "id": q.get("id") or str(uuid.uuid4()),
                    "text": q["text"].strip(),
                    "think_time_seconds": int(q.get("think_time_seconds", 30)),
                })
            if not errors:
                updates["questions"] = json.dumps(normalized)

    if "language" in data:
        if data["language"] not in ("en", "ar", "both"):
            errors.append("language must be 'en', 'ar', or 'both'")
        else:
            updates["language"] = data["language"]

    if "invite_expiry_days" in data:
        updates["invite_expiry_days"] = int(data["invite_expiry_days"])

    if "allow_retakes" in data:
        updates["allow_retakes"] = bool(data["allow_retakes"])

    if "max_recording_seconds" in data:
        updates["max_recording_seconds"] = int(data["max_recording_seconds"])

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    # Build dynamic UPDATE
    set_parts = []
    values = []
    for k, v in updates.items():
        if k == "questions":
            set_parts.append(f"{k} = %s::jsonb")
        else:
            set_parts.append(f"{k} = %s")
        values.append(v)

    values.append(template_id)
    values.append(g.current_user["id"])

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE campaign_templates SET {", ".join(set_parts)}
                    WHERE id = %s AND user_id = %s AND is_system = FALSE
                    RETURNING {TEMPLATE_SELECT_COLS}
                    """,
                    values,
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Update template DB error: %s", str(e))
        return jsonify({"error": "Failed to update template"}), 500

    if not row:
        return jsonify({"error": "Template not found"}), 404

    return jsonify({"template": _format_template(row)})


# ──────────────────────────────────────────────────────────────
# DELETE /api/templates/:id
# Delete a custom template (not system templates)
# ──────────────────────────────────────────────────────────────

@templates_bp.route("/templates/<template_id>", methods=["DELETE"])
@require_auth
def delete_template(template_id):
    """Delete a custom template. System templates cannot be deleted."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Check existence and ownership first
                cur.execute(
                    "SELECT id, is_system, user_id FROM campaign_templates WHERE id = %s",
                    (template_id,),
                )
                existing = cur.fetchone()

                if not existing:
                    return jsonify({"error": "Template not found"}), 404

                if existing[1]:  # is_system
                    return jsonify({"error": "System templates cannot be deleted"}), 403

                if str(existing[2]) != g.current_user["id"]:
                    return jsonify({"error": "Template not found"}), 404

                cur.execute(
                    "DELETE FROM campaign_templates WHERE id = %s AND user_id = %s AND is_system = FALSE",
                    (template_id, g.current_user["id"]),
                )
                deleted = cur.rowcount
    except Exception as e:
        logger.error("Delete template DB error: %s", str(e))
        return jsonify({"error": "Failed to delete template"}), 500

    if deleted == 0:
        return jsonify({"error": "Template not found"}), 404

    return jsonify({"message": "Template deleted"})


# ──────────────────────────────────────────────────────────────
# POST /api/campaigns/:campaign_id/save-as-template
# Save an existing campaign as a reusable template
# ──────────────────────────────────────────────────────────────

@templates_bp.route("/campaigns/<campaign_id>/save-as-template", methods=["POST"])
@require_auth
def save_campaign_as_template(campaign_id):
    """
    Create a template from an existing campaign.
    Copies questions, language, expiry, retakes, and recording settings.
    """
    data = request.get_json(silent=True) or {}

    # Verify campaign ownership
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT name, job_title, job_description, language, questions,
                           invite_expiry_days, allow_retakes, max_recording_seconds
                    FROM campaigns
                    WHERE id = %s AND user_id = %s
                    """,
                    (campaign_id, g.current_user["id"]),
                )
                campaign = cur.fetchone()
    except Exception as e:
        logger.error("Save-as-template campaign lookup error: %s", str(e))
        return jsonify({"error": "Failed to verify campaign"}), 500

    if not campaign:
        return jsonify({"error": "Campaign not found"}), 404

    # Allow overriding the template name; default to campaign name
    template_name = (data.get("name") or "").strip() or f"Template from: {campaign[0]}"
    description = (data.get("description") or "").strip() or f"Created from campaign '{campaign[0]}' ({campaign[1]})"

    questions = campaign[4]
    if isinstance(questions, str):
        questions = json.loads(questions)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO campaign_templates
                    (user_id, name, description, questions, language,
                     invite_expiry_days, allow_retakes, max_recording_seconds, is_system)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s, FALSE)
                    RETURNING {TEMPLATE_SELECT_COLS}
                    """,
                    (
                        g.current_user["id"], template_name, description,
                        json.dumps(questions), campaign[3],
                        campaign[5], campaign[6], campaign[7],
                    ),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Save-as-template DB error: %s", str(e))
        return jsonify({"error": "Failed to create template from campaign"}), 500

    return jsonify({
        "message": "Template created from campaign",
        "template": _format_template(row),
    }), 201
