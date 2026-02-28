# Database Schema

## Overview

The Conversational Survey Engine uses SQLite as its database, accessed asynchronously via `aiosqlite` and `SQLAlchemy 2.0`. The database is stored at `data/cse.db`.

## Tables

### `surveys`
Stores survey configurations created by admins.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID identifier |
| `title` | TEXT | NOT NULL | Survey title |
| `context` | TEXT | NOT NULL | Background context for the AI agent |
| `goal` | TEXT | NOT NULL | Research goal/objective |
| `constraints` | TEXT | NOT NULL, DEFAULT '[]' | JSON array of constraint strings |
| `max_questions` | INTEGER | NOT NULL, DEFAULT 10 | Maximum questions per session |
| `completion_criteria` | TEXT | NOT NULL, DEFAULT '' | Natural language completion criteria |
| `goal_coverage_threshold` | REAL | NOT NULL, DEFAULT 0.85 | Embedding similarity threshold for goal coverage |
| `context_similarity_threshold` | REAL | NOT NULL, DEFAULT 0.7 | Threshold for context relevance checks |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT 1 | Soft delete flag |
| `created_at` | TEXT | NOT NULL | ISO 8601 timestamp |
| `updated_at` | TEXT | NOT NULL | ISO 8601 timestamp |

### `users`
Stores participant information (anonymous-friendly).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID identifier |
| `participant_name` | TEXT | NULLABLE | Optional display name |
| `metadata` | TEXT | DEFAULT '{}' | JSON metadata (source, etc.) |
| `created_at` | TEXT | NOT NULL | ISO 8601 timestamp |

### `sessions`
Tracks survey sessions between a user and a survey.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID identifier |
| `survey_id` | TEXT | NOT NULL, FK → surveys(id) | Associated survey |
| `user_id` | TEXT | NOT NULL, FK → users(id) | Participant |
| `status` | TEXT | NOT NULL, DEFAULT 'active' | One of: active, completed, exited |
| `completion_reason` | TEXT | NULLABLE | Why session ended |
| `question_count` | INTEGER | NOT NULL, DEFAULT 0 | Questions asked so far |
| `created_at` | TEXT | NOT NULL | ISO 8601 timestamp |
| `completed_at` | TEXT | NULLABLE | When session ended |

**Indexes:**
- `idx_sessions_survey_id` — on `survey_id`
- `idx_sessions_user_id` — on `user_id`
- `idx_sessions_survey_user` — composite on `(survey_id, user_id)`

### `responses`
Stores individual question-answer pairs.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID identifier |
| `session_id` | TEXT | NOT NULL, FK → sessions(id) | Parent session |
| `survey_id` | TEXT | NOT NULL, FK → surveys(id) | Associated survey |
| `user_id` | TEXT | NOT NULL, FK → users(id) | Participant |
| `question_id` | TEXT | NOT NULL | Unique question identifier |
| `question_text` | TEXT | NOT NULL | The generated question |
| `answer_text` | TEXT | NOT NULL | Participant's answer |
| `question_number` | INTEGER | NOT NULL | Sequence number in session |
| `question_embedding` | TEXT | NULLABLE | Cached embedding vector (JSON) |
| `created_at` | TEXT | NOT NULL | ISO 8601 timestamp |

**Indexes:**
- `idx_responses_session_id` — on `session_id`
- `idx_responses_survey_id` — on `survey_id`
- `idx_responses_user_id` — on `user_id`
- `idx_responses_survey_user` — composite on `(survey_id, user_id)`

## Configuration

- **WAL mode** enabled for concurrent read access during writes
- **busy_timeout=5000** to handle writer contention
- **Foreign keys** enforced via `PRAGMA foreign_keys = ON`

## Migrations

Managed via Alembic. See `backend/alembic/` for migration scripts.

```bash
# Run migrations
cd backend
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

## Seed Data

Development seed data is in `database/seed.sql`. To load:

```bash
sqlite3 data/cse.db < database/seed.sql
```
