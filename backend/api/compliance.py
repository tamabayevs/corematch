"""
CoreMatch — PDPL Compliance Blueprint
Audit log viewer, compliance overview, data retention reports, and retention policy management.
All endpoints require JWT auth.
"""
import logging
import json
import csv
import io
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, g, Response
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
compliance_bp = Blueprint("compliance", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/compliance/audit-log
# Paginated audit log viewer with filters
# ──────────────────────────────────────────────────────────────

@compliance_bp.route("/audit-log", methods=["GET"])
@require_auth
def audit_log():
    """Paginated audit log entries for campaigns/candidates owned by current user."""
    user_id = g.current_user["id"]
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 50)), 1), 200)
    offset = (page - 1) * per_page

    # Build filter clauses
    filters = []
    params = [user_id, user_id]

    filter_user_id = request.args.get("user_id")
    if filter_user_id:
        filters.append("al.user_id = %s")
        params.append(filter_user_id)

    filter_action = request.args.get("action")
    if filter_action:
        filters.append("al.action = %s")
        params.append(filter_action)

    filter_entity_type = request.args.get("entity_type")
    if filter_entity_type:
        filters.append("al.entity_type = %s")
        params.append(filter_entity_type)

    filter_from = request.args.get("from")
    if filter_from:
        filters.append("al.created_at >= %s")
        params.append(filter_from)

    filter_to = request.args.get("to")
    if filter_to:
        filters.append("al.created_at <= %s")
        params.append(filter_to)

    where_extra = ""
    if filters:
        where_extra = "AND " + " AND ".join(filters)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Only return entries for campaigns/candidates owned by current user
                base_where = """
                    WHERE (
                        al.user_id = %s
                        OR al.entity_id IN (
                            SELECT c.id FROM campaigns c WHERE c.user_id = %s
                            UNION
                            SELECT cand.id FROM candidates cand
                            JOIN campaigns c2 ON cand.campaign_id = c2.id
                            WHERE c2.user_id = %s
                        )
                    )
                """
                # Add the third user_id param for the subquery
                params_with_ownership = [user_id, user_id, user_id] + params[2:]

                cur.execute(
                    f"""
                    SELECT al.id, al.user_id, u.full_name, al.action, al.entity_type,
                           al.entity_id, al.metadata, al.ip_address, al.created_at
                    FROM audit_log al
                    LEFT JOIN users u ON al.user_id = u.id
                    {base_where}
                    {where_extra}
                    ORDER BY al.created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    params_with_ownership + [per_page, offset],
                )
                rows = cur.fetchall()

                # Total count
                cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM audit_log al
                    {base_where}
                    {where_extra}
                    """,
                    params_with_ownership,
                )
                total = cur.fetchone()[0]

    except Exception as e:
        logger.error("Audit log error: %s", str(e))
        return jsonify({"error": "Failed to fetch audit log"}), 500

    entries = []
    for row in rows:
        entries.append({
            "id": str(row[0]),
            "user_id": str(row[1]) if row[1] else None,
            "user_name": row[2],
            "action": row[3],
            "entity_type": row[4],
            "entity_id": str(row[5]) if row[5] else None,
            "metadata": row[6] or {},
            "ip_address": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
        })

    return jsonify({
        "entries": entries,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max((total + per_page - 1) // per_page, 1),
    })


# ──────────────────────────────────────────────────────────────
# GET /api/compliance/audit-log/export
# CSV export of audit log (same filters, no pagination)
# ──────────────────────────────────────────────────────────────

@compliance_bp.route("/audit-log/export", methods=["GET"])
@require_auth
def audit_log_export():
    """Export audit log as CSV file."""
    user_id = g.current_user["id"]

    # Build filter clauses (same as above)
    filters = []
    params = [user_id, user_id, user_id]

    filter_action = request.args.get("action")
    if filter_action:
        filters.append("al.action = %s")
        params.append(filter_action)

    filter_entity_type = request.args.get("entity_type")
    if filter_entity_type:
        filters.append("al.entity_type = %s")
        params.append(filter_entity_type)

    filter_from = request.args.get("from")
    if filter_from:
        filters.append("al.created_at >= %s")
        params.append(filter_from)

    filter_to = request.args.get("to")
    if filter_to:
        filters.append("al.created_at <= %s")
        params.append(filter_to)

    where_extra = ""
    if filters:
        where_extra = "AND " + " AND ".join(filters)

    base_where = """
        WHERE (
            al.user_id = %s
            OR al.entity_id IN (
                SELECT c.id FROM campaigns c WHERE c.user_id = %s
                UNION
                SELECT cand.id FROM candidates cand
                JOIN campaigns c2 ON cand.campaign_id = c2.id
                WHERE c2.user_id = %s
            )
        )
    """

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT al.created_at, u.full_name, al.action, al.entity_type,
                           al.entity_id, al.ip_address, al.metadata
                    FROM audit_log al
                    LEFT JOIN users u ON al.user_id = u.id
                    {base_where}
                    {where_extra}
                    ORDER BY al.created_at DESC
                    """,
                    params,
                )
                rows = cur.fetchall()

    except Exception as e:
        logger.error("Audit log export error: %s", str(e))
        return jsonify({"error": "Failed to export audit log"}), 500

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "User", "Action", "Entity Type", "Entity ID", "IP Address", "Details"])

    for row in rows:
        metadata_str = json.dumps(row[6]) if row[6] else ""
        writer.writerow([
            row[0].isoformat() if row[0] else "",
            row[1] or "",
            row[2] or "",
            row[3] or "",
            str(row[4]) if row[4] else "",
            row[5] or "",
            metadata_str,
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=audit_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


# ──────────────────────────────────────────────────────────────
# GET /api/compliance/overview
# Compliance statistics for the current user
# ──────────────────────────────────────────────────────────────

@compliance_bp.route("/overview", methods=["GET"])
@require_auth
def compliance_overview():
    """Compliance statistics: totals, consent rates, data age, pending erasure."""
    user_id = g.current_user["id"]

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Total candidates (non-erased)
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s AND cand.status != 'erased'
                    """,
                    (user_id,),
                )
                total_candidates = cur.fetchone()[0]

                # Erased candidates
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s AND cand.status = 'erased'
                    """,
                    (user_id,),
                )
                erased_candidates = cur.fetchone()[0]

                # Consent rate
                cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE cand.consent_given = TRUE) AS consented,
                        COUNT(*) AS total
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s AND cand.status != 'erased'
                    """,
                    (user_id,),
                )
                consent_row = cur.fetchone()
                consent_rate = round(
                    (consent_row[0] / consent_row[1] * 100), 1
                ) if consent_row[1] > 0 else 0

                # Average data age in days
                cur.execute(
                    """
                    SELECT ROUND(AVG(EXTRACT(EPOCH FROM (NOW() - cand.created_at)) / 86400)::numeric, 1)
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s AND cand.status != 'erased'
                    """,
                    (user_id,),
                )
                avg_data_age_days = float(cur.fetchone()[0] or 0)

                # Get user's retention policy
                cur.execute(
                    "SELECT COALESCE(retention_months, 12) FROM users WHERE id = %s",
                    (user_id,),
                )
                retention_months = cur.fetchone()[0]

                # Pending erasure: candidates past retention period that are not yet erased
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s
                      AND cand.status != 'erased'
                      AND cand.created_at < NOW() - (INTERVAL '1 month' * %s)
                    """,
                    (user_id, retention_months),
                )
                pending_erasure = cur.fetchone()[0]

    except Exception as e:
        logger.error("Compliance overview error: %s", str(e))
        return jsonify({"error": "Failed to fetch compliance overview"}), 500

    return jsonify({
        "total_candidates": total_candidates,
        "erased_candidates": erased_candidates,
        "consent_rate": consent_rate,
        "avg_data_age_days": avg_data_age_days,
        "pending_erasure": pending_erasure,
        "retention_months": retention_months,
    })


# ──────────────────────────────────────────────────────────────
# GET /api/compliance/retention-report
# Candidates approaching data expiry (within 30 days)
# ──────────────────────────────────────────────────────────────

@compliance_bp.route("/retention-report", methods=["GET"])
@require_auth
def retention_report():
    """Data approaching expiry — candidates within 30 days of retention limit."""
    user_id = g.current_user["id"]

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get user's retention policy
                cur.execute(
                    "SELECT COALESCE(retention_months, 12) FROM users WHERE id = %s",
                    (user_id,),
                )
                retention_months = cur.fetchone()[0]

                # Find candidates where expiry is within 30 days from now
                cur.execute(
                    """
                    SELECT cand.id, cand.full_name, cand.email, c.name AS campaign_name,
                           cand.created_at,
                           EXTRACT(DAY FROM (
                               cand.created_at + (INTERVAL '1 month' * %s) - NOW()
                           ))::integer AS days_until_expiry
                    FROM candidates cand
                    JOIN campaigns c ON cand.campaign_id = c.id
                    WHERE c.user_id = %s
                      AND cand.status != 'erased'
                      AND cand.created_at + (INTERVAL '1 month' * %s) < NOW() + INTERVAL '30 days'
                      AND cand.created_at + (INTERVAL '1 month' * %s) > NOW() - INTERVAL '30 days'
                    ORDER BY days_until_expiry ASC
                    """,
                    (retention_months, user_id, retention_months, retention_months),
                )
                rows = cur.fetchall()

    except Exception as e:
        logger.error("Retention report error: %s", str(e))
        return jsonify({"error": "Failed to fetch retention report"}), 500

    candidates = []
    for row in rows:
        candidates.append({
            "candidate_id": str(row[0]),
            "full_name": row[1],
            "email": row[2],
            "campaign_name": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "days_until_expiry": row[5],
        })

    return jsonify({
        "candidates": candidates,
        "retention_months": retention_months,
    })


# ──────────────────────────────────────────────────────────────
# PUT /api/compliance/retention-policy
# Update the user's default data retention period
# ──────────────────────────────────────────────────────────────

@compliance_bp.route("/retention-policy", methods=["PUT"])
@require_auth
def update_retention_policy():
    """Set the default data retention period for the current user."""
    user_id = g.current_user["id"]
    data = request.get_json()

    if not data or "retention_months" not in data:
        return jsonify({"error": "retention_months is required"}), 400

    retention_months = data["retention_months"]
    if retention_months not in (6, 12, 24):
        return jsonify({"error": "retention_months must be 6, 12, or 24"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET retention_months = %s WHERE id = %s",
                    (retention_months, user_id),
                )

                # Log the action in audit_log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        "retention_policy.updated",
                        "user",
                        user_id,
                        json.dumps({"retention_months": retention_months}),
                        request.remote_addr,
                    ),
                )

    except Exception as e:
        logger.error("Retention policy update error: %s", str(e))
        return jsonify({"error": "Failed to update retention policy"}), 500

    return jsonify({
        "message": "Retention policy updated",
        "retention_months": retention_months,
    })
