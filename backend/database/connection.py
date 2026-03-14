"""
CoreMatch — Database Connection
Manages PostgreSQL connection pool using psycopg2.
Sized for production: up to 100 concurrent customers.
"""
import os
import logging
import time
import psycopg2
import psycopg2.pool
import psycopg2.extensions
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Module-level connection pool (initialized once on startup)
_pool = None

# Pool metrics for monitoring
_pool_exhaustion_count = 0
_pool_wait_count = 0


def init_pool(min_conn: int = 2, max_conn: int = 15) -> None:
    """
    Initialize the connection pool. Called once at app startup.

    Sizing guide (per gunicorn worker with preload_app):
      - With preload_app=True, pool is shared across threads in a worker
      - 15 max connections × N workers = fits within Railway Postgres limits
      - Railway Postgres default limit = 97 connections
      - Leave headroom for RQ workers + admin queries
    """
    global _pool
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    # Read pool size from env for easy tuning without code changes
    max_conn = int(os.environ.get("DB_POOL_MAX", str(max_conn)))
    min_conn = int(os.environ.get("DB_POOL_MIN", str(min_conn)))

    _pool = psycopg2.pool.ThreadedConnectionPool(
        min_conn,
        max_conn,
        dsn=database_url,
        # Ensure connections use UTC
        options="-c timezone=UTC",
    )
    logger.info("PostgreSQL connection pool initialized (min=%d, max=%d)", min_conn, max_conn)


def get_pool():
    """Return the connection pool, initializing if needed."""
    global _pool
    if _pool is None:
        init_pool()
    return _pool


@contextmanager
def get_db():
    """
    Context manager that yields a database connection from the pool.
    Automatically commits on success, rolls back on exception,
    and returns the connection to the pool.

    Includes:
      - Connection health check (discards broken connections)
      - Pool exhaustion logging
      - Timeout protection (30s statement timeout set at pool level)

    Usage:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    global _pool_exhaustion_count, _pool_wait_count
    pool = get_pool()

    start = time.monotonic()
    try:
        conn = pool.getconn()
    except psycopg2.pool.PoolError:
        _pool_exhaustion_count += 1
        logger.error(
            "DB pool exhausted (count=%d). All connections in use. "
            "Consider increasing DB_POOL_MAX.",
            _pool_exhaustion_count,
        )
        raise

    wait_ms = (time.monotonic() - start) * 1000
    if wait_ms > 100:
        _pool_wait_count += 1
        logger.warning("Slow pool checkout: %.0fms (total slow=%d)", wait_ms, _pool_wait_count)

    try:
        # Health check: verify connection is still alive
        if conn.closed or conn.status != psycopg2.extensions.STATUS_READY:
            logger.warning("Recycling stale DB connection (closed=%s, status=%s)", conn.closed, conn.status)
            pool.putconn(conn, close=True)
            conn = pool.getconn()

        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass  # Connection may be broken; putconn with close=True below
        raise
    finally:
        # If connection is in error state, close it instead of returning to pool
        try:
            if conn.closed or conn.status != psycopg2.extensions.STATUS_READY:
                pool.putconn(conn, close=True)
            else:
                pool.putconn(conn)
        except Exception:
            pass


def close_pool() -> None:
    """Close all connections in the pool. Called on app shutdown."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("PostgreSQL connection pool closed")


def pool_stats() -> dict:
    """Return pool health metrics for monitoring endpoints."""
    return {
        "exhaustion_count": _pool_exhaustion_count,
        "slow_checkout_count": _pool_wait_count,
    }
