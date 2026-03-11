"""
CoreMatch — Insights Blueprint
Analytics endpoints: summary KPIs, pipeline funnel, score distribution, per-campaign comparison.
All endpoints require JWT auth.
"""
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
insights_bp = Blueprint("insights", __name__)


def _parse_filters():
    """Extract common query-param filters: from, to, campaign_id."""
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    campaign_id = request.args.get("campaign_id")
    return date_from, date_to, campaign_id


def _build_where(user_id, date_from, date_to, campaign_id):
    """
    Build a WHERE clause + params list that scopes queries to the
    current user's campaigns and applies optional date / campaign filters.

    Returns (where_sql, params) where where_sql starts with 'WHERE ...'.
    Expects tables aliased as: campaigns -> c, candidates -> cand.
    Date filters apply to cand.created_at.
    """
    clauses = ["c.user_id = %s", "cand.status != 'erased'"]
    params = [user_id]

    if campaign_id:
        clauses.append("c.id = %s")
        params.append(campaign_id)
    if date_from:
        clauses.append("cand.created_at >= %s::date")
        params.append(date_from)
    if date_to:
        clauses.append("cand.created_at < (%s::date + INTERVAL '1 day')")
        params.append(date_to)

    return "WHERE " + " AND ".join(clauses), params


# ──────────────────────────────────────────────────────────────
# GET /api/insights/summary
# Overall KPIs: time-to-submit, completion rate, pass rate, avg score
# ──────────────────────────────────────────────────────────────

@insights_bp.route("/summary", methods=["GET"])
@require_auth
def insights_summary():
    """Return high-level KPI cards for the insights page."""
    user_id = g.current_user["id"]
    date_from, date_to, campaign_id = _parse_filters()
    where, params = _build_where(user_id, date_from, date_to, campaign_id)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Time to submit (average hours from invite to submission)
                cur.execute(
                    f"""
                    SELECT ROUND(
                        AVG(EXTRACT(EPOCH FROM (cand.updated_at - cand.created_at)) / 3600)::numeric,
                        1
                    )
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    {where}
                      AND cand.status = 'submitted'
                    """,
                    params,
                )
                time_to_submit_avg = float(cur.fetchone()[0] or 0)

                # Completion rate (submitted / total invited %)
                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) FILTER (WHERE cand.status = 'submitted') AS submitted,
                        COUNT(*) AS total
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    {where}
                    """,
                    params,
                )
                row = cur.fetchone()
                total = row[1] or 0
                submitted = row[0] or 0
                completion_rate = round(submitted / total * 100, 1) if total > 0 else 0

                # Pass rate (shortlisted / total reviewed %)
                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) FILTER (WHERE cand.hr_decision = 'shortlisted') AS shortlisted,
                        COUNT(*) FILTER (WHERE cand.hr_decision IS NOT NULL) AS reviewed
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    {where}
                    """,
                    params,
                )
                row = cur.fetchone()
                shortlisted = row[0] or 0
                reviewed = row[1] or 0
                pass_rate = round(shortlisted / reviewed * 100, 1) if reviewed > 0 else 0

                # Average AI score
                cur.execute(
                    f"""
                    SELECT ROUND(AVG(cand.overall_score)::numeric, 1)
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    {where}
                      AND cand.overall_score IS NOT NULL
                    """,
                    params,
                )
                avg_ai_score = float(cur.fetchone()[0] or 0)

    except Exception as e:
        logger.error("Insights summary error: %s", str(e))
        return jsonify({"error": "Failed to fetch insights summary"}), 500

    return jsonify({
        "time_to_submit_avg": time_to_submit_avg,
        "completion_rate": completion_rate,
        "pass_rate": pass_rate,
        "avg_ai_score": avg_ai_score,
    })


# ──────────────────────────────────────────────────────────────
# GET /api/insights/funnel
# Pipeline funnel: invited → started → submitted → reviewed → shortlisted / rejected
# ──────────────────────────────────────────────────────────────

