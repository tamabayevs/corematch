"""
CoreMatch — Calibration Blueprint
Scorecard calibration view: side-by-side reviewer comparison with disagreement highlighting.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
calibration_bp = Blueprint("calibration", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/calibration/:campaign_id — calibration overview
# ──────────────────────────────────────────────────────────────

@calibration_bp.route("/<campaign_id>", methods=["GET"])
@require_auth
def calibration_overview(campaign_id):
    """
    Get calibration data for a campaign: all candidates with evaluations
    from multiple reviewers, highlighting disagreements.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify campaign belongs to user
                cur.execute(
                    "SELECT id, name FROM campaigns WHERE id = %s AND user_id = %s",
                    (campaign_id, g.current_user["id"]),
                )
                campaign = cur.fetchone()
                if not campaign:
                    return jsonify({"error": "Campaign not found"}), 404

                # Get all candidates with evaluations for this campaign
                cur.execute(
                    """
                    SELECT c.id, c.full_name, c.email, c.overall_score, c.tier,
                           c.hr_decision, c.status
                    FROM candidates c
                    WHERE c.campaign_id = %s AND c.status IN ('submitted', 'scored')
                    ORDER BY c.full_name ASC
                    """,
                    (campaign_id,),
                )
                candidates = cur.fetchall()

                # Get all evaluations for these candidates
                candidate_ids = [str(c[0]) for c in candidates]
                evaluations_map = {}

                if candidate_ids:
                    placeholders = ",".join(["%s"] * len(candidate_ids))
                    cur.execute(
                        f"""
                        SELECT ce.candidate_id, ce.reviewer_id, u.full_name as reviewer_name,
                               ce.ratings, ce.overall_rating, ce.notes, ce.submitted_at
                        FROM candidate_evaluations ce
                        JOIN users u ON ce.reviewer_id = u.id
                        WHERE ce.candidate_id IN ({placeholders})
                        ORDER BY ce.submitted_at ASC
                        """,
                        candidate_ids,
                    )
                    for row in cur.fetchall():
                        cid = str(row[0])
                        if cid not in evaluations_map:
                            evaluations_map[cid] = []
                        evaluations_map[cid].append({
                            "reviewer_id": str(row[1]),
                            "reviewer_name": row[2],
                            "ratings": row[3],
                            "overall_rating": row[4],
                            "notes": row[5],
                            "submitted_at": row[6].isoformat() if row[6] else None,
                        })

    except Exception as e:
        logger.error("Calibration overview error: %s", str(e))
        return jsonify({"error": "Failed to fetch calibration data"}), 500

    # Compute disagreement metrics
    results = []
    for c in candidates:
        cid = str(c[0])
        evals = evaluations_map.get(cid, [])

        # Calculate disagreement score
        disagreement = 0.0
        if len(evals) >= 2:
            ratings_list = [e["overall_rating"] for e in evals if e["overall_rating"] is not None]
            if len(ratings_list) >= 2:
                avg = sum(ratings_list) / len(ratings_list)
                variance = sum((r - avg) ** 2 for r in ratings_list) / len(ratings_list)
                disagreement = round(variance ** 0.5, 2)  # standard deviation

        results.append({
            "id": cid,
            "full_name": c[1],
            "email": c[2],
            "ai_score": float(c[3]) if c[3] is not None else None,
            "tier": c[4],
            "hr_decision": c[5],
            "status": c[6],
            "evaluations": evals,
            "evaluation_count": len(evals),
            "disagreement_score": disagreement,
            "avg_human_rating": round(
                sum(e["overall_rating"] for e in evals if e["overall_rating"]) / max(len([e for e in evals if e["overall_rating"]]), 1), 1
            ) if evals else None,
        })

    # Sort by disagreement (highest first) to surface conflicts
    results.sort(key=lambda x: x["disagreement_score"], reverse=True)

    return jsonify({
        "campaign": {"id": str(campaign[0]), "name": campaign[1]},
        "candidates": results,
        "total_candidates": len(results),
        "total_with_evaluations": len([r for r in results if r["evaluation_count"] > 0]),
        "avg_disagreement": round(
            sum(r["disagreement_score"] for r in results) / max(len(results), 1), 2
        ),
    })


# ──────────────────────────────────────────────────────────────
# GET /api/calibration/:campaign_id/candidate/:candidate_id — detailed comparison
# ──────────────────────────────────────────────────────────────

@calibration_bp.route("/<campaign_id>/candidate/<candidate_id>", methods=["GET"])
@require_auth
def candidate_calibration_detail(campaign_id, candidate_id):
    """
    Detailed side-by-side comparison for a single candidate:
    each reviewer's ratings broken down by competency.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify access
                cur.execute(
                    """
                    SELECT c.id, c.full_name, c.overall_score, c.tier
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s AND c.campaign_id = %s AND camp.user_id = %s
                    """,
                    (candidate_id, campaign_id, g.current_user["id"]),
                )
                candidate = cur.fetchone()
                if not candidate:
                    return jsonify({"error": "Candidate not found"}), 404

                # Get all evaluations with full rating details
                cur.execute(
                    """
                    SELECT ce.id, ce.reviewer_id, u.full_name as reviewer_name,
                           ce.scorecard_template_id, st.name as template_name,
                           ce.ratings, ce.overall_rating, ce.notes, ce.submitted_at
                    FROM candidate_evaluations ce
                    JOIN users u ON ce.reviewer_id = u.id
                    LEFT JOIN scorecard_templates st ON ce.scorecard_template_id = st.id
                    WHERE ce.candidate_id = %s
                    ORDER BY ce.submitted_at ASC
                    """,
                    (candidate_id,),
                )
                eval_rows = cur.fetchall()

    except Exception as e:
        logger.error("Candidate calibration detail error: %s", str(e))
        return jsonify({"error": "Failed to fetch calibration detail"}), 500

    evaluations = []
    for r in eval_rows:
        evaluations.append({
            "id": str(r[0]),
            "reviewer_id": str(r[1]),
            "reviewer_name": r[2],
            "scorecard_template_id": str(r[3]) if r[3] else None,
            "template_name": r[4],
            "ratings": r[5],
            "overall_rating": r[6],
            "notes": r[7],
            "submitted_at": r[8].isoformat() if r[8] else None,
        })

    # Compute per-competency disagreement
    competency_comparison = {}
    for ev in evaluations:
        if isinstance(ev["ratings"], list):
            for rating in ev["ratings"]:
                comp_name = rating.get("name", "Unknown")
                if comp_name not in competency_comparison:
                    competency_comparison[comp_name] = []
                competency_comparison[comp_name].append({
                    "reviewer": ev["reviewer_name"],
                    "score": rating.get("score", rating.get("rating")),
                })

    # Calculate per-competency stats
    competency_stats = []
    for comp_name, scores in competency_comparison.items():
        values = [s["score"] for s in scores if s["score"] is not None]
        if values:
            avg = sum(values) / len(values)
            spread = max(values) - min(values) if len(values) > 1 else 0
            competency_stats.append({
                "competency": comp_name,
                "scores": scores,
                "avg": round(avg, 1),
                "min": min(values),
                "max": max(values),
                "spread": spread,
                "has_disagreement": spread >= 2,
            })

    return jsonify({
        "candidate": {
            "id": str(candidate[0]),
            "full_name": candidate[1],
            "ai_score": float(candidate[2]) if candidate[2] is not None else None,
            "tier": candidate[3],
        },
        "evaluations": evaluations,
        "competency_stats": competency_stats,
    })
