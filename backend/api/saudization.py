"""
CoreMatch — Saudization Blueprint
Nationality quota monitoring (Nitaqat) across campaigns.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
saudization_bp = Blueprint("saudization", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/saudization/dashboard — nationality breakdown
# ──────────────────────────────────────────────────────────────

@saudization_bp.route("/dashboard", methods=["GET"])
@require_auth
def dashboard():
    """
    Get nationality breakdown across campaigns with Nitaqat compliance metrics.
    """
    campaign_id = request.args.get("campaign_id")

    conditions = ["camp.user_id = %s", "c.status != 'erased'"]
    params = [g.current_user["id"]]

    if campaign_id:
        conditions.append("c.campaign_id = %s")
        params.append(campaign_id)

    where_clause = " AND ".join(conditions)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Nationality breakdown
                cur.execute(
                    f"""
                    SELECT
                        COALESCE(c.nationality, 'Not Specified') as nationality,
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE c.hr_decision = 'shortlisted') as shortlisted,
                        AVG(c.overall_score) FILTER (WHERE c.overall_score IS NOT NULL) as avg_score
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE {where_clause}
                    GROUP BY COALESCE(c.nationality, 'Not Specified')
                    ORDER BY total DESC
                    """,
                    params,
                )
                nationality_rows = cur.fetchall()

                # Get total
                total_candidates = sum(r[1] for r in nationality_rows)

                # Get Saudi count for Nitaqat calculation
                saudi_count = 0
                for r in nationality_rows:
                    if r[0] and r[0].lower() in ("saudi", "saudi arabian", "sa", "ksa"):
                        saudi_count += r[1]

                # Get quota targets
                cur.execute(
                    """
                    SELECT id, category, target_percentage, notes, created_at
                    FROM saudization_quotas
                    WHERE user_id = %s
                    ORDER BY category ASC
                    """,
                    (g.current_user["id"],),
                )
                quota_rows = cur.fetchall()

                # Per-campaign breakdown
                cur.execute(
                    f"""
                    SELECT camp.id, camp.name, camp.job_title,
                           COUNT(*) as total,
                           COUNT(*) FILTER (WHERE LOWER(COALESCE(c.nationality, '')) IN ('saudi', 'saudi arabian', 'sa', 'ksa')) as saudi_count,
                           COUNT(*) FILTER (WHERE c.hr_decision = 'shortlisted') as shortlisted
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE {where_clause}
                    GROUP BY camp.id, camp.name, camp.job_title
                    ORDER BY total DESC
                    """,
                    params,
                )
                campaign_rows = cur.fetchall()

    except Exception as e:
        logger.error("Saudization dashboard error: %s", str(e))
        return jsonify({"error": "Failed to fetch saudization data"}), 500

    current_saudi_pct = round(saudi_count / max(total_candidates, 1) * 100, 1)

    return jsonify({
        "summary": {
            "total_candidates": total_candidates,
            "saudi_count": saudi_count,
            "non_saudi_count": total_candidates - saudi_count,
            "saudi_percentage": current_saudi_pct,
        },
        "nationality_breakdown": [
            {
                "nationality": r[0],
                "count": r[1],
                "percentage": round(r[1] / max(total_candidates, 1) * 100, 1),
                "shortlisted": r[2],
                "avg_score": round(float(r[3]), 1) if r[3] else None,
            }
            for r in nationality_rows
        ],
        "quotas": [
            {
                "id": str(r[0]),
                "category": r[1],
                "target_percentage": float(r[2]),
                "notes": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
                "current_percentage": current_saudi_pct,
                "is_compliant": current_saudi_pct >= float(r[2]),
            }
            for r in quota_rows
        ],
        "per_campaign": [
            {
                "id": str(r[0]),
                "name": r[1],
                "job_title": r[2],
                "total": r[3],
                "saudi_count": r[4],
                "saudi_percentage": round(r[4] / max(r[3], 1) * 100, 1),
                "shortlisted": r[5],
            }
            for r in campaign_rows
        ],
    })


# ──────────────────────────────────────────────────────────────
# POST /api/saudization/quotas — create/update quota target
# ──────────────────────────────────────────────────────────────

@saudization_bp.route("/quotas", methods=["POST"])
@require_auth
def create_quota():
    """Create a Nitaqat quota target."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    category = (data.get("category") or "").strip()
    target_percentage = data.get("target_percentage")
    notes = (data.get("notes") or "").strip() or None

    if not category:
        return jsonify({"error": "Category is required"}), 400
    if target_percentage is None or not (0 <= float(target_percentage) <= 100):
        return jsonify({"error": "Target percentage must be between 0 and 100"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO saudization_quotas (user_id, category, target_percentage, notes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, created_at
                    """,
                    (g.current_user["id"], category, float(target_percentage), notes),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Create quota error: %s", str(e))
        return jsonify({"error": "Failed to create quota"}), 500

    return jsonify({
        "message": "Quota created",
        "quota": {
            "id": str(row[0]),
            "category": category,
            "target_percentage": target_percentage,
            "created_at": row[1].isoformat(),
        },
    }), 201


# ──────────────────────────────────────────────────────────────
# PUT /api/saudization/quotas/:id — update quota
# ──────────────────────────────────────────────────────────────

@saudization_bp.route("/quotas/<quota_id>", methods=["PUT"])
@require_auth
def update_quota(quota_id):
    """Update a Nitaqat quota target."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                updates = {}
                if "category" in data:
                    updates["category"] = data["category"].strip()
                if "target_percentage" in data:
                    updates["target_percentage"] = float(data["target_percentage"])
                if "notes" in data:
                    updates["notes"] = (data["notes"] or "").strip() or None

                if not updates:
                    return jsonify({"error": "No fields to update"}), 400

                set_parts = [f"{k} = %s" for k in updates.keys()]
                values = list(updates.values())
                values.extend([quota_id, g.current_user["id"]])

                cur.execute(
                    f"UPDATE saudization_quotas SET {', '.join(set_parts)} WHERE id = %s AND user_id = %s",
                    values,
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "Quota not found"}), 404
    except Exception as e:
        logger.error("Update quota error: %s", str(e))
        return jsonify({"error": "Failed to update quota"}), 500

    return jsonify({"message": "Quota updated"})


# ──────────────────────────────────────────────────────────────
# DELETE /api/saudization/quotas/:id — delete quota
# ──────────────────────────────────────────────────────────────

@saudization_bp.route("/quotas/<quota_id>", methods=["DELETE"])
@require_auth
def delete_quota(quota_id):
    """Delete a Nitaqat quota target."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM saudization_quotas WHERE id = %s AND user_id = %s",
                    (quota_id, g.current_user["id"]),
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "Quota not found"}), 404
    except Exception as e:
        logger.error("Delete quota error: %s", str(e))
        return jsonify({"error": "Failed to delete quota"}), 500

    return jsonify({"message": "Quota deleted"})


# ──────────────────────────────────────────────────────────────
# PUT /api/saudization/candidate/:id/nationality — set candidate nationality
# ──────────────────────────────────────────────────────────────

@saudization_bp.route("/candidate/<candidate_id>/nationality", methods=["PUT"])
@require_auth
def set_nationality(candidate_id):
    """Set the nationality of a candidate for Nitaqat tracking."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    nationality = (data.get("nationality") or "").strip()
    if not nationality:
        return jsonify({"error": "Nationality is required"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE candidates SET nationality = %s
                    WHERE id = %s AND campaign_id IN (
                        SELECT id FROM campaigns WHERE user_id = %s
                    )
                    """,
                    (nationality, candidate_id, g.current_user["id"]),
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "Candidate not found"}), 404

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "candidate.nationality_set", "candidate",
                        candidate_id, json.dumps({"nationality": nationality}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Set nationality error: %s", str(e))
        return jsonify({"error": "Failed to set nationality"}), 500

    return jsonify({"message": "Nationality updated"})
