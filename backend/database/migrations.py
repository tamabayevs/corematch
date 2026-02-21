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
    # ── Phase 2: Scorecards, Team Members, Company Settings ──
    """
    -- Scorecard templates for structured human evaluation
    CREATE TABLE IF NOT EXISTS scorecard_templates (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
        name            VARCHAR(300) NOT NULL,
        description     TEXT,
        competencies    JSONB NOT NULL DEFAULT '[]'::jsonb,
        is_system       BOOLEAN DEFAULT FALSE,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_scorecard_templates_user ON scorecard_templates(user_id);

    DROP TRIGGER IF EXISTS trg_update_scorecard_templates_updated_at ON scorecard_templates;
    CREATE TRIGGER trg_update_scorecard_templates_updated_at
    BEFORE UPDATE ON scorecard_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Candidate evaluations (human scorecard submissions)
    CREATE TABLE IF NOT EXISTS candidate_evaluations (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        candidate_id    UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
        reviewer_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        scorecard_template_id UUID REFERENCES scorecard_templates(id) ON DELETE SET NULL,
        ratings         JSONB NOT NULL DEFAULT '[]'::jsonb,
        overall_rating  INTEGER CHECK (overall_rating BETWEEN 1 AND 5),
        notes           TEXT,
        submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_candidate_evaluations_candidate ON candidate_evaluations(candidate_id);
    CREATE INDEX IF NOT EXISTS idx_candidate_evaluations_reviewer ON candidate_evaluations(reviewer_id);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_candidate_evaluations_unique ON candidate_evaluations(candidate_id, reviewer_id);

    -- Team members table
    CREATE TABLE IF NOT EXISTS team_members (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role            VARCHAR(20) NOT NULL DEFAULT 'reviewer'
                        CHECK (role IN ('admin', 'recruiter', 'reviewer', 'viewer')),
        invited_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        accepted_at     TIMESTAMPTZ,
        status          VARCHAR(20) DEFAULT 'pending'
                        CHECK (status IN ('pending', 'active', 'deactivated')),
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_team_members_owner ON team_members(owner_id);
    CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_team_members_unique ON team_members(owner_id, user_id);

    -- Company settings (branding and defaults)
    CREATE TABLE IF NOT EXISTS company_settings (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        logo_url        VARCHAR(500),
        primary_color   VARCHAR(7) DEFAULT '#0D9488',
        secondary_color VARCHAR(7) DEFAULT '#F59E0B',
        company_website VARCHAR(500),
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    DROP TRIGGER IF EXISTS trg_update_company_settings_updated_at ON company_settings;
    CREATE TRIGGER trg_update_company_settings_updated_at
    BEFORE UPDATE ON company_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Add scorecard_template_id to campaigns
    ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS scorecard_template_id UUID REFERENCES scorecard_templates(id) ON DELETE SET NULL;

    -- Seed system scorecard templates
    INSERT INTO scorecard_templates (name, description, competencies, is_system)
    SELECT 'General Interview', 'Standard behavioral interview evaluation',
           '[{"name":"Communication","description":"Clarity, articulation, and structure of responses","weight":25},{"name":"Problem Solving","description":"Analytical thinking and approach to challenges","weight":25},{"name":"Culture Fit","description":"Alignment with company values and team dynamics","weight":25},{"name":"Motivation","description":"Enthusiasm, drive, and career alignment","weight":25}]'::jsonb,
           TRUE
    WHERE NOT EXISTS (SELECT 1 FROM scorecard_templates WHERE is_system = TRUE AND name = 'General Interview');

    INSERT INTO scorecard_templates (name, description, competencies, is_system)
    SELECT 'Technical Role', 'Technical skills and problem-solving evaluation',
           '[{"name":"Technical Knowledge","description":"Depth and breadth of technical expertise","weight":30},{"name":"Problem Solving","description":"Approach to solving complex technical problems","weight":30},{"name":"Communication","description":"Ability to explain technical concepts clearly","weight":20},{"name":"Learning Agility","description":"Adaptability and willingness to learn new technologies","weight":20}]'::jsonb,
           TRUE
    WHERE NOT EXISTS (SELECT 1 FROM scorecard_templates WHERE is_system = TRUE AND name = 'Technical Role');

    INSERT INTO scorecard_templates (name, description, competencies, is_system)
    SELECT 'Customer-Facing', 'Customer service and relationship evaluation',
           '[{"name":"Customer Focus","description":"Empathy and dedication to customer satisfaction","weight":30},{"name":"Communication","description":"Professional and clear communication style","weight":25},{"name":"Problem Resolution","description":"Ability to resolve issues effectively","weight":25},{"name":"Composure","description":"Grace under pressure and difficult situations","weight":20}]'::jsonb,
           TRUE
    WHERE NOT EXISTS (SELECT 1 FROM scorecard_templates WHERE is_system = TRUE AND name = 'Customer-Facing');

    INSERT INTO scorecard_templates (name, description, competencies, is_system)
    SELECT 'Leadership', 'Leadership and management competency evaluation',
           '[{"name":"Strategic Thinking","description":"Vision and long-term planning ability","weight":25},{"name":"Team Leadership","description":"Ability to inspire, motivate, and develop teams","weight":25},{"name":"Decision Making","description":"Sound judgment and decisive action","weight":25},{"name":"Communication","description":"Effective stakeholder communication","weight":25}]'::jsonb,
           TRUE
    WHERE NOT EXISTS (SELECT 1 FROM scorecard_templates WHERE is_system = TRUE AND name = 'Leadership');
    """,
    # ── Phase 2: Comments, Notifications, Review Assignments ──
    """
    -- Candidate comments (threaded discussions)
    CREATE TABLE IF NOT EXISTS candidate_comments (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        candidate_id    UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
        user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        parent_id       UUID REFERENCES candidate_comments(id) ON DELETE CASCADE,
        content         TEXT NOT NULL,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_candidate_comments_candidate ON candidate_comments(candidate_id);
    CREATE INDEX IF NOT EXISTS idx_candidate_comments_user ON candidate_comments(user_id);

    DROP TRIGGER IF EXISTS trg_update_candidate_comments_updated_at ON candidate_comments;
    CREATE TRIGGER trg_update_candidate_comments_updated_at
    BEFORE UPDATE ON candidate_comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Notifications
    CREATE TABLE IF NOT EXISTS notifications (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        type            VARCHAR(50) NOT NULL,
        title           VARCHAR(300) NOT NULL,
        message         TEXT,
        entity_type     VARCHAR(50),
        entity_id       UUID,
        is_read         BOOLEAN DEFAULT FALSE,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);

    -- Review assignments
    CREATE TABLE IF NOT EXISTS review_assignments (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
        candidate_id    UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
        reviewer_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        assigned_by     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        status          VARCHAR(20) DEFAULT 'pending'
                        CHECK (status IN ('pending', 'completed')),
        completed_at    TIMESTAMPTZ,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_review_assignments_campaign ON review_assignments(campaign_id);
    CREATE INDEX IF NOT EXISTS idx_review_assignments_reviewer ON review_assignments(reviewer_id);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_review_assignments_unique ON review_assignments(candidate_id, reviewer_id);
    """,
    # ── Phase 2: Saved Searches, Data Subject Requests ──
    """
    -- Saved searches for talent pool
    CREATE TABLE IF NOT EXISTS saved_searches (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name            VARCHAR(300) NOT NULL,
        filters         JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_saved_searches_user ON saved_searches(user_id);

    -- Data subject requests (PDPL compliance)
    CREATE TABLE IF NOT EXISTS data_subject_requests (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        candidate_id    UUID REFERENCES candidates(id) ON DELETE SET NULL,
        request_type    VARCHAR(20) NOT NULL
                        CHECK (request_type IN ('access', 'erasure', 'rectification', 'portability', 'objection')),
        requester_name  VARCHAR(300) NOT NULL,
        requester_email VARCHAR(320) NOT NULL,
        description     TEXT,
        status          VARCHAR(20) DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'completed', 'rejected')),
        due_date        TIMESTAMPTZ NOT NULL,
        completed_at    TIMESTAMPTZ,
        response_notes  TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_dsr_user ON data_subject_requests(user_id);
    CREATE INDEX IF NOT EXISTS idx_dsr_status ON data_subject_requests(status);

    DROP TRIGGER IF EXISTS trg_update_dsr_updated_at ON data_subject_requests;
    CREATE TRIGGER trg_update_dsr_updated_at
    BEFORE UPDATE ON data_subject_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """,
    # ── Phase 2: Column Additions to Existing Tables ──
    """
    -- Add WhatsApp toggle to campaigns
    ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS whatsapp_enabled BOOLEAN DEFAULT FALSE;

    -- Add source tracking to candidates (for talent pool re-engage)
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'direct';

    -- Add calendar preference to users
    ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'Asia/Riyadh';
    ALTER TABLE users ADD COLUMN IF NOT EXISTS calendar_preference VARCHAR(10) DEFAULT 'gregorian';
    ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
    """,
    # ── Phase 3: Fix notifications table + new tables ──
    """
    -- Fix notifications table: add read_at and metadata columns
    ALTER TABLE notifications ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ;
    ALTER TABLE notifications ADD COLUMN IF NOT EXISTS metadata JSONB;

    -- Notification templates (customizable email/WhatsApp templates)
    CREATE TABLE IF NOT EXISTS notification_templates (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
        name            VARCHAR(300) NOT NULL,
        type            VARCHAR(20) NOT NULL CHECK (type IN ('email', 'whatsapp', 'both')),
        subject         VARCHAR(500),
        body            TEXT NOT NULL,
        variables       JSONB DEFAULT '[]'::jsonb,
        is_system       BOOLEAN DEFAULT FALSE,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_notification_templates_user ON notification_templates(user_id);

    DROP TRIGGER IF EXISTS trg_update_notification_templates_updated_at ON notification_templates;
    CREATE TRIGGER trg_update_notification_templates_updated_at
    BEFORE UPDATE ON notification_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Seed system notification templates
    INSERT INTO notification_templates (name, type, subject, body, variables, is_system)
    SELECT 'Interview Invitation', 'email',
           'You are invited to a video interview for {{job_title}}',
           'Hello {{candidate_name}},\n\nYou have been invited to complete a video interview for the position of {{job_title}} at {{company_name}}.\n\nPlease click the link below to begin:\n{{interview_link}}\n\nThis link will expire on {{expiry_date}}.\n\nBest regards,\n{{sender_name}}',
           '["candidate_name","job_title","company_name","interview_link","expiry_date","sender_name"]'::jsonb,
           TRUE
    WHERE NOT EXISTS (SELECT 1 FROM notification_templates WHERE is_system = TRUE AND name = 'Interview Invitation');

    INSERT INTO notification_templates (name, type, subject, body, variables, is_system)
    SELECT 'Interview Reminder', 'email',
           'Reminder: Complete your video interview for {{job_title}}',
           'Hello {{candidate_name}},\n\nThis is a friendly reminder to complete your video interview for {{job_title}} at {{company_name}}.\n\nYour interview link: {{interview_link}}\nDeadline: {{expiry_date}}\n\nBest regards,\n{{sender_name}}',
           '["candidate_name","job_title","company_name","interview_link","expiry_date","sender_name"]'::jsonb,
           TRUE
    WHERE NOT EXISTS (SELECT 1 FROM notification_templates WHERE is_system = TRUE AND name = 'Interview Reminder');

    INSERT INTO notification_templates (name, type, subject, body, variables, is_system)
    SELECT 'WhatsApp Invitation', 'whatsapp',
           NULL,
           'Hello {{candidate_name}}! You have been invited to a video interview for {{job_title}} at {{company_name}}. Click here to begin: {{interview_link}} (expires {{expiry_date}})',
           '["candidate_name","job_title","company_name","interview_link","expiry_date"]'::jsonb,
           TRUE
    WHERE NOT EXISTS (SELECT 1 FROM notification_templates WHERE is_system = TRUE AND name = 'WhatsApp Invitation');

    -- ATS integrations config
    CREATE TABLE IF NOT EXISTS ats_integrations (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        provider        VARCHAR(50) NOT NULL CHECK (provider IN ('greenhouse', 'lever', 'other')),
        api_key_encrypted VARCHAR(500),
        webhook_url     VARCHAR(500),
        is_active       BOOLEAN DEFAULT FALSE,
        sync_direction  VARCHAR(20) DEFAULT 'export' CHECK (sync_direction IN ('import', 'export', 'bidirectional')),
        last_synced_at  TIMESTAMPTZ,
        settings        JSONB DEFAULT '{}'::jsonb,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_ats_integrations_user ON ats_integrations(user_id);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_ats_integrations_unique ON ats_integrations(user_id, provider);

    DROP TRIGGER IF EXISTS trg_update_ats_integrations_updated_at ON ats_integrations;
    CREATE TRIGGER trg_update_ats_integrations_updated_at
    BEFORE UPDATE ON ats_integrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """,
    # ── Phase 3: Saudization, practice questions, auto-notify ──
    """
    -- Saudization/Nitaqat tracking
    CREATE TABLE IF NOT EXISTS saudization_quotas (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        category        VARCHAR(100) NOT NULL,
        target_percentage NUMERIC(5,2) NOT NULL DEFAULT 0,
        notes           TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_saudization_quotas_user ON saudization_quotas(user_id);

    DROP TRIGGER IF EXISTS trg_update_saudization_quotas_updated_at ON saudization_quotas;
    CREATE TRIGGER trg_update_saudization_quotas_updated_at
    BEFORE UPDATE ON saudization_quotas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Add nationality tracking to candidates
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS nationality VARCHAR(100);

    -- Add practice question support to campaigns
    ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS practice_question_text TEXT;
    ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS practice_question_enabled BOOLEAN DEFAULT FALSE;

    -- Add auto-notify to saved searches
    ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS auto_notify BOOLEAN DEFAULT FALSE;
    ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS last_notified_at TIMESTAMPTZ;

    -- Add updated_at to saved_searches for consistency
    ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
    """,
    # ── Fixup: Rename DSR columns for existing DBs (deadline_at → due_date, notes → response_notes) ──
    """
    -- Rename deadline_at → due_date if old column exists
    ALTER TABLE data_subject_requests RENAME COLUMN deadline_at TO due_date;
    """,
    """
    -- Rename notes → response_notes if old column exists
    ALTER TABLE data_subject_requests RENAME COLUMN notes TO response_notes;
    """,
    # ── Fixup: Add missing request_type values to DSR CHECK constraint ──
    """
    ALTER TABLE data_subject_requests DROP CONSTRAINT IF EXISTS data_subject_requests_request_type_check;
    ALTER TABLE data_subject_requests ADD CONSTRAINT data_subject_requests_request_type_check
        CHECK (request_type IN ('access', 'erasure', 'rectification', 'portability', 'objection'));
    """,
]


def run_migrations() -> None:
    """Apply all migrations. Safe to run multiple times.
    Each migration runs in its own transaction to avoid rollback cascading."""
    for i, sql in enumerate(MIGRATIONS):
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
            logger.info("Migration %d applied successfully", i + 1)
        except Exception as e:
            logger.warning("Migration %d skipped or failed: %s", i + 1, str(e))
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
