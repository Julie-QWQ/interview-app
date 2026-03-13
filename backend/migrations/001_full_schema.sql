-- Full database bootstrap schema for interview-service (PostgreSQL)
-- This file must match the schema expected by the current runtime code.
-- Safe to run on a fresh DB. Statements are idempotent where possible.

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

-- 4) Prompt config
CREATE TABLE IF NOT EXISTS prompt_configs (
    id SERIAL PRIMARY KEY,
    config_type VARCHAR(50) UNIQUE NOT NULL,
    config_data JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5) Interview snapshots
CREATE TABLE IF NOT EXISTS interview_snapshots (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6) Profile plugins
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

-- 7) Interview-profile binding
CREATE TABLE IF NOT EXISTS interview_profiles (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    position_plugin_id VARCHAR(50),
    interviewer_plugin_id VARCHAR(50),
    custom_config JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8) Tool invocation records
CREATE TABLE IF NOT EXISTS tool_invocations (
    id SERIAL PRIMARY KEY,
    trace_id VARCHAR(100),
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,
    trigger VARCHAR(50) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    request_payload JSONB,
    response_payload JSONB,
    status VARCHAR(30) NOT NULL,
    latency_ms INTEGER DEFAULT 0,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9) Tool context cache
CREATE TABLE IF NOT EXISTS interview_tool_contexts (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    context_key VARCHAR(255) NOT NULL,
    prompt_context TEXT,
    structured_payload JSONB,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10) Expression analysis feature segments
CREATE TABLE IF NOT EXISTS expression_feature_segments (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    feature_type VARCHAR(20) NOT NULL,
    segment_key VARCHAR(255) NOT NULL,
    stage VARCHAR(50),
    source VARCHAR(50),
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    metrics JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11) Expression analysis reports
CREATE TABLE IF NOT EXISTS expression_analysis_reports (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    overall_score INTEGER NOT NULL,
    confidence_level VARCHAR(20) NOT NULL,
    confidence_score INTEGER NOT NULL,
    modality_coverage JSONB NOT NULL,
    metrics JSONB NOT NULL,
    dimension_scores JSONB NOT NULL,
    evidence_summary JSONB NOT NULL,
    risk_flags JSONB NOT NULL,
    narrative_summary TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Keep exactly one profile binding row per interview
CREATE UNIQUE INDEX IF NOT EXISTS uq_interview_profiles_interview_id
    ON interview_profiles(interview_id);

-- Runtime indexes
CREATE INDEX IF NOT EXISTS idx_messages_interview_id ON messages(interview_id);
CREATE INDEX IF NOT EXISTS idx_messages_parent_id ON messages(parent_id);
CREATE INDEX IF NOT EXISTS idx_messages_branch_id ON messages(branch_id);
CREATE INDEX IF NOT EXISTS idx_messages_is_active ON messages(is_active);

CREATE INDEX IF NOT EXISTS idx_interviews_status ON interviews(status);
CREATE INDEX IF NOT EXISTS idx_interviews_current_stage ON interviews(current_stage);
CREATE INDEX IF NOT EXISTS idx_interviews_current_message_id ON interviews(current_message_id);

CREATE INDEX IF NOT EXISTS idx_snapshots_interview_id ON interview_snapshots(interview_id);

CREATE INDEX IF NOT EXISTS idx_profile_plugins_type ON profile_plugins(type);
CREATE INDEX IF NOT EXISTS idx_profile_plugins_plugin_id ON profile_plugins(plugin_id);

CREATE INDEX IF NOT EXISTS idx_interview_profiles_interview_id ON interview_profiles(interview_id);

CREATE INDEX IF NOT EXISTS idx_tool_invocations_interview_id ON tool_invocations(interview_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_trace_id ON tool_invocations(trace_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_stage_tool ON tool_invocations(stage, tool_name);

CREATE INDEX IF NOT EXISTS idx_interview_tool_contexts_interview_id ON interview_tool_contexts(interview_id);
CREATE INDEX IF NOT EXISTS idx_interview_tool_contexts_stage_tool ON interview_tool_contexts(stage, tool_name);

CREATE INDEX IF NOT EXISTS idx_expression_feature_segments_interview_id
    ON expression_feature_segments(interview_id);
CREATE INDEX IF NOT EXISTS idx_expression_feature_segments_type
    ON expression_feature_segments(interview_id, feature_type);

CREATE INDEX IF NOT EXISTS idx_expression_analysis_reports_interview_id
    ON expression_analysis_reports(interview_id);

COMMIT;
