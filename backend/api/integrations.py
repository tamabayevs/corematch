"""
CoreMatch — ATS Integrations Blueprint
Greenhouse and Lever API connector configuration and sync management.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
integrations_bp = Blueprint("integrations", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/integrations — list configured integrations
# ──────────────────────────────────────────────────────────────

@integrations_bp.route("", methods=["GET"])
@require_auth
def list_integrations():
    """List all ATS integrations for the current user."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, provider, is_active, sync_direction,
                           last_synced_at, settings, created_at, updated_at
                    FROM ats_integrations
                    WHERE user_id = %s
                    ORDER BY provider ASC
                    """,
                    (g.current_user["id"],),
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("List integrations error: %s", str(e))
        return jsonify({"error": "Failed to fetch integrations"}), 500

    return jsonify({
        "integrations": [
            {
                "id": str(r[0]),
                "provider": r[1],
                "is_active": r[2],
                "sync_direction": r[3],
                "last_synced_at": r[4].isoformat() if r[4] else None,
                "settings": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
                "updated_at": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ],
        "available_providers": [
            {
                "id": "greenhouse",
                "name": "Greenhouse",
                "description": "Sync candidates and jobs with Greenhouse ATS",
                "features": ["Import jobs", "Export candidates", "Sync decisions"],
            },
            {
                "id": "lever",
                "name": "Lever",
                "description": "Connect with Lever for seamless candidate management",
                "features": ["Import opportunities", "Export candidates", "Sync feedback"],
            },
        ],
    })


# ──────────────────────────────────────────────────────────────
# POST /api/integrations — configure a new integration
# ──────────────────────────────────────────────────────────────

@integrations_bp.route("", methods=["POST"])
@require_auth
def create_integration():
    """Configure a new ATS integration."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    provider = data.get("provider", "").strip()
    api_key = data.get("api_key", "").strip()
    webhook_url = (data.get("webhook_url") or "").strip() or None
    sync_direction = data.get("sync_direction", "export")
    settings = data.get("settings", {})

    if provider not in ("greenhouse", "lever", "other"):
        return jsonify({"error": "Invalid provider. Must be greenhouse, lever, or other"}), 400
    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    if sync_direction not in ("import", "export", "bidirectional"):
        return jsonify({"error": "Invalid sync direction"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Upsert — one integration per provider per user
                cur.execute(
                    """
                    INSERT INTO ats_integrations
                    (user_id, provider, api_key_encrypted, webhook_url, is_active, sync_direction, settings)
                    VALUES (%s, %s, %s, %s, TRUE, %s, %s::jsonb)
                    ON CONFLICT (user_id, provider) DO UPDATE SET
                        api_key_encrypted = EXCLUDED.api_key_encrypted,
                        webhook_url = EXCLUDED.webhook_url,
                        is_active = TRUE,
                        sync_direction = EXCLUDED.sync_direction,
                        settings = EXCLUDED.settings,
                        updated_at = NOW()
                    RETURNING id, created_at
                    """,
                    (
                        g.current_user["id"], provider, api_key,
                        webhook_url, sync_direction, json.dumps(settings),
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
                        g.current_user["id"], "integration.configured", "ats_integration",
                        str(row[0]), json.dumps({"provider": provider}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Create integration error: %s", str(e))
        return jsonify({"error": "Failed to configure integration"}), 500

    return jsonify({
        "message": f"{provider.capitalize()} integration configured",
        "integration": {"id": str(row[0]), "provider": provider},
    }), 201


# ──────────────────────────────────────────────────────────────
# PUT /api/integrations/:id — update integration settings
# ──────────────────────────────────────────────────────────────

@integrations_bp.route("/<integration_id>", methods=["PUT"])
@require_auth
def update_integration(integration_id):
    """Update integration settings (toggle active, change sync direction, etc)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                updates = {}
                if "is_active" in data:
                    updates["is_active"] = bool(data["is_active"])
                if "sync_direction" in data:
                    if data["sync_direction"] in ("import", "export", "bidirectional"):
                        updates["sync_direction"] = data["sync_direction"]
                if "webhook_url" in data:
                    updates["webhook_url"] = (data["webhook_url"] or "").strip() or None
                if "settings" in data:
                    updates["settings"] = json.dumps(data["settings"])
                if "api_key" in data and data["api_key"].strip():
                    updates["api_key_encrypted"] = data["api_key"].strip()

                if not updates:
                    return jsonify({"error": "No fields to update"}), 400

                set_parts = []
                values = []
                for k, v in updates.items():
                    if k == "settings":
                        set_parts.append(f"{k} = %s::jsonb")
                    else:
                        set_parts.append(f"{k} = %s")
                    values.append(v)

                values.extend([integration_id, g.current_user["id"]])
                cur.execute(
                    f"UPDATE ats_integrations SET {', '.join(set_parts)} WHERE id = %s AND user_id = %s",
                    values,
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "Integration not found"}), 404
    except Exception as e:
        logger.error("Update integration error: %s", str(e))
        return jsonify({"error": "Failed to update integration"}), 500

    return jsonify({"message": "Integration updated"})


# ──────────────────────────────────────────────────────────────
# DELETE /api/integrations/:id — remove integration
# ──────────────────────────────────────────────────────────────

@integrations_bp.route("/<integration_id>", methods=["DELETE"])
@require_auth
def delete_integration(integration_id):
    """Remove an ATS integration."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM ats_integrations WHERE id = %s AND user_id = %s",
                    (integration_id, g.current_user["id"]),
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "Integration not found"}), 404

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "integration.removed", "ats_integration",
                        integration_id, json.dumps({}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Delete integration error: %s", str(e))
        return jsonify({"error": "Failed to remove integration"}), 500

    return jsonify({"message": "Integration removed"})


# ──────────────────────────────────────────────────────────────
# POST /api/integrations/:id/test — test integration connection
# ──────────────────────────────────────────────────────────────

@integrations_bp.route("/<integration_id>/test", methods=["POST"])
@require_auth
def test_integration(integration_id):
    """Test the connection to the ATS provider (simulated for now)."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT provider, api_key_encrypted, is_active FROM ats_integrations WHERE id = %s AND user_id = %s",
                    (integration_id, g.current_user["id"]),
                )
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Integration not found"}), 404

                provider = row[0]
                has_key = bool(row[1])
                is_active = row[2]

    except Exception as e:
        logger.error("Test integration error: %s", str(e))
        return jsonify({"error": "Failed to test integration"}), 500

    # Simulated connection test (real implementation would call the ATS API)
    if not has_key:
        return jsonify({
            "success": False,
            "message": "No API key configured",
            "provider": provider,
        })

    if not is_active:
        return jsonify({
            "success": False,
            "message": "Integration is inactive",
            "provider": provider,
        })

    return jsonify({
        "success": True,
        "message": f"Successfully connected to {provider.capitalize()}",
        "provider": provider,
    })


# ──────────────────────────────────────────────────────────────
# POST /api/integrations/:id/sync — trigger manual sync
# ──────────────────────────────────────────────────────────────

@integrations_bp.route("/<integration_id>/sync", methods=["POST"])
@require_auth
def trigger_sync(integration_id):
    """Trigger a manual sync with the ATS provider (placeholder for background job)."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT provider, is_active FROM ats_integrations WHERE id = %s AND user_id = %s",
                    (integration_id, g.current_user["id"]),
                )
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Integration not found"}), 404
                if not row[1]:
                    return jsonify({"error": "Integration is not active"}), 400

                # Update last_synced_at
                cur.execute(
                    "UPDATE ats_integrations SET last_synced_at = NOW() WHERE id = %s",
                    (integration_id,),
                )

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "integration.sync_triggered", "ats_integration",
                        integration_id, json.dumps({"provider": row[0]}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Trigger sync error: %s", str(e))
        return jsonify({"error": "Failed to trigger sync"}), 500

    return jsonify({
        "message": f"Sync triggered for {row[0].capitalize()}",
        "provider": row[0],
    })
