"""
CoreMatch — Branding Blueprint
Company branding settings for candidate-facing interview pages.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
branding_bp = Blueprint("branding", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/branding — get company branding settings
# ──────────────────────────────────────────────────────────────

@branding_bp.route("", methods=["GET"])
@require_auth
def get_branding():
    """Get branding settings for the current user's company."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, company_name, logo_url, primary_color,
                           secondary_color, company_website, custom_welcome_message,
                           created_at, updated_at
                    FROM company_branding
                    WHERE user_id = %s
                    """,
                    (g.current_user["id"],),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Get branding error: %s", str(e))
        return jsonify({"error": "Failed to fetch branding settings"}), 500

    if not row:
        # Return defaults
        return jsonify({
            "branding": {
                "id": None,
                "company_name": g.current_user.get("company_name"),
                "logo_url": None,
                "primary_color": "#2563EB",
                "secondary_color": "#1E40AF",
                "company_website": None,
                "custom_welcome_message": None,
            }
        })

    return jsonify({
        "branding": {
            "id": str(row[0]),
            "user_id": str(row[1]),
            "company_name": row[2],
            "logo_url": row[3],
            "primary_color": row[4],
            "secondary_color": row[5],
            "company_website": row[6],
            "custom_welcome_message": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None,
        }
    })


# ──────────────────────────────────────────────────────────────
# PUT /api/branding — update branding
# ──────────────────────────────────────────────────────────────

@branding_bp.route("", methods=["PUT"])
@require_auth
def update_branding():
    """
    Update company branding settings.
    Upserts: creates if not exists, updates if exists.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    company_name = (data.get("company_name") or "").strip() or g.current_user.get("company_name")
    logo_url = (data.get("logo_url") or "").strip() or None
    primary_color = (data.get("primary_color") or "").strip() or "#2563EB"
    secondary_color = (data.get("secondary_color") or "").strip() or "#1E40AF"
    company_website = (data.get("company_website") or "").strip() or None
    custom_welcome_message = (data.get("custom_welcome_message") or "").strip() or None

    # Validate color format (basic hex check)
    import re
    hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
    if not hex_pattern.match(primary_color):
        return jsonify({"error": "primary_color must be a valid hex color (e.g., #2563EB)"}), 400
    if not hex_pattern.match(secondary_color):
        return jsonify({"error": "secondary_color must be a valid hex color (e.g., #1E40AF)"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO company_branding
                    (user_id, company_name, logo_url, primary_color, secondary_color,
                     company_website, custom_welcome_message)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        logo_url = EXCLUDED.logo_url,
                        primary_color = EXCLUDED.primary_color,
                        secondary_color = EXCLUDED.secondary_color,
                        company_website = EXCLUDED.company_website,
                        custom_welcome_message = EXCLUDED.custom_welcome_message,
                        updated_at = NOW()
                    RETURNING id
                    """,
                    (
                        g.current_user["id"], company_name, logo_url,
                        primary_color, secondary_color, company_website,
                        custom_welcome_message,
                    ),
                )
                row = cur.fetchone()

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "branding.updated", "company_branding",
                        str(row[0]),
                        json.dumps({"primary_color": primary_color, "secondary_color": secondary_color}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Update branding error: %s", str(e))
        return jsonify({"error": "Failed to update branding"}), 500

    return jsonify({"message": "Branding updated"})


# ──────────────────────────────────────────────────────────────
# GET /api/public/branding/:campaign_id — public endpoint (no auth)
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
# POST /api/branding/logo — upload company logo
# ──────────────────────────────────────────────────────────────

@branding_bp.route("/logo", methods=["POST"])
@require_auth
def upload_logo():
    """
    Upload a company logo image file.
    Accepts PNG, JPEG, SVG. Max 2MB.
    Stores via storage service and updates company_branding.logo_url.
    """
    import uuid as uuid_mod

    if "logo" not in request.files:
        return jsonify({"error": "Logo file is required"}), 400

    file = request.files["logo"]
    content_type = file.content_type or ""

    allowed_types = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/svg+xml": "svg",
    }
    if content_type not in allowed_types:
        return jsonify({"error": "Invalid file type. Only PNG, JPEG, and SVG are accepted"}), 400

    file_data = file.read()
    max_size = 2 * 1024 * 1024  # 2MB
    if len(file_data) > max_size:
        return jsonify({"error": "File too large. Maximum size is 2MB"}), 413
    if len(file_data) == 0:
        return jsonify({"error": "File is empty"}), 400

    ext = allowed_types[content_type]
    storage_key = f"logos/{g.current_user['id']}/{uuid_mod.uuid4()}.{ext}"

    try:
        import io
        from services.storage_service import get_storage_service
        storage = get_storage_service()
        file_obj = io.BytesIO(file_data)
        logo_url = storage.upload_file(file_obj, storage_key, content_type=content_type)
    except Exception as e:
        logger.error("Logo upload storage error: %s", str(e))
        return jsonify({"error": "Failed to store logo"}), 500

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO company_branding (user_id, logo_url)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET logo_url = EXCLUDED.logo_url, updated_at = NOW()
                    """,
                    (g.current_user["id"], logo_url),
                )

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "branding.logo_uploaded", "company_branding",
                        None, json.dumps({"storage_key": storage_key}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Logo upload DB error: %s", str(e))
        return jsonify({"error": "Failed to save logo URL"}), 500

    return jsonify({"message": "Logo uploaded", "logo_url": logo_url}), 201


# ──────────────────────────────────────────────────────────────
# DELETE /api/branding/logo — remove company logo
# ──────────────────────────────────────────────────────────────

@branding_bp.route("/logo", methods=["DELETE"])
@require_auth
def delete_logo():
    """Remove the company logo."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE company_branding SET logo_url = NULL, updated_at = NOW() WHERE user_id = %s",
                    (g.current_user["id"],),
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "No branding found"}), 404

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "branding.logo_removed", "company_branding",
                        None, json.dumps({}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Delete logo error: %s", str(e))
        return jsonify({"error": "Failed to remove logo"}), 500

    return jsonify({"message": "Logo removed"})


# ──────────────────────────────────────────────────────────────
# GET /api/public/branding/:campaign_id — public endpoint (no auth)
# ──────────────────────────────────────────────────────────────

@branding_bp.route("/public/<campaign_id>", methods=["GET"])
def get_public_branding(campaign_id):
    """
    Public endpoint: get branding for candidate-facing pages.
    No authentication required. Returns only safe public fields.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT cb.company_name, cb.logo_url, cb.primary_color,
                           cb.secondary_color, cb.company_website, cb.custom_welcome_message
                    FROM company_branding cb
                    JOIN campaigns camp ON camp.user_id = cb.user_id
                    WHERE camp.id = %s
                    """,
                    (campaign_id,),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Get public branding error: %s", str(e))
        return jsonify({"error": "Failed to fetch branding"}), 500

    if not row:
        # Return defaults if no branding configured
        return jsonify({
            "branding": {
                "company_name": None,
                "logo_url": None,
                "primary_color": "#2563EB",
                "secondary_color": "#1E40AF",
                "company_website": None,
                "custom_welcome_message": None,
            }
        })

    return jsonify({
        "branding": {
            "company_name": row[0],
            "logo_url": row[1],
            "primary_color": row[2],
            "secondary_color": row[3],
            "company_website": row[4],
            "custom_welcome_message": row[5],
        }
    })