@insights_bp.route("/funnel", methods=["GET"])
@require_auth
def insights_funnel():
    """Return pipeline funnel stage counts."""
    user_id = g.current_user["id"]
    date_from, date_to, campaign_id = _parse_filters()
    where, params = _build_where(user_id, date_from, date_to, campaign_id)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) AS invited,
                        COUNT(*) FILTER (WHERE cand.status IN ('started', 'submitted')) AS started,
                        COUNT(*) FILTER (WHERE cand.status = 'submitted') AS submitted,
                        COUNT(*) FILTER (WHERE cand.reviewed_at IS NOT NULL) AS reviewed,
                        COUNT(*) FILTER (WHERE cand.hr_decision = 'shortlisted') AS shortlisted,
                        COUNT(*) FILTER (WHERE cand.hr_decision = 'rejected') AS rejected
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    {where}
                    """,
                    params,
                )
                row = cur.fetchone()

    except Exception as e:
        logger.error("Insights funnel error: %s", str(e))
        return jsonify({"error": "Failed to fetch funnel data"}), 500

    stages = [
        {"name": "invited", "count": row[0] or 0},
        {"name": "started", "count": row[1] or 0},
        {"name": "submitted", "count": row[2] or 0},
        {"name": "reviewed", "count": row[3] or 0},
        {"name": "shortlisted", "count": row[4] or 0},
        {"name": "rejected", "count": row[5] or 0},
    ]

    return jsonify({"stages": stages})


# ──────────────────────────────────────────────────────────────
# GET /api/insights/score-distribution
# Score histogram: 0-20, 20-40, 40-60, 60-80, 80-100
# ──────────────────────────────────────────────────────────────

@insights_bp.route("/score-distribution", methods=["GET"])
@require_auth
def insights_score_distribution():
    """Return score histogram buckets."""
    user_id = g.current_user["id"]
    date_from, date_to, campaign_id = _parse_filters()
    where, params = _build_where(user_id, date_from, date_to, campaign_id)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) FILTER (WHERE cand.overall_score >= 0  AND cand.overall_score < 20)  AS bucket_0_20,
                        COUNT(*) FILTER (WHERE cand.overall_score >= 20 AND cand.overall_score < 40)  AS bucket_20_40,
                        COUNT(*) FILTER (WHERE cand.overall_score >= 40 AND cand.overall_score < 60)  AS bucket_40_60,
                        COUNT(*) FILTER (WHERE cand.overall_score >= 60 AND cand.overall_score < 80)  AS bucket_60_80,
                        COUNT(*) FILTER (WHERE cand.overall_score >= 80 AND cand.overall_score <= 100) AS bucket_80_100
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    {where}
                      AND cand.overall_score IS NOT NULL
                    """,
                    params,
                )
                row = cur.fetchone()

    except Exception as e:
        logger.error("Insights score-distribution error: %s", str(e))
        return jsonify({"error": "Failed to fetch score distribution"}), 500

    buckets = [
        {"range": "0-20", "count": row[0] or 0},
        {"range": "20-40", "count": row[1] or 0},
        {"range": "40-60", "count": row[2] or 0},
        {"range": "60-80", "count": row[3] or 0},
        {"range": "80-100", "count": row[4] or 0},
    ]

    return jsonify({"buckets": buckets})


# ──────────────────────────────────────────────────────────────
# GET /api/insights/by-campaign
# Per-campaign comparison table
# ──────────────────────────────────────────────────────────────

