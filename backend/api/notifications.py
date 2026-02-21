"""
CoreMatch — Notifications Blueprint
In-app notification endpoints for HR users.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
notifications_bp = Blueprint("notifications", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/notifications — list notifications (paginated)
# ──────────────────────────────────────────────────────────────

@notifications_bp.route("", methods=["GET"])
@require_auth
def list_notifications():
    """
    List notifications for the current user.
    Paginated with unread count included.
    """
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    offset = (page - 1) * per_page
    unread_only = request.args.get("unread_only", "false").lower() == "true"

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get unread count
                cur.execute(
                    "SELECT COUNT(*) FROM notifications WHERE user_id = %s AND read_at IS NULL",
                    (g.current_user["id"],),
                )
                unread_count = cur.fetchone()[0]

                # Build query with optional unread filter
                conditions = ["user_id = %s"]
                params = [g.current_user["id"]]

                if unread_only:
                    conditions.append("read_at IS NULL")

                where_clause = " AND ".join(conditions)

                # Get total count
                cur.execute(
                    f"SELECT COUNT(*) FROM notifications WHERE {where_clause}",
                    params,
                )
                total = cur.fetchone()[0]

                # Get paginated results
                cur.execute(
                    f"""
                    SELECT id, user_id, type, title, message, metadata,
                           read_at, created_at
                    FROM notifications
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [per_page, offset],
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("List notifications error: %s", str(e))
        return jsonify({"error": "Failed to fetch notifications"}), 500

    return jsonify({
        "notifications": [
            {
                "id": str(r[0]),
                "user_id": str(r[1]),
                "type": r[2],
                "title": r[3],
                "message": r[4],
                "metadata": r[5],
                "is_read": r[6] is not None,
                "read_at": r[6].isoformat() if r[6] else None,
                "created_at": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ],
        "unread_count": unread_count,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
    })


# ──────────────────────────────────────────────────────────────
# PUT /api/notifications/:id/read — mark as read
# ──────────────────────────────────────────────────────────────

@notifications_bp.route("/<notification_id>/read", methods=["PUT"])
@require_auth
def mark_read(notification_id):
    """Mark a single notification as read."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notifications SET read_at = NOW()
                    WHERE id = %s AND user_id = %s AND read_at IS NULL
                    """,
                    (notification_id, g.current_user["id"]),
                )
                if cur.rowcount == 0:
                    # Either not found or already read
                    cur.execute(
                        "SELECT id FROM notifications WHERE id = %s AND user_id = %s",
                        (notification_id, g.current_user["id"]),
                    )
                    if not cur.fetchone():
                        return jsonify({"error": "Notification not found"}), 404
    except Exception as e:
        logger.error("Mark notification read error: %s", str(e))
        return jsonify({"error": "Failed to mark notification as read"}), 500

    return jsonify({"message": "Notification marked as read"})


# ──────────────────────────────────────────────────────────────
# PUT /api/notifications/read-all — mark all as read
# ──────────────────────────────────────────────────────────────

@notifications_bp.route("/read-all", methods=["PUT"])
@require_auth
def mark_all_read():
    """Mark all unread notifications as read for the current user."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notifications SET read_at = NOW()
                    WHERE user_id = %s AND read_at IS NULL
                    """,
                    (g.current_user["id"],),
                )
                updated_count = cur.rowcount

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "notifications.marked_all_read", "notification",
                        None,
                        json.dumps({"count": updated_count}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Mark all notifications read error: %s", str(e))
        return jsonify({"error": "Failed to mark notifications as read"}), 500

    return jsonify({
        "message": f"Marked {updated_count} notification(s) as read",
        "updated": updated_count,
    })


# ──────────────────────────────────────────────────────────────
# GET /api/notifications/unread-count — get unread count
# ──────────────────────────────────────────────────────────────

@notifications_bp.route("/unread-count", methods=["GET"])
@require_auth
def unread_count():
    """Get the count of unread notifications for the current user."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM notifications WHERE user_id = %s AND read_at IS NULL",
                    (g.current_user["id"],),
                )
                count = cur.fetchone()[0]
    except Exception as e:
        logger.error("Unread count error: %s", str(e))
        return jsonify({"error": "Failed to fetch unread count"}), 500

    return jsonify({"unread_count": count})
