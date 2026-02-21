"""
CoreMatch — Dashboard Blueprint
Aggregated stats, action items, and activity feed for the HR dashboard.
All endpoints require JWT auth.
"""
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint("dashboard", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/dashboard/summary
# Returns KPIs, action items, and pipeline overview
# ──────────────────────────────────────────────────────────────

@dashboard_bp.route("/summary", methods=["GET"])
@require_auth
def dashboard_summary():
    """Aggregated dashboard data for the current HR user."""
    user_id = g.current_user["id"]

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # ── KPI Cards ──
                # Active campaigns count
                cur.execute(
                    "SELECT COUNT(*) FROM campaigns WHERE user_id = %s AND status = 'active'",
                    (user_id,),
                )
                active_campaigns = cur.fetchone()[0]

                # Total candidates this month
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s
                      AND cand.created_at >= date_trunc('month', NOW())
                      AND cand.status != 'erased'
                    """,
                    (user_id,),
                )
                candidates_this_month = cur.fetchone()[0]

                # Average completion rate (submitted / total invited across active campaigns)
                cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE cand.status = 'submitted') AS submitted,
                        COUNT(*) AS total
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s AND c.status = 'active' AND cand.status != 'erased'
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                completion_rate = round((row[0] / row[1] * 100), 1) if row[1] > 0 else 0

                # Average AI score across all submitted candidates
                cur.execute(
                    """
                    SELECT ROUND(AVG(cand.overall_score)::numeric, 1)
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s
                      AND cand.overall_score IS NOT NULL
                      AND cand.status != 'erased'
                    """,
                    (user_id,),
                )
                avg_score = float(cur.fetchone()[0] or 0)

                # ── Pipeline Overview ──
                cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE cand.status = 'invited') AS invited,
                        COUNT(*) FILTER (WHERE cand.status = 'started') AS started,
                        COUNT(*) FILTER (WHERE cand.status = 'submitted' AND cand.hr_decision IS NULL) AS awaiting_review,
                        COUNT(*) FILTER (WHERE cand.status = 'submitted' AND cand.hr_decision IS NOT NULL) AS reviewed,
                        COUNT(*) FILTER (WHERE cand.hr_decision = 'shortlisted') AS shortlisted,
                        COUNT(*) FILTER (WHERE cand.hr_decision = 'rejected') AS rejected,
                        COUNT(*) FILTER (WHERE cand.hr_decision = 'hold') AS hold
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s AND c.status = 'active' AND cand.status != 'erased'
                    """,
                    (user_id,),
                )
                pipeline_row = cur.fetchone()
                pipeline = {
                    "invited": pipeline_row[0],
                    "started": pipeline_row[1],
                    "awaiting_review": pipeline_row[2],
                    "reviewed": pipeline_row[3],
                    "shortlisted": pipeline_row[4],
                    "rejected": pipeline_row[5],
                    "hold": pipeline_row[6],
                }

                # ── Action Items ──
                action_items = []

                # 1. New submissions awaiting review
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s
                      AND cand.status = 'submitted'
                      AND cand.hr_decision IS NULL
                    """,
                    (user_id,),
                )
                new_submissions = cur.fetchone()[0]
                if new_submissions > 0:
                    action_items.append({
                        "type": "new_submissions",
                        "count": new_submissions,
                        "priority": "high",
                        "link": "/dashboard/reviews",
                    })

                # 2. Candidates awaiting decision for >48 hours
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s
                      AND cand.status = 'submitted'
                      AND cand.hr_decision IS NULL
                      AND cand.updated_at < NOW() - INTERVAL '48 hours'
                    """,
                    (user_id,),
                )
                overdue_decisions = cur.fetchone()[0]
                if overdue_decisions > 0:
                    action_items.append({
                        "type": "overdue_decisions",
                        "count": overdue_decisions,
                        "priority": "medium",
                        "link": "/dashboard/reviews",
                    })

                # 3. Candidates who haven't started (invited >3 days ago)
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s
                      AND c.status = 'active'
                      AND cand.status = 'invited'
                      AND cand.created_at < NOW() - INTERVAL '3 days'
                      AND cand.invite_expires_at > NOW()
                    """,
                    (user_id,),
                )
                not_started = cur.fetchone()[0]
                if not_started > 0:
                    action_items.append({
                        "type": "not_started",
                        "count": not_started,
                        "priority": "low",
                        "link": "/dashboard/campaigns",
                    })

                # 4. Invites expiring within 48 hours
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s
                      AND cand.status IN ('invited', 'started')
                      AND cand.invite_expires_at BETWEEN NOW() AND NOW() + INTERVAL '48 hours'
                    """,
                    (user_id,),
                )
                expiring_soon = cur.fetchone()[0]
                if expiring_soon > 0:
                    action_items.append({
                        "type": "expiring_invites",
                        "count": expiring_soon,
                        "priority": "medium",
                        "link": "/dashboard/campaigns",
                    })

    except Exception as e:
        logger.error("Dashboard summary error: %s", str(e))
        return jsonify({"error": "Failed to fetch dashboard data"}), 500

    return jsonify({
        "kpis": {
            "active_campaigns": active_campaigns,
            "candidates_this_month": candidates_this_month,
            "completion_rate": completion_rate,
            "avg_score": avg_score,
        },
        "pipeline": pipeline,
        "action_items": action_items,
    })


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
