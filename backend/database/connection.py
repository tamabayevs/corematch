"""
CoreMatch — Database Connection
Manages PostgreSQL connection pool using psycopg2.
Sized for production: up to 100 concurrent customers.
"""
import os
import logging
import psycopg2
import psycopg2.pool
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Module-level connection pool (initialized once on startup)
_pool = None


def init_pool(min_conn: int = 2, max_conn: int = 15) -> None:
    """
    Initialize the connection pool. Called once at app startup.

    Sizing guide (per gunicorn worker with preload_app):
      - With preload_app=True, pool is shared across threads in a worker
      - 15 max connections per worker (configurable via DB_POOL_MAX)
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

    Usage:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def close_pool() -> None:
    """Close all connections in the pool. Called on app shutdown."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("PostgreSQL connection pool closed")
