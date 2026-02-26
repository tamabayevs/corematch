"""
CoreMatch — Pipeline Worker
RQ background job that processes each pipeline stage.
Called by pipeline_service.start_pipeline() and _enqueue_stage().
"""
import os
import sys
import json
import logging

# Ensure backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


def process_pipeline_stage(candidate_id: str, campaign_id: str, stage: int) -> None:
    """Process a candidate through a specific pipeline stage.

    Args:
        candidate_id: UUID of the candidate.
        campaign_id: UUID of the campaign.
        stage: Pipeline stage number (1-4).
    """
    logger.info("Processing pipeline stage %d for candidate %s (campaign %s)",
                stage, candidate_id, campaign_id)

    from services.pipeline_service import (
        get_pipeline_config, on_stage_complete, save_agent_evaluation
    )

    # Load pipeline config
    config = get_pipeline_config(campaign_id)
    if not config:
        logger.error("No pipeline config found for campaign %s", campaign_id)
        return

    # Route to the appropriate agent
    if stage == 1:
        result = _run_cv_screening(candidate_id, campaign_id, config)
    elif stage == 2:
        result = _run_video_scoring(candidate_id, campaign_id, config)
    elif stage == 3:
        result = _run_deep_evaluation(candidate_id, campaign_id, config)
    elif stage == 4:
        result = _run_shortlist_ranking(candidate_id, campaign_id, config)
    else:
        logger.error("Unknown pipeline stage: %d", stage)
        return

    if result is None:
        logger.error("Agent returned None for stage %d, candidate %s", stage, candidate_id)
        return

    # Save evaluation result
    eval_id = save_agent_evaluation(candidate_id, campaign_id, stage, result)
    logger.info("Saved agent evaluation %s for candidate %s stage %d (score: %.1f, rec: %s)",
                eval_id, candidate_id, stage, result.overall_score, result.recommendation)

    # Mark stage as complete (triggers notification to HR)
    on_stage_complete(candidate_id, campaign_id, stage)


def _run_cv_screening(candidate_id: str, campaign_id: str, config: dict):
    """Run Stage 1: CV Screening Agent."""
    from database.connection import get_db
    from ai.cv_screener import screen_cv

    # Load candidate CV text + campaign details
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get CV extracted text
                cur.execute("""
                    SELECT extracted_text FROM candidate_documents
                    WHERE candidate_id = %s AND document_type = 'cv'
                    ORDER BY created_at DESC LIMIT 1
                """, (candidate_id,))
                doc_row = cur.fetchone()
                cv_text = doc_row[0] if doc_row else ""

                # Get candidate LinkedIn URL
                cur.execute("SELECT linkedin_url FROM candidates WHERE id = %s", (candidate_id,))
                cand_row = cur.fetchone()
                linkedin_url = cand_row[0] if cand_row else None

                # Get campaign job details
                cur.execute("""
                    SELECT job_title, job_description FROM campaigns WHERE id = %s
                """, (campaign_id,))
                camp_row = cur.fetchone()
                if not camp_row:
                    logger.error("Campaign %s not found", campaign_id)
                    return None
                job_title = camp_row[0] or ""
                job_description = camp_row[1] or ""

    except Exception as e:
        logger.error("Failed to load data for CV screening: %s", e)
        return None

    # Run the CV screener
    return screen_cv(
        cv_text=cv_text,
        job_title=job_title,
        job_description=job_description,
        pipeline_config=config,
        linkedin_url=linkedin_url,
    )


