"""
CoreMatch — Database Migrations
Applies incremental schema changes to an existing database.
Safe to run multiple times (all statements use IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
"""
import logging
from database.connection import get_db

logger = logging.getLogger(__name__)

MIGRATIONS = [
    # ── Phase 1, Feature 2: Bulk Invite & Reminders ──
    """
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMPTZ;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS reminder_count INTEGER DEFAULT 0;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
    """,
]


def run_migrations() -> None:
    """Apply all migrations. Safe to run multiple times."""
    with get_db() as conn:
        with conn.cursor() as cur:
            for i, sql in enumerate(MIGRATIONS):
                try:
                    cur.execute(sql)
                    logger.info("Migration %d applied successfully", i + 1)
                except Exception as e:
                    logger.warning("Migration %d skipped or failed: %s", i + 1, str(e))
                    conn.rollback()
    logger.info("All migrations complete")


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(level=logging.INFO)
    run_migrations()
    print("Migrations complete.")
