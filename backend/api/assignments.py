"""
CoreMatch — Assignments Blueprint
Review assignment endpoints for distributing candidate reviews among team members.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
assignments_bp = Blueprint("assignments", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/assignments/campaign/:campaign_id — list assignments
# ──────────────────────────────────────────────────────────────

@assignments_bp.route("/campaign/<campaign_id>", methods=["GET"])
@require_auth
def list_campaign_assignments(campaign_id):
    """
    List all review assignments for a campaign.
    Includes reviewer info and completion progress.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify campaign ownership
                cur.execute(
                    "SELECT id FROM campaigns WHERE id = %s AND user_id = %s",
                    (campaign_id, g.current_user["id"]),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Campaign not found"}), 404

                cur.execute(
                    """
                    SELECT ra.id, ra.campaign_id, ra.reviewer_id, u.full_name as reviewer_name,
                           u.email as reviewer_email, ra.candidate_id,
                           c.full_name as candidate_name, c.overall_score,
                           ra.status, ra.assigned_at, ra.completed_at, ra.notes
                    FROM review_assignments ra
                    JOIN users u ON ra.reviewer_id = u.id
                    JOIN candidates c ON ra.candidate_id = c.id
                    WHERE ra.campaign_id = %s
                    ORDER BY ra.assigned_at DESC
                    """,
                    (campaign_id,),
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("List campaign assignments error: %s", str(e))
        return jsonify({"error": "Failed to fetch assignments"}), 500

    # Calculate progress summary per reviewer
    reviewer_progress = {}
    assignments = []
    for r in rows:
        reviewer_id = str(r[2])
        if reviewer_id not in reviewer_progress:
            reviewer_progress[reviewer_id] = {
                "reviewer_name": r[3],
                "total": 0,
                "completed": 0,
            }
        reviewer_progress[reviewer_id]["total"] += 1
        if r[8] == "completed":
            reviewer_progress[reviewer_id]["completed"] += 1

        assignments.append({
            "id": str(r[0]),
            "campaign_id": str(r[1]),
            "reviewer_id": reviewer_id,
            "reviewer_name": r[3],
            "reviewer_email": r[4],
            "candidate_id": str(r[5]),
            "candidate_name": r[6],
            "candidate_score": float(r[7]) if r[7] is not None else None,
            "status": r[8],
            "assigned_at": r[9].isoformat() if r[9] else None,
            "completed_at": r[10].isoformat() if r[10] else None,
            "notes": r[11],
        })

    return jsonify({
        "assignments": assignments,
        "progress": reviewer_progress,
        "total": len(assignments),
    })


# ──────────────────────────────────────────────────────────────
# POST /api/assignments/campaign/:campaign_id — create assignments
# ──────────────────────────────────────────────────────────────

@assignments_bp.route("/campaign/<campaign_id>", methods=["POST"])
@require_auth
def create_assignments(campaign_id):
    """
    Create review assignments for a campaign.
    Two modes:
    1. Explicit: {reviewer_id, candidate_ids} — assign specific candidates to a reviewer
    2. Round robin: {mode: "round_robin", reviewer_ids} — auto-distribute all unassigned candidates
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify campaign ownership
                cur.execute(
                    "SELECT id FROM campaigns WHERE id = %s AND user_id = %s",
                    (campaign_id, g.current_user["id"]),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Campaign not found"}), 404

                mode = data.get("mode", "explicit")
                created_count = 0

                if mode == "round_robin":
                    # Round-robin distribution
                    reviewer_ids = data.get("reviewer_ids", [])
                    if not isinstance(reviewer_ids, list) or len(reviewer_ids) == 0:
                        return jsonify({"error": "reviewer_ids array is required for round_robin mode"}), 400

                    # Get all submitted candidates not yet assigned
                    cur.execute(
                        """
                        SELECT c.id FROM candidates c
                        WHERE c.campaign_id = %s
                          AND c.status = 'submitted'
                          AND c.id NOT IN (
                              SELECT candidate_id FROM review_assignments WHERE campaign_id = %s
                          )
                        ORDER BY c.created_at ASC
                        """,
                        (campaign_id, campaign_id),
                    )
                    unassigned = [str(r[0]) for r in cur.fetchall()]

                    if not unassigned:
                        return jsonify({"message": "No unassigned candidates to distribute", "created": 0})

                    # Distribute candidates among reviewers
                    for i, cand_id in enumerate(unassigned):
                        reviewer_id = reviewer_ids[i % len(reviewer_ids)]
                        cur.execute(
                            """
                            INSERT INTO review_assignments (campaign_id, reviewer_id, candidate_id, status, assigned_at)
                            VALUES (%s, %s, %s, 'pending', NOW())
                            ON CONFLICT (campaign_id, reviewer_id, candidate_id) DO NOTHING
                            """,
                            (campaign_id, reviewer_id, cand_id),
                        )
                        if cur.rowcount > 0:
                            created_count += 1

                else:
                    # Explicit assignment
                    reviewer_id = data.get("reviewer_id")
                    candidate_ids = data.get("candidate_ids", [])

                    if not reviewer_id:
                        return jsonify({"error": "reviewer_id is required"}), 400
                    if not isinstance(candidate_ids, list) or len(candidate_ids) == 0:
                        return jsonify({"error": "candidate_ids array is required"}), 400

                    for cand_id in candidate_ids:
                        cur.execute(
                            """
                            INSERT INTO review_assignments (campaign_id, reviewer_id, candidate_id, status, assigned_at)
                            VALUES (%s, %s, %s, 'pending', NOW())
                            ON CONFLICT (campaign_id, reviewer_id, candidate_id) DO NOTHING
                            """,
                            (campaign_id, reviewer_id, cand_id),
                        )
                        if cur.rowcount > 0:
                            created_count += 1

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "assignments.created", "campaign",
                        campaign_id,
                        json.dumps({"mode": mode, "count": created_count}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Create assignments error: %s", str(e))
        return jsonify({"error": "Failed to create assignments"}), 500

    # In-app notifications to assigned reviewers
    if created_count > 0:
        from services.notification_service import notify_user
        if mode == "round_robin":
            # Notify each reviewer
            for rid in data.get("reviewer_ids", []):
                notify_user(
                    user_id=rid,
                    notification_type="assignment",
                    title="New review assignment",
                    message="You have been assigned candidates to review.",
                    entity_type="campaign",
                    entity_id=campaign_id,
                )
        else:
            reviewer_id = data.get("reviewer_id")
            if reviewer_id:
                notify_user(
                    user_id=reviewer_id,
                    notification_type="assignment",
                    title="New review assignment",
                    message=f"You have been assigned {created_count} candidate(s) to review.",
                    entity_type="campaign",
                    entity_id=campaign_id,
                )

    return jsonify({
        "message": f"Created {created_count} assignment(s)",
        "created": created_count,
    }), 201


# ──────────────────────────────────────────────────────────────
# PUT /api/assignments/:id/complete — mark assignment complete
# ──────────────────────────────────────────────────────────────

@assignments_bp.route("/<assignment_id>/complete", methods=["PUT"])
@require_auth
def complete_assignment(assignment_id):
    """Mark a review assignment as completed."""
    data = request.get_json(silent=True) or {}
    notes = (data.get("notes") or "").strip() or None

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify the assignment belongs to current user as reviewer
                cur.execute(
                    """
                    SELECT ra.id, ra.campaign_id, ra.status
                    FROM review_assignments ra
                    WHERE ra.id = %s AND ra.reviewer_id = %s
                    """,
                    (assignment_id, g.current_user["id"]),
                )
                existing = cur.fetchone()
                if not existing:
                    return jsonify({"error": "Assignment not found"}), 404

                if existing[2] == "completed":
                    return jsonify({"message": "Assignment already completed"}), 200

                cur.execute(
                    """
                    UPDATE review_assignments
                    SET status = 'completed', completed_at = NOW(), notes = %s
                    WHERE id = %s
                    """,
                    (notes, assignment_id),
                )

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "assignment.completed", "review_assignment",
                        assignment_id,
                        json.dumps({"campaign_id": str(existing[1])}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Complete assignment error: %s", str(e))
        return jsonify({"error": "Failed to complete assignment"}), 500

    return jsonify({"message": "Assignment marked as completed"})


# ──────────────────────────────────────────────────────────────
# GET /api/assignments/my — get current user's assignments
# ──────────────────────────────────────────────────────────────

@assignments_bp.route("/my", methods=["GET"])
@require_auth
def my_assignments():
    """Get all assignments for the current user as reviewer."""
    status_filter = request.args.get("status")  # pending, completed

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                conditions = ["ra.reviewer_id = %s"]
                params = [g.current_user["id"]]

                if status_filter and status_filter in ("pending", "completed"):
                    conditions.append("ra.status = %s")
                    params.append(status_filter)

                where_clause = " AND ".join(conditions)

                cur.execute(
                    f"""
                    SELECT ra.id, ra.campaign_id, camp.name as campaign_name,
                           camp.job_title, ra.candidate_id,
                           c.full_name as candidate_name, c.email as candidate_email,
                           c.overall_score, c.tier,
                           ra.status, ra.assigned_at, ra.completed_at, ra.notes
                    FROM review_assignments ra
                    JOIN campaigns camp ON ra.campaign_id = camp.id
                    JOIN candidates c ON ra.candidate_id = c.id
                    WHERE {where_clause}
                    ORDER BY ra.assigned_at DESC
                    """,
                    params,
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("My assignments error: %s", str(e))
        return jsonify({"error": "Failed to fetch assignments"}), 500

    return jsonify({
        "assignments": [
            {
                "id": str(r[0]),
                "campaign_id": str(r[1]),
                "campaign_name": r[2],
                "job_title": r[3],
                "candidate_id": str(r[4]),
                "candidate_name": r[5],
                "candidate_email": r[6],
                "candidate_score": float(r[7]) if r[7] is not None else None,
                "candidate_tier": r[8],
                "status": r[9],
                "assigned_at": r[10].isoformat() if r[10] else None,
                "completed_at": r[11].isoformat() if r[11] else None,
                "notes": r[12],
            }
            for r in rows
        ],
        "total": len(rows),
    })
