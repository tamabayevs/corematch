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
    # ── Fixup: Create company_branding table ──
    """
    CREATE TABLE IF NOT EXISTS company_branding (
        id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id                 UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        company_name            VARCHAR(300),
        logo_url                VARCHAR(500),
        primary_color           VARCHAR(7) DEFAULT '#2563EB',
        secondary_color         VARCHAR(7) DEFAULT '#1E40AF',
        company_website         VARCHAR(500),
        custom_welcome_message  TEXT,
        created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_company_branding_user ON company_branding(user_id);

    DROP TRIGGER IF EXISTS trg_update_company_branding_updated_at ON company_branding;
    CREATE TRIGGER trg_update_company_branding_updated_at
    BEFORE UPDATE ON company_branding
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """,
    # ── Fixup: Add missing columns to review_assignments ──
    """
    ALTER TABLE review_assignments ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ DEFAULT NOW();
    ALTER TABLE review_assignments ADD COLUMN IF NOT EXISTS notes TEXT;
    """,
    # ── Fixup: Relax review_assignments unique constraint to include campaign_id ──
    """
    DROP INDEX IF EXISTS idx_review_assignments_unique;
    CREATE UNIQUE INDEX IF NOT EXISTS idx_review_assignments_unique
        ON review_assignments(campaign_id, reviewer_id, candidate_id);
    """,
    # ── v1.1: Full-text search index on video_answers transcript ──
    """
    CREATE INDEX IF NOT EXISTS idx_video_answers_transcript_fts
        ON video_answers USING GIN (to_tsvector('english', COALESCE(transcript, '')));
    """,
    # ── v2.0: Agentic Pipeline — pipeline_configs, candidate_documents, agent_evaluations ──
    """
    -- Pipeline configuration per campaign
    CREATE TABLE IF NOT EXISTS pipeline_configs (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        campaign_id         UUID NOT NULL UNIQUE REFERENCES campaigns(id) ON DELETE CASCADE,
        stages              JSONB NOT NULL DEFAULT '[]'::jsonb,
        default_provider    VARCHAR(50) DEFAULT 'groq',
        default_model       VARCHAR(100) DEFAULT 'llama-3.3-70b-versatile',
        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_pipeline_configs_campaign ON pipeline_configs(campaign_id);

    DROP TRIGGER IF EXISTS trg_update_pipeline_configs_updated_at ON pipeline_configs;
    CREATE TRIGGER trg_update_pipeline_configs_updated_at
    BEFORE UPDATE ON pipeline_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """,
    """
    -- Candidate documents (CV uploads, extracted text)
    CREATE TABLE IF NOT EXISTS candidate_documents (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        candidate_id        UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
        document_type       VARCHAR(20) NOT NULL
                            CHECK (document_type IN ('cv', 'cover_letter', 'other')),
        original_filename   VARCHAR(500),
        storage_key         VARCHAR(500) NOT NULL,
        content_type        VARCHAR(100),
        file_size_bytes     BIGINT,
        extracted_text      TEXT,
        extraction_status   VARCHAR(20) DEFAULT 'pending'
                            CHECK (extraction_status IN ('pending', 'processing', 'complete', 'failed')),
        metadata            JSONB DEFAULT '{}'::jsonb,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_candidate_docs_candidate ON candidate_documents(candidate_id);
    """,
    """
    -- Agent evaluations (AI agent assessments across all pipeline stages)
    CREATE TABLE IF NOT EXISTS agent_evaluations (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        candidate_id        UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
        campaign_id         UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
        stage               INTEGER NOT NULL CHECK (stage BETWEEN 1 AND 4),
        agent_type          VARCHAR(30) NOT NULL
                            CHECK (agent_type IN ('cv_screener', 'video_scorer', 'deep_evaluator', 'shortlist_ranker')),
        overall_score       NUMERIC(5,2),
        scores_detail       JSONB DEFAULT '{}'::jsonb,
        recommendation      VARCHAR(20) NOT NULL
                            CHECK (recommendation IN ('advance', 'reject', 'needs_review')),
        confidence          NUMERIC(4,2),
        summary             TEXT,
        strengths           JSONB DEFAULT '[]'::jsonb,
        concerns            JSONB DEFAULT '[]'::jsonb,
        evidence            JSONB DEFAULT '[]'::jsonb,
        hr_decision         VARCHAR(20)
                            CHECK (hr_decision IN ('approved', 'rejected', 'overridden')),
        hr_decision_by      UUID REFERENCES users(id) ON DELETE SET NULL,
        hr_decision_at      TIMESTAMPTZ,
        hr_override_reason  TEXT,
        provider            VARCHAR(50),
        model_used          VARCHAR(100),
        raw_response        JSONB,
        tokens_used         INTEGER,
        latency_ms          INTEGER,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_agent_evals_candidate ON agent_evaluations(candidate_id);
    CREATE INDEX IF NOT EXISTS idx_agent_evals_campaign_stage ON agent_evaluations(campaign_id, stage);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_evals_unique ON agent_evaluations(candidate_id, stage, agent_type);
    """,
    """
    -- Add pipeline columns to campaigns and candidates
    ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS pipeline_enabled BOOLEAN DEFAULT FALSE;

    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR(500);
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS pipeline_stage INTEGER DEFAULT 0;
    """,
    """
    -- Expand candidates status CHECK to include pipeline statuses
    ALTER TABLE candidates DROP CONSTRAINT IF EXISTS candidates_status_check;
    ALTER TABLE candidates ADD CONSTRAINT candidates_status_check
        CHECK (status IN (
            'invited', 'started', 'submitted', 'erased',
            'applied', 'screening', 'screen_complete',
            'video_scored', 'deep_eval', 'deep_complete',
            'shortlisted', 'rejected', 'on_hold'
        ));
    """,
    # ── GTM Phase 2B: Email Verification ──
    """
    -- Add email_verified flag to users (default FALSE for new users, TRUE for existing)
    ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

    -- Set existing users as verified (they were already using the platform)
    UPDATE users SET email_verified = TRUE WHERE email_verified = FALSE;

    -- Email verification codes table
    CREATE TABLE IF NOT EXISTS email_verification_codes (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        code        VARCHAR(6) NOT NULL,
        expires_at  TIMESTAMPTZ NOT NULL,
        used        BOOLEAN DEFAULT FALSE,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_evc_user_id ON email_verification_codes(user_id);
    """,
    # ── GTM Phase 2C: Usage Limits / Plan Tiers ──
    """
    CREATE TABLE IF NOT EXISTS plan_limits (
        id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id                     UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        plan_tier                   VARCHAR(20) NOT NULL DEFAULT 'starter'
                                    CHECK (plan_tier IN ('free', 'starter', 'growth', 'enterprise')),
        max_campaigns               INTEGER NOT NULL DEFAULT 3,
        max_candidates_per_month    INTEGER NOT NULL DEFAULT 50,
        max_team_members            INTEGER NOT NULL DEFAULT 3,
        current_candidates_this_month INTEGER NOT NULL DEFAULT 0,
        period_start                DATE NOT NULL DEFAULT CURRENT_DATE,
        created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_plan_limits_user ON plan_limits(user_id);

    DROP TRIGGER IF EXISTS trg_update_plan_limits_updated_at ON plan_limits;
    CREATE TRIGGER trg_update_plan_limits_updated_at
    BEFORE UPDATE ON plan_limits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

    -- Seed starter plan for all existing users
    INSERT INTO plan_limits (user_id, plan_tier, max_campaigns, max_candidates_per_month, max_team_members)
    SELECT id, 'starter', 3, 50, 3 FROM users
    WHERE id NOT IN (SELECT user_id FROM plan_limits);
    """,

    # ── Migration 23: Demand Measurement (waitlist + page events) ──
    """
    CREATE TABLE IF NOT EXISTS waitlist_signups (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        full_name       VARCHAR(300) NOT NULL,
        email           VARCHAR(320) NOT NULL,
        company_name    VARCHAR(300),
        source          VARCHAR(50) DEFAULT 'landing_page',
        utm_source      VARCHAR(200),
        utm_medium      VARCHAR(200),
        utm_campaign    VARCHAR(200),
        ip_address      VARCHAR(45),
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_waitlist_signups_email ON waitlist_signups(email);

    CREATE TABLE IF NOT EXISTS page_events (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        event_type      VARCHAR(50) NOT NULL,
        page            VARCHAR(500) DEFAULT '/',
        referrer        VARCHAR(500),
        utm_source      VARCHAR(200),
        utm_medium      VARCHAR(200),
        utm_campaign    VARCHAR(200),
        ip_address      VARCHAR(45),
        user_agent      VARCHAR(500),
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_page_events_created_at ON page_events(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_page_events_type ON page_events(event_type);
    """,
    # ── Migration 24: Fix team_members for pending invites ──
    # user_id must be nullable (pending invites have no user yet)
    # invited_email stores the email for pending invites
    """
    ALTER TABLE team_members ALTER COLUMN user_id DROP NOT NULL;
    ALTER TABLE team_members ADD COLUMN IF NOT EXISTS invited_email VARCHAR(320);
    DROP INDEX IF EXISTS idx_team_members_unique;
    CREATE UNIQUE INDEX IF NOT EXISTS idx_team_members_owner_user
        ON team_members(owner_id, user_id) WHERE user_id IS NOT NULL;
    CREATE UNIQUE INDEX IF NOT EXISTS idx_team_members_owner_email
        ON team_members(owner_id, invited_email) WHERE invited_email IS NOT NULL;
    """,
    # ── Migration 25: Add category column to campaign_templates ──
    """
    ALTER TABLE campaign_templates ADD COLUMN IF NOT EXISTS category VARCHAR(100);

    -- Tag existing system templates
    UPDATE campaign_templates SET category = 'General'          WHERE is_system = TRUE AND name = 'General Interview';
    UPDATE campaign_templates SET category = 'Technology & IT'  WHERE is_system = TRUE AND name = 'Technical Screening';
    UPDATE campaign_templates SET category = 'Retail'           WHERE is_system = TRUE AND name = 'Sales Role';
    UPDATE campaign_templates SET category = 'Call Center & Support' WHERE is_system = TRUE AND name = 'Customer Service';
    """,
    # ── Migration 26: Seed 48 MENA industry templates ──
    # Hospitality & Tourism (7)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Hotel Front Desk Agent',
           'Screen candidates for guest check-in/check-out, reservation handling, and front-office operations',
           'Hospitality & Tourism',
           '[{"id":"sys-13","text":"A guest arrives upset because their room is not ready. How would you handle the situation while maintaining a positive guest experience?","think_time_seconds":30},{"id":"sys-14","text":"Describe your experience managing reservations, check-ins, and guest requests simultaneously during peak hours.","think_time_seconds":30},{"id":"sys-15","text":"How do you handle a situation where a guest makes a special request that falls outside standard hotel policy?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Hotel Front Desk Agent');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Housekeeping Staff',
           'Evaluate attention to detail, time management, and hygiene standards compliance',
           'Hospitality & Tourism',
           '[{"id":"sys-16","text":"Walk us through how you organize and prioritize room cleaning when you have a full floor to complete before check-in time.","think_time_seconds":30},{"id":"sys-17","text":"Describe how you ensure hygiene and cleanliness standards are consistently met in every room you service.","think_time_seconds":30},{"id":"sys-18","text":"Tell us about a time you found a guest''s lost or damaged item. How did you handle it?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Housekeeping Staff');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Restaurant Server',
           'Assess customer service skills, menu knowledge, and ability to handle a fast-paced dining environment',
           'Hospitality & Tourism',
           '[{"id":"sys-19","text":"A table has been waiting longer than expected for their food. How do you manage their expectations and keep them satisfied?","think_time_seconds":30},{"id":"sys-20","text":"Describe how you upsell menu items to guests without being pushy. Give a specific example if possible.","think_time_seconds":30},{"id":"sys-21","text":"How do you handle serving a large party while still giving quality attention to your other tables?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Restaurant Server');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Chef / Line Cook',
           'Evaluate kitchen experience, food safety knowledge, and ability to work under pressure',
           'Hospitality & Tourism',
           '[{"id":"sys-22","text":"Describe how you maintain food safety and hygiene standards during a busy service rush.","think_time_seconds":30},{"id":"sys-23","text":"Tell us about a time you had to prepare dishes under extreme time pressure. How did you ensure quality was not compromised?","think_time_seconds":30},{"id":"sys-24","text":"How do you handle receiving a dish sent back by a guest? Walk us through your approach.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Chef / Line Cook');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Guest Relations Executive',
           'Assess complaint resolution skills, VIP guest handling, and brand representation ability',
           'Hospitality & Tourism',
           '[{"id":"sys-25","text":"Describe how you would handle a VIP guest who is dissatisfied with their experience at the property.","think_time_seconds":30},{"id":"sys-26","text":"Tell us about a time you went above and beyond to create a memorable experience for a guest.","think_time_seconds":30},{"id":"sys-27","text":"How do you track and follow up on guest feedback to ensure continuous service improvement?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Guest Relations Executive');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Event Coordinator',
           'Evaluate event planning ability, vendor management skills, and problem-solving under pressure',
           'Hospitality & Tourism',
           '[{"id":"sys-28","text":"Walk us through how you plan and execute an event from initial brief to post-event review.","think_time_seconds":30},{"id":"sys-29","text":"Describe a time when something went wrong during an event. How did you resolve it on the spot?","think_time_seconds":30},{"id":"sys-30","text":"How do you manage multiple vendors and ensure everyone delivers on time and on budget?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Event Coordinator');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Tour Guide',
           'Assess local knowledge, public speaking ability, and tourist group management skills',
           'Hospitality & Tourism',
           '[{"id":"sys-31","text":"How do you keep a diverse group of tourists engaged and entertained throughout a full-day tour?","think_time_seconds":30},{"id":"sys-32","text":"Describe how you handle a situation where a tourist becomes unwell or has an emergency during a tour.","think_time_seconds":30},{"id":"sys-33","text":"Tell us about your knowledge of local history and culture. What makes your tours stand out?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Tour Guide');
    """,
    # Retail (4)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Retail Sales Associate',
           'Screen for product knowledge, sales approach, and customer engagement skills',
           'Retail',
           '[{"id":"sys-34","text":"A customer walks in but seems unsure about what they need. How do you approach and assist them without being overbearing?","think_time_seconds":30},{"id":"sys-35","text":"Describe a time you successfully convinced a hesitant customer to make a purchase. What technique did you use?","think_time_seconds":30},{"id":"sys-36","text":"How do you stay updated on product features and promotions to give customers the best advice?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Retail Sales Associate');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Store Manager',
           'Evaluate leadership, merchandising strategy, and ability to manage sales KPIs',
           'Retail',
           '[{"id":"sys-37","text":"How do you motivate your team to meet or exceed monthly sales targets?","think_time_seconds":30},{"id":"sys-38","text":"Describe how you handle inventory management and visual merchandising to maximize sales.","think_time_seconds":30},{"id":"sys-39","text":"Tell us about a time you had to deal with an underperforming team member. What steps did you take?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Store Manager');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Cashier',
           'Assess transaction accuracy, speed, and customer interaction at the point of sale',
           'Retail',
           '[{"id":"sys-40","text":"How do you ensure accuracy when processing a high volume of transactions during peak hours?","think_time_seconds":30},{"id":"sys-41","text":"Describe how you would handle a situation where a customer disputes a charge or price at the register.","think_time_seconds":30},{"id":"sys-42","text":"What steps do you take at the end of your shift to ensure your cash register balances correctly?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Cashier');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Visual Merchandiser',
           'Evaluate creative display skills, brand standards knowledge, and trend awareness',
           'Retail',
           '[{"id":"sys-43","text":"Walk us through your process for designing a window display that drives foot traffic into the store.","think_time_seconds":30},{"id":"sys-44","text":"How do you balance brand guidelines with creative ideas when setting up in-store displays?","think_time_seconds":30},{"id":"sys-45","text":"Describe how you use sales data and customer behavior to decide on product placement and display changes.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Visual Merchandiser');
    """,
    # Logistics & Supply Chain (4)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Delivery Driver',
           'Screen for route knowledge, time management, and safe delivery practices',
           'Logistics & Supply Chain',
           '[{"id":"sys-46","text":"How do you plan your delivery route to complete all deliveries on time, especially during traffic congestion?","think_time_seconds":30},{"id":"sys-47","text":"Describe a situation where a delivery went wrong — wrong address, damaged item, or missed deadline. How did you resolve it?","think_time_seconds":30},{"id":"sys-48","text":"What steps do you take to ensure customer packages are handled safely and delivered in good condition?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Delivery Driver');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Warehouse Associate',
           'Evaluate inventory handling, safety awareness, and physical task management',
           'Logistics & Supply Chain',
           '[{"id":"sys-49","text":"Describe your experience with inventory management systems and how you ensure stock accuracy.","think_time_seconds":30},{"id":"sys-50","text":"How do you maintain safety standards while working under pressure to meet shipping deadlines?","think_time_seconds":30},{"id":"sys-51","text":"Walk us through how you would organize a warehouse section to maximize picking efficiency.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Warehouse Associate');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Procurement Officer',
           'Assess vendor negotiation skills, cost optimization ability, and procurement compliance',
           'Logistics & Supply Chain',
           '[{"id":"sys-52","text":"Describe your approach to evaluating and selecting new suppliers. What criteria do you prioritize?","think_time_seconds":30},{"id":"sys-53","text":"Tell us about a time you negotiated a better deal with a vendor. What strategy did you use?","think_time_seconds":30},{"id":"sys-54","text":"How do you ensure compliance with procurement policies while still meeting urgent business needs?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Procurement Officer');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Supply Chain Analyst',
           'Evaluate data analysis capabilities, demand forecasting, and process improvement skills',
           'Logistics & Supply Chain',
           '[{"id":"sys-55","text":"Walk us through how you would analyze supply chain data to identify bottlenecks and recommend improvements.","think_time_seconds":30},{"id":"sys-56","text":"Describe your experience with demand forecasting. What tools and methods have you used?","think_time_seconds":30},{"id":"sys-57","text":"Tell us about a time your analysis led to measurable cost savings or efficiency gains in the supply chain.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Supply Chain Analyst');
    """,
    # Construction & Facilities (5)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Site Engineer',
           'Screen for technical construction expertise, site management, and safety compliance',
           'Construction & Facilities',
           '[{"id":"sys-58","text":"Describe how you ensure a construction project stays on schedule and within specification while managing on-site challenges.","think_time_seconds":30},{"id":"sys-59","text":"Tell us about a time you identified a structural or safety issue on-site. How did you address it?","think_time_seconds":30},{"id":"sys-60","text":"How do you coordinate between design teams, subcontractors, and laborers to ensure smooth project execution?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Site Engineer');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Construction Foreman',
           'Evaluate team supervision ability, scheduling skills, and quality control methods',
           'Construction & Facilities',
           '[{"id":"sys-61","text":"How do you manage a team of workers to ensure daily construction targets are met safely and on schedule?","think_time_seconds":30},{"id":"sys-62","text":"Describe a situation where a subcontractor or crew member was underperforming. How did you handle it?","think_time_seconds":30},{"id":"sys-63","text":"What is your approach to quality control on a construction site? Give a specific example.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Construction Foreman');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Electrician / Maintenance Technician',
           'Assess technical troubleshooting skills, safety awareness, and preventive maintenance experience',
           'Construction & Facilities',
           '[{"id":"sys-64","text":"Describe your approach to diagnosing and repairing an electrical fault in a building. Walk us through your process.","think_time_seconds":30},{"id":"sys-65","text":"How do you ensure your own safety and the safety of others when working with high-voltage systems?","think_time_seconds":30},{"id":"sys-66","text":"Tell us about your experience with preventive maintenance schedules. How do you prioritize tasks?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Electrician / Maintenance Technician');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Health & Safety Officer (HSE)',
           'Evaluate risk assessment expertise, regulatory compliance knowledge, and incident response skills',
           'Construction & Facilities',
           '[{"id":"sys-67","text":"Walk us through how you conduct a risk assessment on a construction site before work begins.","think_time_seconds":30},{"id":"sys-68","text":"Describe a time you had to stop work on a site due to a safety violation. How did you handle the pushback?","think_time_seconds":30},{"id":"sys-69","text":"How do you keep your team informed and compliant with the latest health and safety regulations?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Health & Safety Officer (HSE)');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Facilities Manager',
           'Screen for building operations knowledge, vendor management, and budget control skills',
           'Construction & Facilities',
           '[{"id":"sys-70","text":"How do you prioritize and manage multiple maintenance requests across a large facility?","think_time_seconds":30},{"id":"sys-71","text":"Describe your experience managing facility service contracts and vendor relationships.","think_time_seconds":30},{"id":"sys-72","text":"Tell us about a time you implemented a cost-saving initiative in facilities operations. What was the outcome?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Facilities Manager');
    """,
    # Healthcare (5)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Registered Nurse',
           'Evaluate patient care skills, clinical knowledge, and ability to handle emergencies',
           'Healthcare',
           '[{"id":"sys-73","text":"Describe how you prioritize patient care when managing multiple patients with different levels of acuity.","think_time_seconds":30},{"id":"sys-74","text":"Tell us about a time you had to respond to a medical emergency. What actions did you take?","think_time_seconds":30},{"id":"sys-75","text":"How do you communicate with patients and their families to ensure they understand their care plan?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Registered Nurse');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Pharmacist',
           'Assess medication knowledge, patient counseling skills, and accuracy under pressure',
           'Healthcare',
           '[{"id":"sys-76","text":"How do you verify prescription accuracy and catch potential drug interactions before dispensing?","think_time_seconds":30},{"id":"sys-77","text":"Describe your approach to counseling a patient who is unfamiliar with a new medication and its side effects.","think_time_seconds":30},{"id":"sys-78","text":"Tell us about a time you identified a prescribing error. How did you handle it?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Pharmacist');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Hospital Administrator',
           'Evaluate operations management, healthcare compliance, and stakeholder communication skills',
           'Healthcare',
           '[{"id":"sys-79","text":"How do you balance operational efficiency with patient care quality in a hospital setting?","think_time_seconds":30},{"id":"sys-80","text":"Describe your experience managing healthcare regulatory compliance and accreditation requirements.","think_time_seconds":30},{"id":"sys-81","text":"Tell us about a time you resolved a conflict between clinical staff and administrative requirements.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Hospital Administrator');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Lab Technician',
           'Screen for laboratory procedure knowledge, quality control practices, and accuracy',
           'Healthcare',
           '[{"id":"sys-82","text":"Walk us through how you process and handle a high volume of laboratory samples while maintaining accuracy.","think_time_seconds":30},{"id":"sys-83","text":"How do you ensure quality control in your laboratory work? Describe your calibration and validation routine.","think_time_seconds":30},{"id":"sys-84","text":"Describe a time you encountered an unusual test result. What steps did you take to investigate?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Lab Technician');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Caregiver / Home Health Aide',
           'Assess patient empathy, daily care skills, and awareness of emergency protocols',
           'Healthcare',
           '[{"id":"sys-85","text":"How do you build trust and rapport with elderly or vulnerable patients who may be resistant to care?","think_time_seconds":30},{"id":"sys-86","text":"Describe how you manage daily care routines — medication reminders, hygiene, mobility — while respecting patient dignity.","think_time_seconds":30},{"id":"sys-87","text":"What would you do if a patient in your care suddenly showed signs of a medical emergency?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Caregiver / Home Health Aide');
    """,
    # Technology & IT (4)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Software Developer',
           'Evaluate coding skills, system design thinking, and collaborative development experience',
           'Technology & IT',
           '[{"id":"sys-88","text":"Describe a software project you built from scratch. What architecture decisions did you make and why?","think_time_seconds":30},{"id":"sys-89","text":"How do you approach debugging a complex issue in a production system under time pressure?","think_time_seconds":30},{"id":"sys-90","text":"Tell us about your experience with code reviews. How do you give and receive constructive feedback?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Software Developer');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'IT Support Specialist',
           'Screen for troubleshooting ability, customer service orientation, and technical knowledge',
           'Technology & IT',
           '[{"id":"sys-91","text":"Describe your process for diagnosing and resolving a technical issue reported by a non-technical user.","think_time_seconds":30},{"id":"sys-92","text":"How do you prioritize multiple support tickets when several users report urgent issues simultaneously?","think_time_seconds":30},{"id":"sys-93","text":"Tell us about the most challenging IT issue you resolved. What made it difficult and how did you solve it?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'IT Support Specialist');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Cybersecurity Analyst',
           'Assess threat detection skills, incident response experience, and security protocol knowledge',
           'Technology & IT',
           '[{"id":"sys-94","text":"Walk us through how you would investigate and respond to a suspected data breach or security incident.","think_time_seconds":30},{"id":"sys-95","text":"Describe your experience with security monitoring tools and how you identify potential threats.","think_time_seconds":30},{"id":"sys-96","text":"How do you stay current with evolving cyber threats and ensure your organization''s defenses remain effective?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Cybersecurity Analyst');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Data Analyst',
           'Evaluate data interpretation, visualization skills, and ability to derive business insights',
           'Technology & IT',
           '[{"id":"sys-97","text":"Describe a project where your data analysis directly influenced a business decision. What was your approach?","think_time_seconds":30},{"id":"sys-98","text":"How do you ensure data quality and accuracy before presenting findings to stakeholders?","think_time_seconds":30},{"id":"sys-99","text":"Walk us through the tools and techniques you use to visualize data and tell a compelling story with numbers.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Data Analyst');
    """,
    # Digital & Marketing (4)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Digital Marketing Specialist',
           'Screen for campaign management skills, analytics proficiency, and content strategy experience',
           'Digital & Marketing',
           '[{"id":"sys-100","text":"Walk us through how you plan, execute, and measure the success of a digital marketing campaign.","think_time_seconds":30},{"id":"sys-101","text":"Describe a campaign that underperformed. How did you analyze the results and what changes did you make?","think_time_seconds":30},{"id":"sys-102","text":"How do you allocate budget across different digital channels — paid search, social, email — to maximize ROI?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Digital Marketing Specialist');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Social Media Manager',
           'Evaluate content creation, community management, and social media trend awareness',
           'Digital & Marketing',
           '[{"id":"sys-103","text":"How do you develop a content calendar that aligns with brand goals and engages the target audience?","think_time_seconds":30},{"id":"sys-104","text":"Describe how you handle a negative comment or a brand crisis on social media.","think_time_seconds":30},{"id":"sys-105","text":"What metrics do you track to measure social media success, and how do you report them to stakeholders?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Social Media Manager');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Content Creator',
           'Assess writing and visual skills, brand voice consistency, and audience engagement techniques',
           'Digital & Marketing',
           '[{"id":"sys-106","text":"Walk us through your creative process for producing content — from idea to published piece.","think_time_seconds":30},{"id":"sys-107","text":"How do you adapt your content style for different platforms while maintaining a consistent brand voice?","think_time_seconds":30},{"id":"sys-108","text":"Describe a piece of content you created that significantly boosted engagement. What made it work?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Content Creator');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'SEO / SEM Specialist',
           'Evaluate search optimization expertise, keyword strategy, and analytics-driven decision making',
           'Digital & Marketing',
           '[{"id":"sys-109","text":"Describe your process for auditing a website''s SEO performance and creating an action plan for improvement.","think_time_seconds":30},{"id":"sys-110","text":"How do you conduct keyword research and decide which terms to target for a new campaign or product page?","think_time_seconds":30},{"id":"sys-111","text":"Tell us about a time your SEO or SEM strategy led to a measurable increase in organic traffic or conversions.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'SEO / SEM Specialist');
    """,
    # Finance & Banking (4)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Accountant',
           'Screen for financial reporting accuracy, compliance knowledge, and attention to detail',
           'Finance & Banking',
           '[{"id":"sys-112","text":"Walk us through your month-end closing process. How do you ensure all entries are accurate and complete?","think_time_seconds":30},{"id":"sys-113","text":"Describe a time you identified a discrepancy or error in financial records. How did you investigate and resolve it?","think_time_seconds":30},{"id":"sys-114","text":"How do you stay up to date with changing accounting standards and tax regulations?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Accountant');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Financial Analyst',
           'Assess financial modeling, forecasting ability, and skill in presenting business recommendations',
           'Finance & Banking',
           '[{"id":"sys-115","text":"Describe your experience building financial models. What assumptions do you typically consider?","think_time_seconds":30},{"id":"sys-116","text":"How do you present complex financial data to non-financial stakeholders in a way they can act on?","think_time_seconds":30},{"id":"sys-117","text":"Tell us about a time your financial analysis influenced a major business decision.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Financial Analyst');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Bank Teller',
           'Evaluate transaction accuracy, customer service at the counter, and compliance awareness',
           'Finance & Banking',
           '[{"id":"sys-118","text":"How do you ensure accuracy and compliance when processing a high volume of banking transactions each day?","think_time_seconds":30},{"id":"sys-119","text":"Describe how you would handle a customer who is confused or upset about a charge on their account.","think_time_seconds":30},{"id":"sys-120","text":"What steps do you take to identify and escalate potentially fraudulent transactions?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Bank Teller');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Auditor',
           'Screen for risk assessment expertise, regulatory compliance knowledge, and analytical thinking',
           'Finance & Banking',
           '[{"id":"sys-121","text":"Walk us through your approach to planning and conducting an audit from start to finish.","think_time_seconds":30},{"id":"sys-122","text":"Describe a time you uncovered a significant finding during an audit. How did you report it and what was the outcome?","think_time_seconds":30},{"id":"sys-123","text":"How do you handle pushback from a department that disagrees with your audit findings?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Auditor');
    """,
    # Administrative & Office (4)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Administrative Assistant',
           'Assess organizational skills, communication clarity, and ability to multitask effectively',
           'Administrative & Office',
           '[{"id":"sys-124","text":"Describe how you organize and prioritize your workload when multiple managers need tasks completed urgently.","think_time_seconds":30},{"id":"sys-125","text":"How do you manage executive calendars, meeting scheduling, and travel arrangements efficiently?","think_time_seconds":30},{"id":"sys-126","text":"Tell us about a time you identified a way to improve an office process or workflow. What did you do?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Administrative Assistant');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Receptionist',
           'Evaluate first-impression skills, phone handling, and ability to manage front-desk operations',
           'Administrative & Office',
           '[{"id":"sys-127","text":"How do you create a welcoming first impression for visitors while managing phone calls and front-desk duties simultaneously?","think_time_seconds":30},{"id":"sys-128","text":"Describe a time you had to deal with a difficult or aggressive visitor. How did you handle the situation?","think_time_seconds":30},{"id":"sys-129","text":"What systems or tools do you use to manage visitor logs, meeting room bookings, and deliveries?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Receptionist');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'HR Coordinator',
           'Screen for recruitment support capability, employee relations awareness, and HR compliance',
           'Administrative & Office',
           '[{"id":"sys-130","text":"Describe your experience coordinating the recruitment process — from job posting to onboarding a new hire.","think_time_seconds":30},{"id":"sys-131","text":"How do you handle sensitive employee information while ensuring HR compliance and confidentiality?","think_time_seconds":30},{"id":"sys-132","text":"Tell us about a time you helped resolve a workplace conflict or employee concern.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'HR Coordinator');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Office Manager',
           'Evaluate office operations management, team coordination, and budget planning skills',
           'Administrative & Office',
           '[{"id":"sys-133","text":"How do you ensure smooth day-to-day office operations across departments?","think_time_seconds":30},{"id":"sys-134","text":"Describe your experience managing office budgets, vendor contracts, and supply procurement.","think_time_seconds":30},{"id":"sys-135","text":"Tell us about a time you implemented a change that improved office efficiency or employee satisfaction.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Office Manager');
    """,
    # Call Center & Support (3)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Call Center Agent',
           'Assess communication clarity, script adherence, and ability to show empathy under pressure',
           'Call Center & Support',
           '[{"id":"sys-136","text":"A caller is angry about a billing issue and keeps interrupting you. How do you de-escalate the situation and resolve their concern?","think_time_seconds":30},{"id":"sys-137","text":"Describe how you manage your call handling time while still ensuring each customer feels heard and helped.","think_time_seconds":30},{"id":"sys-138","text":"How do you handle back-to-back calls on a busy day without letting fatigue affect your service quality?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Call Center Agent');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Technical Support Agent',
           'Evaluate remote troubleshooting skills, patience, and technical communication clarity',
           'Call Center & Support',
           '[{"id":"sys-139","text":"Describe how you guide a non-technical customer through solving a technical issue step by step over the phone.","think_time_seconds":30},{"id":"sys-140","text":"Tell us about the most complex technical issue you resolved remotely. What was your troubleshooting process?","think_time_seconds":30},{"id":"sys-141","text":"How do you document and escalate issues when they go beyond your level of expertise?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Technical Support Agent');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Customer Success Manager',
           'Screen for client relationship building, retention strategies, and upselling ability',
           'Call Center & Support',
           '[{"id":"sys-142","text":"How do you proactively identify and address risks of customer churn before they escalate?","think_time_seconds":30},{"id":"sys-143","text":"Describe your approach to onboarding a new client and ensuring they see value from your product quickly.","think_time_seconds":30},{"id":"sys-144","text":"Tell us about a time you turned a dissatisfied customer into a long-term advocate for your company.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Customer Success Manager');
    """,
    # Education (2)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Teacher / Instructor',
           'Evaluate teaching methodology, student engagement techniques, and classroom management',
           'Education',
           '[{"id":"sys-145","text":"Describe your approach to planning a lesson that engages students with different learning styles and abilities.","think_time_seconds":30},{"id":"sys-146","text":"How do you handle classroom disruptions while maintaining a positive learning environment?","think_time_seconds":30},{"id":"sys-147","text":"Tell us about a time you adapted your teaching approach because students were not grasping the material. What did you change?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Teacher / Instructor');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Academic Coordinator',
           'Assess curriculum management, faculty coordination, and student program administration',
           'Education',
           '[{"id":"sys-148","text":"How do you coordinate between faculty members to ensure curriculum consistency and quality across sections?","think_time_seconds":30},{"id":"sys-149","text":"Describe your experience managing student enrollment, scheduling, and academic program logistics.","think_time_seconds":30},{"id":"sys-150","text":"Tell us about a time you implemented a change that improved academic outcomes or operational efficiency.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Academic Coordinator');
    """,
    # Oil & Gas / Energy (3)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Petroleum Technician',
           'Screen for technical operations knowledge, field safety compliance, and hands-on experience',
           'Oil & Gas / Energy',
           '[{"id":"sys-151","text":"Describe your experience working in upstream or downstream petroleum operations. What equipment have you worked with?","think_time_seconds":30},{"id":"sys-152","text":"How do you ensure personal and team safety when working in a high-risk field environment?","think_time_seconds":30},{"id":"sys-153","text":"Tell us about a time you identified a potential equipment failure before it became a serious incident.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Petroleum Technician');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Renewable Energy Technician',
           'Evaluate solar/wind systems knowledge, installation experience, and maintenance skills',
           'Oil & Gas / Energy',
           '[{"id":"sys-154","text":"Walk us through your experience installing and maintaining solar panel or wind turbine systems.","think_time_seconds":30},{"id":"sys-155","text":"How do you troubleshoot performance issues in a renewable energy system? Describe your diagnostic approach.","think_time_seconds":30},{"id":"sys-156","text":"What safety protocols do you follow when working at height or with high-voltage renewable energy equipment?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Renewable Energy Technician');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'HSE Officer (Oil & Gas)',
           'Assess oil and gas safety expertise, incident investigation skills, and regulatory compliance',
           'Oil & Gas / Energy',
           '[{"id":"sys-157","text":"Describe your experience managing health, safety, and environmental compliance on an oil and gas site.","think_time_seconds":30},{"id":"sys-158","text":"Walk us through how you investigate a workplace incident and implement corrective actions.","think_time_seconds":30},{"id":"sys-159","text":"How do you foster a safety-first culture among workers who may be fatigued or under production pressure?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'HSE Officer (Oil & Gas)');
    """,
    # Security & Project Management (3)
    """
    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Security Officer',
           'Evaluate vigilance, emergency response capability, and professional communication',
           'Security',
           '[{"id":"sys-160","text":"Describe how you handle a situation where an unauthorized person attempts to enter a restricted area.","think_time_seconds":30},{"id":"sys-161","text":"How do you stay alert and vigilant during long shifts, especially during night duty?","think_time_seconds":30},{"id":"sys-162","text":"Tell us about a time you responded to an emergency or security incident. What actions did you take?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Security Officer');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Project Manager',
           'Screen for project planning, stakeholder management, and deadline-driven execution skills',
           'Management',
           '[{"id":"sys-163","text":"Walk us through how you plan and kick off a new project from stakeholder alignment to team mobilization.","think_time_seconds":30},{"id":"sys-164","text":"Describe a project that faced scope creep or timeline delays. How did you get it back on track?","think_time_seconds":30},{"id":"sys-165","text":"How do you manage competing priorities and keep multiple stakeholders aligned throughout a project lifecycle?","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Project Manager');

    INSERT INTO campaign_templates (name, description, category, questions, language, is_system)
    SELECT 'Business Development Manager',
           'Assess market expansion skills, client acquisition strategy, and revenue growth experience',
           'Management',
           '[{"id":"sys-166","text":"How do you identify and evaluate new business opportunities in a competitive market?","think_time_seconds":30},{"id":"sys-167","text":"Describe your approach to building a pipeline from initial prospecting to closing a deal.","think_time_seconds":30},{"id":"sys-168","text":"Tell us about a partnership or deal you closed that had a significant impact on company revenue.","think_time_seconds":30}]'::jsonb,
           'en', TRUE
    WHERE NOT EXISTS (SELECT 1 FROM campaign_templates WHERE is_system = TRUE AND name = 'Business Development Manager');
    """,

    # ── Migration 27: AI Eval Bench tables ──
    """
    CREATE TABLE IF NOT EXISTS eval_benchmarks (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name            VARCHAR(300) NOT NULL,
        question_text   TEXT NOT NULL,
        job_title       VARCHAR(300) NOT NULL,
        job_description TEXT DEFAULT '',
        language        VARCHAR(5) DEFAULT 'en',
        storage_key     VARCHAR(500) NOT NULL,
        file_size_bytes INTEGER,
        notes           TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_eval_benchmarks_user ON eval_benchmarks(user_id);

    CREATE TABLE IF NOT EXISTS eval_runs (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        model_name      VARCHAR(100) NOT NULL,
        status          VARCHAR(20) NOT NULL DEFAULT 'pending',
        total_benchmarks    INTEGER DEFAULT 0,
        completed_benchmarks INTEGER DEFAULT 0,
        failed_benchmarks   INTEGER DEFAULT 0,
        started_at      TIMESTAMPTZ,
        completed_at    TIMESTAMPTZ,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_eval_runs_user ON eval_runs(user_id);

    CREATE TABLE IF NOT EXISTS eval_results (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        run_id          UUID NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
        benchmark_id    UUID NOT NULL REFERENCES eval_benchmarks(id) ON DELETE CASCADE,
        status          VARCHAR(20) NOT NULL DEFAULT 'pending',
        transcript      TEXT,
        detected_language VARCHAR(10),
        content_score   NUMERIC(5,2),
        communication_score NUMERIC(5,2),
        behavioral_score NUMERIC(5,2),
        overall_score   NUMERIC(5,2),
        tier            VARCHAR(20),
        strengths       JSONB DEFAULT '[]'::jsonb,
        improvements    JSONB DEFAULT '[]'::jsonb,
        language_match  BOOLEAN,
        model_used      VARCHAR(100),
        latency_ms      INTEGER,
        error_message   TEXT,
        raw_response    JSONB DEFAULT '{}'::jsonb,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_eval_results_run ON eval_results(run_id);
    CREATE INDEX IF NOT EXISTS idx_eval_results_benchmark ON eval_results(benchmark_id);
    """,

    # ── Migration 28: Stripe billing columns on users ──
    """
    ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100);
    ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(100);
    ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_status VARCHAR(30);
    CREATE INDEX IF NOT EXISTS idx_users_stripe_customer ON users(stripe_customer_id);
    CREATE INDEX IF NOT EXISTS idx_users_stripe_subscription ON users(stripe_subscription_id);
    """,
    # ── Migration 29: Superuser flag + sidebar visibility ──
    """
    ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE;
    UPDATE users SET is_superuser = TRUE WHERE email = 'olzhas.tamabayev@gmail.com';
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
