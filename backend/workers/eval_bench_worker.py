"""
CoreMatch — Eval Bench Worker
Processes benchmark videos through the AI scorer for model evaluation.
Runs as an RQ job — each video: download → FFmpeg → Whisper → LLM score → store result.
"""
import time
import logging
from database.connection import get_db

logger = logging.getLogger(__name__)


def run_eval(run_id: str, user_id: str, model_name: str) -> dict:
    """
    Process all benchmark videos for this user through the AI scorer
    with the specified model. Updates eval_results rows as each completes.
    """
    from ai.scorer import _extract_audio_wav, transcribe_audio, score_answer
    from services.storage_service import get_storage_service

    storage = get_storage_service()

    # Fetch benchmarks for this user
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, question_text, job_title, job_description, language, storage_key "
                "FROM eval_benchmarks WHERE user_id = %s ORDER BY created_at",
                (user_id,)
            )
            benchmarks = cur.fetchall()

    if not benchmarks:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE eval_runs SET status = 'failed', completed_at = NOW() WHERE id = %s",
                    (run_id,)
                )
        return {"status": "failed", "error": "No benchmarks found"}

    # Update run as started
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE eval_runs SET status = 'running', started_at = NOW(), "
                "total_benchmarks = %s WHERE id = %s",
                (len(benchmarks), run_id)
            )

    completed = 0
    failed = 0

    for bm in benchmarks:
        bm_id, bm_name, question, job_title, job_desc, language, storage_key = bm
        start_time = time.time()

        try:
            # Download video from storage
            video_bytes = storage.download_file(storage_key)

            # Extract audio
            audio_bytes = _extract_audio_wav(video_bytes)

            # Transcribe
            transcript, detected_lang = transcribe_audio(audio_bytes, language or "en")

            # Score with specified model
            result = score_answer(
                question=question,
                transcript=transcript,
                job_title=job_title,
                job_description=job_desc or "",
                duration_seconds=len(audio_bytes) / (16000 * 2),
                detected_language=detected_lang,
                expected_language=language or "en",
                scoring_model=model_name,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Store result
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE eval_results SET
                            status = 'complete',
                            transcript = %s,
                            detected_language = %s,
                            content_score = %s,
                            communication_score = %s,
                            behavioral_score = %s,
                            overall_score = %s,
                            tier = %s,
                            strengths = %s::jsonb,
                            improvements = %s::jsonb,
                            language_match = %s,
                            model_used = %s,
                            latency_ms = %s,
                            raw_response = %s::jsonb
                        WHERE run_id = %s AND benchmark_id = %s
                    """, (
                        result.transcript,
                        result.detected_language,
                        result.content_score,
                        result.communication_score,
                        result.behavioral_score,
                        result.overall_score,
                        result.tier,
                        __import__("json").dumps(result.strengths),
                        __import__("json").dumps(result.improvements),
                        result.language_match,
                        result.model_used,
                        latency_ms,
                        __import__("json").dumps(result.raw_response),
                        run_id, bm_id,
                    ))

            completed += 1
            logger.info("Eval benchmark '%s' complete: score=%.1f tier=%s (%dms)",
                        bm_name, result.overall_score, result.tier, latency_ms)

        except Exception as e:
            failed += 1
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error("Eval benchmark '%s' failed: %s", bm_name, str(e))

            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE eval_results SET
                            status = 'failed',
                            error_message = %s,
                            latency_ms = %s
                        WHERE run_id = %s AND benchmark_id = %s
                    """, (str(e)[:500], latency_ms, run_id, bm_id))

        # Update progress counter
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE eval_runs SET completed_benchmarks = %s, failed_benchmarks = %s WHERE id = %s",
                    (completed + failed, failed, run_id)
                )

    # Finalize run
    status = "complete" if failed == 0 else ("partial" if completed > 0 else "failed")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE eval_runs SET status = %s, completed_at = NOW(), "
                "completed_benchmarks = %s, failed_benchmarks = %s WHERE id = %s",
                (status, completed, failed, run_id)
            )

    logger.info("Eval run %s finished: %d complete, %d failed", run_id, completed, failed)
    return {"status": status, "completed": completed, "failed": failed}
