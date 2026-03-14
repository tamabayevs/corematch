"""
CoreMatch — Dashboard Blueprint
Aggregated stats, action items, and activity feed for the HR dashboard.
All endpoints require JWT auth.

Performance: Dashboard summary consolidated from 11 queries → 2 queries.
Optional Redis caching (5-min TTL) when Redis is available.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint("dashboard", __name__)

# ── Optional Redis cache for dashboard ──
_redis_client = None
_redis_checked = False
DASHBOARD_CACHE_TTL = 300  # 5 minutes


def _get_cache():
    """Return Redis client for caching, or None if unavailable."""
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        import redis
        import os
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            _redis_client = redis.from_url(redis_url, socket_timeout=1, socket_connect_timeout=1)
            _redis_client.ping()
        else:
            _redis_client = None
    except Exception:
        _redis_client = None
    return _redis_client


# ──────────────────────────────────────────────────────────────
# GET /api/dashboard/summary
# Returns KPIs, action items, and pipeline overview
# Consolidated: 11 queries → 2 queries for 10x faster load
# ──────────────────────────────────────────────────────────────

@dashboard_bp.route("/summary", methods=["GET"])
@require_auth
def dashboard_summary():
    """Aggregated dashboard data for the current HR user."""
    user_id = g.current_user["id"]

    # Check cache first
    cache = _get_cache()
    cache_key = "dash:%s" % user_id
    if cache:
        try:
            cached = cache.get(cache_key)
            if cached:
                return jsonify(json.loads(cached))
        except Exception:
            pass

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # ── QUERY 1: All KPIs + Pipeline in single pass ──
                cur.execute(
                    """
                    SELECT
                        -- KPIs
                        (SELECT COUNT(*) FROM campaigns WHERE user_id = %(uid)s AND status = 'active') AS active_campaigns,
                        -- Candidates this month (across all campaigns)
                        COUNT(*) FILTER (WHERE cand.created_at >= date_trunc('month', NOW())) AS candidates_this_month,
                        -- Completion rate components
                        COUNT(*) FILTER (WHERE cand.status = 'submitted' AND c.status = 'active') AS submitted_active,
                        COUNT(*) FILTER (WHERE c.status = 'active') AS total_active,
                        -- Average AI score
                        ROUND(AVG(cand.overall_score) FILTER (WHERE cand.overall_score IS NOT NULL)::numeric, 1) AS avg_score,
                        -- Pipeline counts
                        COUNT(*) FILTER (WHERE cand.status = 'invited' AND c.status = 'active') AS p_invited,
                        COUNT(*) FILTER (WHERE cand.status = 'started' AND c.status = 'active') AS p_started,
                        COUNT(*) FILTER (WHERE cand.status = 'submitted' AND cand.hr_decision IS NULL AND c.status = 'active') AS p_awaiting,
                        COUNT(*) FILTER (WHERE cand.status = 'submitted' AND cand.hr_decision IS NOT NULL AND c.status = 'active') AS p_reviewed,
                        COUNT(*) FILTER (WHERE cand.hr_decision = 'shortlisted' AND c.status = 'active') AS p_shortlisted,
                        COUNT(*) FILTER (WHERE cand.hr_decision = 'rejected' AND c.status = 'active') AS p_rejected,
                        COUNT(*) FILTER (WHERE cand.hr_decision = 'hold' AND c.status = 'active') AS p_hold
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %(uid)s AND cand.status != 'erased'
                    """,
                    {"uid": user_id},
                )
                r = cur.fetchone()
                active_campaigns = r[0]
                candidates_this_month = r[1]
                completion_rate = round((r[2] / r[3] * 100), 1) if r[3] > 0 else 0
                avg_score = float(r[4] or 0)
                pipeline = {
                    "invited": r[5], "started": r[6],
                    "awaiting_review": r[7], "reviewed": r[8],
                    "shortlisted": r[9], "rejected": r[10], "hold": r[11],
                }

                # ── QUERY 2: All action items in single pass ──
                cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (
                            WHERE cand.status = 'submitted' AND cand.hr_decision IS NULL
                        ) AS new_submissions,
                        COUNT(*) FILTER (
                            WHERE cand.status = 'submitted' AND cand.hr_decision IS NULL
                              AND cand.updated_at < NOW() - INTERVAL '48 hours'
                        ) AS overdue_decisions,
                        COUNT(*) FILTER (
                            WHERE c.status = 'active' AND cand.status = 'invited'
                              AND cand.created_at < NOW() - INTERVAL '3 days'
                              AND cand.invite_expires_at > NOW()
                        ) AS not_started,
                        COUNT(*) FILTER (
                            WHERE cand.status IN ('invited', 'started')
                              AND cand.invite_expires_at BETWEEN NOW() AND NOW() + INTERVAL '48 hours'
                        ) AS expiring_soon
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s AND cand.status != 'erased'
                    """,
                    (user_id,),
                )
                ar = cur.fetchone()

                action_items = []
                if ar[0] > 0:
                    action_items.append({"type": "new_submissions", "count": ar[0], "priority": "high", "link": "/dashboard/reviews"})
                if ar[1] > 0:
                    action_items.append({"type": "overdue_decisions", "count": ar[1], "priority": "medium", "link": "/dashboard/reviews"})
                if ar[2] > 0:
                    action_items.append({"type": "not_started", "count": ar[2], "priority": "low", "link": "/dashboard/campaigns"})
                if ar[3] > 0:
                    action_items.append({"type": "expiring_invites", "count": ar[3], "priority": "medium", "link": "/dashboard/campaigns"})

    except Exception as e:
        logger.error("Dashboard summary error: %s", str(e))
        return jsonify({"error": "Failed to fetch dashboard data"}), 500

    result = {
        "kpis": {
            "active_campaigns": active_campaigns,
            "candidates_this_month": candidates_this_month,
            "completion_rate": completion_rate,
            "avg_score": avg_score,
        },
        "pipeline": pipeline,
        "action_items": action_items,
    }

    # Cache result
    if cache:
        try:
            cache.setex(cache_key, DASHBOARD_CACHE_TTL, json.dumps(result))
        except Exception:
            pass

    return jsonify(result)


