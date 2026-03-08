"""
CoreMatch — Demand Blueprint
Waitlist signup (public) + page event tracking (public) + demand stats (admin auth).
Zero external dependencies — all analytics stored in PostgreSQL.
"""
import json
import os
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
demand_bp = Blueprint("demand", __name__)


# ──────────────────────────────────────────────────────────────
# POST /api/demand/waitlist — public, no auth
# ──────────────────────────────────────────────────────────────

@demand_bp.route("/waitlist", methods=["POST"])
def join_waitlist():
    """Add an email to the waitlist. Sends auto-reply confirmation."""
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email_raw = (data.get("email") or "").strip().lower()
    company_name = (data.get("company_name") or "").strip() or None
    source = (data.get("source") or "landing_page").strip()
    utm_source = (data.get("utm_source") or "").strip() or None
    utm_medium = (data.get("utm_medium") or "").strip() or None
    utm_campaign = (data.get("utm_campaign") or "").strip() or None

    if not full_name:
        return jsonify({"error": "Full name is required"}), 400
    if not email_raw:
        return jsonify({"error": "Email is required"}), 400
    if len(full_name) > 300:
        return jsonify({"error": "Name too long"}), 400

    from email_validator import validate_email, EmailNotValidError
    try:
        result = validate_email(email_raw, check_deliverability=False)
        email = result.normalized
    except EmailNotValidError:
        return jsonify({"error": "Invalid email address"}), 400

    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip_address:
        ip_address = ip_address.split(",")[0].strip()

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO waitlist_signups
                        (full_name, email, company_name, source, utm_source, utm_medium, utm_campaign, ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                    """,
                    (full_name, email, company_name, source, utm_source, utm_medium, utm_campaign, ip_address),
                )
                row = cur.fetchone()

        # Send auto-reply email (fire-and-forget)
        try:
            from services.email_service import get_email_service
            email_svc = get_email_service()
            email_svc.send_waitlist_confirmation(email, full_name)
        except Exception as e:
            logger.warning("Waitlist confirmation email failed: %s", e)

        return jsonify({
            "message": "Successfully joined the waitlist",
            "id": str(row[0]),
        }), 201

    except Exception as e:
        if "idx_waitlist_signups_email" in str(e) or "duplicate key" in str(e).lower():
            return jsonify({"error": "This email is already on the waitlist"}), 409
        logger.error("Waitlist signup failed: %s", str(e))
        return jsonify({"error": "Failed to join waitlist"}), 500


# ──────────────────────────────────────────────────────────────
# POST /api/demand/track — public, no auth
# Lightweight page event tracking (replaces external analytics)
# ──────────────────────────────────────────────────────────────

VALID_EVENT_TYPES = ("page_view", "cta_click", "waitlist_submit", "scroll_50", "scroll_100")

@demand_bp.route("/track", methods=["POST"])
def track_event():
    """Log a page event. Fire-and-forget from frontend."""
    data = request.get_json(silent=True) or {}
    event_type = (data.get("event_type") or "").strip()

    if event_type not in VALID_EVENT_TYPES:
        return jsonify({"error": "Invalid event_type"}), 400

    page = (data.get("page") or "/").strip()[:500]
    referrer = (data.get("referrer") or "").strip()[:500] or None
    utm_source = (data.get("utm_source") or "").strip()[:200] or None
    utm_medium = (data.get("utm_medium") or "").strip()[:200] or None
    utm_campaign = (data.get("utm_campaign") or "").strip()[:200] or None

    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip_address:
        ip_address = ip_address.split(",")[0].strip()
    user_agent = (request.headers.get("User-Agent") or "")[:500] or None

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO page_events
                        (event_type, page, referrer, utm_source, utm_medium, utm_campaign, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (event_type, page, referrer, utm_source, utm_medium, utm_campaign, ip_address, user_agent),
                )
        return jsonify({"ok": True}), 201
    except Exception as e:
        logger.warning("Track event failed: %s", e)
        return jsonify({"ok": False}), 200  # Don't fail the frontend


# ──────────────────────────────────────────────────────────────
# GET /api/demand/stats — requires auth
# ──────────────────────────────────────────────────────────────

@demand_bp.route("/stats", methods=["GET"])
@require_auth
def demand_stats():
    """Return all demand metrics: waitlist, page events, LinkedIn outreach."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # ── Waitlist metrics ──
                cur.execute("SELECT COUNT(*) FROM waitlist_signups")
                total_signups = cur.fetchone()[0]

                cur.execute(
                    "SELECT COUNT(*) FROM waitlist_signups WHERE created_at >= CURRENT_DATE"
                )
                signups_today = cur.fetchone()[0]

                cur.execute(
                    "SELECT COUNT(*) FROM waitlist_signups WHERE created_at >= date_trunc('week', CURRENT_DATE)"
                )
                signups_this_week = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT date_trunc('day', created_at)::date AS day, COUNT(*) AS count
                    FROM waitlist_signups
                    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY day ORDER BY day ASC
                    """
                )
                signups_over_time = [
                    {"date": str(row[0]), "count": row[1]} for row in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT company_name, COUNT(*) AS count
                    FROM waitlist_signups
                    WHERE company_name IS NOT NULL AND company_name != ''
                    GROUP BY company_name ORDER BY count DESC LIMIT 10
                    """
                )
                top_companies = [
                    {"company": row[0], "count": row[1]} for row in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT source, COUNT(*) AS count
                    FROM waitlist_signups GROUP BY source ORDER BY count DESC
                    """
                )
                source_breakdown = [
                    {"source": row[0], "count": row[1]} for row in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT id, full_name, email, company_name, source, created_at
                    FROM waitlist_signups ORDER BY created_at DESC LIMIT 20
                    """
                )
                recent_signups = [
                    {
                        "id": str(row[0]),
                        "full_name": row[1],
                        "email": row[2],
                        "company_name": row[3],
                        "source": row[4],
                        "created_at": row[5].isoformat() if row[5] else None,
                    }
                    for row in cur.fetchall()
                ]

                # ── Page event metrics ──
                cur.execute(
                    """
                    SELECT event_type, COUNT(*) AS count
                    FROM page_events
                    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY event_type ORDER BY count DESC
                    """
                )
                event_breakdown = [
                    {"event": row[0], "count": row[1]} for row in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT date_trunc('day', created_at)::date AS day, COUNT(*) AS count
                    FROM page_events
                    WHERE event_type = 'page_view'
                      AND created_at >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY day ORDER BY day ASC
                    """
                )
                page_views_over_time = [
                    {"date": str(row[0]), "count": row[1]} for row in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT referrer, COUNT(*) AS count
                    FROM page_events
                    WHERE referrer IS NOT NULL AND referrer != ''
                      AND created_at >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY referrer ORDER BY count DESC LIMIT 10
                    """
                )
                top_referrers = [
                    {"referrer": row[0], "count": row[1]} for row in cur.fetchall()
                ]

        # ── LinkedIn outreach metrics (from local JSON) ──
        linkedin_metrics = _read_linkedin_metrics()

        return jsonify({
            "waitlist": {
                "total": total_signups,
                "today": signups_today,
                "this_week": signups_this_week,
                "over_time": signups_over_time,
                "top_companies": top_companies,
                "source_breakdown": source_breakdown,
                "recent": recent_signups,
            },
            "events": {
                "breakdown": event_breakdown,
                "page_views_over_time": page_views_over_time,
                "top_referrers": top_referrers,
            },
            "linkedin": linkedin_metrics,
        }), 200

    except Exception as e:
        logger.error("Demand stats failed: %s", str(e))
        return jsonify({"error": "Failed to fetch demand stats"}), 500


