"""
CoreMatch — Pipeline API Blueprint
Manages the agentic hiring pipeline: configuration, candidate flow, HR approvals.
"""
import json
import logging
from uuid import uuid4
from flask import Blueprint, request, jsonify, g

from api.auth import require_auth

pipeline_bp = Blueprint("pipeline", __name__)
logger = logging.getLogger(__name__)


def _validate_uuid(value):
    """Validate UUID format."""
    import re
    return bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', str(value).lower()))


# ──────────────────────────────────────────────────────────────
# Pipeline Configuration
# ──────────────────────────────────────────────────────────────

@pipeline_bp.route("/config/<campaign_id>", methods=["GET"])
@require_auth
def get_config(campaign_id):
    """Get pipeline configuration for a campaign."""
    if not _validate_uuid(campaign_id):
        return jsonify({"error": "Invalid campaign ID format"}), 400

    from database.connection import get_db
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.pipeline_enabled, pc.id, pc.stages,
                           pc.default_provider, pc.default_model,
                           pc.created_at, pc.updated_at
                    FROM campaigns c
                    LEFT JOIN pipeline_configs pc ON pc.campaign_id = c.id
                    WHERE c.id = %s AND c.user_id = %s
                """, (campaign_id, g.current_user["id"]))
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Campaign not found"}), 404

                return jsonify({
                    "pipeline_enabled": row[0] or False,
                    "config": {
                        "id": str(row[1]) if row[1] else None,
                        "stages": row[2] or [],
                        "default_provider": row[3] or "groq",
                        "default_model": row[4] or "llama-3.3-70b-versatile",
                        "created_at": row[5].isoformat() if row[5] else None,
                        "updated_at": row[6].isoformat() if row[6] else None,
                    } if row[1] else None,
                }), 200

    except Exception as e:
        logger.error("Failed to get pipeline config: %s", e)
        return jsonify({"error": "Internal server error"}), 500


@pipeline_bp.route("/config/<campaign_id>", methods=["POST"])
@require_auth
def upsert_config(campaign_id):
    """Create or update pipeline configuration for a campaign."""
    if not _validate_uuid(campaign_id):
        return jsonify({"error": "Invalid campaign ID format"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    pipeline_enabled = data.get("pipeline_enabled", True)
    stages = data.get("stages", _default_stages())
    default_provider = data.get("default_provider", "groq")
    default_model = data.get("default_model", "llama-3.3-70b-versatile")

    from database.connection import get_db
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify campaign ownership
                cur.execute("SELECT id FROM campaigns WHERE id = %s AND user_id = %s",
                            (campaign_id, g.current_user["id"]))
                if not cur.fetchone():
                    return jsonify({"error": "Campaign not found"}), 404

                # Update campaign pipeline_enabled flag
                cur.execute("""
                    UPDATE campaigns SET pipeline_enabled = %s, updated_at = NOW()
                    WHERE id = %s
                """, (pipeline_enabled, campaign_id))

                # Upsert pipeline_configs
                config_id = str(uuid4())
                cur.execute("""
                    INSERT INTO pipeline_configs (id, campaign_id, stages, default_provider, default_model)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (campaign_id) DO UPDATE SET
                        stages = EXCLUDED.stages,
                        default_provider = EXCLUDED.default_provider,
                        default_model = EXCLUDED.default_model,
                        updated_at = NOW()
                    RETURNING id
                """, (config_id, campaign_id, json.dumps(stages), default_provider, default_model))
                result = cur.fetchone()

                # Audit log
                cur.execute("""
                    INSERT INTO audit_log (id, user_id, action, entity_type, entity_id, metadata)
                    VALUES (%s, %s, 'pipeline.config_updated', 'campaign', %s, %s)
                """, (str(uuid4()), g.current_user["id"], campaign_id,
                      json.dumps({"pipeline_enabled": pipeline_enabled})))

        return jsonify({
            "message": "Pipeline configuration saved",
            "config_id": str(result[0]),
            "pipeline_enabled": pipeline_enabled,
        }), 200

    except Exception as e:
        logger.error("Failed to upsert pipeline config: %s", e)
        return jsonify({"error": "Internal server error"}), 500


# ──────────────────────────────────────────────────────────────
# Pipeline Candidates
# ──────────────────────────────────────────────────────────────

@pipeline_bp.route("/candidates/<campaign_id>", methods=["GET"])
@require_auth
def list_pipeline_candidates(campaign_id):
    """List candidates with their pipeline state and latest agent evaluations."""
    if not _validate_uuid(campaign_id):
        return jsonify({"error": "Invalid campaign ID format"}), 400

    from database.connection import get_db
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.id, c.full_name, c.email, c.status, c.pipeline_stage,
                           c.overall_score, c.tier, c.linkedin_url, c.created_at,
                           (SELECT json_agg(json_build_object(
                               'stage', ae.stage,
                               'agent_type', ae.agent_type,
                               'overall_score', ae.overall_score,
                               'recommendation', ae.recommendation,
                               'confidence', ae.confidence,
                               'hr_decision', ae.hr_decision,
                               'created_at', ae.created_at
                           ) ORDER BY ae.stage)
                           FROM agent_evaluations ae WHERE ae.candidate_id = c.id
                           ) as evaluations
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.campaign_id = %s AND camp.user_id = %s
                    ORDER BY c.created_at DESC
                """, (campaign_id, g.current_user["id"]))
                rows = cur.fetchall()

                candidates = []
                for r in rows:
                    candidates.append({
                        "id": str(r[0]),
                        "full_name": r[1],
                        "email": r[2],
                        "status": r[3],
                        "pipeline_stage": r[4] or 0,
                        "overall_score": float(r[5]) if r[5] else None,
                        "tier": r[6],
                        "linkedin_url": r[7],
                        "created_at": r[8].isoformat() if r[8] else None,
                        "evaluations": r[9] or [],
                    })

                return jsonify({"candidates": candidates}), 200

    except Exception as e:
        logger.error("Failed to list pipeline candidates: %s", e)
        return jsonify({"error": "Internal server error"}), 500