# ──────────────────────────────────────────────────────────────
# GET /api/dashboard/activity
# Returns recent activity feed from audit_log
# ──────────────────────────────────────────────────────────────

@dashboard_bp.route("/activity", methods=["GET"])
@require_auth
def dashboard_activity():
    """Paginated activity feed for the current HR user."""
    user_id = g.current_user["id"]
    limit = min(int(request.args.get("limit", 10)), 50)
    offset = int(request.args.get("offset", 0))

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT al.action, al.entity_type, al.entity_id, al.metadata,
                           al.created_at, u.full_name
                    FROM audit_log al
                    LEFT JOIN users u ON al.user_id = u.id
                    WHERE al.user_id = %s
                    ORDER BY al.created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset),
                )
                rows = cur.fetchall()

                # Get total count
                cur.execute(
                    "SELECT COUNT(*) FROM audit_log WHERE user_id = %s",
                    (user_id,),
                )
                total = cur.fetchone()[0]

    except Exception as e:
        logger.error("Dashboard activity error: %s", str(e))
        return jsonify({"error": "Failed to fetch activity"}), 500

    activities = []
    for row in rows:
        activities.append({
            "action": row[0],
            "entity_type": row[1],
            "entity_id": str(row[2]) if row[2] else None,
            "metadata": row[3] or {},
            "created_at": row[4].isoformat() if row[4] else None,
            "user_name": row[5],
        })

    return jsonify({
        "activities": activities,
        "total": total,
        "limit": limit,
        "offset": offset,
    })


# ──────────────────────────────────────────────────────────────
# GET /api/dashboard/campaigns
# Returns campaigns list enhanced with completion rates
# ──────────────────────────────────────────────────────────────

@dashboard_bp.route("/campaigns", methods=["GET"])
@require_auth
def dashboard_campaigns():
    """Campaigns with enhanced stats for dashboard display."""
    user_id = g.current_user["id"]
    status_filter = request.args.get("status")

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                status_clause = ""
                params = [user_id]

                if status_filter and status_filter in ("active", "closed", "archived"):
                    status_clause = "AND c.status = %s"
                    params.append(status_filter)
                else:
                    status_clause = "AND c.status != 'archived'"

                cur.execute(
                    f"""
                    SELECT c.id, c.name, c.job_title, c.status, c.created_at,
                           COUNT(cand.id) AS total_candidates,
                           COUNT(cand.id) FILTER (WHERE cand.status = 'submitted') AS submitted_count,
                           COUNT(cand.id) FILTER (WHERE cand.status = 'invited') AS invited_count,
                           COUNT(cand.id) FILTER (WHERE cand.hr_decision IS NOT NULL) AS decided_count,
                           ROUND(AVG(cand.overall_score) FILTER (WHERE cand.overall_score IS NOT NULL)::numeric, 1) AS avg_score,
                           jsonb_array_length(c.questions) AS question_count
                    FROM campaigns c
                    LEFT JOIN candidates cand ON cand.campaign_id = c.id AND cand.status != 'erased'
                    WHERE c.user_id = %s {status_clause}
                    GROUP BY c.id
                    ORDER BY c.created_at DESC
                    """,
                    params,
                )
                rows = cur.fetchall()

    except Exception as e:
        logger.error("Dashboard campaigns error: %s", str(e))
        return jsonify({"error": "Failed to fetch campaigns"}), 500

    campaigns = []
    for row in rows:
        total = row[5] or 0
        submitted = row[6] or 0
        campaigns.append({
            "id": str(row[0]),
            "name": row[1],
            "job_title": row[2],
            "status": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "total_candidates": total,
            "submitted_count": submitted,
            "invited_count": row[7] or 0,
            "decided_count": row[8] or 0,
            "avg_score": float(row[9]) if row[9] else None,
            "question_count": row[10] or 0,
            "completion_rate": round(submitted / total * 100, 1) if total > 0 else 0,
        })

    return jsonify({"campaigns": campaigns})
