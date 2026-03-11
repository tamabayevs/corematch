"""
CoreMatch — Stage 2: Video Scoring Agent
Wraps the existing video scoring pipeline to produce a holistic Stage 2
recommendation that incorporates CV screening data + video scores.

For pipeline-enabled campaigns only. Non-pipeline campaigns continue using
the existing ai/scorer.py directly.
"""
import logging
import time
from typing import Optional

from ai.providers import AgentResult, get_provider_for_stage, parse_json_response

logger = logging.getLogger(__name__)


def evaluate_video_stage(
    candidate_name: str,
    job_title: str,
    job_description: str,
    video_scores: list,
    transcripts: list,
    cv_summary: Optional[str],
    pipeline_config: dict,
) -> AgentResult:
    """
    Produce a holistic Stage 2 recommendation from video scores + transcripts + CV data.

    Args:
        candidate_name: Candidate's full name.
        job_title: Campaign job title.
        job_description: Campaign job description.
        video_scores: List of dicts with per-question AI scores from existing scorer.
        transcripts: List of dicts with question_text + transcript text.
        cv_summary: Summary from Stage 1 CV screening (if available).
        pipeline_config: Pipeline configuration dict.

    Returns:
        AgentResult with holistic video stage recommendation.
    """
    if not video_scores:
        return AgentResult(
            recommendation="needs_review",
            summary="No video scores available for evaluation.",
            provider="none",
            model_used="none",
        )

    # Build transcript section
    transcript_parts = []
    for i, t in enumerate(transcripts):
        q_text = t.get("question_text", f"Question {i + 1}")
        t_text = t.get("transcript", "").strip()
        if t_text:
            transcript_parts.append(f"Q{i+1}: {q_text}\nA: {t_text[:2000]}")

    transcript_section = "\n\n".join(transcript_parts) if transcript_parts else "No transcripts available."

    # Build scores section
    score_parts = []
    total_score = 0
    for s in video_scores:
        q_idx = s.get("question_index", "?")
        score = s.get("overall_score", 0)
        tier = s.get("tier", "unknown")
        total_score += score
        score_parts.append(f"Q{q_idx}: Score {score}/100 (Tier: {tier})")

    avg_score = total_score / len(video_scores) if video_scores else 0
    scores_section = "\n".join(score_parts)

    cv_section = f"\n## CV Screening Summary\n{cv_summary}" if cv_summary else ""

    prompt = f"""You are an expert HR evaluation agent for CoreMatch. Your task is to provide a holistic assessment of a candidate's video interview performance.

## Job Details
- **Job Title:** {job_title}
- **Job Description:** {job_description}

## Candidate: {candidate_name}
{cv_section}

## Video Interview Scores (per question)
{scores_section}
Average Score: {avg_score:.1f}/100

## Interview Transcripts
{transcript_section}

## Your Task
Provide a holistic evaluation combining the video interview performance with any CV screening data. Consider:
1. Communication quality and clarity
2. Depth and relevance of answers
3. Alignment with the job requirements
4. Overall impression and confidence

Respond with ONLY valid JSON:
{{
    "overall_score": <0-100>,
    "communication_score": <0-100>,
    "content_quality": <0-100>,
    "job_alignment": <0-100>,
    "recommendation": "<advance|reject|needs_review>",
    "confidence": <0.0-1.0>,
    "summary": "<2-3 sentence holistic assessment>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "concerns": ["<concern 1>", "<concern 2>"],
    "evidence": [
        {{"claim": "<observation>", "source": "video", "detail": "<specific example from transcript>"}}
    ]
}}"""

    try:
        provider, model = get_provider_for_stage(pipeline_config, stage=2)
    except Exception as e:
        logger.error("Failed to get provider for Stage 2: %s", e)
        return AgentResult(
            overall_score=avg_score,
            recommendation="needs_review",
            summary=f"Provider unavailable. Average video score: {avg_score:.1f}/100",
            provider="fallback",
            model_used="none",
        )

    start_time = time.time()
    try:
        response = provider.chat_completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1500,
        )
        latency_ms = int((time.time() - start_time) * 1000)

        content = response["content"]
        tokens_used = response.get("tokens_used", 0)

        parsed = parse_json_response(content)
        if not parsed:
            return AgentResult(
                overall_score=avg_score,
                recommendation="needs_review",
                summary=f"Failed to parse agent response. Average video score: {avg_score:.1f}/100",
                provider=provider.__class__.__name__,
                model_used=model,
                latency_ms=latency_ms,
            )

        overall = float(parsed.get("overall_score", avg_score))
        recommendation = parsed.get("recommendation", "needs_review")
        if recommendation not in ("advance", "reject", "needs_review"):
            recommendation = "needs_review"

        return AgentResult(
            overall_score=overall,
            scores_detail={
                "communication_score": parsed.get("communication_score", 0),
                "content_quality": parsed.get("content_quality", 0),
                "job_alignment": parsed.get("job_alignment", 0),
            },
            recommendation=recommendation,
            confidence=float(parsed.get("confidence", 0.5)),
            summary=parsed.get("summary", ""),
            strengths=parsed.get("strengths", []),
            concerns=parsed.get("concerns", []),
            evidence=parsed.get("evidence", []),
            model_used=model,
            provider=provider.__class__.__name__,
            raw_response=parsed,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error("Stage 2 video agent error: %s", e)
        return AgentResult(
            overall_score=avg_score,
            recommendation="needs_review",
            summary=f"Agent error: {str(e)[:100]}. Average video score: {avg_score:.1f}/100",
            provider=provider.__class__.__name__,
            model_used=model,
            latency_ms=latency_ms,
        )
