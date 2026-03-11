"""
CoreMatch — Notification Templates Blueprint
Customizable email/WhatsApp templates with variable placeholders.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
notification_templates_bp = Blueprint("notification_templates", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/notification-templates — list all templates
# ──────────────────────────────────────────────────────────────

@notification_templates_bp.route("", methods=["GET"])
@require_auth
def list_templates():
    """List notification templates (user's custom + system defaults)."""
    template_type = request.args.get("type")  # email, whatsapp, both

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                conditions = ["(user_id = %s OR is_system = TRUE)"]
                params = [g.current_user["id"]]

                if template_type and template_type in ("email", "whatsapp", "both"):
                    conditions.append("type = %s")
                    params.append(template_type)

                where_clause = " AND ".join(conditions)
                cur.execute(
                    f"""
                    SELECT id, user_id, name, type, subject, body, variables,
                           is_system, created_at, updated_at
                    FROM notification_templates
                    WHERE {where_clause}
                    ORDER BY is_system DESC, created_at DESC
                    """,
                    params,
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("List notification templates error: %s", str(e))
        return jsonify({"error": "Failed to fetch templates"}), 500

    return jsonify({
        "templates": [
            {
                "id": str(r[0]),
                "user_id": str(r[1]) if r[1] else None,
                "name": r[2],
                "type": r[3],
                "subject": r[4],
                "body": r[5],
                "variables": r[6],
                "is_system": r[7],
                "created_at": r[8].isoformat() if r[8] else None,
                "updated_at": r[9].isoformat() if r[9] else None,
            }
            for r in rows
        ]
    })


# ──────────────────────────────────────────────────────────────
# POST /api/notification-templates — create custom template
# ──────────────────────────────────────────────────────────────

@notification_templates_bp.route("", methods=["POST"])
@require_auth
def create_template():
    """Create a custom notification template."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    name = (data.get("name") or "").strip()
    template_type = data.get("type", "email")
    subject = (data.get("subject") or "").strip() or None
    body = (data.get("body") or "").strip()
    variables = data.get("variables", [])

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if not body:
        return jsonify({"error": "Body is required"}), 400
    if template_type not in ("email", "whatsapp", "both"):
        return jsonify({"error": "Type must be email, whatsapp, or both"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notification_templates (user_id, name, type, subject, body, variables)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    RETURNING id, created_at
                    """,
                    (g.current_user["id"], name, template_type, subject, body, json.dumps(variables)),
                )
                row = cur.fetchone()

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "notification_template.created", "notification_template",
                        str(row[0]), json.dumps({"name": name, "type": template_type}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Create notification template error: %s", str(e))
        return jsonify({"error": "Failed to create template"}), 500

    return jsonify({
        "message": "Template created",
        "template": {"id": str(row[0]), "name": name, "created_at": row[1].isoformat()},
    }), 201


# ──────────────────────────────────────────────────────────────
# PUT /api/notification-templates/:id — update custom template
# ──────────────────────────────────────────────────────────────

@notification_templates_bp.route("/<template_id>", methods=["PUT"])
@require_auth
def update_template(template_id):
    """Update a custom notification template (cannot edit system templates)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Check template exists and is not system
                cur.execute(
                    "SELECT id, is_system FROM notification_templates WHERE id = %s",
                    (template_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    return jsonify({"error": "Template not found"}), 404
                if existing[1]:
                    return jsonify({"error": "Cannot edit system templates"}), 403

                updates = {}
                if "name" in data:
                    updates["name"] = data["name"].strip()
                if "type" in data:
                    updates["type"] = data["type"]
                if "subject" in data:
                    updates["subject"] = data["subject"].strip() or None
                if "body" in data:
                    updates["body"] = data["body"].strip()
                if "variables" in data:
                    updates["variables"] = json.dumps(data["variables"])

                if not updates:
                    return jsonify({"error": "No fields to update"}), 400

                set_parts = []
                values = []
                for k, v in updates.items():
                    if k == "variables":
                        set_parts.append(f"{k} = %s::jsonb")
                    else:
                        set_parts.append(f"{k} = %s")
                    values.append(v)

                values.extend([template_id, g.current_user["id"]])
                cur.execute(
                    f"UPDATE notification_templates SET {', '.join(set_parts)} WHERE id = %s AND user_id = %s",
                    values,
                )
    except Exception as e:
        logger.error("Update notification template error: %s", str(e))
        return jsonify({"error": "Failed to update template"}), 500

    return jsonify({"message": "Template updated"})


# ──────────────────────────────────────────────────────────────
# DELETE /api/notification-templates/:id — delete custom template
# ──────────────────────────────────────────────────────────────

@notification_templates_bp.route("/<template_id>", methods=["DELETE"])
@require_auth
def delete_template(template_id):
    """Delete a custom notification template (cannot delete system templates)."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM notification_templates WHERE id = %s AND user_id = %s AND is_system = FALSE",
                    (template_id, g.current_user["id"]),
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "Template not found or cannot be deleted"}), 404
    except Exception as e:
        logger.error("Delete notification template error: %s", str(e))
        return jsonify({"error": "Failed to delete template"}), 500

    return jsonify({"message": "Template deleted"})


# ──────────────────────────────────────────────────────────────
# POST /api/notification-templates/:id/preview — preview with sample data
# ──────────────────────────────────────────────────────────────

@notification_templates_bp.route("/<template_id>/preview", methods=["POST"])
@require_auth
def preview_template(template_id):
    """Preview a template with sample variable values."""
    data = request.get_json(silent=True) or {}
    sample_values = data.get("values", {})

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT name, type, subject, body, variables
                    FROM notification_templates
                    WHERE id = %s AND (user_id = %s OR is_system = TRUE)
                    """,
                    (template_id, g.current_user["id"]),
                )
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Template not found"}), 404
    except Exception as e:
        logger.error("Preview template error: %s", str(e))
        return jsonify({"error": "Failed to preview template"}), 500

    # Replace variables with sample values or placeholders
    subject = row[2] or ""
    body = row[3] or ""

    default_values = {
        "candidate_name": "Ahmed Al-Rashid",
        "job_title": "Software Engineer",
        "company_name": "Acme Corp",
        "interview_link": "https://app.corematch.ai/interview/abc123/welcome",
        "expiry_date": "March 1, 2026",
        "sender_name": g.current_user.get("full_name", "HR Team"),
        "reference_id": "CM-ABC123",
    }

    # Merge defaults with provided values
    merged = {**default_values, **sample_values}

    for key, value in merged.items():
        subject = subject.replace("{{" + key + "}}", str(value))
        body = body.replace("{{" + key + "}}", str(value))

    return jsonify({
        "name": row[0],
        "type": row[1],
        "subject_preview": subject,
        "body_preview": body,
    })
