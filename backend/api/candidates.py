"""
CoreMatch — Candidates Blueprint
HR endpoints for viewing and managing candidates.
All endpoints require JWT auth + campaign ownership verification.
"""
import json
import uuid
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
candidates_bp = Blueprint("candidates", __name__)


def _format_candidate(row) -> dict:
    """Format a DB row into a candidate dict for HR dashboard."""
    return {
        "id": str(row[0]),
        "campaign_id": str(row[1]),
        "email": row[2],
        "full_name": row[3],
        "status": row[4],
        "overall_score": float(row[5]) if row[5] is not None else None,
        "tier": row[6],
        "hr_decision": row[7],
        "hr_decision_at": row[8].isoformat() if row[8] else None,
        "hr_decision_note": row[9],
        "reference_id": row[10],
        "consent_given": row[11],
        "created_at": row[12].isoformat() if row[12] else None,
        "updated_at": row[13].isoformat() if row[13] else None,
    }


# ──────────────────────────────────────────────────────────────
# GET /api/candidates/campaign/:campaign_id
# ──────────────────────────────────────────────────────────────

@candidates_bp.route("/campaign/<campaign_id>", methods=["GET"])
@require_auth
def list_candidates(campaign_id):
    """
    List all candidates for a campaign.
    Supports filtering: tier, status, hr_decision
    Supports sorting: score, name, created_at
    """
    # Verify campaign ownership
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM campaigns WHERE id = %s AND user_id = %s",
                    (campaign_id, g.current_user["id"]),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Campaign not found"}), 404
    except Exception as e:
        logger.error("List candidates — ownership check error: %s", str(e))
        return jsonify({"error": "Failed to verify campaign"}), 500

    # Parse query params
    tier_filter = request.args.get("tier")
    status_filter = request.args.get("status")
    decision_filter = request.args.get("hr_decision")
    sort_by = request.args.get("sort", "score")  # 'score' | 'name' | 'date'

    # Build query
    conditions = ["c.campaign_id = %s", "c.status != 'erased'"]
    params = [campaign_id]

    valid_tiers = ("strong_proceed", "consider", "likely_pass")
    if tier_filter and tier_filter in valid_tiers:
        conditions.append("c.tier = %s")
        params.append(tier_filter)

    valid_statuses = ("invited", "started", "submitted")
    if status_filter and status_filter in valid_statuses:
        conditions.append("c.status = %s")
        params.append(status_filter)

    valid_decisions = ("shortlisted", "rejected", "hold")
    if decision_filter and decision_filter in valid_decisions:
        conditions.append("c.hr_decision = %s")
        params.append(decision_filter)
    elif decision_filter == "none":
        conditions.append("c.hr_decision IS NULL")

    order_clause = {
        "score": "c.overall_score DESC NULLS LAST, c.created_at DESC",
        "name": "c.full_name ASC",
        "date": "c.created_at DESC",
    }.get(sort_by, "c.overall_score DESC NULLS LAST")

    where_clause = " AND ".join(conditions)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT c.id, c.campaign_id, c.email, c.full_name, c.status,
                           c.overall_score, c.tier, c.hr_decision, c.hr_decision_at,
                           c.hr_decision_note, c.reference_id, c.consent_given,
                           c.created_at, c.updated_at
                    FROM candidates c
                    WHERE {where_clause}
                    ORDER BY {order_clause}
                    """,
                    params,
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("List candidates DB error: %s", str(e))
        return jsonify({"error": "Failed to fetch candidates"}), 500

    return jsonify({
        "candidates": [_format_candidate(row) for row in rows],
        "total": len(rows),
    })


# ──────────────────────────────────────────────────────────────
# GET /api/candidates/:id
# ──────────────────────────────────────────────────────────────

@candidates_bp.route("/<candidate_id>", methods=["GET"])
@require_auth
def get_candidate(candidate_id):
    """
    Get full candidate detail including video answers and AI scores.
    Only accessible if the candidate's campaign belongs to the current user.
    """
    try:
        uuid.UUID(candidate_id)
    except (ValueError, AttributeError):
        return jsonify({"error": "Invalid candidate ID format"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Main candidate record + campaign ownership check
                cur.execute(
                    """
                    SELECT c.id, c.campaign_id, c.email, c.full_name, c.phone,
                           c.status, c.overall_score, c.tier, c.hr_decision,
                           c.hr_decision_at, c.hr_decision_note, c.reference_id,
                           c.consent_given, c.consent_given_at,
                           c.questions_snapshot, c.invite_expires_at,
                           c.created_at, c.updated_at,
                           camp.name as campaign_name, camp.job_title
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s AND camp.user_id = %s
                    """,
                    (candidate_id, g.current_user["id"]),
                )
                candidate_row = cur.fetchone()

                if not candidate_row:
                    return jsonify({"error": "Candidate not found"}), 404

                # Video answers with AI scores
                cur.execute(
                    """
                    SELECT va.id, va.question_index, va.question_text,
                           va.storage_key, va.file_format, va.duration_seconds,
                           va.transcript, va.detected_language, va.processing_status,
                           va.uploaded_at, va.processed_at,
                           s.content_score, s.communication_score, s.behavioral_score,
                           s.overall_score, s.tier, s.strengths, s.improvements,
                           s.language_match, s.model_used, s.scoring_source
                    FROM video_answers va
                    LEFT JOIN ai_scores s ON s.video_answer_id = va.id
                    WHERE va.candidate_id = %s
                    ORDER BY va.question_index ASC
                    """,
                    (candidate_id,),
                )
                answer_rows = cur.fetchall()
    except Exception as e:
        logger.error("Get candidate DB error: %s", str(e))
        return jsonify({"error": "Failed to fetch candidate"}), 500

    # Format video answers
    answers = []
    for ar in answer_rows:
        # Generate signed URL if video exists
        signed_url = None
        if ar[3]:  # storage_key exists
            try:
                from services.storage_service import get_storage_service
                storage = get_storage_service()
                signed_url = storage.generate_signed_url(ar[3], expires_in=3600)  # 1 hour
            except Exception as e:
                logger.warning("Failed to generate signed URL for %s: %s", ar[3], str(e))

        answers.append({
            "id": str(ar[0]),
            "question_index": ar[1],
            "question_text": ar[2],
            "has_video": ar[3] is not None,
            "signed_url": signed_url,
            "file_format": ar[4],
            "duration_seconds": float(ar[5]) if ar[5] else None,
            "transcript": ar[6],
            "detected_language": ar[7],
            "processing_status": ar[8],
            "uploaded_at": ar[9].isoformat() if ar[9] else None,
            "processed_at": ar[10].isoformat() if ar[10] else None,
            "scores": {
                "content": float(ar[11]) if ar[11] is not None else None,
                "communication": float(ar[12]) if ar[12] is not None else None,
                "behavioral": float(ar[13]) if ar[13] is not None else None,
                "overall": float(ar[14]) if ar[14] is not None else None,
                "tier": ar[15],
                "strengths": ar[16] or [],
                "improvements": ar[17] or [],
                "language_match": ar[18],
                "model_used": ar[19],
                "scoring_source": ar[20],
            } if ar[11] is not None else None,
        })

    candidate = {
        "id": str(candidate_row[0]),
        "campaign_id": str(candidate_row[1]),
        "email": candidate_row[2],
        "full_name": candidate_row[3],
        "phone": candidate_row[4],
        "status": candidate_row[5],
        "overall_score": float(candidate_row[6]) if candidate_row[6] else None,
        "tier": candidate_row[7],
        "hr_decision": candidate_row[8],
        "hr_decision_at": candidate_row[9].isoformat() if candidate_row[9] else None,
        "hr_decision_note": candidate_row[10],
        "reference_id": candidate_row[11],
        "consent_given": candidate_row[12],
        "consent_given_at": candidate_row[13].isoformat() if candidate_row[13] else None,
        "questions_snapshot": candidate_row[14],
        "invite_expires_at": candidate_row[15].isoformat() if candidate_row[15] else None,
        "created_at": candidate_row[16].isoformat() if candidate_row[16] else None,
        "updated_at": candidate_row[17].isoformat() if candidate_row[17] else None,
        "campaign_name": candidate_row[18],
        "job_title": candidate_row[19],
        "video_answers": answers,
    }

    return jsonify({"candidate": candidate})


# ──────────────────────────────────────────────────────────────
# PUT /api/candidates/:id/decision
# ──────────────────────────────────────────────────────────────

@candidates_bp.route("/<candidate_id>/decision", methods=["PUT"])
@require_auth
def update_decision(candidate_id):
    """
    Set HR decision on a candidate: shortlisted, rejected, hold, or null (clear).
    Records to audit_log for PDPL compliance.
    """
    try:
        uuid.UUID(candidate_id)
    except (ValueError, AttributeError):
        return jsonify({"error": "Invalid candidate ID format"}), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    decision = data.get("decision")
    note = data.get("note", "").strip() or None

    valid_decisions = ("shortlisted", "rejected", "hold", None)
    if decision not in valid_decisions:
        return jsonify({"error": "decision must be 'shortlisted', 'rejected', 'hold', or null"}), 400

    import datetime

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify ownership
                cur.execute(
                    """
                    SELECT c.id, c.status FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s AND camp.user_id = %s
                    """,
                    (candidate_id, g.current_user["id"]),
                )
                candidate = cur.fetchone()

                if not candidate:
                    return jsonify({"error": "Candidate not found"}), 404

                # Update decision
                cur.execute(
                    """
                    UPDATE candidates
                    SET hr_decision = %s,
                        hr_decision_at = %s,
                        hr_decision_note = %s
                    WHERE id = %s
                    """,
                    (
                        decision,
                        datetime.datetime.utcnow() if decision else None,
                        note,
                        candidate_id,
                    ),
                )

                # Audit log
                action = f"candidate.{decision}" if decision else "candidate.decision_cleared"
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"],
                        action,
                        "candidate",
                        candidate_id,
                        json.dumps({"decision": decision, "note": note}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Update decision DB error: %s", str(e))
        return jsonify({"error": "Failed to update decision"}), 500

    return jsonify({
        "message": "Decision updated",
        "decision": decision,
        "note": note,
    })


# ──────────────────────────────────────────────────────────────
# DELETE /api/candidates/:id/erase
# PDPL Right-to-Erasure
# ──────────────────────────────────────────────────────────────

@candidates_bp.route("/<candidate_id>/erase", methods=["DELETE"])
@require_auth
def erase_candidate(candidate_id):
    """
    PDPL Right-to-Erasure: Anonymize a single candidate.
    - Deletes videos from storage
    - NULLs out all PII fields
    - Marks status as 'erased'
    - Records in audit_log
    """
    try:
        uuid.UUID(candidate_id)
    except (ValueError, AttributeError):
        return jsonify({"error": "Invalid candidate ID format"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify ownership
                cur.execute(
                    """
                    SELECT c.id, c.email FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s AND camp.user_id = %s
                    """,
                    (candidate_id, g.current_user["id"]),
                )
                candidate = cur.fetchone()

                if not candidate:
                    return jsonify({"error": "Candidate not found"}), 404

                # Get video storage keys for deletion
                cur.execute(
                    "SELECT storage_key FROM video_answers WHERE candidate_id = %s AND storage_key IS NOT NULL",
                    (candidate_id,),
                )
                storage_keys = [row[0] for row in cur.fetchall()]

                # Delete videos from storage
                if storage_keys:
                    try:
                        from services.storage_service import get_storage_service
                        storage = get_storage_service()
                        for key in storage_keys:
                            storage.delete_file(key)
                    except Exception as e:
                        logger.error("Failed to delete videos for candidate %s: %s", candidate_id, str(e))
                        # Continue with anonymization even if storage deletion fails

                # Anonymize the candidate record
                cur.execute(
                    """
                    UPDATE candidates SET
                        email = 'erased@erased.invalid',
                        full_name = '[Erased]',
                        phone = NULL,
                        status = 'erased',
                        overall_score = NULL,
                        tier = NULL
                    WHERE id = %s
                    """,
                    (candidate_id,),
                )

                # Anonymize transcripts and remove storage keys
                cur.execute(
                    """
                    UPDATE video_answers SET
                        transcript = NULL,
                        storage_key = NULL,
                        detected_language = NULL
                    WHERE candidate_id = %s
                    """,
                    (candidate_id,),
                )

                # Audit log (kept for PDPL accountability)
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"],
                        "candidate.erased",
                        "candidate",
                        candidate_id,
                        json.dumps({"original_email_hash": candidate[1][:3] + "***"}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Erase candidate DB error: %s", str(e))
        return jsonify({"error": "Failed to erase candidate"}), 500

    return jsonify({"message": "Candidate data erased successfully"})


# ──────────────────────────────────────────────────────────────
# PUT /api/candidates/:id/reviewed
# Mark a candidate as reviewed
# ──────────────────────────────────────────────────────────────

@candidates_bp.route("/<candidate_id>/reviewed", methods=["PUT"])
@require_auth
def mark_reviewed(candidate_id):
    """Mark a candidate as reviewed by the current user."""
    try:
        uuid.UUID(candidate_id)
    except (ValueError, AttributeError):
        return jsonify({"error": "Invalid candidate ID format"}), 400

    import datetime

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify ownership
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
                    UPDATE candidates
                    SET reviewed_at = %s, reviewed_by = %s
                    WHERE id = %s
                    """,
                    (datetime.datetime.utcnow(), g.current_user["id"], candidate_id),
                )
    except Exception as e:
        logger.error("Mark reviewed DB error: %s", str(e))
        return jsonify({"error": "Failed to mark as reviewed"}), 500

    return jsonify({"message": "Candidate marked as reviewed"})
