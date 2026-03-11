"""
CoreMatch — Pipeline Orchestration Service
Manages the 4-stage agentic hiring pipeline:
  Stage 1: CV Screening
  Stage 2: Video Interview + AI Scoring
  Stage 3: Deep Evaluation
  Stage 4: Final Shortlist Ranking

Each stage: agent runs → produces recommendation → HR approves/rejects/overrides.
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

from database.connection import get_db

logger = logging.getLogger(__name__)

# Stage name mapping
STAGE_NAMES = {
    1: "cv_screening",
    2: "video_scoring",
    3: "deep_evaluation",
    4: "shortlist_ranking",
}

AGENT_TYPES = {
    1: "cv_screener",
    2: "video_scorer",
    3: "deep_evaluator",
    4: "shortlist_ranker",
}

# Candidate status per stage
STAGE_PROCESSING_STATUS = {
    1: "screening",
    2: "submitted",       # Reuse existing status for video stage
    3: "deep_eval",
    4: "deep_complete",   # Stage 4 runs on already-approved candidates
}

STAGE_COMPLETE_STATUS = {
    1: "screen_complete",
    2: "video_scored",
    3: "deep_complete",
    4: "shortlisted",
}


def get_pipeline_config(campaign_id: str) -> Optional[Dict]:
    """Get pipeline configuration for a campaign. Returns None if not pipeline-enabled."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.pipeline_enabled, pc.id, pc.stages, pc.default_provider, pc.default_model
                    FROM campaigns c
                    LEFT JOIN pipeline_configs pc ON pc.campaign_id = c.id
                    WHERE c.id = %s
                """, (campaign_id,))
                row = cur.fetchone()
                if not row or not row[0]:  # not pipeline_enabled
                    return None
                return {
                    "id": str(row[1]) if row[1] else None,
                    "stages": row[2] if row[2] else [],
                    "default_provider": row[3] or "groq",
                    "default_model": row[4] or "llama-3.3-70b-versatile",
                }
    except Exception as e:
        logger.error("Failed to get pipeline config for campaign %s: %s", campaign_id, e)
        return None


def start_pipeline(candidate_id: str, campaign_id: str) -> bool:
    """Start the pipeline for a candidate. Enqueues Stage 1 (CV screening).

    Returns True if pipeline was started, False if not applicable.
    """
    config = get_pipeline_config(campaign_id)
    if not config:
        return False

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Update candidate status to 'screening'
                cur.execute("""
                    UPDATE candidates
                    SET status = 'screening', pipeline_stage = 1, updated_at = NOW()
                    WHERE id = %s
                """, (candidate_id,))

                # Audit log
                cur.execute("""
                    INSERT INTO audit_log (id, user_id, action, entity_type, entity_id, metadata)
                    VALUES (%s, NULL, 'pipeline.started', 'candidate', %s, %s)
                """, (str(uuid4()), candidate_id, json.dumps({"stage": 1})))

        # Enqueue Stage 1 to RQ
        _enqueue_stage(candidate_id, campaign_id, stage=1)
        logger.info("Pipeline started for candidate %s (campaign %s)", candidate_id, campaign_id)
        return True

    except Exception as e:
        logger.error("Failed to start pipeline for candidate %s: %s", candidate_id, e)
        return False


def on_stage_complete(candidate_id: str, campaign_id: str, stage: int) -> None:
    """Called when an agent finishes processing a stage.
    Updates candidate status and notifies HR.
    """
    complete_status = STAGE_COMPLETE_STATUS.get(stage)
    if not complete_status:
        logger.error("Unknown stage %d for on_stage_complete", stage)
        return

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE candidates
                    SET status = %s, pipeline_stage = %s, updated_at = NOW()
                    WHERE id = %s
                """, (complete_status, stage, candidate_id))

                # Audit log
                cur.execute("""
                    INSERT INTO audit_log (id, user_id, action, entity_type, entity_id, metadata)
                    VALUES (%s, NULL, %s, 'candidate', %s, %s)
                """, (str(uuid4()), f"pipeline.stage_{stage}_complete", candidate_id,
                      json.dumps({"stage": stage, "status": complete_status})))

        # Send notification to campaign owner
        try:
            from services.notification_service import notify_campaign_owner
            stage_name = STAGE_NAMES.get(stage, f"Stage {stage}")
            notify_campaign_owner(
                candidate_id=candidate_id,
                notification_type="pipeline_stage_complete",
                title=f"Pipeline: {stage_name} complete",
                message=f"AI agent has completed {stage_name}. Review and approve to advance.",
            )
        except Exception as e:
            logger.warning("Failed to send pipeline notification: %s", e)

    except Exception as e:
        logger.error("Failed to update stage completion for candidate %s stage %d: %s",
                      candidate_id, stage, e)


