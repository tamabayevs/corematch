"""
CoreMatch — CV Screening Agent (Pipeline Stage 1)
Matches candidate CV/resume against job description.
Produces a structured evaluation with scores and recommendation.
"""
import os
import logging
from typing import Optional, Dict

from ai.providers import AgentResult, get_provider_for_stage, parse_json_response

logger = logging.getLogger(__name__)

# Default thresholds (overridden by pipeline_config)
DEFAULT_ADVANCE_THRESHOLD = 70
DEFAULT_REJECT_THRESHOLD = 30

# Load prompt template
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt_template() -> str:
    path = os.path.join(_PROMPT_DIR, "cv_screening.txt")
    with open(path, "r") as f:
        return f.read()


def screen_cv(
    cv_text: str,
    job_title: str,
    job_description: str,
    pipeline_config: Dict,
    linkedin_url: Optional[str] = None,
) -> AgentResult:
    """Run the CV screening agent.

    Args:
        cv_text: Extracted text from the candidate's CV.
        job_title: The job title from the campaign.
        job_description: The job description from the campaign.
        pipeline_config: Pipeline configuration dict (with stages and defaults).
        linkedin_url: Optional LinkedIn profile URL.

    Returns:
        AgentResult with scores, recommendation, and reasoning.
    """
    if not cv_text or not cv_text.strip():
        return AgentResult(
            overall_score=0,
            recommendation="needs_review",
            confidence=0.0,
            summary="CV text could not be extracted. Manual review required.",
            concerns=["CV text extraction failed or produced empty result"],
            provider="none",
            model_used="none",
        )

    # Get stage-specific config
    stage_config = _get_stage_config(pipeline_config, stage=1)
    advance_threshold = stage_config.get("advance_threshold", DEFAULT_ADVANCE_THRESHOLD)
    reject_threshold = stage_config.get("reject_threshold", DEFAULT_REJECT_THRESHOLD)

    # Build prompt
    template = _load_prompt_template()
    linkedin_section = ""
    if linkedin_url:
        linkedin_section = f"## LinkedIn Profile\nURL: {linkedin_url}"

    prompt = template.format(
        job_title=job_title,
        job_description=job_description or "No detailed description provided.",
        cv_text=cv_text[:8000],  # Limit CV text to ~8k chars to stay within context
        linkedin_section=linkedin_section,
        advance_threshold=advance_threshold,
        reject_threshold=reject_threshold,
    )

    # Get provider and model
    try:
        provider, model = get_provider_for_stage(pipeline_config, stage=1)
    except Exception as e:
        logger.error("Failed to get AI provider for Stage 1: %s", e)
        return AgentResult(
            overall_score=0,
            recommendation="needs_review",
            confidence=0.0,
            summary=f"AI provider error: {str(e)}",
            concerns=["AI provider configuration error"],
        )

    # Call LLM
    messages = [
        {"role": "system", "content": "You are an expert HR screening agent. Respond with valid JSON only."},
        {"role": "user", "content": prompt},
    ]

    try:
        response = provider.chat_completion(
            messages=messages,
            model=model,
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.error("CV screening LLM call failed: %s", e)
        return AgentResult(
            overall_score=0,
            recommendation="needs_review",
            confidence=0.0,
            summary=f"AI evaluation failed: {str(e)}",
            concerns=["AI evaluation call failed"],
            provider=pipeline_config.get("default_provider", "groq"),
            model_used=model if 'model' in dir() else "unknown",
        )

    # Parse response
    data = parse_json_response(response["content"])
    if not data:
        return AgentResult(
            overall_score=0,
            recommendation="needs_review",
            confidence=0.0,
            summary="Failed to parse AI response",
            concerns=["AI response was not valid JSON"],
            raw_response={"content": response["content"][:500]},
            provider=response.get("provider", ""),
            model_used=response.get("model", ""),
            tokens_used=response.get("tokens_used", 0),
            latency_ms=response.get("latency_ms", 0),
        )

    # Build AgentResult
    overall_score = float(data.get("overall_score", 0))

    # Determine recommendation based on thresholds
    if overall_score >= advance_threshold:
        recommendation = "advance"
    elif overall_score <= reject_threshold:
        recommendation = "reject"
    else:
        recommendation = "needs_review"

    # Use agent's recommendation if it seems more conservative (human safety)
    agent_rec = data.get("recommendation", recommendation)
    if agent_rec == "reject" and recommendation != "reject":
        recommendation = "needs_review"  # Don't auto-reject if score says otherwise

    return AgentResult(
        overall_score=overall_score,
        scores_detail={
            "relevance": float(data.get("relevance", 0)),
            "experience_match": float(data.get("experience_match", 0)),
            "skills_match": float(data.get("skills_match", 0)),
            "education_match": float(data.get("education_match", 0)),
            "skills_found": data.get("skills_found", []),
            "skills_missing": data.get("skills_missing", []),
            "experience_years_estimated": data.get("experience_years_estimated"),
        },
        recommendation=recommendation,
        confidence=float(data.get("confidence", 0.5)),
        summary=data.get("summary", ""),
        strengths=data.get("strengths", []),
        concerns=data.get("concerns", []),
        evidence=data.get("evidence", []),
        model_used=response.get("model", ""),
        provider=response.get("provider", ""),
        raw_response=data,
        tokens_used=response.get("tokens_used", 0),
        latency_ms=response.get("latency_ms", 0),
    )


def _get_stage_config(pipeline_config: Dict, stage: int) -> Dict:
    """Extract stage-specific config from pipeline_config."""
    stages = pipeline_config.get("stages", [])
    for s in stages:
        if s.get("stage") == stage:
            return s
    return {}
