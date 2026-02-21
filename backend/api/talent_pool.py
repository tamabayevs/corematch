"""
CoreMatch — Talent Pool Blueprint
Cross-campaign candidate search with filters and saved searches.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
talent_pool_bp = Blueprint("talent_pool", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/talent-pool — cross-campaign candidate search
# ──────────────────────────────────────────────────────────────

@talent_pool_bp.route("", methods=["GET"])
@require_auth
def search_candidates():
    """
    Cross-campaign candidate search with filters:
    - tier: strong_proceed, consider, likely_pass
    - score_min / score_max: numeric range
    - campaign_id: filter to specific campaign
    - decision: shortlisted, rejected, hold, none
    - search: full_name or email substring match
    - date_from / date_to: created_at date range
    - page / per_page: pagination
    """
    # Parse query params
    tier = request.args.get("tier")
    score_min = request.args.get("score_min")
    score_max = request.args.get("score_max")
    campaign_id = request.args.get("campaign_id")
    decision = request.args.get("decision")
    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    sort_by = request.args.get("sort", "score")  # score, name, date

    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 25)), 1), 100)
    offset = (page - 1) * per_page

    # Build query — only candidates from campaigns owned by the current user
    conditions = [
        "camp.user_id = %s",
        "c.status != 'erased'",
    ]
    params = [g.current_user["id"]]

    valid_tiers = ("strong_proceed", "consider", "likely_pass")
    if tier and tier in valid_tiers:
        conditions.append("c.tier = %s")
        params.append(tier)

    if score_min is not None:
        try:
            conditions.append("c.overall_score >= %s")
            params.append(float(score_min))
        except ValueError:
            pass

    if score_max is not None:
        try:
            conditions.append("c.overall_score <= %s")
            params.append(float(score_max))
        except ValueError:
            pass

    if campaign_id:
        conditions.append("c.campaign_id = %s")
        params.append(campaign_id)

    valid_decisions = ("shortlisted", "rejected", "hold")
    if decision and decision in valid_decisions:
        conditions.append("c.hr_decision = %s")
        params.append(decision)
    elif decision == "none":
        conditions.append("c.hr_decision IS NULL")

    if search:
        conditions.append("(c.full_name ILIKE %s OR c.email ILIKE %s)")
        like_pattern = f"%{search}%"
        params.extend([like_pattern, like_pattern])

    if date_from:
        conditions.append("c.created_at >= %s")
        params.append(date_from)

    if date_to:
        conditions.append("c.created_at <= %s")
        params.append(date_to)

    where_clause = " AND ".join(conditions)

    order_clause = {
        "score": "c.overall_score DESC NULLS LAST",
        "name": "c.full_name ASC",
        "date": "c.created_at DESC",
    }.get(sort_by, "c.overall_score DESC NULLS LAST")

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get total count
                cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE {where_clause}
                    """,
                    params,
                )
                total = cur.fetchone()[0]

                # Get paginated results
                cur.execute(
                    f"""
                    SELECT c.id, c.campaign_id, camp.name as campaign_name,
                           camp.job_title, c.email, c.full_name, c.status,
                           c.overall_score, c.tier, c.hr_decision,
                           c.hr_decision_note, c.reference_id,
                           c.created_at, c.updated_at
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE {where_clause}
                    ORDER BY {order_clause}
                    LIMIT %s OFFSET %s
                    """,
                    params + [per_page, offset],
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("Talent pool search error: %s", str(e))
        return jsonify({"error": "Failed to search candidates"}), 500

    return jsonify({
        "candidates": [
            {
                "id": str(r[0]),
                "campaign_id": str(r[1]),
                "campaign_name": r[2],
                "job_title": r[3],
                "email": r[4],
                "full_name": r[5],
                "status": r[6],
                "overall_score": float(r[7]) if r[7] is not None else None,
                "tier": r[8],
                "hr_decision": r[9],
                "hr_decision_note": r[10],
                "reference_id": r[11],
                "created_at": r[12].isoformat() if r[12] else None,
                "updated_at": r[13].isoformat() if r[13] else None,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
    })


# ──────────────────────────────────────────────────────────────
# POST /api/talent-pool/saved-searches — save a search
# ──────────────────────────────────────────────────────────────

@talent_pool_bp.route("/saved-searches", methods=["POST"])
@require_auth
def save_search():
    """Save a talent pool search with its filter criteria."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    filters = data.get("filters", {})
    if not isinstance(filters, dict):
        return jsonify({"error": "Filters must be an object"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO saved_searches (user_id, name, filters)
                    VALUES (%s, %s, %s::jsonb)
                    RETURNING id, created_at
                    """,
                    (g.current_user["id"], name, json.dumps(filters)),
                )
                row = cur.fetchone()

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "talent_pool.search_saved", "saved_search",
                        str(row[0]), json.dumps({"name": name}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Save search error: %s", str(e))
        return jsonify({"error": "Failed to save search"}), 500

    return jsonify({
        "message": "Search saved",
        "saved_search": {
            "id": str(row[0]),
            "name": name,
            "filters": filters,
            "created_at": row[1].isoformat(),
        },
    }), 201


# ──────────────────────────────────────────────────────────────
# GET /api/talent-pool/saved-searches — list saved searches
# ──────────────────────────────────────────────────────────────

@talent_pool_bp.route("/saved-searches", methods=["GET"])
@require_auth
def list_saved_searches():
    """List all saved searches for the current user."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, filters, created_at, updated_at
                    FROM saved_searches
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (g.current_user["id"],),
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("List saved searches error: %s", str(e))
        return jsonify({"error": "Failed to fetch saved searches"}), 500

    return jsonify({
        "saved_searches": [
            {
                "id": str(r[0]),
                "name": r[1],
                "filters": r[2],
                "created_at": r[3].isoformat() if r[3] else None,
                "updated_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]
    })


# ──────────────────────────────────────────────────────────────
# DELETE /api/talent-pool/saved-searches/:id — delete saved search
# ──────────────────────────────────────────────────────────────

@talent_pool_bp.route("/saved-searches/<search_id>", methods=["DELETE"])
@require_auth
def delete_saved_search(search_id):
    """Delete a saved search. Only the owner can delete."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM saved_searches WHERE id = %s AND user_id = %s",
                    (search_id, g.current_user["id"]),
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "Saved search not found"}), 404

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "talent_pool.search_deleted", "saved_search",
                        search_id, json.dumps({}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Delete saved search error: %s", str(e))
        return jsonify({"error": "Failed to delete saved search"}), 500

    return jsonify({"message": "Saved search deleted"})


# ──────────────────────────────────────────────────────────────
# PUT /api/talent-pool/saved-searches/:id/auto-notify — toggle auto-notify
# ──────────────────────────────────────────────────────────────

@talent_pool_bp.route("/saved-searches/<search_id>/auto-notify", methods=["PUT"])
@require_auth
def toggle_auto_notify(search_id):
    """Enable or disable auto-notification for a saved search."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    auto_notify = bool(data.get("auto_notify", False))

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE saved_searches SET auto_notify = %s
                    WHERE id = %s AND user_id = %s
                    """,
                    (auto_notify, search_id, g.current_user["id"]),
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "Saved search not found"}), 404

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "talent_pool.auto_notify_toggled", "saved_search",
                        search_id, json.dumps({"auto_notify": auto_notify}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Toggle auto-notify error: %s", str(e))
        return jsonify({"error": "Failed to update auto-notify"}), 500

    return jsonify({
        "message": "Auto-notify " + ("enabled" if auto_notify else "disabled"),
        "auto_notify": auto_notify,
    })
