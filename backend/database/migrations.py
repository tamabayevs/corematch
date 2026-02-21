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
    # ── Phase 1, Feature 4: Campaign Templates ──
    """
    CREATE TABLE IF NOT EXISTS campaign_templates (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
        name            VARCHAR(300) NOT NULL,
        description     TEXT,
        questions       JSONB NOT NULL DEFAULT '[]'::jsonb,
        language        VARCHAR(5) DEFAULT 'en',
        invite_expiry_days  INTEGER DEFAULT 7,
        allow_retakes   BOOLEAN DEFAULT TRUE,
        max_recording_seconds INTEGER DEFAULT 120,
        is_system       BOOLEAN DEFAULT FALSE,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_campaign_templates_user ON campaign_templates(user_id);

    -- Apply updated_at trigger to campaign_templates
    DROP TRIGGER IF EXISTS trg_update_campaign_templates_updated_at ON campaign_templates;
    CREATE TRIGGER trg_update_campaign_templates_updated_at
    BEFORE UPDATE ON campaign_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Seed system templates (only if none exist yet)
    INSERT INTO campaign_templates (name, description, questions, language, is_system)
    SELECT 'General Interview',
           'Standard interview template with behavioral questions',
           '[{"id":"sys-1","text":"Tell me about yourself and your relevant experience.","think_time_seconds":30},{"id":"sys-2","text":"Describe a challenging situation you faced and how you handled it.","think_time_seconds":30},{"id":"sys-3","text":"Why are you interested in this position?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE);

    INSERT INTO campaign_templates (name, description, questions, language, is_system)
    SELECT 'Technical Screening',
           'Evaluate technical skills, problem-solving ability, and project experience',
           '[{"id":"sys-4","text":"Walk us through a technical project you are most proud of.","think_time_seconds":30},{"id":"sys-5","text":"How do you approach solving a complex problem you have not encountered before?","think_time_seconds":30},{"id":"sys-6","text":"Describe your experience with the core technologies listed in the job description.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Technical Screening');

    INSERT INTO campaign_templates (name, description, questions, language, is_system)
    SELECT 'Sales Role',
           'Assess sales aptitude, target orientation, and customer relationship skills',
           '[{"id":"sys-7","text":"Tell us about a time you exceeded your sales targets and what strategy you used.","think_time_seconds":30},{"id":"sys-8","text":"How do you build and maintain long-term customer relationships?","think_time_seconds":30},{"id":"sys-9","text":"Describe how you handle objections from a hesitant prospect.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Sales Role');

    INSERT INTO campaign_templates (name, description, questions, language, is_system)
    SELECT 'Customer Service',
           'Evaluate conflict resolution, customer satisfaction focus, and multitasking ability',
           '[{"id":"sys-10","text":"Describe a time you resolved a difficult customer complaint successfully.","think_time_seconds":30},{"id":"sys-11","text":"How do you ensure customer satisfaction while managing multiple requests at once?","think_time_seconds":30},{"id":"sys-12","text":"Give an example of how you turned a negative customer experience into a positive one.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Customer Service');
    """,
    # ── Phase 1, Feature 7: PDPL Compliance Dashboard ──
    """
    ALTER TABLE users ADD COLUMN IF NOT EXISTS retention_months INTEGER DEFAULT 12;
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