@pipeline_bp.route("/candidate/<candidate_id>", methods=["GET"])
@require_auth
def get_pipeline_candidate(candidate_id):
    """Get full pipeline detail for a candidate (all stages, evaluations, documents)."""
    if not _validate_uuid(candidate_id):
        return jsonify({"error": "Invalid candidate ID format"}), 400

    from database.connection import get_db
    from services.pipeline_service import get_candidate_evaluations

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.id, c.full_name, c.email, c.phone, c.status,
                           c.pipeline_stage, c.overall_score, c.tier,
                           c.linkedin_url, c.hr_decision, c.created_at
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s AND camp.user_id = %s
                """, (candidate_id, g.current_user["id"]))
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Candidate not found"}), 404

                # Get documents
                cur.execute("""
                    SELECT id, document_type, original_filename, content_type,
                           file_size_bytes, extraction_status, created_at
                    FROM candidate_documents
                    WHERE candidate_id = %s
                    ORDER BY created_at DESC
                """, (candidate_id,))
                doc_rows = cur.fetchall()

        evaluations = get_candidate_evaluations(candidate_id)

        return jsonify({
            "candidate": {
                "id": str(row[0]),
                "full_name": row[1],
                "email": row[2],
                "phone": row[3],
                "status": row[4],
                "pipeline_stage": row[5] or 0,
                "overall_score": float(row[6]) if row[6] else None,
                "tier": row[7],
                "linkedin_url": row[8],
                "hr_decision": row[9],
                "created_at": row[10].isoformat() if row[10] else None,
            },
            "evaluations": evaluations,
            "documents": [
                {
                    "id": str(d[0]),
                    "document_type": d[1],
                    "original_filename": d[2],
                    "content_type": d[3],
                    "file_size_bytes": d[4],
                    "extraction_status": d[5],
                    "created_at": d[6].isoformat() if d[6] else None,
                }
                for d in doc_rows
            ],
        }), 200

    except Exception as e:
        logger.error("Failed to get pipeline candidate detail: %s", e)
        return jsonify({"error": "Internal server error"}), 500


# ──────────────────────────────────────────────────────────────
# HR Approval Actions
# ──────────────────────────────────────────────────────────────

@pipeline_bp.route("/approve/<candidate_id>", methods=["POST"])
@require_auth
def approve(candidate_id):
    """HR approves the agent's recommendation at the current stage."""
    if not _validate_uuid(candidate_id):
        return jsonify({"error": "Invalid candidate ID format"}), 400

    from services.pipeline_service import approve_stage
    from database.connection import get_db

    # Get current pipeline stage
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.pipeline_stage FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s AND camp.user_id = %s
                """, (candidate_id, g.current_user["id"]))
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Candidate not found"}), 404
                stage = row[0] or 0
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

    if stage == 0:
        return jsonify({"error": "Candidate is not in a pipeline"}), 400

    result = approve_stage(candidate_id, stage, g.current_user["id"])
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200


@pipeline_bp.route("/reject/<candidate_id>", methods=["POST"])
@require_auth
def reject(candidate_id):
    """HR rejects candidate at the current pipeline stage."""
    if not _validate_uuid(candidate_id):
        return jsonify({"error": "Invalid candidate ID format"}), 400

    data = request.get_json() or {}
    reason = data.get("reason")

    from services.pipeline_service import reject_at_stage
    from database.connection import get_db

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.pipeline_stage FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s AND camp.user_id = %s
                """, (candidate_id, g.current_user["id"]))
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Candidate not found"}), 404
                stage = row[0] or 0
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

    if stage == 0:
        return jsonify({"error": "Candidate is not in a pipeline"}), 400

    result = reject_at_stage(candidate_id, stage, g.current_user["id"], reason)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200