def approve_stage(candidate_id: str, stage: int, user_id: str) -> Dict[str, Any]:
    """HR approves the agent's recommendation at a stage.

    For Stage 1: Creates invite token and sends interview invitation.
    For Stage 2/3: Advances to next stage.
    For Stage 4: Marks candidate as shortlisted.

    Returns dict with result info.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Update the agent evaluation's HR decision
                cur.execute("""
                    UPDATE agent_evaluations
                    SET hr_decision = 'approved', hr_decision_by = %s, hr_decision_at = NOW()
                    WHERE candidate_id = %s AND stage = %s AND hr_decision IS NULL
                    RETURNING id, recommendation
                """, (user_id, candidate_id, stage))
                eval_row = cur.fetchone()
                if not eval_row:
                    return {"error": "No pending evaluation found for this stage"}

                # Get campaign_id
                cur.execute("SELECT campaign_id FROM candidates WHERE id = %s", (candidate_id,))
                campaign_row = cur.fetchone()
                if not campaign_row:
                    return {"error": "Candidate not found"}
                campaign_id = str(campaign_row[0])

                # Audit log
                cur.execute("""
                    INSERT INTO audit_log (id, user_id, action, entity_type, entity_id, metadata)
                    VALUES (%s, %s, %s, 'candidate', %s, %s)
                """, (str(uuid4()), user_id, f"pipeline.stage_{stage}_approved",
                      candidate_id, json.dumps({"stage": stage})))

        # Stage-specific advancement logic
        if stage == 1:
            # Approved CV → send interview invite
            result = _advance_to_video_interview(candidate_id, campaign_id)
            return {"status": "approved", "stage": stage, "next": "video_interview", **result}

        elif stage in (2, 3):
            # Advance to next stage
            next_stage = stage + 1
            _advance_to_stage(candidate_id, campaign_id, next_stage)
            return {"status": "approved", "stage": stage, "next_stage": next_stage}

        elif stage == 4:
            # Final shortlist
            _mark_shortlisted(candidate_id, user_id)
            return {"status": "approved", "stage": stage, "next": "shortlisted"}

        return {"status": "approved", "stage": stage}

    except Exception as e:
        logger.error("Failed to approve stage %d for candidate %s: %s", stage, candidate_id, e)
        return {"error": str(e)}


def reject_at_stage(candidate_id: str, stage: int, user_id: str, reason: Optional[str] = None) -> Dict:
    """HR rejects candidate at a pipeline stage."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Update agent evaluation
                cur.execute("""
                    UPDATE agent_evaluations
                    SET hr_decision = 'rejected', hr_decision_by = %s, hr_decision_at = NOW(),
                        hr_override_reason = %s
                    WHERE candidate_id = %s AND stage = %s AND hr_decision IS NULL
                """, (user_id, reason, candidate_id, stage))

                # Update candidate status
                cur.execute("""
                    UPDATE candidates
                    SET status = 'rejected', hr_decision = 'rejected', hr_decision_at = NOW(),
                        hr_decision_note = %s, updated_at = NOW()
                    WHERE id = %s
                """, (reason or f"Rejected at pipeline stage {stage}", candidate_id))

                # Audit log
                cur.execute("""
                    INSERT INTO audit_log (id, user_id, action, entity_type, entity_id, metadata)
                    VALUES (%s, %s, %s, 'candidate', %s, %s)
                """, (str(uuid4()), user_id, f"pipeline.stage_{stage}_rejected",
                      candidate_id, json.dumps({"stage": stage, "reason": reason})))

        return {"status": "rejected", "stage": stage}

    except Exception as e:
        logger.error("Failed to reject at stage %d for candidate %s: %s", stage, candidate_id, e)
        return {"error": str(e)}