@insights_bp.route("/by-campaign", methods=["GET"])
@require_auth
def insights_by_campaign():
    """Return per-campaign stats for comparison."""
    user_id = g.current_user["id"]
    date_from, date_to, _ = _parse_filters()

    clauses = ["c.user_id = %s"]
    params = [user_id]

    if date_from:
        clauses.append("cand.created_at >= %s::date")
        params.append(date_from)
    if date_to:
        clauses.append("cand.created_at < (%s::date + INTERVAL '1 day')")
        params.append(date_to)

    where = "WHERE " + " AND ".join(clauses)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        c.id,
                        c.name,
                        COUNT(cand.id) FILTER (WHERE cand.status != 'erased') AS candidate_count,
                        COUNT(cand.id) FILTER (WHERE cand.status = 'submitted') AS submitted_count,
                        ROUND(
                            AVG(cand.overall_score) FILTER (WHERE cand.overall_score IS NOT NULL AND cand.status != 'erased')::numeric,
                            1
                        ) AS avg_score
                    FROM campaigns c
                    LEFT JOIN candidates cand ON cand.campaign_id = c.id
                    {where}
                    GROUP BY c.id, c.name
                    ORDER BY c.created_at DESC
                    """,
                    params,
                )
                rows = cur.fetchall()

    except Exception as e:
        logger.error("Insights by-campaign error: %s", str(e))
        return jsonify({"error": "Failed to fetch campaign comparison"}), 500

    campaigns = []
    for row in rows:
        total = row[2] or 0
        submitted = row[3] or 0
        campaigns.append({
            "campaign_id": str(row[0]),
            "name": row[1],
            "candidate_count": total,
            "submitted_count": submitted,
            "completion_rate": round(submitted / total * 100, 1) if total > 0 else 0,
            "avg_score": float(row[4]) if row[4] else None,
        })

    return jsonify({"campaigns": campaigns})


# ──────────────────────────────────────────────────────────────
# GET /api/insights/dropoff
# Per-question abandonment analysis
# ──────────────────────────────────────────────────────────────

@insights_bp.route("/dropoff", methods=["GET"])
@require_auth
def insights_dropoff():
    """
    Drop-off analysis: per-question score variance, abandonment by question number,
    and per-campaign completion comparison.
    """
    user_id = g.current_user["id"]
    date_from, date_to, campaign_id = _parse_filters()
    where, params = _build_where(user_id, date_from, date_to, campaign_id)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Per-question stats: avg score, score variance, number of answers
                cur.execute(
                    f"""
                    SELECT
                        va.question_index,
                        COUNT(va.id) AS answer_count,
                        ROUND(AVG(ais.overall_score)::numeric, 1) AS avg_score,
                        ROUND(STDDEV(ais.overall_score)::numeric, 1) AS score_stddev
                    FROM video_answers va
                    JOIN candidates cand ON va.candidate_id = cand.id
                    JOIN campaigns c ON cand.campaign_id = c.id
                    LEFT JOIN ai_scores ais ON ais.video_answer_id = va.id
                    {where}
                    GROUP BY va.question_index
                    ORDER BY va.question_index
                    """,
                    params,
                )
                question_rows = cur.fetchall()

                # Abandonment: candidates who started but didn't submit, by last answered question
                cur.execute(
                    f"""
                    SELECT
                        COALESCE(max_q.last_question, -1) AS last_question_answered,
                        COUNT(*) AS abandoned_count
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    LEFT JOIN (
                        SELECT candidate_id, MAX(question_index) AS last_question
                        FROM video_answers
                        WHERE storage_key IS NOT NULL
                        GROUP BY candidate_id
                    ) max_q ON max_q.candidate_id = cand.id
                    {where}
                      AND cand.status IN ('invited', 'started')
                      AND cand.consent_given = TRUE
                    GROUP BY max_q.last_question
                    ORDER BY max_q.last_question
                    """,
                    params,
                )
                abandonment_rows = cur.fetchall()

                # Completion comparison by campaign
                cur.execute(
                    f"""
                    SELECT
                        c.id, c.name,
                        COUNT(cand.id) AS total,
                        COUNT(cand.id) FILTER (WHERE cand.status = 'submitted') AS submitted,
                        COUNT(cand.id) FILTER (WHERE cand.status IN ('invited', 'started') AND cand.consent_given = TRUE) AS abandoned
                    FROM campaigns c
                    LEFT JOIN candidates cand ON cand.campaign_id = c.id AND cand.status != 'erased'
                    WHERE c.user_id = %s
                    GROUP BY c.id, c.name
                    HAVING COUNT(cand.id) > 0
                    ORDER BY c.created_at DESC
                    """,
                    (user_id,),
                )
                comparison_rows = cur.fetchall()

    except Exception as e:
        logger.error("Insights dropoff error: %s", str(e))
        return jsonify({"error": "Failed to fetch drop-off analysis"}), 500

    return jsonify({
        "per_question": [
            {
                "question_index": r[0],
                "answer_count": r[1],
                "avg_score": float(r[2]) if r[2] else None,
                "score_variance": float(r[3]) if r[3] else None,
            }
            for r in question_rows
        ],
        "abandonment": [
            {
                "last_question_answered": r[0],
                "count": r[1],
            }
            for r in abandonment_rows
        ],
        "campaign_completion": [
            {
                "campaign_id": str(r[0]),
                "name": r[1],
                "total": r[2],
                "submitted": r[3],
                "abandoned": r[4],
                "completion_rate": round(r[3] / r[2] * 100, 1) if r[2] > 0 else 0,
            }
            for r in comparison_rows
        ],
    })
