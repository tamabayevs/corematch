"""
CoreMatch — Data Subject Request (DSR) Blueprint
PDPL compliance endpoints for managing data subject requests.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
dsr_bp = Blueprint("dsr", __name__)

VALID_REQUEST_TYPES = ("access", "erasure", "rectification", "portability", "objection")
VALID_STATUSES = ("pending", "in_progress", "completed", "rejected")


# ──────────────────────────────────────────────────────────────
# GET /api/dsr — list all data subject requests
# ──────────────────────────────────────────────────────────────

@dsr_bp.route("", methods=["GET"])
@require_auth
def list_requests():
    """List all data subject requests for the current user."""
    status_filter = request.args.get("status")
    request_type_filter = request.args.get("request_type")

    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 25)), 1), 100)
    offset = (page - 1) * per_page

    conditions = ["user_id = %s"]
    params = [g.current_user["id"]]

    if status_filter and status_filter in VALID_STATUSES:
        conditions.append("status = %s")
        params.append(status_filter)

    if request_type_filter and request_type_filter in VALID_REQUEST_TYPES:
        conditions.append("request_type = %s")
        params.append(request_type_filter)

    where_clause = " AND ".join(conditions)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get total count
                cur.execute(
                    f"SELECT COUNT(*) FROM data_subject_requests WHERE {where_clause}",
                    params,
                )
                total = cur.fetchone()[0]

                # Get paginated results
                cur.execute(
                    f"""
                    SELECT id, user_id, request_type, requester_name, requester_email,
                           candidate_id, description, status, response_notes,
                           due_date, completed_at, created_at, updated_at
                    FROM data_subject_requests
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [per_page, offset],
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("List DSR error: %s", str(e))
        return jsonify({"error": "Failed to fetch data subject requests"}), 500

    return jsonify({
        "requests": [
            {
                "id": str(r[0]),
                "user_id": str(r[1]),
                "request_type": r[2],
                "requester_name": r[3],
                "requester_email": r[4],
                "candidate_id": str(r[5]) if r[5] else None,
                "description": r[6],
                "status": r[7],
                "response_notes": r[8],
                "due_date": r[9].isoformat() if r[9] else None,
                "completed_at": r[10].isoformat() if r[10] else None,
                "created_at": r[11].isoformat() if r[11] else None,
                "updated_at": r[12].isoformat() if r[12] else None,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
    })


# ──────────────────────────────────────────────────────────────
# POST /api/dsr — create new DSR
# ──────────────────────────────────────────────────────────────

@dsr_bp.route("", methods=["POST"])
@require_auth
def create_request():
    """
    Create a new data subject request.
    PDPL requires responding within 30 days, so due_date is auto-set.
    """
    import datetime

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    request_type = (data.get("request_type") or "").strip().lower()
    if request_type not in VALID_REQUEST_TYPES:
        return jsonify({"error": f"request_type must be one of: {', '.join(VALID_REQUEST_TYPES)}"}), 400

    requester_name = (data.get("requester_name") or "").strip()
    if not requester_name:
        return jsonify({"error": "requester_name is required"}), 400

    requester_email = (data.get("requester_email") or "").strip().lower()
    if not requester_email:
        return jsonify({"error": "requester_email is required"}), 400

    # Validate email
    from email_validator import validate_email, EmailNotValidError
    try:
        valid = validate_email(requester_email)
        requester_email = valid.normalized
    except EmailNotValidError:
        return jsonify({"error": "Invalid requester email address"}), 400

    candidate_id = data.get("candidate_id") or None
    description = (data.get("description") or "").strip() or None

    # PDPL: 30-day deadline for responding to DSRs
    due_date = datetime.datetime.utcnow() + datetime.timedelta(days=30)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # If candidate_id specified, verify access
                if candidate_id:
                    cur.execute(
                        """
                        SELECT c.id FROM candidates c
                        JOIN campaigns camp ON c.campaign_id = camp.id
                        WHERE c.id = %s AND camp.user_id = %s
                        """,
                        (candidate_id, g.current_user["id"]),
                    )
                    if not cur.fetchone():
                        return jsonify({"error": "Candidate not found"}), 404

                cur.execute(
                    """
                    INSERT INTO data_subject_requests
                    (user_id, request_type, requester_name, requester_email,
                     candidate_id, description, status, due_date)
                    VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s)
                    RETURNING id, created_at
                    """,
                    (
                        g.current_user["id"], request_type, requester_name,
                        requester_email, candidate_id, description, due_date,
                    ),
                )
                row = cur.fetchone()
                dsr_id = str(row[0])

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "dsr.created", "data_subject_request",
                        dsr_id,
                        json.dumps({
                            "request_type": request_type,
                            "requester_email": requester_email,
                        }),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Create DSR error: %s", str(e))
        return jsonify({"error": "Failed to create data subject request"}), 500

    # In-app notification to the user who created the DSR (confirmation)
    from services.notification_service import notify_user
    notify_user(
        user_id=g.current_user["id"],
        notification_type="dsr",
        title="Data subject request created",
        message=f"New {request_type} request from {requester_name}. Due in 30 days.",
        entity_type="data_subject_request",
        entity_id=dsr_id,
        metadata={"request_type": request_type, "requester_email": requester_email},
    )

    return jsonify({
        "message": "Data subject request created",
        "request": {
            "id": dsr_id,
            "request_type": request_type,
            "status": "pending",
            "due_date": due_date.isoformat(),
            "created_at": row[1].isoformat(),
        },
    }), 201


# ──────────────────────────────────────────────────────────────
# PUT /api/dsr/:id — update DSR status
# ──────────────────────────────────────────────────────────────

@dsr_bp.route("/<dsr_id>", methods=["PUT"])
@require_auth
def update_request(dsr_id):
    """
    Update a DSR status: in_progress, completed, rejected.
    Records status transitions in the audit log.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    new_status = (data.get("status") or "").strip().lower()
    if new_status not in ("in_progress", "completed", "rejected"):
        return jsonify({"error": "Status must be: in_progress, completed, or rejected"}), 400

    response_notes = (data.get("response_notes") or "").strip() or None

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify ownership and get current status
                cur.execute(
                    "SELECT id, status FROM data_subject_requests WHERE id = %s AND user_id = %s",
                    (dsr_id, g.current_user["id"]),
                )
                existing = cur.fetchone()
                if not existing:
                    return jsonify({"error": "Data subject request not found"}), 404

                old_status = existing[1]

                updates = ["status = %s"]
                values = [new_status]

                if response_notes:
                    updates.append("response_notes = %s")
                    values.append(response_notes)

                if new_status == "completed":
                    updates.append("completed_at = NOW()")

                values.extend([dsr_id, g.current_user["id"]])
                cur.execute(
                    f"""
                    UPDATE data_subject_requests
                    SET {', '.join(updates)}
                    WHERE id = %s AND user_id = %s
                    """,
                    values,
                )

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "dsr.status_updated", "data_subject_request",
                        dsr_id,
                        json.dumps({"old_status": old_status, "new_status": new_status}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Update DSR error: %s", str(e))
        return jsonify({"error": "Failed to update data subject request"}), 500

    return jsonify({"message": "Data subject request updated", "status": new_status})


# ──────────────────────────────────────────────────────────────
# GET /api/dsr/stats — get DSR stats
# ──────────────────────────────────────────────────────────────

@dsr_bp.route("/stats", methods=["GET"])
@require_auth
def get_stats():
    """
    Get DSR statistics: pending count, overdue count, avg completion time.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Pending count
                cur.execute(
                    "SELECT COUNT(*) FROM data_subject_requests WHERE user_id = %s AND status = 'pending'",
                    (g.current_user["id"],),
                )
                pending_count = cur.fetchone()[0]

                # In-progress count
                cur.execute(
                    "SELECT COUNT(*) FROM data_subject_requests WHERE user_id = %s AND status = 'in_progress'",
                    (g.current_user["id"],),
                )
                in_progress_count = cur.fetchone()[0]

                # Overdue count (pending or in_progress past due_date)
                cur.execute(
                    """
                    SELECT COUNT(*) FROM data_subject_requests
                    WHERE user_id = %s
                      AND status IN ('pending', 'in_progress')
                      AND due_date < NOW()
                    """,
                    (g.current_user["id"],),
                )
                overdue_count = cur.fetchone()[0]

                # Completed count
                cur.execute(
                    "SELECT COUNT(*) FROM data_subject_requests WHERE user_id = %s AND status = 'completed'",
                    (g.current_user["id"],),
                )
                completed_count = cur.fetchone()[0]

                # Average completion time (in days)
                cur.execute(
                    """
                    SELECT AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 86400)
                    FROM data_subject_requests
                    WHERE user_id = %s AND status = 'completed' AND completed_at IS NOT NULL
                    """,
                    (g.current_user["id"],),
                )
                avg_row = cur.fetchone()
                avg_completion_days = round(float(avg_row[0]), 1) if avg_row[0] is not None else None

                # Total count
                cur.execute(
                    "SELECT COUNT(*) FROM data_subject_requests WHERE user_id = %s",
                    (g.current_user["id"],),
                )
                total_count = cur.fetchone()[0]
    except Exception as e:
        logger.error("DSR stats error: %s", str(e))
        return jsonify({"error": "Failed to fetch DSR stats"}), 500

    return jsonify({
        "stats": {
            "total": total_count,
            "pending": pending_count,
            "in_progress": in_progress_count,
            "completed": completed_count,
            "overdue": overdue_count,
            "avg_completion_days": avg_completion_days,
        }
    })
