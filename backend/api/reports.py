"""
CoreMatch — Reports Blueprint
Advanced analytics with trend data and CSV/PDF export.
"""
import csv
import io
import json
import logging
from flask import Blueprint, request, jsonify, g, Response
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
reports_bp = Blueprint("reports", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/reports/executive-summary — executive-ready overview
# ──────────────────────────────────────────────────────────────

@reports_bp.route("/executive-summary", methods=["GET"])
@require_auth
def executive_summary():
    """
    Executive summary with trends: monthly hiring velocity, quality metrics,
    reviewer productivity, and campaign performance.
    """
    date_from = request.args.get("from")
    date_to = request.args.get("to")

    conditions = ["camp.user_id = %s"]
    params = [g.current_user["id"]]

    if date_from:
        conditions.append("c.created_at >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("c.created_at <= %s")
        params.append(date_to)

    where_clause = " AND ".join(conditions)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Overall KPIs
                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) as total_candidates,
                        COUNT(*) FILTER (WHERE c.status IN ('submitted', 'scored')) as total_submitted,
                        COUNT(*) FILTER (WHERE c.hr_decision = 'shortlisted') as total_shortlisted,
                        COUNT(*) FILTER (WHERE c.hr_decision = 'rejected') as total_rejected,
                        AVG(c.overall_score) FILTER (WHERE c.overall_score IS NOT NULL) as avg_score,
                        COUNT(DISTINCT c.campaign_id) as campaigns_used
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE {where_clause} AND c.status != 'erased'
                    """,
                    params,
                )
                kpi_row = cur.fetchone()

                # Monthly trend data (last 12 months)
                cur.execute(
                    """
                    SELECT
                        DATE_TRUNC('month', c.created_at) as month,
                        COUNT(*) as invited,
                        COUNT(*) FILTER (WHERE c.status IN ('submitted', 'scored')) as submitted,
                        COUNT(*) FILTER (WHERE c.hr_decision = 'shortlisted') as shortlisted,
                        AVG(c.overall_score) FILTER (WHERE c.overall_score IS NOT NULL) as avg_score
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE camp.user_id = %s AND c.status != 'erased'
                      AND c.created_at >= NOW() - INTERVAL '12 months'
                    GROUP BY DATE_TRUNC('month', c.created_at)
                    ORDER BY month ASC
                    """,
                    (g.current_user["id"],),
                )
                trend_rows = cur.fetchall()

                # Top campaigns by volume
                cur.execute(
                    f"""
                    SELECT camp.id, camp.name, camp.job_title,
                           COUNT(*) as candidate_count,
                           COUNT(*) FILTER (WHERE c.status IN ('submitted', 'scored')) as submitted_count,
                           AVG(c.overall_score) FILTER (WHERE c.overall_score IS NOT NULL) as avg_score
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE {where_clause} AND c.status != 'erased'
                    GROUP BY camp.id, camp.name, camp.job_title
                    ORDER BY candidate_count DESC
                    LIMIT 10
                    """,
                    params,
                )
                campaign_rows = cur.fetchall()

                # Reviewer productivity (from evaluations)
                cur.execute(
                    """
                    SELECT u.full_name, COUNT(ce.id) as evaluations_count,
                           AVG(ce.overall_rating) as avg_rating
                    FROM candidate_evaluations ce
                    JOIN users u ON ce.reviewer_id = u.id
                    WHERE ce.reviewer_id IN (
                        SELECT user_id FROM team_members WHERE owner_id = %s
                        UNION SELECT %s
                    )
                    GROUP BY u.full_name
                    ORDER BY evaluations_count DESC
                    LIMIT 10
                    """,
                    (g.current_user["id"], g.current_user["id"]),
                )
                reviewer_rows = cur.fetchall()

    except Exception as e:
        logger.error("Executive summary error: %s", str(e))
        return jsonify({"error": "Failed to generate executive summary"}), 500

    total = kpi_row[0] or 0
    submitted = kpi_row[1] or 0

    return jsonify({
        "kpis": {
            "total_candidates": total,
            "total_submitted": submitted,
            "total_shortlisted": kpi_row[2] or 0,
            "total_rejected": kpi_row[3] or 0,
            "avg_score": round(float(kpi_row[4]), 1) if kpi_row[4] else None,
            "campaigns_used": kpi_row[5] or 0,
            "completion_rate": round(submitted / total * 100, 1) if total > 0 else 0,
            "shortlist_rate": round((kpi_row[2] or 0) / max(total, 1) * 100, 1),
        },
        "monthly_trends": [
            {
                "month": r[0].isoformat() if r[0] else None,
                "invited": r[1] or 0,
                "submitted": r[2] or 0,
                "shortlisted": r[3] or 0,
                "avg_score": round(float(r[4]), 1) if r[4] else None,
            }
            for r in trend_rows
        ],
        "top_campaigns": [
            {
                "id": str(r[0]),
                "name": r[1],
                "job_title": r[2],
                "candidate_count": r[3],
                "submitted_count": r[4],
                "avg_score": round(float(r[5]), 1) if r[5] else None,
            }
            for r in campaign_rows
        ],
        "reviewer_productivity": [
            {
                "name": r[0],
                "evaluations_count": r[1],
                "avg_rating": round(float(r[2]), 1) if r[2] else None,
            }
            for r in reviewer_rows
        ],
    })


# ──────────────────────────────────────────────────────────────
# GET /api/reports/export/csv — export full report as CSV
# ──────────────────────────────────────────────────────────────

@reports_bp.route("/export/csv", methods=["GET"])
@require_auth
def export_csv():
    """Export comprehensive candidate data as CSV."""
    campaign_id = request.args.get("campaign_id")

    conditions = ["camp.user_id = %s", "c.status != 'erased'"]
    params = [g.current_user["id"]]

    if campaign_id:
        conditions.append("c.campaign_id = %s")
        params.append(campaign_id)

    where_clause = " AND ".join(conditions)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT c.full_name, c.email, camp.name as campaign_name,
                           camp.job_title, c.status, c.overall_score, c.tier,
                           c.hr_decision, c.reference_id, c.nationality,
                           c.created_at, c.updated_at
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE {where_clause}
                    ORDER BY c.created_at DESC
                    """,
                    params,
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("Export CSV error: %s", str(e))
        return jsonify({"error": "Failed to export data"}), 500

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Full Name", "Email", "Campaign", "Job Title", "Status",
        "AI Score", "Tier", "Decision", "Reference ID", "Nationality",
        "Created At", "Updated At",
    ])

    for r in rows:
        writer.writerow([
            r[0], r[1], r[2], r[3], r[4],
            round(float(r[5]), 1) if r[5] is not None else "",
            r[6] or "", r[7] or "", r[8] or "", r[9] or "",
            r[10].isoformat() if r[10] else "",
            r[11].isoformat() if r[11] else "",
        ])

    response = Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=corematch-report.csv"},
    )
    return response