def _run_video_scoring(candidate_id: str, campaign_id: str, config: dict):
    """Run Stage 2: Video Scoring Agent.
    The actual video transcription + per-question scoring is handled by the existing
    video_processor.py worker. This stage agent produces a holistic summary
    combining video scores + CV data into a pipeline recommendation.
    """
    from database.connection import get_db
    from ai.video_agent import evaluate_video_stage

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get candidate name
                cur.execute("SELECT full_name FROM candidates WHERE id = %s", (candidate_id,))
                cand_row = cur.fetchone()
                candidate_name = cand_row[0] if cand_row else "Unknown"

                # Get campaign details
                cur.execute("SELECT job_title, job_description FROM campaigns WHERE id = %s", (campaign_id,))
                camp_row = cur.fetchone()
                if not camp_row:
                    logger.error("Campaign %s not found for Stage 2", campaign_id)
                    return None
                job_title = camp_row[0] or ""
                job_description = camp_row[1] or ""

                # Get per-question AI scores
                cur.execute("""
                    SELECT a.overall_score, a.tier, va.question_index
                    FROM ai_scores a
                    JOIN video_answers va ON a.video_answer_id = va.id
                    WHERE a.candidate_id = %s
                    ORDER BY va.question_index ASC
                """, (candidate_id,))
                score_rows = cur.fetchall()
                video_scores = [
                    {"overall_score": float(r[0]), "tier": r[1], "question_index": r[2]}
                    for r in score_rows
                ]

                # Get transcripts
                cur.execute("""
                    SELECT question_text, transcript, question_index
                    FROM video_answers
                    WHERE candidate_id = %s AND transcript IS NOT NULL
                    ORDER BY question_index ASC
                """, (candidate_id,))
                transcript_rows = cur.fetchall()
                transcripts = [
                    {"question_text": r[0] or f"Question {r[2]+1}", "transcript": r[1] or ""}
                    for r in transcript_rows
                ]

                # Get CV summary from Stage 1 evaluation (if available)
                cur.execute("""
                    SELECT summary FROM agent_evaluations
                    WHERE candidate_id = %s AND stage = 1
                    ORDER BY created_at DESC LIMIT 1
                """, (candidate_id,))
                eval_row = cur.fetchone()
                cv_summary = eval_row[0] if eval_row else None

    except Exception as e:
        logger.error("Failed to load data for Stage 2 video scoring: %s", e)
        return None

    return evaluate_video_stage(
        candidate_name=candidate_name,
        job_title=job_title,
        job_description=job_description,
        video_scores=video_scores,
        transcripts=transcripts,
        cv_summary=cv_summary,
        pipeline_config=config,
    )


def _run_deep_evaluation(candidate_id: str, campaign_id: str, config: dict):
    """Run Stage 3: Deep Evaluation Agent.
    Comprehensive assessment combining CV + video transcripts + AI scores.
    """
    from database.connection import get_db
    from ai.deep_evaluator import evaluate_candidate_deep

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get candidate name
                cur.execute("SELECT full_name FROM candidates WHERE id = %s", (candidate_id,))
                cand_row = cur.fetchone()
                candidate_name = cand_row[0] if cand_row else "Unknown"

                # Get campaign details
                cur.execute("SELECT job_title, job_description FROM campaigns WHERE id = %s", (campaign_id,))
                camp_row = cur.fetchone()
                if not camp_row:
                    logger.error("Campaign %s not found for Stage 3", campaign_id)
                    return None
                job_title = camp_row[0] or ""
                job_description = camp_row[1] or ""

                # Get CV extracted text
                cur.execute("""
                    SELECT extracted_text FROM candidate_documents
                    WHERE candidate_id = %s AND document_type = 'cv'
                    ORDER BY created_at DESC LIMIT 1
                """, (candidate_id,))
                doc_row = cur.fetchone()
                cv_text = doc_row[0] if doc_row else None

                # Get per-question AI scores
                cur.execute("""
                    SELECT a.overall_score, a.tier, va.question_index
                    FROM ai_scores a
                    JOIN video_answers va ON a.video_answer_id = va.id
                    WHERE a.candidate_id = %s
                    ORDER BY va.question_index ASC
                """, (candidate_id,))
                score_rows = cur.fetchall()
                video_scores = [
                    {"overall_score": float(r[0]), "tier": r[1], "question_index": r[2]}
                    for r in score_rows
                ]

                # Get transcripts
                cur.execute("""
                    SELECT question_text, transcript, question_index
                    FROM video_answers
                    WHERE candidate_id = %s AND transcript IS NOT NULL
                    ORDER BY question_index ASC
                """, (candidate_id,))
                transcript_rows = cur.fetchall()
                transcripts = [
                    {"question_text": r[0] or f"Question {r[2]+1}", "transcript": r[1] or ""}
                    for r in transcript_rows
                ]

    except Exception as e:
        logger.error("Failed to load data for Stage 3 deep evaluation: %s", e)
        return None

    return evaluate_candidate_deep(
        candidate_name=candidate_name,
        job_title=job_title,
        job_description=job_description,
        cv_text=cv_text,
        video_scores=video_scores,
        transcripts=transcripts,
        pipeline_config=config,
    )


