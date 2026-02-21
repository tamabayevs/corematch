"""
CoreMatch — Mention Service
Parses @mentions in comment text and creates notifications for mentioned users.
Never-fail: all errors logged silently, never raises to caller.
"""
import re
import logging
from database.connection import get_db
from services.notification_service import create_notification

logger = logging.getLogger(__name__)

# Matches @word patterns (email prefix, name, etc.)
MENTION_PATTERN = re.compile(r'@([\w.+-]+)')


def extract_mentions(content):
    """
    Extract @mention patterns from comment text.
    Returns list of mention strings (without the @).
    """
    if not content:
        return []
    return MENTION_PATTERN.findall(content)


def resolve_mentioned_users(mentions, campaign_owner_id):
    """
    Match mention strings to actual user IDs.
    Looks up team members by email prefix or full_name match.
    Returns list of user_id strings.
    """
    if not mentions:
        return []

    resolved_ids = []
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get team members + owner
                cur.execute(
                    """
                    SELECT u.id, u.email, u.full_name
                    FROM users u
                    WHERE u.id = %s
                       OR u.id IN (SELECT user_id FROM team_members WHERE owner_id = %s AND status = 'active')
                    """,
                    (campaign_owner_id, campaign_owner_id),
                )
                team_users = cur.fetchall()

        for mention in mentions:
            mention_lower = mention.lower()
            for user_row in team_users:
                user_id = str(user_row[0])
                email = (user_row[1] or "").lower()
                full_name = (user_row[2] or "").lower()

                # Match by email prefix (before @) or full name words
                email_prefix = email.split("@")[0] if "@" in email else email
                name_parts = full_name.split()

                if (mention_lower == email_prefix
                        or mention_lower == full_name.replace(" ", ".")
                        or mention_lower in name_parts
                        or mention_lower == full_name.replace(" ", "")):
                    if user_id not in resolved_ids:
                        resolved_ids.append(user_id)
                    break

    except Exception as e:
        logger.error("Failed to resolve mentions: %s", str(e))

    return resolved_ids


def notify_mentioned_users(mentioned_user_ids, author_id, author_name,
                           candidate_name, candidate_id, comment_content):
    """
    Create a notification for each mentioned user (excluding the author).
    Never raises.
    """
    preview = comment_content[:100] + ("..." if len(comment_content) > 100 else "")

    for user_id in mentioned_user_ids:
        if user_id == str(author_id):
            continue  # Don't notify someone who mentioned themselves

        create_notification(
            user_id=user_id,
            notification_type="mention",
            title=f"{author_name} mentioned you",
            message=f'In a comment on {candidate_name}: "{preview}"',
            entity_type="candidate",
            entity_id=candidate_id,
            metadata={"author_id": str(author_id), "author_name": author_name},
        )


def process_mentions(content, candidate_id, author_id, author_name):
    """
    High-level: extract mentions, resolve users, send notifications.
    Call this after creating a comment. Never raises.
    """
    try:
        mentions = extract_mentions(content)
        if not mentions:
            return

        # Look up campaign owner for this candidate
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT camp.user_id, c.full_name
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s
                    """,
                    (candidate_id,),
                )
                row = cur.fetchone()
                if not row:
                    return
                campaign_owner_id = str(row[0])
                candidate_name = row[1] or "Unknown"

        mentioned_ids = resolve_mentioned_users(mentions, campaign_owner_id)
        if mentioned_ids:
            notify_mentioned_users(
                mentioned_user_ids=mentioned_ids,
                author_id=author_id,
                author_name=author_name,
                candidate_name=candidate_name,
                candidate_id=candidate_id,
                comment_content=content,
            )
    except Exception as e:
        logger.error("Failed to process mentions: %s", str(e))
