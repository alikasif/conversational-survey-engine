-- Conversational Survey Engine — Database Schema
-- SQLite DDL

CREATE TABLE surveys (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    context TEXT NOT NULL,
    goal TEXT NOT NULL,
    constraints TEXT NOT NULL DEFAULT '[]',
    max_questions INTEGER NOT NULL DEFAULT 10,
    completion_criteria TEXT NOT NULL DEFAULT '',
    goal_coverage_threshold REAL NOT NULL DEFAULT 0.85,
    context_similarity_threshold REAL NOT NULL DEFAULT 0.7,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    participant_name TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    survey_id TEXT NOT NULL REFERENCES surveys(id),
    user_id TEXT NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'active',
    completion_reason TEXT,
    question_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX idx_sessions_survey_id ON sessions(survey_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_survey_user ON sessions(survey_id, user_id);

CREATE TABLE responses (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    survey_id TEXT NOT NULL REFERENCES surveys(id),
    user_id TEXT NOT NULL REFERENCES users(id),
    question_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    question_number INTEGER NOT NULL,
    question_embedding TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_responses_session_id ON responses(session_id);
CREATE INDEX idx_responses_survey_id ON responses(survey_id);
CREATE INDEX idx_responses_user_id ON responses(user_id);
CREATE INDEX idx_responses_survey_user ON responses(survey_id, user_id);