# ──────────────────────────────────────────────────────────────
# GET /api/reports/tier-distribution — score tier breakdown
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
# GET /api/reports/export/pdf — export executive report as PDF
# ──────────────────────────────────────────────────────────────

@reports_bp.route("/export/pdf", methods=["GET"])
@require_auth
def export_pdf():
    """Export an executive-ready PDF report with KPIs, tier distribution, and top campaigns."""
    campaign_id = request.args.get("campaign_id")

    conditions = ["camp.user_id = %s", "c.status != 'erased'"]
    params = [g.current_user["id"]]

    if campaign_id:
        conditions.append("c.campaign_id = %s")
        params.append(campaign_id)

    where_clause = " AND ".join(conditions)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Overall KPIs
                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) as total_candidates,
                        COUNT(*) FILTER (WHERE c.status IN ('submitted', 'scored')) as total_submitted,
                        COUNT(*) FILTER (WHERE c.hr_decision = 'shortlisted') as total_shortlisted,
                        COUNT(*) FILTER (WHERE c.hr_decision = 'rejected') as total_rejected,
                        AVG(c.overall_score) FILTER (WHERE c.overall_score IS NOT NULL) as avg_score,
                        COUNT(DISTINCT c.campaign_id) as campaigns_used
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE {where_clause}
                    """,
                    params,
                )
                kpi_row = cur.fetchone()

                # Tier distribution
                cur.execute(
                    f"""
                    SELECT c.tier, COUNT(*) as count
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE {where_clause} AND c.tier IS NOT NULL
                    GROUP BY c.tier
                    ORDER BY count DESC
                    """,
                    params,
                )
                tier_rows = cur.fetchall()

                # Top campaigns
                cur.execute(
                    f"""
                    SELECT camp.name, camp.job_title, COUNT(*) as candidate_count,
                           AVG(c.overall_score) FILTER (WHERE c.overall_score IS NOT NULL) as avg_score
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE {where_clause}
                    GROUP BY camp.name, camp.job_title
                    ORDER BY candidate_count DESC
                    LIMIT 10
                    """,
                    params,
                )
                campaign_rows = cur.fetchall()
    except Exception as e:
        logger.error("Export PDF error: %s", str(e))
        return jsonify({"error": "Failed to generate PDF report"}), 500

    # Build PDF
    import datetime
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "CoreMatch Executive Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True, align="C")
    pdf.ln(10)

    # KPIs Section
    total = kpi_row[0] or 0
    submitted = kpi_row[1] or 0
    shortlisted = kpi_row[2] or 0
    rejected = kpi_row[3] or 0
    avg_score = round(float(kpi_row[4]), 1) if kpi_row[4] else 0
    campaigns_used = kpi_row[5] or 0
    completion_rate = round(submitted / total * 100, 1) if total > 0 else 0

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Key Performance Indicators", ln=True)
    pdf.set_font("Helvetica", "", 11)

    kpi_data = [
        ("Total Candidates", str(total)),
        ("Submitted", str(submitted)),
        ("Shortlisted", str(shortlisted)),
        ("Rejected", str(rejected)),
        ("Avg AI Score", str(avg_score)),
        ("Completion Rate", f"{completion_rate}%"),
        ("Campaigns", str(campaigns_used)),
    ]

    col_w = 95
    for i, (label, value) in enumerate(kpi_data):
        x_pos = 10 + (i % 2) * col_w
        pdf.set_x(x_pos)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 7, label + ":", align="L")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(50, 7, value, ln=(i % 2 == 1))

    if len(kpi_data) % 2 == 1:
        pdf.ln()
    pdf.ln(8)

    # Tier Distribution
    if tier_rows:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Tier Distribution", ln=True)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(80, 7, "Tier", border=1)
        pdf.cell(50, 7, "Count", border=1)
        pdf.cell(50, 7, "Percentage", border=1, ln=True)

        total_tiered = sum(r[1] for r in tier_rows)
        pdf.set_font("Helvetica", "", 10)
        for r in tier_rows:
            pct = round(r[1] / total_tiered * 100, 1) if total_tiered > 0 else 0
            tier_label = (r[0] or "Unknown").replace("_", " ").title()
            pdf.cell(80, 7, tier_label, border=1)
            pdf.cell(50, 7, str(r[1]), border=1)
            pdf.cell(50, 7, f"{pct}%", border=1, ln=True)
        pdf.ln(8)

    # Top Campaigns
    if campaign_rows:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Top Campaigns", ln=True)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(60, 7, "Campaign", border=1)
        pdf.cell(50, 7, "Job Title", border=1)
        pdf.cell(35, 7, "Candidates", border=1)
        pdf.cell(35, 7, "Avg Score", border=1, ln=True)

        pdf.set_font("Helvetica", "", 9)
        for r in campaign_rows:
            name = (r[0] or "")[:25]
            job = (r[1] or "")[:22]
            pdf.cell(60, 7, name, border=1)
            pdf.cell(50, 7, job, border=1)
            pdf.cell(35, 7, str(r[2]), border=1)
            pdf.cell(35, 7, str(round(float(r[3]), 1)) if r[3] else "N/A", border=1, ln=True)

    # Output PDF
    pdf_bytes = pdf.output()

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=corematch-report.pdf"},
    )


# ──────────────────────────────────────────────────────────────
# GET /api/reports/tier-distribution — score tier breakdown
# ──────────────────────────────────────────────────────────────

@reports_bp.route("/tier-distribution", methods=["GET"])
@require_auth
def tier_distribution():
    """Get score tier distribution across all campaigns or a specific one."""
    campaign_id = request.args.get("campaign_id")

    conditions = ["camp.user_id = %s", "c.status != 'erased'", "c.tier IS NOT NULL"]
    params = [g.current_user["id"]]

    if campaign_id:
        conditions.append("c.campaign_id = %s")
        params.append(campaign_id)

    where_clause = " AND ".join(conditions)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT c.tier, COUNT(*) as count,
                           AVG(c.overall_score) as avg_score
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE {where_clause}
                    GROUP BY c.tier
                    ORDER BY avg_score DESC NULLS LAST
                    """,
                    params,
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("Tier distribution error: %s", str(e))
        return jsonify({"error": "Failed to fetch tier distribution"}), 500

    total = sum(r[1] for r in rows)

    return jsonify({
        "distribution": [
            {
                "tier": r[0],
                "count": r[1],
                "percentage": round(r[1] / total * 100, 1) if total > 0 else 0,
                "avg_score": round(float(r[2]), 1) if r[2] else None,
            }
            for r in rows
        ],
        "total": total,
    })
