"""
CoreMatch — Team Blueprint
Team accounts & RBAC for managing team members.
Roles: admin, recruiter, reviewer, viewer.
Only the team owner can manage members.
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
team_bp = Blueprint("team", __name__)

VALID_ROLES = ("admin", "recruiter", "reviewer", "viewer")


# ──────────────────────────────────────────────────────────────
# GET /api/team/members — list team members for the current user
# ──────────────────────────────────────────────────────────────

@team_bp.route("/members", methods=["GET"])
@require_auth
def list_members():
    """List all team members for the current user's team."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT tm.id, tm.user_id, u.email, u.full_name,
                           tm.role, tm.invited_at, tm.accepted_at, tm.status
                    FROM team_members tm
                    LEFT JOIN users u ON tm.user_id = u.id
                    WHERE tm.owner_id = %s
                    ORDER BY tm.invited_at DESC
                    """,
                    (g.current_user["id"],),
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("List team members error: %s", str(e))
        return jsonify({"error": "Failed to fetch team members"}), 500

    return jsonify({
        "members": [
            {
                "id": str(r[0]),
                "user_id": str(r[1]) if r[1] else None,
                "email": r[2],
                "full_name": r[3],
                "role": r[4],
                "invited_at": r[5].isoformat() if r[5] else None,
                "accepted_at": r[6].isoformat() if r[6] else None,
                "status": r[7],
            }
            for r in rows
        ]
    })


# ──────────────────────────────────────────────────────────────
# POST /api/team/invite — invite a new team member by email
# ──────────────────────────────────────────────────────────────

@team_bp.route("/invite", methods=["POST"])
@require_auth
def invite_member():
    """
    Invite a new team member by email.
    Creates user record if needed, or just the membership link.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    email_raw = (data.get("email") or "").strip().lower()
    role = (data.get("role") or "").strip().lower()
    full_name = (data.get("full_name") or "").strip() or None

    if not email_raw:
        return jsonify({"error": "Email is required"}), 400
    if role not in VALID_ROLES:
        return jsonify({"error": f"Role must be one of: {', '.join(VALID_ROLES)}"}), 400

    # Validate email format
    from email_validator import validate_email, EmailNotValidError
    try:
        valid = validate_email(email_raw)
        email = valid.normalized
    except EmailNotValidError:
        return jsonify({"error": "Invalid email address"}), 400

    # Cannot invite yourself
    if email == g.current_user["email"]:
        return jsonify({"error": "Cannot invite yourself to your own team"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Check if already a member
                cur.execute(
                    """
                    SELECT id FROM team_members
                    WHERE owner_id = %s AND user_id = (SELECT id FROM users WHERE email = %s)
                    """,
                    (g.current_user["id"], email),
                )
                if cur.fetchone():
                    return jsonify({"error": "This user is already a team member"}), 409

                # Check if there's a pending invite for this email
                cur.execute(
                    """
                    SELECT id FROM team_members
                    WHERE owner_id = %s AND invited_email = %s AND status = 'pending'
                    """,
                    (g.current_user["id"], email),
                )
                if cur.fetchone():
                    return jsonify({"error": "An invitation is already pending for this email"}), 409

                # Check if user exists
                cur.execute(
                    "SELECT id, full_name FROM users WHERE email = %s",
                    (email,),
                )
                existing_user = cur.fetchone()

                user_id = str(existing_user[0]) if existing_user else None
                display_name = full_name or (existing_user[1] if existing_user else None)
                status = "active" if existing_user else "pending"

                cur.execute(
                    """
                    INSERT INTO team_members
                    (owner_id, user_id, invited_email, role, status, invited_at, accepted_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                    RETURNING id, invited_at
                    """,
                    (
                        g.current_user["id"], user_id, email, role, status,
                        "NOW()" if existing_user else None,
                    ),
                )
                row = cur.fetchone()
                member_id = str(row[0])

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "team.member_invited", "team_member",
                        member_id,
                        json.dumps({"email": email, "role": role}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Invite team member error: %s", str(e))
        return jsonify({"error": "Failed to invite team member"}), 500

    return jsonify({
        "message": "Team member invited",
        "member": {
            "id": member_id,
            "email": email,
            "full_name": display_name,
            "role": role,
            "status": status,
        },
    }), 201


# ──────────────────────────────────────────────────────────────
# PUT /api/team/members/:id — update role
# ──────────────────────────────────────────────────────────────

@team_bp.route("/members/<member_id>", methods=["PUT"])
@require_auth
def update_member(member_id):
    """Update a team member's role. Only the team owner can do this."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    role = (data.get("role") or "").strip().lower()
    if role not in VALID_ROLES:
        return jsonify({"error": f"Role must be one of: {', '.join(VALID_ROLES)}"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify ownership
                cur.execute(
                    """
                    SELECT id, role FROM team_members
                    WHERE id = %s AND owner_id = %s
                    """,
                    (member_id, g.current_user["id"]),
                )
                existing = cur.fetchone()
                if not existing:
                    return jsonify({"error": "Team member not found"}), 404

                old_role = existing[1]

                cur.execute(
                    "UPDATE team_members SET role = %s WHERE id = %s AND owner_id = %s",
                    (role, member_id, g.current_user["id"]),
                )

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "team.member_role_updated", "team_member",
                        member_id,
                        json.dumps({"old_role": old_role, "new_role": role}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Update team member error: %s", str(e))
        return jsonify({"error": "Failed to update team member"}), 500

    return jsonify({"message": "Team member role updated", "role": role})


# ──────────────────────────────────────────────────────────────
# DELETE /api/team/members/:id — remove member
# ──────────────────────────────────────────────────────────────

@team_bp.route("/members/<member_id>", methods=["DELETE"])
@require_auth
def remove_member(member_id):
    """Remove a team member. Only the team owner can do this."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify ownership and get member info for audit
                cur.execute(
                    """
                    SELECT tm.id, tm.invited_email, tm.role
                    FROM team_members tm
                    WHERE tm.id = %s AND tm.owner_id = %s
                    """,
                    (member_id, g.current_user["id"]),
                )
                existing = cur.fetchone()
                if not existing:
                    return jsonify({"error": "Team member not found"}), 404

                cur.execute(
                    "DELETE FROM team_members WHERE id = %s AND owner_id = %s",
                    (member_id, g.current_user["id"]),
                )

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "team.member_removed", "team_member",
                        member_id,
                        json.dumps({"email": existing[1], "role": existing[2]}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Remove team member error: %s", str(e))
        return jsonify({"error": "Failed to remove team member"}), 500

    return jsonify({"message": "Team member removed"})