def override_stage(candidate_id: str, stage: int, user_id: str,
                   new_decision: str, reason: str) -> Dict:
    """HR overrides an agent recommendation. Reason is required (PDPL compliance)."""
    if not reason:
        return {"error": "Override reason is required for PDPL compliance"}

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE agent_evaluations
                    SET hr_decision = 'overridden', hr_decision_by = %s, hr_decision_at = NOW(),
                        hr_override_reason = %s
                    WHERE candidate_id = %s AND stage = %s AND hr_decision IS NULL
                    RETURNING recommendation
                """, (user_id, reason, candidate_id, stage))
                eval_row = cur.fetchone()

                # Audit log
                original_rec = eval_row[0] if eval_row else "unknown"
                cur.execute("""
                    INSERT INTO audit_log (id, user_id, action, entity_type, entity_id, metadata)
                    VALUES (%s, %s, %s, 'candidate', %s, %s)
                """, (str(uuid4()), user_id, f"pipeline.stage_{stage}_overridden",
                      candidate_id, json.dumps({
                          "stage": stage,
                          "original_recommendation": original_rec,
                          "new_decision": new_decision,
                          "reason": reason,
                      })))

        # Apply the override decision
        if new_decision == "advance":
            return approve_stage(candidate_id, stage, user_id)
        elif new_decision == "reject":
            return reject_at_stage(candidate_id, stage, user_id, reason)
        else:
            return {"status": "overridden", "stage": stage, "decision": new_decision}

    except Exception as e:
        logger.error("Failed to override stage %d for candidate %s: %s", stage, candidate_id, e)
        return {"error": str(e)}


def save_agent_evaluation(
    candidate_id: str,
    campaign_id: str,
    stage: int,
    agent_result: Any,
) -> Optional[str]:
    """Save an AgentResult to the agent_evaluations table.

    Returns the evaluation ID, or None on failure.
    """
    agent_type = AGENT_TYPES.get(stage)
    if not agent_type:
        logger.error("Unknown stage %d", stage)
        return None

    eval_id = str(uuid4())
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO agent_evaluations (
                        id, candidate_id, campaign_id, stage, agent_type,
                        overall_score, scores_detail, recommendation, confidence,
                        summary, strengths, concerns, evidence,
                        provider, model_used, raw_response, tokens_used, latency_ms
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (candidate_id, stage, agent_type)
                    DO UPDATE SET
                        overall_score = EXCLUDED.overall_score,
                        scores_detail = EXCLUDED.scores_detail,
                        recommendation = EXCLUDED.recommendation,
                        confidence = EXCLUDED.confidence,
                        summary = EXCLUDED.summary,
                        strengths = EXCLUDED.strengths,
                        concerns = EXCLUDED.concerns,
                        evidence = EXCLUDED.evidence,
                        provider = EXCLUDED.provider,
                        model_used = EXCLUDED.model_used,
                        raw_response = EXCLUDED.raw_response,
                        tokens_used = EXCLUDED.tokens_used,
                        latency_ms = EXCLUDED.latency_ms,
                        hr_decision = NULL,
                        hr_decision_by = NULL,
                        hr_decision_at = NULL,
                        hr_override_reason = NULL,
                        created_at = NOW()
                    RETURNING id
                """, (
                    eval_id, candidate_id, campaign_id, stage, agent_type,
                    agent_result.overall_score,
                    json.dumps(agent_result.scores_detail),
                    agent_result.recommendation,
                    agent_result.confidence,
                    agent_result.summary,
                    json.dumps(agent_result.strengths),
                    json.dumps(agent_result.concerns),
                    json.dumps(agent_result.evidence),
                    agent_result.provider,
                    agent_result.model_used,
                    json.dumps(agent_result.raw_response),
                    agent_result.tokens_used,
                    agent_result.latency_ms,
                ))
                result = cur.fetchone()
                return str(result[0]) if result else eval_id

    except Exception as e:
        logger.error("Failed to save agent evaluation for candidate %s stage %d: %s",
                      candidate_id, stage, e)
        return None


