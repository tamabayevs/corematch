"""
CoreMatch — Candidate Status Portal Blueprint
Public-facing endpoint for candidates to check their application status.
No authentication required — uses reference_id for lookup.
"""
import logging
from flask import Blueprint, jsonify
from database.connection import get_db

logger = logging.getLogger(__name__)
candidate_portal_bp = Blueprint("candidate_portal", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/public/candidate-status/:reference_id
# Public endpoint — NO auth required
# ──────────────────────────────────────────────────────────────

@candidate_portal_bp.route("/candidate-status/<reference_id>", methods=["GET"])
def get_candidate_status(reference_id):
    """
    Public endpoint for candidates to check their application status.
    Uses the reference_id (e.g., CM-2026-123456) for lookup.

    Returns a minimal status view — never reveals scores or decision details.
    This protects both the candidate's privacy and the HR team's evaluation process.
    """
    if not reference_id or not reference_id.startswith("CM-"):
        return jsonify({"error": "Invalid reference ID format"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.status, c.created_at, c.reference_id,
                           camp.job_title, u.company_name
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    JOIN users u ON camp.user_id = u.id
                    WHERE c.reference_id = %s AND c.status != 'erased'
                    """,
                    (reference_id,),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Candidate status portal error: %s", str(e))
        return jsonify({"error": "Failed to fetch status"}), 500

    if not row:
        return jsonify({"error": "Application not found. Please check your reference ID."}), 404

    # Map internal statuses to candidate-friendly statuses
    # Never reveal internal scoring or decision details
    internal_status = row[0]
    status_map = {
        "invited": "submitted",
        "started": "submitted",
        "submitted": "under_review",
    }
    public_status = status_map.get(internal_status, "under_review")

    # If there's an HR decision, show "decision_made" without details
    # We need a separate check since hr_decision is a different column
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT hr_decision FROM candidates WHERE reference_id = %s",
                    (reference_id,),
                )
                decision_row = cur.fetchone()
                if decision_row and decision_row[0] is not None:
                    public_status = "decision_made"
    except Exception:
        pass  # Keep the previous status on error

    return jsonify({
        "status": public_status,
        "submitted_at": row[1].isoformat() if row[1] else None,
        "reference_id": row[2],
        "job_title": row[3],
        "company_name": row[4],
    })
