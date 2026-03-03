# Architecture

System architecture for the Conversational Survey Engine.

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Frontend (React)                            │
│        Admin Dashboard  |  Participant Survey  |  Landing Page       │
└──────────────────┬───────────────────────────────────────────────────┘
                   │  HTTP (fetch)
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     Backend API (FastAPI)                             │
│  /health  |  /api/v1/admin/surveys/*  |  /api/v1/surveys/*/sessions  │
├──────────────────────────────────────────────────────────────────────┤
│  Services Layer                                                      │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────┐  │
│  │  survey_service  │ │  session_service │ │  question_service    │  │
│  └─────────────────┘ └──────────────────┘ └──────────┬───────────┘  │
│                                                       │              │
│  Agent Orchestrator ──────────────────────────────────┤              │
│  ┌─────────────────────────┐  ┌───────────────────────┴──────────┐  │
│  │  Generator Agent         │  │  Question Validator              │  │
│  │  (OpenAI Agent SDK +     │  │  (Embeddings + Rule-based)       │  │
│  │   Gemini via LiteLLM)    │  │                                  │  │
│  └─────────────────────────┘  └──────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  Repository Layer                                                    │
│  survey_repo  |  session_repo  |  response_repo                      │
└──────────────────┬───────────────────────────────────────────────────┘
                   │  SQLAlchemy (async)
                   ▼
        ┌─────────────────────┐
        │  SQLite (aiosqlite) │
        │  data/cse.db        │
        └─────────────────────┘
```

---

## Components

### Frontend (React + TypeScript + Vite)

| Concern | Detail |
|---------|--------|
| Framework | React 18 with React Router v6 |
| Styling | Tailwind CSS |
| Build | Vite 6 |
| Key pages | `AdminDashboard`, `SurveyCreator`, `SurveyDetail`, `ParticipantLanding`, `ParticipantSurvey`, `SurveyComplete` |
| API layer | `src/services/api.ts` — thin fetch wrapper targeting `/api/v1` |

### Backend API (FastAPI)

| Concern | Detail |
|---------|--------|
| Framework | FastAPI with async support |
| Server | Uvicorn |
| Routers | `health` (GET /health), `admin` (CRUD under `/api/v1/admin/surveys`), `participant` (session lifecycle under `/api/v1/surveys/{id}/sessions`) |
| Middleware | CORS configured from `CORS_ORIGINS` env var |
| Lifespan | DB tables created on startup via `asynccontextmanager` |

### Agent Orchestrator (`question_service`)

The orchestrator sits in `backend/app/services/question_service.py`. For each turn it:

1. Checks if `max_questions` has been reached.
2. Estimates **goal coverage** using embedding similarity.
3. Calls the **Generator Agent** to produce a candidate question.
4. Returns the question payload (or completes the session).

### Generator Agent

| Concern | Detail |
|---------|--------|
| Location | `backend/app/agents/generator_agent.py` |
| SDK | OpenAI Agent SDK (`agents` package) |
| Model | `gemini/gemini-2.0-flash` via LiteLLM adapter |
| System prompt | Expert survey researcher rules (single question, no leading, no compound, stay on-topic) |
| Retry loop | Up to 3 attempts; on each failure the validator rejection reason is fed back into the prompt |
| Fallback | If all retries fail a generic fallback question is returned |

### Question Validator

| Concern | Detail |
|---------|--------|
| Location | `backend/app/agents/validator.py` |
| Embedding model | `gemini/text-embedding-004` via LiteLLM |
| Rule-based checks | Compound question detection (multiple `?`, pattern matching), Leading question detection (regex patterns) |
| Embedding checks | **Redundancy** — cosine similarity against all prior questions (threshold default 0.85), **Goal alignment** — cosine similarity against survey goal (threshold default 0.3) |
| Goal coverage | Combines all Q&A text, embeds it, and compares to goal embedding |

### Database (SQLite)

SQLite via `aiosqlite` with SQLAlchemy async ORM. WAL mode and `busy_timeout=5000` are set on connect. Foreign keys are enforced.

---

## Data Flow: Question Generation

The end-to-end flow when a participant answers a question:

```
1. Admin creates survey
   POST /api/v1/admin/surveys  →  Survey stored in DB

2. Participant starts session
   POST /api/v1/surveys/{survey_id}/sessions
     → session_service.create_session()
       → Creates User + Session rows
       → question_service.generate_next_question()
         → Checks max_questions → Checks goal_coverage
         → generator_agent.generate_question()
           → Builds prompt with context, goal, constraints, history
           → Runner.run(agent, input=prompt)
           → Gemini generates candidate question
           → validator.validate(candidate, survey, history)
             → check_compound_question (rule-based)
             → check_leading_question (rule-based)
             → check_redundancy (embedding similarity)
             → check_goal_alignment (embedding similarity)
           → If invalid, retry with rejection feedback (up to 3×)
         → Returns QuestionPayload
     → Returns SessionResponse with first question

3. Participant submits answer
   POST /api/v1/surveys/{survey_id}/sessions/{session_id}/respond
     → question_service.process_answer()
       → Stores Response row
       → generate_next_question() (same flow as step 2)
       → Returns NextQuestionResponse
         OR completes session if stopping condition met

4. Session ends when:
   - max_questions reached
   - goal_coverage_threshold met
   - Participant exits early (POST .../exit)
```

---

## Technology Choices

| Technology | Rationale |
|------------|-----------|
| **FastAPI** | Native async support, automatic OpenAPI docs, Pydantic validation |
| **SQLAlchemy 2 (async)** | Mature async ORM; easy swap to PostgreSQL later |
| **SQLite + aiosqlite** | Zero-config for development; WAL mode for concurrent reads |
| **OpenAI Agent SDK** | Structured agent framework with tool support and model swapping |
| **LiteLLM** | Unified interface to 100+ LLM providers; currently wired to Gemini |
| **Gemini 2.0 Flash** | Fast, cost-effective generation for conversational questions |
| **Gemini text-embedding-004** | High-quality embeddings for redundancy and goal alignment checks |
| **React + Vite** | Fast dev experience, modern tooling, broad ecosystem |
| **Tailwind CSS** | Utility-first CSS for rapid UI prototyping |

---

## Database Design

Four tables with the following relationships:

```
surveys 1──────┐
               ├──< sessions ──< responses
users 1────────┘
```

### `surveys`

Core configuration for each survey: title, context, goal, constraints (JSON array stored as TEXT), thresholds, and limits.

### `users`

Lightweight participant record. Created per session with optional `participant_name` and a JSON `metadata` column.

### `sessions`

Tracks participant progress: links to survey + user, status (`active` / `completed` / `exited`), completion reason, and question count.

### `responses`

Individual Q&A pairs: question text, answer text, question number, and optional embedding (TEXT column for future use).

All IDs are UUIDv4 stored as TEXT. Timestamps are ISO 8601 strings in UTC.

See [database/schema.sql](../database/schema.sql) for the full DDL.
