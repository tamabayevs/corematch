"""
CoreMatch — Saved Search Auto-Notify Worker
Checks saved searches with auto_notify=true for new matching candidates.
Creates in-app notifications when new matches are found.
Designed to be run periodically via API trigger or scheduler.
"""
import json
import logging
from datetime import datetime, timezone
from database.connection import get_db

logger = logging.getLogger(__name__)


def check_saved_searches():
    """
    Main entry point: iterate all saved searches with auto_notify=true,
    re-run each search, detect new candidates since last_notified_at,
    and create notifications for the search owner.
    Returns dict with summary stats.
    """
    searches_checked = 0
    notifications_sent = 0
    errors = 0

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, name, filters, last_notified_at
                    FROM saved_searches
                    WHERE auto_notify = TRUE
                    ORDER BY last_notified_at ASC NULLS FIRST
                    """
                )
                searches = cur.fetchall()
    except Exception as e:
        logger.error("Failed to fetch saved searches: %s", e)
        return {"checked": 0, "notified": 0, "errors": 1}

    for search in searches:
        search_id = str(search[0])
        user_id = str(search[1])
        search_name = search[2]
        filters = search[3] or {}
        last_notified_at = search[4]

        try:
            new_count = _check_single_search(
                search_id, user_id, search_name, filters, last_notified_at
            )
            searches_checked += 1
            if new_count > 0:
                notifications_sent += 1
                logger.info(
                    "Search '%s' (user %s): %d new matches",
                    search_name, user_id[:8], new_count,
                )
        except Exception as e:
            errors += 1
            logger.error(
                "Error checking search '%s' (%s): %s",
                search_name, search_id[:8], e,
            )

    logger.info(
        "Saved search check complete: %d checked, %d notified, %d errors",
        searches_checked, notifications_sent, errors,
    )
    return {
        "checked": searches_checked,
        "notified": notifications_sent,
        "errors": errors,
    }


def _check_single_search(search_id, user_id, search_name, filters, last_notified_at):
    """
    Re-run a single saved search and check for new candidates
    added since last_notified_at.
    Returns the count of new matches.
    """
    if isinstance(filters, str):
        filters = json.loads(filters)

    # Build the search query based on saved filters
    conditions = [
        "camp.user_id = %s",
        "c.status != 'erased'",
    ]
    params = [user_id]

    # Only count candidates created after last notification
    if last_notified_at:
        conditions.append("c.created_at > %s")
        params.append(last_notified_at)

    # Apply saved filters
    if filters.get("tier"):
        conditions.append("c.tier = %s")
        params.append(filters["tier"])

    if filters.get("score_min"):
        conditions.append("c.overall_score >= %s")
        params.append(float(filters["score_min"]))

    if filters.get("score_max"):
        conditions.append("c.overall_score <= %s")
        params.append(float(filters["score_max"]))

    if filters.get("campaign_id"):
        conditions.append("c.campaign_id = %s")
        params.append(filters["campaign_id"])

    if filters.get("decision"):
        if filters["decision"] == "none":
            conditions.append("c.hr_decision IS NULL")
        else:
            conditions.append("c.hr_decision = %s")
            params.append(filters["decision"])

    if filters.get("search"):
        search_term = f"%{filters['search']}%"
        conditions.append("(c.full_name ILIKE %s OR c.email ILIKE %s)")
        params.extend([search_term, search_term])

    where_clause = " AND ".join(conditions)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM candidates c
                JOIN campaigns camp ON c.campaign_id = camp.id
                WHERE {where_clause}
                """,
                params,
            )
            new_count = cur.fetchone()[0]

            if new_count > 0:
                # Create in-app notification
                try:
                    from services.notification_service import create_notification
                    create_notification(
                        user_id=user_id,
                        notification_type="saved_search_match",
                        title=f"New matches for \"{search_name}\"",
                        message=f"{new_count} new candidate{'s' if new_count != 1 else ''} match your saved search \"{search_name}\".",
                        metadata={"search_id": search_id, "count": new_count},
                    )
                except Exception as e:
                    logger.warning("Failed to create notification: %s", e)

                # Update last_notified_at
                cur.execute(
                    """
                    UPDATE saved_searches
                    SET last_notified_at = NOW()
                    WHERE id = %s
                    """,
                    (search_id,),
                )

    return new_count
