"""
CoreMatch — Shared Rate Limiter
Provides rate limit decorators for all blueprints.
"""
import functools
import logging
from flask import request, jsonify, g, current_app

logger = logging.getLogger(__name__)


def get_limiter():
    """Get the Flask-Limiter instance from the current app."""
    return current_app.extensions.get("limiter")


def rate_limit(limit_string):
    """
    Decorator factory for rate limiting endpoints.
    Usage: @rate_limit("5 per minute")

    Falls back to no-op if limiter is not configured (e.g., in tests).
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            limiter = get_limiter()
            if limiter:
                # Use limiter's check method to enforce the rate limit
                try:
                    limit = limiter._limiter.parse(limit_string)
                    key = "rate_limit:%s:%s:%s" % (
                        f.__name__,
                        request.remote_addr or "unknown",
                        limit_string.replace(" ", "_"),
                    )
                    # Use Redis directly for rate checking
                    import time
                    redis_client = _get_redis()
                    if redis_client:
                        count = redis_client.incr(key)
                        if count == 1:
                            # Parse window from limit_string
                            ttl = _parse_window(limit_string)
                            redis_client.expire(key, ttl)
                        max_requests = _parse_max(limit_string)
                        if count > max_requests:
                            logger.warning(
                                "Rate limit exceeded: %s on %s from %s",
                                limit_string, request.path, request.remote_addr,
                            )
                            return jsonify({"error": "Too many requests. Please try again later."}), 429
                except Exception as e:
                    logger.debug("Rate limit check failed (non-blocking): %s", e)
            return f(*args, **kwargs)
        return decorated
    return decorator


_redis = None


def _get_redis():
    """Lazy-load Redis client for rate limiting."""
    global _redis
    if _redis is None:
        try:
            import os
            import redis as redis_lib
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
            _redis = redis_lib.from_url(redis_url, decode_responses=True)
            _redis.ping()
        except Exception:
            _redis = False  # Mark as unavailable
    return _redis if _redis else None


def _parse_window(limit_string):
    """Parse window in seconds from limit string like '5 per minute'."""
    parts = limit_string.lower().split()
    if "second" in parts[-1]:
        return 1
    elif "minute" in parts[-1]:
        return 60
    elif "hour" in parts[-1]:
        return 3600
    elif "day" in parts[-1]:
        return 86400
    return 60  # Default 1 minute


def _parse_max(limit_string):
    """Parse max requests from limit string like '5 per minute'."""
    parts = limit_string.split()
    try:
        return int(parts[0])
    except (ValueError, IndexError):
        return 10  # Default
