"""
CoreMatch — Comments Blueprint
Candidate comments with threaded replies (parent_id support).
"""
import json
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth

logger = logging.getLogger(__name__)
comments_bp = Blueprint("comments", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/comments/:candidate_id — get all comments for a candidate
# ──────────────────────────────────────────────────────────────

@comments_bp.route("/<candidate_id>", methods=["GET"])
@require_auth
def get_comments(candidate_id):
    """
    Get all comments for a candidate, with replies threaded by parent_id.
    Returns a flat list; frontend groups by parent_id for nested display.
    """
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

                cur.execute(
                    """
                    SELECT cc.id, cc.candidate_id, cc.user_id, u.full_name as author_name,
                           cc.content, cc.parent_id, cc.created_at, cc.updated_at
                    FROM candidate_comments cc
                    JOIN users u ON cc.user_id = u.id
                    WHERE cc.candidate_id = %s
                    ORDER BY cc.created_at ASC
                    """,
                    (candidate_id,),
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("Get comments error: %s", str(e))
        return jsonify({"error": "Failed to fetch comments"}), 500

    return jsonify({
        "comments": [
            {
                "id": str(r[0]),
                "candidate_id": str(r[1]),
                "user_id": str(r[2]),
                "author_name": r[3],
                "content": r[4],
                "parent_id": str(r[5]) if r[5] else None,
                "created_at": r[6].isoformat() if r[6] else None,
                "updated_at": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ]
    })


# ──────────────────────────────────────────────────────────────
# POST /api/comments/:candidate_id — create a new comment
# ──────────────────────────────────────────────────────────────

@comments_bp.route("/<candidate_id>", methods=["POST"])
@require_auth
def create_comment(candidate_id):
    """
    Create a new comment on a candidate.
    Optionally specify parent_id for threaded replies.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Comment content is required"}), 400

    parent_id = data.get("parent_id")

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

                # If parent_id specified, verify it exists and belongs to same candidate
                if parent_id:
                    cur.execute(
                        "SELECT id FROM candidate_comments WHERE id = %s AND candidate_id = %s",
                        (parent_id, candidate_id),
                    )
                    if not cur.fetchone():
                        return jsonify({"error": "Parent comment not found"}), 404

                cur.execute(
                    """
                    INSERT INTO candidate_comments (candidate_id, user_id, content, parent_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, created_at
                    """,
                    (candidate_id, g.current_user["id"], content, parent_id),
                )
                row = cur.fetchone()
                comment_id = str(row[0])

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "comment.created", "candidate_comment",
                        comment_id,
                        json.dumps({"candidate_id": candidate_id, "is_reply": parent_id is not None}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Create comment error: %s", str(e))
        return jsonify({"error": "Failed to create comment"}), 500

    # In-app notification to campaign owner (if comment by team member)
    from services.notification_service import notify_campaign_owner
    notify_campaign_owner(
        candidate_id=candidate_id,
        notification_type="comment",
        title="New comment",
        message=f'{g.current_user["full_name"]} commented on a candidate.',
        exclude_user_id=g.current_user["id"],
        metadata={"comment_id": comment_id},
    )

    # Process @mentions and notify mentioned users
    from services.mention_service import process_mentions
    process_mentions(
        content=content,
        candidate_id=candidate_id,
        author_id=g.current_user["id"],
        author_name=g.current_user["full_name"],
    )

    return jsonify({
        "message": "Comment created",
        "comment": {
            "id": comment_id,
            "candidate_id": candidate_id,
            "user_id": g.current_user["id"],
            "author_name": g.current_user["full_name"],
            "content": content,
            "parent_id": parent_id,
            "created_at": row[1].isoformat(),
        },
    }), 201


# ──────────────────────────────────────────────────────────────
# PUT /api/comments/:comment_id — edit own comment
# ──────────────────────────────────────────────────────────────

@comments_bp.route("/edit/<comment_id>", methods=["PUT"])
@require_auth
def edit_comment(comment_id):
    """Edit own comment. Only the comment author can edit."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Comment content is required"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify ownership
                cur.execute(
                    "SELECT id, user_id FROM candidate_comments WHERE id = %s",
                    (comment_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    return jsonify({"error": "Comment not found"}), 404
                if str(existing[1]) != g.current_user["id"]:
                    return jsonify({"error": "Cannot edit another user's comment"}), 403

                cur.execute(
                    "UPDATE candidate_comments SET content = %s WHERE id = %s",
                    (content, comment_id),
                )

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "comment.edited", "candidate_comment",
                        comment_id, json.dumps({}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Edit comment error: %s", str(e))
        return jsonify({"error": "Failed to edit comment"}), 500

    return jsonify({"message": "Comment updated"})


# ──────────────────────────────────────────────────────────────
# DELETE /api/comments/:comment_id — delete own comment
# ──────────────────────────────────────────────────────────────

@comments_bp.route("/edit/<comment_id>", methods=["DELETE"])
@require_auth
def delete_comment(comment_id):
    """Delete own comment. Only the comment author can delete."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify ownership
                cur.execute(
                    "SELECT id, user_id, candidate_id FROM candidate_comments WHERE id = %s",
                    (comment_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    return jsonify({"error": "Comment not found"}), 404
                if str(existing[1]) != g.current_user["id"]:
                    return jsonify({"error": "Cannot delete another user's comment"}), 403

                # Delete the comment (and any child replies via CASCADE if configured)
                cur.execute(
                    "DELETE FROM candidate_comments WHERE id = %s",
                    (comment_id,),
                )

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        g.current_user["id"], "comment.deleted", "candidate_comment",
                        comment_id,
                        json.dumps({"candidate_id": str(existing[2])}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Delete comment error: %s", str(e))
        return jsonify({"error": "Failed to delete comment"}), 500

    return jsonify({"message": "Comment deleted"})
