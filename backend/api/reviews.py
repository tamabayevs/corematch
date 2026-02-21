"""
CoreMatch — Reviews Blueprint
Review queue for HR users to evaluate submitted candidates.
All endpoints require JWT auth.
"""
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
reviews_bp = Blueprint("reviews", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/reviews/queue
# Paginated list of submitted candidates for HR review
# ──────────────────────────────────────────────────────────────

@reviews_bp.route("/queue", methods=["GET"])
@require_auth
def review_queue():
    """
    Returns a paginated list of submitted candidates across all
    campaigns owned by the current HR user.

    Query params:
        campaign_id  — filter by specific campaign (optional)
        tier         — filter by AI tier: strong_proceed, consider, likely_pass (optional)
        reviewed     — filter by reviewed status: true/false (optional)
        sort         — sort order: score (default), name, date
        page         — page number, 1-based (default 1)
        per_page     — items per page, max 100 (default 20)
    """
    user_id = g.current_user["id"]

    # Parse query params
    campaign_id = request.args.get("campaign_id")
    tier_filter = request.args.get("tier")
    reviewed_filter = request.args.get("reviewed")
    sort_by = request.args.get("sort", "score")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    offset = (page - 1) * per_page

    # Build dynamic WHERE clauses
    conditions = [
        "camp.user_id = %s",
        "cand.status = 'submitted'",
        "cand.status != 'erased'",
    ]
    params = [user_id]

    if campaign_id:
        conditions.append("cand.campaign_id = %s")
        params.append(campaign_id)

    valid_tiers = ("strong_proceed", "consider", "likely_pass")
    if tier_filter and tier_filter in valid_tiers:
        conditions.append("cand.tier = %s")
        params.append(tier_filter)

    if reviewed_filter is not None:
        if reviewed_filter.lower() in ("true", "1"):
            conditions.append("cand.reviewed_at IS NOT NULL")
        elif reviewed_filter.lower() in ("false", "0"):
            conditions.append("cand.reviewed_at IS NULL")

    where_clause = " AND ".join(conditions)

    # Sort order
    order_clause = {
        "score": "cand.overall_score DESC NULLS LAST, cand.created_at DESC",
        "name": "cand.full_name ASC, cand.created_at DESC",
        "date": "cand.created_at DESC",
    }.get(sort_by, "cand.overall_score DESC NULLS LAST, cand.created_at DESC")

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Total count for pagination
                cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM candidates cand
                    JOIN campaigns camp ON cand.campaign_id = camp.id
                    WHERE {where_clause}
                    """,
                    params,
                )
                total = cur.fetchone()[0]

                # Main query: candidates with campaign info and video stats
                query_params = params + [per_page, offset]
                cur.execute(
                    f"""
                    SELECT
                        cand.id,
                        cand.campaign_id,
                        cand.full_name,
                        cand.email,
                        cand.overall_score,
                        cand.tier,
                        cand.status,
                        cand.hr_decision,
                        cand.hr_decision_at,
                        cand.hr_decision_note,
                        cand.reviewed_at,
                        cand.reviewed_by,
                        cand.reference_id,
                        cand.created_at,
                        cand.updated_at,
                        camp.name AS campaign_name,
                        camp.job_title,
                        COUNT(va.id) AS video_count,
                        COUNT(va.id) FILTER (
                            WHERE va.processing_status = 'complete'
                        ) AS videos_scored,
                        CASE
                            WHEN COUNT(va.id) > 0
                                 AND COUNT(va.id) = COUNT(va.id) FILTER (
                                     WHERE va.processing_status = 'complete'
                                 )
                            THEN TRUE
                            ELSE FALSE
                        END AS scoring_complete
                    FROM candidates cand
                    JOIN campaigns camp ON cand.campaign_id = camp.id
                    LEFT JOIN video_answers va ON va.candidate_id = cand.id
                    WHERE {where_clause}
                    GROUP BY cand.id, camp.name, camp.job_title
                    ORDER BY {order_clause}
                    LIMIT %s OFFSET %s
                    """,
                    query_params,
                )
                rows = cur.fetchall()

    except Exception as e:
        logger.error("Review queue error: %s", str(e))
        return jsonify({"error": "Failed to fetch review queue"}), 500

    candidates = []
    for row in rows:
        candidates.append({
            "id": str(row[0]),
            "campaign_id": str(row[1]),
            "full_name": row[2],
            "email": row[3],
            "overall_score": float(row[4]) if row[4] is not None else None,
            "tier": row[5],
            "status": row[6],
            "hr_decision": row[7],
            "hr_decision_at": row[8].isoformat() if row[8] else None,
            "hr_decision_note": row[9],
            "reviewed_at": row[10].isoformat() if row[10] else None,
            "reviewed_by": str(row[11]) if row[11] else None,
            "reference_id": row[12],
            "created_at": row[13].isoformat() if row[13] else None,
            "updated_at": row[14].isoformat() if row[14] else None,
            "campaign_name": row[15],
            "job_title": row[16],
            "video_count": row[17],
            "videos_scored": row[18],
            "scoring_complete": row[19],
        })

    total_pages = (total + per_page - 1) // per_page  # ceiling division

    return jsonify({
        "candidates": candidates,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    })


# ──────────────────────────────────────────────────────────────
# GET /api/reviews/stats
# Review queue statistics
# ──────────────────────────────────────────────────────────────

@reviews_bp.route("/stats", methods=["GET"])
@require_auth
def review_stats():
    """
    Returns aggregate review queue statistics:
    - total_unreviewed: submitted candidates with no reviewed_at
    - total_reviewed: submitted candidates with reviewed_at set
    - by_campaign: breakdown per campaign with unreviewed counts
    """
    user_id = g.current_user["id"]

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Overall counts
                cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (
                            WHERE cand.reviewed_at IS NULL
                        ) AS total_unreviewed,
                        COUNT(*) FILTER (
                            WHERE cand.reviewed_at IS NOT NULL
                        ) AS total_reviewed
                    FROM candidates cand
                    JOIN campaigns camp ON cand.campaign_id = camp.id
                    WHERE camp.user_id = %s
                      AND cand.status = 'submitted'
                      AND cand.status != 'erased'
                    """,
                    (user_id,),
                )
                totals_row = cur.fetchone()
                total_unreviewed = totals_row[0]
                total_reviewed = totals_row[1]

                # Per-campaign breakdown
                cur.execute(
                    """
                    SELECT
                        camp.id,
                        camp.name,
                        COUNT(*) FILTER (
                            WHERE cand.reviewed_at IS NULL
                        ) AS unreviewed_count
                    FROM candidates cand
                    JOIN campaigns camp ON cand.campaign_id = camp.id
                    WHERE camp.user_id = %s
                      AND cand.status = 'submitted'
                      AND cand.status != 'erased'
                    GROUP BY camp.id, camp.name
                    HAVING COUNT(*) FILTER (WHERE cand.reviewed_at IS NULL) > 0
                       OR COUNT(*) FILTER (WHERE cand.reviewed_at IS NOT NULL) > 0
                    ORDER BY COUNT(*) FILTER (WHERE cand.reviewed_at IS NULL) DESC
                    """,
                    (user_id,),
                )
                campaign_rows = cur.fetchall()

    except Exception as e:
        logger.error("Review stats error: %s", str(e))
        return jsonify({"error": "Failed to fetch review stats"}), 500

    by_campaign = []
    for row in campaign_rows:
        by_campaign.append({
            "campaign_id": str(row[0]),
            "name": row[1],
            "unreviewed_count": row[2],
        })

    return jsonify({
        "total_unreviewed": total_unreviewed,
        "total_reviewed": total_reviewed,
        "by_campaign": by_campaign,
    })