def get_candidate_evaluations(candidate_id: str) -> list:
    """Get all agent evaluations for a candidate, ordered by stage."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, stage, agent_type, overall_score, scores_detail,
                           recommendation, confidence, summary, strengths, concerns,
                           evidence, hr_decision, hr_decision_by, hr_decision_at,
                           hr_override_reason, provider, model_used, tokens_used,
                           latency_ms, created_at
                    FROM agent_evaluations
                    WHERE candidate_id = %s
                    ORDER BY stage ASC
                """, (candidate_id,))
                rows = cur.fetchall()
                return [
                    {
                        "id": str(r[0]),
                        "stage": r[1],
                        "agent_type": r[2],
                        "overall_score": float(r[3]) if r[3] else 0,
                        "scores_detail": r[4] or {},
                        "recommendation": r[5],
                        "confidence": float(r[6]) if r[6] else 0,
                        "summary": r[7],
                        "strengths": r[8] or [],
                        "concerns": r[9] or [],
                        "evidence": r[10] or [],
                        "hr_decision": r[11],
                        "hr_decision_by": str(r[12]) if r[12] else None,
                        "hr_decision_at": r[13].isoformat() if r[13] else None,
                        "hr_override_reason": r[14],
                        "provider": r[15],
                        "model_used": r[16],
                        "tokens_used": r[17],
                        "latency_ms": r[18],
                        "created_at": r[19].isoformat() if r[19] else None,
                    }
                    for r in rows
                ]
    except Exception as e:
        logger.error("Failed to get evaluations for candidate %s: %s", candidate_id, e)
        return []


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _enqueue_stage(candidate_id: str, campaign_id: str, stage: int) -> None:
    """Enqueue a pipeline stage to the RQ worker."""
    try:
        import redis
        from rq import Queue
        import os

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        redis_conn = redis.from_url(redis_url)
        q = Queue("pipeline", connection=redis_conn)
        q.enqueue(
            "workers.pipeline_worker.process_pipeline_stage",
            candidate_id,
            campaign_id,
            stage,
            job_timeout=300,  # 5 min timeout
        )
        logger.info("Enqueued pipeline stage %d for candidate %s", stage, candidate_id)
    except Exception as e:
        logger.error("Failed to enqueue pipeline stage %d for candidate %s: %s",
                      stage, candidate_id, e)


def _advance_to_video_interview(candidate_id: str, campaign_id: str) -> Dict:
    """After Stage 1 approval, create invite token and update status to 'invited'."""
    invite_token = str(uuid4())
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get campaign questions for snapshot
                cur.execute("SELECT questions FROM campaigns WHERE id = %s", (campaign_id,))
                campaign_row = cur.fetchone()
                questions = campaign_row[0] if campaign_row else []

                cur.execute("""
                    UPDATE candidates
                    SET status = 'invited', invite_token = %s,
                        questions_snapshot = %s, pipeline_stage = 2,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING email, full_name
                """, (invite_token, json.dumps(questions), candidate_id))
                row = cur.fetchone()

        frontend_url = os.environ.get("FRONTEND_URL", "https://corematch.vercel.app")
        interview_url = f"{frontend_url}/interview/{invite_token}/welcome"
        return {"invite_token": invite_token, "interview_url": interview_url}

    except Exception as e:
        logger.error("Failed to advance candidate %s to video interview: %s", candidate_id, e)
        return {"error": str(e)}


def _advance_to_stage(candidate_id: str, campaign_id: str, next_stage: int) -> None:
    """Advance candidate to the next pipeline stage."""
    processing_status = STAGE_PROCESSING_STATUS.get(next_stage)
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                if processing_status:
                    cur.execute("""
                        UPDATE candidates
                        SET status = %s, pipeline_stage = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (processing_status, next_stage, candidate_id))

        _enqueue_stage(candidate_id, campaign_id, next_stage)

    except Exception as e:
        logger.error("Failed to advance candidate %s to stage %d: %s",
                      candidate_id, next_stage, e)


def _mark_shortlisted(candidate_id: str, user_id: str) -> None:
    """Mark candidate as shortlisted (final pipeline stage)."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE candidates
                    SET status = 'shortlisted', hr_decision = 'shortlisted',
                        hr_decision_at = NOW(), pipeline_stage = 4, updated_at = NOW()
                    WHERE id = %s
                """, (candidate_id,))
    except Exception as e:
        logger.error("Failed to mark candidate %s as shortlisted: %s", candidate_id, e)


# Need os for FRONTEND_URL
import os
