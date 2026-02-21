"""
CoreMatch — Database Schema
Defines all tables and creates them if they don't exist.
Run this once to initialize the database.
"""
import logging
from database.connection import get_db

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# TABLE DEFINITIONS
# ──────────────────────────────────────────────────────────────

CREATE_TABLES_SQL = """
-- ─────────────────────────────────────────
-- Table: users
-- HR users who manage campaigns
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(320) NOT NULL UNIQUE,
    password_hash   VARCHAR(256) NOT NULL,
    full_name       VARCHAR(200),
    job_title       VARCHAR(200),
    company_name    VARCHAR(200),
    language        VARCHAR(5) DEFAULT 'en',   -- 'en' or 'ar'
    notify_on_complete  BOOLEAN DEFAULT TRUE,
    notify_weekly       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- Table: password_reset_tokens
-- Secure password reset flow
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(64) NOT NULL,   -- SHA-256 hex of the raw token
    expires_at  TIMESTAMPTZ NOT NULL,
    used        BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prt_token_hash ON password_reset_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_prt_user_id ON password_reset_tokens(user_id);

-- ─────────────────────────────────────────
-- Table: campaigns
-- Video interview campaigns created by HR users
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS campaigns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(300) NOT NULL,
    job_title       VARCHAR(300) NOT NULL,
    job_description TEXT,
    language        VARCHAR(5) DEFAULT 'en',   -- expected interview language: 'en', 'ar', 'both'
    -- JSONB array of question objects:
    -- [{"id": "uuid", "text": "...", "think_time_seconds": 30, "max_duration_seconds": 120}]
    questions       JSONB NOT NULL DEFAULT '[]'::jsonb,
    invite_expiry_days  INTEGER DEFAULT 7,      -- 7, 14, or 30
    allow_retakes   BOOLEAN DEFAULT TRUE,
    max_recording_seconds INTEGER DEFAULT 120,  -- 60, 120, or 180
    status          VARCHAR(20) DEFAULT 'active'  -- 'active' | 'closed' | 'archived'
                    CHECK (status IN ('active', 'closed', 'archived')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_user_id ON campaigns(user_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(user_id, status);

-- ─────────────────────────────────────────
-- Table: candidates
-- Invited candidates for a campaign
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    email           VARCHAR(320) NOT NULL,
    full_name       VARCHAR(300) NOT NULL,
    phone           VARCHAR(30),            -- optional, for SMS invitations
    invite_token    VARCHAR(36) NOT NULL UNIQUE,  -- UUID v4 used as auth token
    -- Snapshot of campaign questions at time of invitation
    -- Prevents campaign edits from corrupting existing invitations
    questions_snapshot  JSONB NOT NULL DEFAULT '[]'::jsonb,
    invite_expires_at   TIMESTAMPTZ NOT NULL,
    status          VARCHAR(20) DEFAULT 'invited'
                    CHECK (status IN ('invited', 'started', 'submitted', 'erased')),
    consent_given   BOOLEAN DEFAULT FALSE,
    consent_given_at    TIMESTAMPTZ,
    overall_score   NUMERIC(5,2),           -- denormalized average for fast sorting
    tier            VARCHAR(20),            -- 'strong_proceed' | 'consider' | 'likely_pass'
    hr_decision     VARCHAR(20),            -- 'shortlisted' | 'rejected' | 'hold' | null
    hr_decision_at  TIMESTAMPTZ,
    hr_decision_note TEXT,
    reference_id    VARCHAR(20),            -- CM-2026-XXXXXX displayed to candidates
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Critical indexes (every public request hits invite_token)
CREATE UNIQUE INDEX IF NOT EXISTS idx_candidates_invite_token ON candidates(invite_token);
-- HR dashboard: sort candidates by score within a campaign
CREATE INDEX IF NOT EXISTS idx_candidates_campaign_score ON candidates(campaign_id, overall_score DESC NULLS LAST);
-- HR decision filtering
CREATE INDEX IF NOT EXISTS idx_candidates_campaign_status ON candidates(campaign_id, status);

-- ─────────────────────────────────────────
-- Table: video_answers
-- Individual video recordings per question per candidate
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS video_answers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    question_index  INTEGER NOT NULL,       -- 0-based index into questions_snapshot
    question_text   TEXT NOT NULL,          -- denormalized for AI scoring without join
    storage_key     VARCHAR(500),           -- R2/S3 object key (null until uploaded)
    storage_provider VARCHAR(20) DEFAULT 'r2',
    file_format     VARCHAR(10),            -- 'webm' | 'mp4'
    file_size_bytes BIGINT,
    duration_seconds NUMERIC(8,2),
    transcript      TEXT,                   -- set after AI processing
    detected_language VARCHAR(5),           -- 'en' | 'ar'
    processing_status VARCHAR(20) DEFAULT 'pending'
                    CHECK (processing_status IN ('pending', 'processing', 'complete', 'failed')),
    uploaded_at     TIMESTAMPTZ,
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_video_answers_candidate_question ON video_answers(candidate_id, question_index);
CREATE INDEX IF NOT EXISTS idx_video_answers_candidate_id ON video_answers(candidate_id);
CREATE INDEX IF NOT EXISTS idx_video_answers_status ON video_answers(processing_status);

-- ─────────────────────────────────────────
-- Table: ai_scores
-- One row per video_answer with AI evaluation
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_answer_id     UUID NOT NULL UNIQUE REFERENCES video_answers(id) ON DELETE CASCADE,
    candidate_id        UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    content_score       NUMERIC(5,2),       -- 0-100: relevance, depth, examples
    communication_score NUMERIC(5,2),       -- 0-100: clarity, fluency, structure
    behavioral_score    NUMERIC(5,2),       -- 0-100: confidence, enthusiasm
    overall_score       NUMERIC(5,2),       -- weighted: content 50% + comm 30% + behavioral 20%
    tier                VARCHAR(20),        -- 'strong_proceed' | 'consider' | 'likely_pass'
    strengths           JSONB DEFAULT '[]'::jsonb,    -- ["strength 1", "strength 2"]
    improvements        JSONB DEFAULT '[]'::jsonb,    -- ["improvement 1", ...]
    language_match      BOOLEAN DEFAULT TRUE,
    model_used          VARCHAR(100),       -- e.g., 'llama-3.3-70b-versatile'
    scoring_source      VARCHAR(20) DEFAULT 'groq',   -- 'groq' | 'mock'
    raw_response        JSONB,              -- full LLM JSON response for debugging
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_scores_candidate_id ON ai_scores(candidate_id);

-- ─────────────────────────────────────────
-- Table: audit_log
-- Immutable record of all HR actions (PDPL compliance)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    action      VARCHAR(100) NOT NULL,  -- e.g., 'candidate.shortlisted', 'candidate.erased'
    entity_type VARCHAR(50),            -- 'candidate' | 'campaign' | 'user'
    entity_id   UUID,
    metadata    JSONB DEFAULT '{}'::jsonb,
    ip_address  VARCHAR(45),            -- supports IPv6
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);

-- ─────────────────────────────────────────
-- Function: auto-update updated_at timestamp
-- ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['users', 'campaigns', 'candidates'] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_update_%I_updated_at ON %I;
             CREATE TRIGGER trg_update_%I_updated_at
             BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();',
            t, t, t, t
        );
    END LOOP;
END;
$$;
"""


def create_tables() -> None:
    """Create all tables if they don't exist. Safe to run multiple times (idempotent)."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLES_SQL)
    logger.info("Database schema initialized successfully")


def drop_all_tables() -> None:
    """
    DANGER: Drop all CoreMatch tables.
    Only for development/testing — never run in production.
    """
    drop_sql = """
    DROP TABLE IF EXISTS audit_log CASCADE;
    DROP TABLE IF EXISTS ai_scores CASCADE;
    DROP TABLE IF EXISTS video_answers CASCADE;
    DROP TABLE IF EXISTS candidates CASCADE;
    DROP TABLE IF EXISTS campaigns CASCADE;
    DROP TABLE IF EXISTS password_reset_tokens CASCADE;
    DROP TABLE IF EXISTS users CASCADE;
    DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(drop_sql)
    logger.warning("All CoreMatch tables dropped")


if __name__ == "__main__":
    """Run this directly to initialize the schema: python -m database.schema"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(level=logging.INFO)
    create_tables()
    print("Schema created successfully.")
