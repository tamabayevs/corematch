"""
CoreMatch — Video Processor Worker
Background RQ job that processes candidate video answers through the AI pipeline.
Called by: public.py:_submit_for_processing() → RQ enqueue → this function.
"""
import json
import logging
import datetime
from database.connection import get_db
from services.storage_service import get_storage_service
from services.email_service import get_email_service
from ai.scorer import score_video, TIER_STRONG_PROCEED, TIER_CONSIDER

logger = logging.getLogger(__name__)


def process_candidate(candidate_id: str) -> dict:
    """
    Process all uploaded video answers for a candidate through the AI pipeline.

    Steps:
    1. Fetch candidate + campaign + HR user data
    2. For each video_answer: download → score_video() → save scores
    3. Compute overall candidate score and tier
    4. Send notification emails
    5. Audit log

    Returns dict with processing summary.
    """
    logger.info("Starting AI processing for candidate %s", candidate_id)

    # ── Step 1: Fetch candidate, campaign, and HR user data ──
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.id, c.campaign_id, c.email, c.full_name, c.reference_id,
                           camp.job_title, camp.job_description, camp.language, camp.name as campaign_name,
                           u.email as hr_email, u.full_name as hr_name,
                           u.notify_on_complete, u.company_name
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    JOIN users u ON camp.user_id = u.id
                    WHERE c.id = %s
                    """,
                    (candidate_id,),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Failed to fetch candidate data for %s: %s", candidate_id, str(e))
        raise

    if not row:
        logger.error("Candidate %s not found", candidate_id)
        raise ValueError(f"Candidate {candidate_id} not found")

    candidate_email = row[2]
    candidate_name = row[3]
    reference_id = row[4]
    job_title = row[5]
    job_description = row[6] or ""
    language = row[7] or "en"
    campaign_name = row[8]
    hr_email = row[9]
    hr_name = row[10]
    notify_on_complete = row[11]
    company_name = row[12] or "the company"

    # ── Step 2: Fetch video answers ──
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, question_index, question_text, storage_key
                    FROM video_answers
                    WHERE candidate_id = %s AND storage_key IS NOT NULL
                    ORDER BY question_index ASC
                    """,
                    (candidate_id,),
                )
                video_answers = cur.fetchall()
    except Exception as e:
        logger.error("Failed to fetch video answers for %s: %s", candidate_id, str(e))
        raise

    if not video_answers:
        logger.warning("No video answers found for candidate %s", candidate_id)
        return {"candidate_id": candidate_id, "processed": 0, "failed": 0}

    storage = get_storage_service()
    processed_count = 0
    failed_count = 0
    all_scores = []

    # ── Step 3: Process each video answer ──
    for va in video_answers:
        va_id = str(va[0])
        question_index = va[1]
        question_text = va[2]
        storage_key = va[3]

        logger.info(
            "Processing video answer %s (Q%d) for candidate %s",
            va_id, question_index, candidate_id,
        )

        # Mark as processing
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE video_answers SET processing_status = 'processing' WHERE id = %s",
                        (va_id,),
                    )
        except Exception as e:
            logger.error("Failed to mark video %s as processing: %s", va_id, str(e))

        try:
            # Download video from storage
            video_bytes = storage.download_file(storage_key)
            logger.info("Downloaded video %s: %d bytes", storage_key, len(video_bytes))

            # Run AI pipeline: extract audio → transcribe → score
            result = score_video(
                video_bytes=video_bytes,
                question=question_text,
                job_title=job_title,
                job_description=job_description,
                expected_language=language,
            )

            # Save AI score to database
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ai_scores
                        (video_answer_id, candidate_id, content_score, communication_score,
                         behavioral_score, overall_score, tier, strengths, improvements,
                         language_match, model_used, scoring_source, raw_response)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (video_answer_id) DO UPDATE SET
                            content_score = EXCLUDED.content_score,
                            communication_score = EXCLUDED.communication_score,
                            behavioral_score = EXCLUDED.behavioral_score,
                            overall_score = EXCLUDED.overall_score,
                            tier = EXCLUDED.tier,
                            strengths = EXCLUDED.strengths,
                            improvements = EXCLUDED.improvements,
                            language_match = EXCLUDED.language_match,
                            model_used = EXCLUDED.model_used,
                            scoring_source = EXCLUDED.scoring_source,
                            raw_response = EXCLUDED.raw_response
                        """,
                        (
                            va_id, candidate_id,
                            result.content_score, result.communication_score,
                            result.behavioral_score, result.overall_score,
                            result.tier,
                            json.dumps(result.strengths),
                            json.dumps(result.improvements),
                            result.language_match,
                            result.model_used,
                            result.scoring_source,
                            json.dumps(result.raw_response),
                        ),
                    )

                    # Update video_answer with transcript and status
                    cur.execute(
                        """
                        UPDATE video_answers
                        SET transcript = %s,
                            detected_language = %s,
                            processing_status = 'complete',
                            processed_at = NOW()
                        WHERE id = %s
                        """,
                        (result.transcript, result.detected_language, va_id),
                    )

            all_scores.append(result.overall_score)
            processed_count += 1
            logger.info(
                "Scored video %s: overall=%.1f tier=%s",
                va_id, result.overall_score, result.tier,
            )

        except Exception as e:
            logger.error(
                "Failed to process video %s for candidate %s: %s",
                va_id, candidate_id, str(e),
            )
            failed_count += 1

            # Mark as failed but continue to next video
            try:
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE video_answers SET processing_status = 'failed' WHERE id = %s",
                            (va_id,),
                        )
            except Exception:
                pass

    # ── Step 4: Compute overall candidate score and tier ──
    if all_scores:
        overall_score = round(sum(all_scores) / len(all_scores), 2)

        if overall_score >= TIER_STRONG_PROCEED:
            tier = "strong_proceed"
        elif overall_score >= TIER_CONSIDER:
            tier = "consider"
        else:
            tier = "likely_pass"

        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE candidates
                        SET overall_score = %s, tier = %s
                        WHERE id = %s
                        """,
                        (overall_score, tier, candidate_id),
                    )
        except Exception as e:
            logger.error("Failed to update candidate score: %s", str(e))
    else:
        overall_score = None
        tier = None

    # ── Step 5: Send notification emails ──
    email_svc = get_email_service()

    # Candidate confirmation email
    try:
        email_svc.send_candidate_confirmation(
            to_email=candidate_email,
            to_name=candidate_name,
            company_name=company_name,
            job_title=job_title,
            reference_id=reference_id,
            submitted_at=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        )
        logger.info("Sent confirmation email to candidate %s", candidate_email)
    except Exception as e:
        logger.error("Failed to send candidate confirmation email: %s", str(e))

    # HR notification email (if enabled)
    if notify_on_complete and overall_score is not None:
        try:
            import os
            frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
            dashboard_url = f"{frontend_url}/dashboard/candidates/{candidate_id}"

            # Get top strengths from all scores
            top_strengths = []
            try:
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT strengths FROM ai_scores WHERE candidate_id = %s",
                            (candidate_id,),
                        )
                        for row in cur.fetchall():
                            if row[0]:
                                strengths = row[0] if isinstance(row[0], list) else json.loads(row[0])
                                top_strengths.extend(strengths)
            except Exception:
                pass

            # Deduplicate and limit to top 3
            seen = set()
            unique_strengths = []
            for s in top_strengths:
                if s not in seen:
                    seen.add(s)
                    unique_strengths.append(s)
                if len(unique_strengths) >= 3:
                    break

            email_svc.send_hr_notification(
                to_email=hr_email,
                hr_name=hr_name or "there",
                candidate_name=candidate_name,
                job_title=job_title,
                campaign_name=campaign_name,
                overall_score=overall_score,
                tier=tier,
                strengths=unique_strengths,
                dashboard_url=dashboard_url,
            )
            logger.info("Sent HR notification to %s", hr_email)
        except Exception as e:
            logger.error("Failed to send HR notification email: %s", str(e))

    # ── Step 6: Audit log ──
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log (action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        "candidate.processed",
                        "candidate",
                        candidate_id,
                        json.dumps({
                            "processed": processed_count,
                            "failed": failed_count,
                            "overall_score": overall_score,
                            "tier": tier,
                        }),
                        "system",
                    ),
                )
    except Exception as e:
        logger.error("Failed to write audit log: %s", str(e))

    # ── Step 7: In-app notification to campaign owner ──
    from services.notification_service import notify_campaign_owner
    notify_campaign_owner(
        candidate_id=candidate_id,
        notification_type="scoring",
        title="AI scoring complete",
        message=f"AI scoring complete for {candidate_name}. Score: {overall_score}, Tier: {tier}.",
        metadata={"overall_score": overall_score, "tier": tier},
    )

    summary = {
        "candidate_id": candidate_id,
        "processed": processed_count,
        "failed": failed_count,
        "overall_score": overall_score,
        "tier": tier,
    }
    logger.info("Completed processing for candidate %s: %s", candidate_id, summary)
    return summary
