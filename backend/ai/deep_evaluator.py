"""
CoreMatch — Deep Evaluation Agent (Pipeline Stage 3)
Comprehensive candidate assessment combining CV data, video transcripts,
and AI scores into a single holistic evaluation.

Uses a higher-capability model (Claude or GPT-4 class by default) since
this is the most consequential evaluation stage before final shortlisting.
"""
import os
import time
import logging
from typing import Optional, List, Dict

from ai.providers import AgentResult, get_provider_for_stage, parse_json_response

logger = logging.getLogger(__name__)

_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt_template() -> str:
    path = os.path.join(_PROMPT_DIR, "deep_evaluation.txt")
    with open(path, "r") as f:
        return f.read()


def evaluate_candidate_deep(
    candidate_name: str,
    job_title: str,
    job_description: str,
    cv_text: Optional[str],
    video_scores: List[Dict],
    transcripts: List[Dict],
    pipeline_config: dict,
) -> AgentResult:
    """
    Produce a comprehensive Stage 3 evaluation combining all candidate data.

    Args:
        candidate_name: Candidate's full name.
        job_title: Campaign job title.
        job_description: Campaign job description.
        cv_text: Extracted CV text (may be None if no CV uploaded).
        video_scores: List of dicts with per-question AI scores.
        transcripts: List of dicts with question_text + transcript text.
        pipeline_config: Pipeline configuration dict.

    Returns:
        AgentResult with deep evaluation scores and recommendation.
    """
    if not video_scores and not cv_text:
        return AgentResult(
            recommendation="needs_review",
            summary="Insufficient data for deep evaluation. No CV or video scores available.",
            provider="none",
            model_used="none",
        )

    # Build CV section
    cv_section = ""
    if cv_text and cv_text.strip():
        cv_section = f"## CV / Resume\n{cv_text[:6000]}"
    else:
        cv_section = "## CV / Resume\nNo CV data available."

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

    avg_video_score = total_score / len(video_scores) if video_scores else 0
    scores_section = "\n".join(score_parts) if score_parts else "No video scores available."

    # Load and fill template
    template = _load_prompt_template()
    prompt = template.format(
        job_title=job_title,
        job_description=job_description or "No detailed description provided.",
        candidate_name=candidate_name,
        cv_section=cv_section,
        scores_section=scores_section,
        avg_video_score=f"{avg_video_score:.1f}",
        transcript_section=transcript_section,
    )

    # Get provider and model
    try:
        provider, model = get_provider_for_stage(pipeline_config, stage=3)
    except Exception as e:
        logger.error("Failed to get provider for Stage 3: %s", e)
        return AgentResult(
            overall_score=avg_video_score,
            recommendation="needs_review",
            summary=f"Provider unavailable. Average video score: {avg_video_score:.1f}/100",
            provider="fallback",
            model_used="none",
        )

    # Call LLM
    start_time = time.time()
    try:
        response = provider.chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert senior HR evaluation agent. Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=3000,
        )
        latency_ms = int((time.time() - start_time) * 1000)

        content = response["content"]
        tokens_used = response.get("tokens_used", 0)

        parsed = parse_json_response(content)
        if not parsed:
            return AgentResult(
                overall_score=avg_video_score,
                recommendation="needs_review",
                summary=f"Failed to parse agent response. Average video score: {avg_video_score:.1f}/100",
                provider=provider.__class__.__name__,
                model_used=model,
                latency_ms=latency_ms,
            )

        # Extract composite score
        composite = float(parsed.get("composite_score", avg_video_score))

        # Determine recommendation
        recommendation = parsed.get("recommendation", "needs_review")
        if recommendation not in ("advance", "reject", "needs_review"):
            recommendation = "needs_review"

        return AgentResult(
            overall_score=composite,
            scores_detail={
                "technical_fit": parsed.get("technical_fit", 0),
                "communication_quality": parsed.get("communication_quality", 0),
                "cultural_fit": parsed.get("cultural_fit", 0),
                "growth_potential": parsed.get("growth_potential", 0),
                "experience_depth": parsed.get("experience_depth", 0),
                "risk_factors": parsed.get("risk_factors", []),
                "skills_matrix": parsed.get("skills_matrix", []),
                "interview_focus_areas": parsed.get("interview_focus_areas", []),
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
        logger.error("Stage 3 deep evaluation error: %s", e)
        return AgentResult(
            overall_score=avg_video_score,
            recommendation="needs_review",
            summary=f"Agent error: {str(e)[:100]}. Average video score: {avg_video_score:.1f}/100",
            provider=provider.__class__.__name__,
            model_used=model,
            latency_ms=latency_ms,
        )
