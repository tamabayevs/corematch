"""
CoreMatch — Scorecards Blueprint
Scorecard templates and human evaluations for candidates.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
scorecards_bp = Blueprint("scorecards", __name__)


# GET /api/scorecards/templates — list all scorecard templates (user's + system)
@scorecards_bp.route("/templates", methods=["GET"])
@require_auth
def list_templates():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, name, description, competencies, is_system, created_at, updated_at
                    FROM scorecard_templates
                    WHERE user_id = %s OR is_system = TRUE
                    ORDER BY is_system DESC, created_at DESC
                    """,
                    (g.current_user["id"],),
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("List scorecard templates error: %s", str(e))
        return jsonify({"error": "Failed to fetch templates"}), 500

    return jsonify({
        "templates": [
            {
                "id": str(r[0]),
                "user_id": str(r[1]) if r[1] else None,
                "name": r[2],
                "description": r[3],
                "competencies": r[4],
                "is_system": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
                "updated_at": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ]
    })


# POST /api/scorecards/templates — create custom scorecard template
@scorecards_bp.route("/templates", methods=["POST"])
@require_auth
def create_template():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    description = (data.get("description") or "").strip() or None
    competencies = data.get("competencies", [])

    if not isinstance(competencies, list) or len(competencies) < 2:
        return jsonify({"error": "At least 2 competencies required"}), 400

    # Validate each competency has name and weight
    for comp in competencies:
        if not comp.get("name"):
            return jsonify({"error": "Each competency must have a name"}), 400
        if not isinstance(comp.get("weight", 0), (int, float)):
            return jsonify({"error": "Each competency must have a numeric weight"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO scorecard_templates (user_id, name, description, competencies)
                    VALUES (%s, %s, %s, %s::jsonb)
                    RETURNING id, created_at
                    """,
                    (g.current_user["id"], name, description, json.dumps(competencies)),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Create scorecard template error: %s", str(e))
        return jsonify({"error": "Failed to create template"}), 500

    return jsonify({
        "message": "Scorecard template created",
        "template": {"id": str(row[0]), "name": name, "created_at": row[1].isoformat()},
    }), 201


# PUT /api/scorecards/templates/:id — update own template
@scorecards_bp.route("/templates/<template_id>", methods=["PUT"])
@require_auth
def update_template(template_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, is_system FROM scorecard_templates WHERE id = %s",
                    (template_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    return jsonify({"error": "Template not found"}), 404
                if existing[1]:
                    return jsonify({"error": "Cannot edit system templates"}), 403

                updates = {}
                if "name" in data:
                    updates["name"] = data["name"].strip()
                if "description" in data:
                    updates["description"] = data["description"].strip() or None
                if "competencies" in data:
                    updates["competencies"] = json.dumps(data["competencies"])

                if not updates:
                    return jsonify({"error": "No fields to update"}), 400

                set_parts = []
                values = []
                for k, v in updates.items():
                    if k == "competencies":
                        set_parts.append(f"{k} = %s::jsonb")
                    else:
                        set_parts.append(f"{k} = %s")
                    values.append(v)

                values.extend([template_id, g.current_user["id"]])
                cur.execute(
                    f"UPDATE scorecard_templates SET {', '.join(set_parts)} WHERE id = %s AND user_id = %s",
                    values,
                )
    except Exception as e:
        logger.error("Update scorecard template error: %s", str(e))
        return jsonify({"error": "Failed to update template"}), 500

    return jsonify({"message": "Template updated"})


# DELETE /api/scorecards/templates/:id
@scorecards_bp.route("/templates/<template_id>", methods=["DELETE"])
@require_auth
def delete_template(template_id):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM scorecard_templates WHERE id = %s AND user_id = %s AND is_system = FALSE",
                    (template_id, g.current_user["id"]),
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "Template not found or cannot be deleted"}), 404
    except Exception as e:
        logger.error("Delete scorecard template error: %s", str(e))
        return jsonify({"error": "Failed to delete template"}), 500

    return jsonify({"message": "Template deleted"})


# POST /api/scorecards/evaluate/:candidate_id — submit human evaluation
@scorecards_bp.route("/evaluate/<candidate_id>", methods=["POST"])
@require_auth
def submit_evaluation(candidate_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    ratings = data.get("ratings", [])
    overall_rating = data.get("overall_rating")
    notes = (data.get("notes") or "").strip() or None
    scorecard_template_id = data.get("scorecard_template_id")

    if not isinstance(ratings, list) or len(ratings) == 0:
        return jsonify({"error": "Ratings are required"}), 400
    if overall_rating is not None and not (1 <= int(overall_rating) <= 5):
        return jsonify({"error": "Overall rating must be 1-5"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify candidate access
                cur.execute(
                    """
                    SELECT c.id FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s AND camp.user_id = %s
                    """,
                    (candidate_id, g.current_user["id"]),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Candidate not found"}), 404

                # Upsert evaluation
                cur.execute(
                    """
                    INSERT INTO candidate_evaluations
                    (candidate_id, reviewer_id, scorecard_template_id, ratings, overall_rating, notes)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                    ON CONFLICT (candidate_id, reviewer_id)
                    DO UPDATE SET
                        scorecard_template_id = EXCLUDED.scorecard_template_id,
                        ratings = EXCLUDED.ratings,
                        overall_rating = EXCLUDED.overall_rating,
                        notes = EXCLUDED.notes,
                        submitted_at = NOW()
                    RETURNING id
                    """,
                    (
                        candidate_id, g.current_user["id"], scorecard_template_id,
                        json.dumps(ratings), overall_rating, notes,
                    ),
                )
                eval_id = str(cur.fetchone()[0])

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "candidate.evaluated", "candidate",
                        candidate_id, json.dumps({"overall_rating": overall_rating}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Submit evaluation error: %s", str(e))
        return jsonify({"error": "Failed to submit evaluation"}), 500

    # In-app notification to campaign owner
    from services.notification_service import notify_campaign_owner
    notify_campaign_owner(
        candidate_id=candidate_id,
        notification_type="evaluation",
        title="New scorecard evaluation",
        message=f'{g.current_user["full_name"]} submitted an evaluation.',
        exclude_user_id=g.current_user["id"],
        metadata={"evaluation_id": eval_id, "overall_rating": overall_rating},
    )

    return jsonify({"message": "Evaluation submitted", "evaluation_id": eval_id}), 201


# GET /api/scorecards/evaluate/:candidate_id — get evaluations for a candidate
@scorecards_bp.route("/evaluate/<candidate_id>", methods=["GET"])
@require_auth
def get_evaluations(candidate_id):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.id FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s AND camp.user_id = %s
                    """,
                    (candidate_id, g.current_user["id"]),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Candidate not found"}), 404

                cur.execute(
                    """
                    SELECT ce.id, ce.reviewer_id, u.full_name as reviewer_name,
                           ce.scorecard_template_id, ce.ratings, ce.overall_rating,
                           ce.notes, ce.submitted_at
                    FROM candidate_evaluations ce
                    JOIN users u ON ce.reviewer_id = u.id
                    WHERE ce.candidate_id = %s
                    ORDER BY ce.submitted_at DESC
                    """,
                    (candidate_id,),
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("Get evaluations error: %s", str(e))
        return jsonify({"error": "Failed to fetch evaluations"}), 500

    return jsonify({
        "evaluations": [
            {
                "id": str(r[0]),
                "reviewer_id": str(r[1]),
                "reviewer_name": r[2],
                "scorecard_template_id": str(r[3]) if r[3] else None,
                "ratings": r[4],
                "overall_rating": r[5],
                "notes": r[6],
                "submitted_at": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ]
    })