# ──────────────────────────────────────────────────────────────
# Helper: Read LinkedIn outreach JSON files
# ──────────────────────────────────────────────────────────────

def _read_linkedin_metrics():
    """Read leads.json and outreach-log.json. Returns empty if files don't exist (e.g. on Railway)."""
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        ".claude", "skills", "agent-linkedin-outreach", "data",
    )

    leads = []
    leads_path = os.path.join(data_dir, "leads.json")
    try:
        if os.path.exists(leads_path):
            with open(leads_path, "r") as f:
                leads = json.load(f)
    except Exception:
        pass

    log_entries = []
    log_path = os.path.join(data_dir, "outreach-log.json")
    try:
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                log_entries = json.load(f)
    except Exception:
        pass

    status_counts = {}
    for lead in leads:
        status = lead.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    replied_leads = [
        {
            "name": lead.get("name"),
            "company": lead.get("company"),
            "title": lead.get("title"),
            "linkedin_url": lead.get("linkedin_url"),
        }
        for lead in leads
        if lead.get("status") == "replied"
    ]

    return {
        "total_leads": len(leads),
        "funnel": {
            "discovered": status_counts.get("discovered", 0),
            "connected": status_counts.get("connected", 0),
            "replied": status_counts.get("replied", 0),
        },
        "replied_leads": replied_leads,
    }
