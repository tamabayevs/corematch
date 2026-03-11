"""
CoreMatch — Shortlist Ranking Agent (Pipeline Stage 4)
Ranks and compares all candidates who passed Stage 3 (deep evaluation)
within a campaign. Produces a final ordered shortlist with comparative analysis.

Unlike other stages (per-candidate), this agent runs across ALL approved
candidates in a campaign to produce relative rankings.
"""
import os
import time
import logging
from typing import List, Dict

from ai.providers import AgentResult, get_provider_for_stage, parse_json_response

logger = logging.getLogger(__name__)

_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt_template() -> str:
    path = os.path.join(_PROMPT_DIR, "shortlist_ranking.txt")
    with open(path, "r") as f:
        return f.read()


def rank_shortlist(
    job_title: str,
    job_description: str,
    candidates_data: List[Dict],
    pipeline_config: dict,
) -> AgentResult:
    """
    Rank and compare all Stage 3-approved candidates.

    Args:
        job_title: Campaign job title.
        job_description: Campaign job description.
        candidates_data: List of dicts, each containing:
            - candidate_id, candidate_name
            - cv_summary (from Stage 1)
            - video_summary (from Stage 2)
            - deep_summary (from Stage 3)
            - deep_score, video_score, cv_score
            - strengths, concerns
        pipeline_config: Pipeline configuration dict.

    Returns:
        AgentResult with rankings in scores_detail and executive summary.
    """
    if not candidates_data:
        return AgentResult(
            recommendation="needs_review",
            summary="No candidates available for shortlist ranking.",
            provider="none",
            model_used="none",
        )

    if len(candidates_data) == 1:
        # Only one candidate — no comparison needed
        c = candidates_data[0]
        return AgentResult(
            overall_score=float(c.get("deep_score", 0)),
            scores_detail={
                "rankings": [{
                    "candidate_id": c["candidate_id"],
                    "candidate_name": c["candidate_name"],
                    "rank": 1,
                    "final_score": float(c.get("deep_score", 0)),
                    "comparative_advantage": "Only candidate in the shortlist",
                    "key_risk": "; ".join(c.get("concerns", [])[:2]) or "None identified",
                    "interview_focus": "General fit assessment",
                    "summary": c.get("deep_summary", ""),
                }],
                "hiring_insights": ["Single candidate in pipeline — consider expanding sourcing"],
            },
            recommendation="advance",
            confidence=0.7,
            summary=f"Single candidate {c['candidate_name']} with score {c.get('deep_score', 0):.0f}/100.",
            strengths=c.get("strengths", []),
            concerns=c.get("concerns", []),
            provider="none",
            model_used="none",
        )

    # Build candidates section for the prompt
    candidate_parts = []
    for i, c in enumerate(candidates_data):
        part = f"""### Candidate {i+1}: {c['candidate_name']} (ID: {c['candidate_id']})
- **CV Score:** {c.get('cv_score', 'N/A')}/100 — {c.get('cv_summary', 'No CV data')}
- **Video Score:** {c.get('video_score', 'N/A')}/100 — {c.get('video_summary', 'No video data')}
- **Deep Eval Score:** {c.get('deep_score', 'N/A')}/100 — {c.get('deep_summary', 'No deep eval data')}
- **Strengths:** {', '.join(c.get('strengths', ['None listed']))}
- **Concerns:** {', '.join(c.get('concerns', ['None listed']))}"""
        candidate_parts.append(part)

    candidates_section = "\n\n".join(candidate_parts)

    # Load and fill template
    template = _load_prompt_template()
    prompt = template.format(
        job_title=job_title,
        job_description=job_description or "No detailed description provided.",
        candidates_section=candidates_section,
    )

    # Get provider and model
    try:
        provider, model = get_provider_for_stage(pipeline_config, stage=4)
    except Exception as e:
        logger.error("Failed to get provider for Stage 4: %s", e)
        # Fallback: rank by deep_score
        return _fallback_ranking(candidates_data)

    # Call LLM
    start_time = time.time()
    try:
        response = provider.chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert HR shortlisting agent. Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=3000,
        )
        latency_ms = int((time.time() - start_time) * 1000)

        content = response["content"]
        tokens_used = response.get("tokens_used", 0)

        parsed = parse_json_response(content)
        if not parsed:
            return _fallback_ranking(candidates_data)

        rankings = parsed.get("rankings", [])

        # Calculate average final score
        avg_score = 0
        if rankings:
            avg_score = sum(r.get("final_score", 0) for r in rankings) / len(rankings)

        return AgentResult(
            overall_score=avg_score,
            scores_detail={
                "rankings": rankings,
                "hiring_insights": parsed.get("hiring_insights", []),
            },
            recommendation=parsed.get("recommendation", "advance"),
            confidence=float(parsed.get("confidence", 0.5)),
            summary=parsed.get("executive_summary", ""),
            strengths=[r.get("comparative_advantage", "") for r in rankings[:3]],
            concerns=[r.get("key_risk", "") for r in rankings[:3]],
            evidence=[],
            model_used=model,
            provider=provider.__class__.__name__,
            raw_response=parsed,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error("Stage 4 shortlist ranking error: %s", e)
        return _fallback_ranking(candidates_data)


def _fallback_ranking(candidates_data: List[Dict]) -> AgentResult:
    """Produce a simple score-based ranking when AI is unavailable."""
    sorted_candidates = sorted(
        candidates_data,
        key=lambda c: float(c.get("deep_score", 0)),
        reverse=True,
    )

    rankings = []
    for i, c in enumerate(sorted_candidates):
        rankings.append({
            "candidate_id": c["candidate_id"],
            "candidate_name": c["candidate_name"],
            "rank": i + 1,
            "final_score": float(c.get("deep_score", 0)),
            "comparative_advantage": "Ranked by AI evaluation score",
            "key_risk": "AI ranking unavailable — manual review recommended",
            "interview_focus": "General assessment",
            "summary": c.get("deep_summary", ""),
        })

    avg_score = sum(r["final_score"] for r in rankings) / len(rankings) if rankings else 0

    return AgentResult(
        overall_score=avg_score,
        scores_detail={
            "rankings": rankings,
            "hiring_insights": ["AI ranking agent unavailable — candidates ranked by deep evaluation score"],
        },
        recommendation="advance",
        confidence=0.3,
        summary=f"Fallback ranking of {len(rankings)} candidates by deep evaluation score.",
        provider="fallback",
        model_used="none",
    )
