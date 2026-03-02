-- Full database bootstrap schema for interview-service (PostgreSQL)
-- Safe to run on a fresh DB. Most statements are idempotent.

BEGIN;

-- 1) Core interview table (create first, without current_message_id FK to avoid circular dependency)
CREATE TABLE IF NOT EXISTS interviews (
    id SERIAL PRIMARY KEY,
    candidate_name VARCHAR(255) NOT NULL,
    position VARCHAR(255) NOT NULL,
    skill_domain VARCHAR(50) NOT NULL,
    skills TEXT[] NOT NULL,
    experience_level VARCHAR(50) DEFAULT 'mid',
    duration_minutes INTEGER DEFAULT 30,
    additional_requirements TEXT,
    resume_file_id VARCHAR(255),
    resume_text TEXT,
    status VARCHAR(50) DEFAULT 'created',
    current_stage VARCHAR(50) DEFAULT 'welcome',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 2) Conversation messages (tree + branch support)
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parent_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    branch_id VARCHAR(100) DEFAULT 'main',
    tree_path TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE
);

-- 3) Add current_message_id FK now that messages exists
ALTER TABLE interviews
    ADD COLUMN IF NOT EXISTS current_message_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_interviews_current_message_id'
    ) THEN
        ALTER TABLE interviews
            ADD CONSTRAINT fk_interviews_current_message_id
            FOREIGN KEY (current_message_id)
            REFERENCES messages(id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- 4) Evaluation results
CREATE TABLE IF NOT EXISTS evaluations (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    overall_score INTEGER CHECK (overall_score >= 0 AND overall_score <= 100),
    dimension_scores JSONB,
    strengths TEXT[],
    weaknesses TEXT[],
    recommendation TEXT,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5) Prompt config
CREATE TABLE IF NOT EXISTS prompt_configs (
    id SERIAL PRIMARY KEY,
    config_type VARCHAR(50) UNIQUE NOT NULL,
    config_data JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6) Interview snapshots
CREATE TABLE IF NOT EXISTS interview_snapshots (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7) Profile plugins
CREATE TABLE IF NOT EXISTS profile_plugins (
    id SERIAL PRIMARY KEY,
    plugin_id VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    config JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8) Interview-profile binding
CREATE TABLE IF NOT EXISTS interview_profiles (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    position_plugin_id VARCHAR(50),
    interviewer_plugin_id VARCHAR(50),
    custom_config JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Keep exactly one profile binding row per interview (matches runtime assumption)
CREATE UNIQUE INDEX IF NOT EXISTS uq_interview_profiles_interview_id
    ON interview_profiles(interview_id);

-- Runtime indexes
CREATE INDEX IF NOT EXISTS idx_messages_interview_id ON messages(interview_id);
CREATE INDEX IF NOT EXISTS idx_messages_parent_id ON messages(parent_id);
CREATE INDEX IF NOT EXISTS idx_messages_branch_id ON messages(branch_id);
CREATE INDEX IF NOT EXISTS idx_messages_is_active ON messages(is_active);

CREATE INDEX IF NOT EXISTS idx_evaluations_interview_id ON evaluations(interview_id);

CREATE INDEX IF NOT EXISTS idx_interviews_status ON interviews(status);
CREATE INDEX IF NOT EXISTS idx_interviews_current_stage ON interviews(current_stage);
CREATE INDEX IF NOT EXISTS idx_interviews_current_message_id ON interviews(current_message_id);

CREATE INDEX IF NOT EXISTS idx_snapshots_interview_id ON interview_snapshots(interview_id);

CREATE INDEX IF NOT EXISTS idx_profile_plugins_type ON profile_plugins(type);
CREATE INDEX IF NOT EXISTS idx_profile_plugins_plugin_id ON profile_plugins(plugin_id);

CREATE INDEX IF NOT EXISTS idx_interview_profiles_interview_id ON interview_profiles(interview_id);

COMMIT;

