"""
CoreMatch — Notification Service
Never-fail helper for creating in-app notifications.
All functions wrap DB calls in try/except so callers never break.
"""
import json
import logging
from uuid import uuid4
from database.connection import get_db

logger = logging.getLogger(__name__)


def create_notification(user_id, notification_type, title, message,
                        entity_type=None, entity_id=None, metadata=None):
    """
    Insert a single notification row. Never raises — logs errors silently.

    Args:
        user_id: UUID string of the user to notify
        notification_type: e.g. 'submission', 'scoring', 'decision', 'comment', 'assignment', 'dsr', 'evaluation', 'mention'
        title: Short notification title
        message: Longer notification body
        entity_type: Optional entity type (e.g. 'candidate', 'campaign')
        entity_id: Optional entity UUID
        metadata: Optional dict of extra data
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notifications (id, user_id, type, title, message,
                                               entity_type, entity_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        str(uuid4()), user_id, notification_type, title, message,
                        entity_type, entity_id,
                        json.dumps(metadata) if metadata else None,
                    ),
                )
    except Exception as e:
        logger.error("Failed to create notification for user %s: %s", user_id, str(e))


def notify_campaign_owner(candidate_id, notification_type, title, message,
                          entity_type="candidate", entity_id=None,
                          exclude_user_id=None, metadata=None):
    """
    Look up the campaign owner from a candidate_id and notify them.
    Optionally exclude a user (e.g., the person who triggered the action).
    Never raises.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT camp.user_id
                    FROM candidates c
                    JOIN campaigns camp ON c.campaign_id = camp.id
                    WHERE c.id = %s
                    """,
                    (candidate_id,),
                )
                row = cur.fetchone()
                if not row:
                    return
                owner_id = str(row[0])

        if exclude_user_id and owner_id == str(exclude_user_id):
            return

        create_notification(
            user_id=owner_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id or candidate_id,
            metadata=metadata,
        )
    except Exception as e:
        logger.error("Failed to notify campaign owner for candidate %s: %s", candidate_id, str(e))


def notify_user(user_id, notification_type, title, message,
                entity_type=None, entity_id=None, metadata=None):
    """
    Direct notification to a specific user. Never raises.
    Convenience wrapper around create_notification.
    """
    create_notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata,
    )