@pipeline_bp.route("/override/<candidate_id>", methods=["POST"])
@require_auth
def override(candidate_id):
    """HR overrides the agent's recommendation. Reason required."""
    if not _validate_uuid(candidate_id):
        return jsonify({"error": "Invalid candidate ID format"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    new_decision = data.get("decision")
    reason = data.get("reason")

    if not new_decision or new_decision not in ("advance", "reject"):
        return jsonify({"error": "Decision must be 'advance' or 'reject'"}), 400
    if not reason:
        return jsonify({"error": "Override reason is required for PDPL compliance"}), 400

    from services.pipeline_service import override_stage
    from database.connection import get_db

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.pipeline_stage FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s AND camp.user_id = %s
                """, (candidate_id, g.current_user["id"]))
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Candidate not found"}), 404
                stage = row[0] or 0
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

    if stage == 0:
        return jsonify({"error": "Candidate is not in a pipeline"}), 400

    result = override_stage(candidate_id, stage, g.current_user["id"], new_decision, reason)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200


# ──────────────────────────────────────────────────────────────
# Pipeline Stats
# ──────────────────────────────────────────────────────────────

@pipeline_bp.route("/stats/<campaign_id>", methods=["GET"])
@require_auth
def pipeline_stats(campaign_id):
    """Get pipeline funnel stats for a campaign."""
    if not _validate_uuid(campaign_id):
        return jsonify({"error": "Invalid campaign ID format"}), 400

    from database.connection import get_db
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'applied' OR pipeline_stage >= 0) as total_applied,
                        COUNT(*) FILTER (WHERE status IN ('screen_complete','screening') OR pipeline_stage >= 1) as stage_1,
                        COUNT(*) FILTER (WHERE status IN ('invited','started','submitted','video_scored') OR pipeline_stage >= 2) as stage_2,
                        COUNT(*) FILTER (WHERE status IN ('deep_eval','deep_complete') OR pipeline_stage >= 3) as stage_3,
                        COUNT(*) FILTER (WHERE status = 'shortlisted' OR pipeline_stage >= 4) as stage_4,
                        COUNT(*) FILTER (WHERE status = 'rejected') as rejected
                    FROM candidates
                    WHERE campaign_id = %s
                """, (campaign_id,))
                row = cur.fetchone()

                return jsonify({
                    "funnel": {
                        "applied": row[0] or 0,
                        "cv_screened": row[1] or 0,
                        "video_interview": row[2] or 0,
                        "deep_evaluated": row[3] or 0,
                        "shortlisted": row[4] or 0,
                        "rejected": row[5] or 0,
                    }
                }), 200

    except Exception as e:
        logger.error("Failed to get pipeline stats: %s", e)
        return jsonify({"error": "Internal server error"}), 500


@pipeline_bp.route("/providers", methods=["GET"])
@require_auth
def list_providers():
    """List available AI providers and their models."""
    return jsonify({
        "providers": [
            {
                "name": "groq",
                "display_name": "Groq",
                "models": [
                    {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "recommended": True},
                    {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "recommended": False},
                ],
            },
            {
                "name": "anthropic",
                "display_name": "Anthropic",
                "models": [
                    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "recommended": True},
                    {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "recommended": False},
                ],
            },
            {
                "name": "openai",
                "display_name": "OpenAI",
                "models": [
                    {"id": "gpt-4o", "name": "GPT-4o", "recommended": True},
                    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "recommended": False},
                ],
            },
        ]
    }), 200


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _default_stages():
    """Return default pipeline stage configuration."""
    return [
        {
            "stage": 1,
            "name": "cv_screening",
            "enabled": True,
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "advance_threshold": 70,
            "reject_threshold": 30,
        },
        {
            "stage": 2,
            "name": "video_scoring",
            "enabled": True,
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
        },
        {
            "stage": 3,
            "name": "deep_evaluation",
            "enabled": True,
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
        },
        {
            "stage": 4,
            "name": "shortlist_ranking",
            "enabled": True,
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
        },
    ]