def _run_shortlist_ranking(candidate_id: str, campaign_id: str, config: dict):
    """Run Stage 4: Shortlist Ranking Agent.
    Ranks ALL Stage 3-approved candidates in the campaign, not just this one.
    The result is stored under this candidate's evaluation but contains
    rankings for all approved candidates.
    """
    from database.connection import get_db
    from ai.shortlist_ranker import rank_shortlist

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get campaign details
                cur.execute("SELECT job_title, job_description FROM campaigns WHERE id = %s", (campaign_id,))
                camp_row = cur.fetchone()
                if not camp_row:
                    logger.error("Campaign %s not found for Stage 4", campaign_id)
                    return None
                job_title = camp_row[0] or ""
                job_description = camp_row[1] or ""

                # Get all candidates who have completed Stage 3 or are at Stage 4
                cur.execute("""
                    SELECT c.id, c.full_name
                    FROM candidates c
                    WHERE c.campaign_id = %s
                    AND (c.status IN ('deep_complete', 'shortlisted')
                         OR (c.pipeline_stage >= 3 AND c.status != 'rejected'))
                """, (campaign_id,))
                candidate_rows = cur.fetchall()

                if not candidate_rows:
                    logger.warning("No Stage 3-approved candidates found for campaign %s", campaign_id)
                    return None

                # For each candidate, gather their stage evaluations
                candidates_data = []
                for cand_id, cand_name in candidate_rows:
                    cand_id_str = str(cand_id)

                    # Get evaluations across stages
                    cur.execute("""
                        SELECT stage, overall_score, summary, strengths, concerns
                        FROM agent_evaluations
                        WHERE candidate_id = %s
                        ORDER BY stage ASC
                    """, (cand_id_str,))
                    evals = cur.fetchall()

                    cv_score = 0
                    cv_summary = ""
                    video_score = 0
                    video_summary = ""
                    deep_score = 0
                    deep_summary = ""
                    strengths = []
                    concerns = []

                    for ev in evals:
                        stage_num = ev[0]
                        score = float(ev[1]) if ev[1] else 0
                        summary = ev[2] or ""
                        s = ev[3] or []
                        c = ev[4] or []
                        if stage_num == 1:
                            cv_score = score
                            cv_summary = summary
                        elif stage_num == 2:
                            video_score = score
                            video_summary = summary
                        elif stage_num == 3:
                            deep_score = score
                            deep_summary = summary
                            strengths = s if isinstance(s, list) else []
                            concerns = c if isinstance(c, list) else []

                    candidates_data.append({
                        "candidate_id": cand_id_str,
                        "candidate_name": cand_name,
                        "cv_score": cv_score,
                        "cv_summary": cv_summary,
                        "video_score": video_score,
                        "video_summary": video_summary,
                        "deep_score": deep_score,
                        "deep_summary": deep_summary,
                        "strengths": strengths,
                        "concerns": concerns,
                    })

    except Exception as e:
        logger.error("Failed to load data for Stage 4 shortlist ranking: %s", e)
        return None

    return rank_shortlist(
        job_title=job_title,
        job_description=job_description,
        candidates_data=candidates_data,
        pipeline_config=config,
    )
