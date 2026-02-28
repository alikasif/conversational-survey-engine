# Project Name: conversational_survey_engine

## Branch: `feature/cse-mvp`

---

## 1. Overview

Build a **Conversational Survey Engine (CSE)** — a goal-constrained, agentic conversational research engine that dynamically generates survey questions in real time based on admin-defined context/goal and participant responses.

### Tech Stack
- **Backend:** Python 3.11+, FastAPI, OpenAI Agent SDK, LiteLLM, Gemini
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
- **Database:** SQLite (async via aiosqlite, SQLAlchemy 2.0)
- **Testing:** pytest + httpx (backend), Vitest (frontend)

---

## 2. Modules

### Module 1: Database (`database/`)
- SQLite schema (surveys, users, sessions, responses)
- Alembic migrations
- Seed data for development
- Indexes on `survey_id`, `user_id`

### Module 2: Backend (`backend/`)
- FastAPI REST API with CORS
- Pydantic schemas for all request/response models
- SQLAlchemy async ORM models
- Repository layer (data access)
- Service layer (business logic)
- Agent orchestration: Generator Agent (OpenAI Agent SDK + LiteLLM → Gemini)
- Validator layer: embedding similarity, goal alignment, redundancy detection, drift detection, max-question enforcement
- Stopping conditions: goal coverage, max questions, completion criteria, user exit

### Module 3: Frontend (`frontend/`)
- React SPA with React Router v6
- Admin panel: create/manage surveys, view responses/stats
- Participant UI: chat-style Q&A interface
- API client consuming backend endpoints
- Tailwind CSS styling

### Module 4: Documentation (`docs/`)
- Architecture overview
- API reference
- Setup guide
- Admin & participant guides

---

## 3. API Contracts

### Base URL: `/api/v1`

### 3.1 Health
| Method | Path | Response |
|--------|------|----------|
| `GET` | `/health` | `{ "status": "ok", "version": "string" }` |

### 3.2 Admin — Surveys
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/surveys` | Create survey |
| `GET` | `/admin/surveys` | List surveys |
| `GET` | `/admin/surveys/{survey_id}` | Get survey detail |
| `PUT` | `/admin/surveys/{survey_id}` | Update survey |
| `DELETE` | `/admin/surveys/{survey_id}` | Delete survey |
| `GET` | `/admin/surveys/{survey_id}/responses` | View responses |
| `GET` | `/admin/surveys/{survey_id}/stats` | Survey stats |

### 3.3 Participant — Sessions
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/surveys/{survey_id}/sessions` | Start session (returns first question) |
| `POST` | `/surveys/{survey_id}/sessions/{session_id}/respond` | Submit answer, get next question |
| `GET` | `/surveys/{survey_id}/sessions/{session_id}` | Get session state |
| `POST` | `/surveys/{survey_id}/sessions/{session_id}/exit` | Exit early |

### 3.4 Schema Definitions

```typescript
// Requests
interface CreateSurveyRequest {
  title: string;
  context: string;
  goal: string;
  constraints: string[];
  max_questions: number;
  completion_criteria: string;
  goal_coverage_threshold?: number;    // 0.0–1.0, default 0.85
  context_similarity_threshold?: number; // 0.0–1.0, default 0.7
}

interface UpdateSurveyRequest {
  title?: string; context?: string; goal?: string;
  constraints?: string[]; max_questions?: number;
  completion_criteria?: string;
  goal_coverage_threshold?: number;
  context_similarity_threshold?: number;
}

interface CreateSessionRequest {
  participant_name?: string;
  metadata?: Record<string, string>;
}

interface SubmitAnswerRequest {
  answer: string;
}

// Responses
interface SurveyResponse {
  id: string; title: string; context: string; goal: string;
  constraints: string[]; max_questions: number;
  completion_criteria: string;
  goal_coverage_threshold: number;
  context_similarity_threshold: number;
  is_active: boolean;
  created_at: string; updated_at: string;
}

interface SurveyListResponse {
  surveys: SurveyResponse[]; total: number; skip: number; limit: number;
}

interface SurveyDetailResponse extends SurveyResponse {
  total_sessions: number; completed_sessions: number;
  avg_questions_per_session: number;
}

interface SurveyStatsResponse {
  survey_id: string; total_sessions: number;
  completed_sessions: number; abandoned_sessions: number;
  avg_questions_per_session: number;
  avg_completion_time_seconds: number;
  top_themes: string[];
}

interface SessionResponse {
  session_id: string; user_id: string; survey_id: string;
  status: "active" | "completed" | "exited";
  current_question: QuestionPayload;
  question_number: number; max_questions: number;
  created_at: string;
}

interface QuestionPayload {
  question_id: string; text: string; question_number: number;
}

interface NextQuestionResponse {
  session_id: string;
  status: "active" | "completed";
  question?: QuestionPayload;
  completion_reason?: string;
  question_number: number; max_questions: number;
}

interface SessionDetailResponse {
  session_id: string; user_id: string; survey_id: string;
  status: "active" | "completed" | "exited";
  conversation: ConversationEntry[];
  question_count: number;
  created_at: string; completed_at?: string;
}

interface ConversationEntry {
  question_id: string; question_text: string;
  answer_text: string; question_number: number;
  answered_at: string;
}

interface SessionCompleteResponse {
  session_id: string; status: "exited";
  question_count: number; message: string;
}

interface ResponseListResponse {
  responses: SessionDetailResponse[];
  total: number; skip: number; limit: number;
}
```

---

## 4. Technical Decisions

### 4.1 Agent SDK + LiteLLM + Gemini
- Use `openai-agents` SDK with `LitellmModel(model="gemini/gemini-2.0-flash")`.
- Generator Agent: pure text generation, no tools. Receives survey context + goal + conversation history → returns single question.
- Validator: NOT an LLM agent. Python service class with embedding checks + rule-based heuristics.
- Retry loop: max 3 retries with validator feedback. Fallback generic question on exhaustion.

### 4.2 Embedding
- Use `litellm.embedding()` with `model="gemini/text-embedding-004"`.
- Cache embeddings in `responses.question_embedding` column.
- Cosine similarity for redundancy (>0.85 = redundant) and drift (<0.3 vs goal = drifting).

### 4.3 SQLite + Async SQLAlchemy
- `sqlite+aiosqlite:///./data/cse.db`
- WAL mode for concurrent reads during writes.
- `busy_timeout=5000` for writer contention.
- Atomic per-response writes via `session.begin()`.

### 4.4 Database Schema
See `database/schema.sql` for full DDL. Tables: `surveys`, `users`, `sessions`, `responses`.
Key indexes: composite `(survey_id, user_id)` on sessions and responses.

### 4.5 Session Management
- No auth for participants–`session_id` (UUID) is the token.
- Admin auth deferred to v2.
- Sessions expire after 24h inactivity.

### 4.6 CORS
- Allow `http://localhost:5173` (Vite dev) + production origin.

### 4.7 Frontend
- React 18 + TypeScript + Vite + Tailwind CSS
- React Router v6: `/admin`, `/admin/surveys/new`, `/admin/surveys/:id`, `/survey/:surveyId`, `/survey/:surveyId/session/:sessionId`, `/survey/:surveyId/complete`
- API client: `fetch`-based with `VITE_API_BASE_URL` env var.

### 4.8 Environment Variables
```env
# Backend
GEMINI_API_KEY=...
DATABASE_URL=sqlite+aiosqlite:///./data/cse.db
CORS_ORIGINS=["http://localhost:5173"]
LOG_LEVEL=info

# Frontend
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 4.9 Stopping Conditions
1. Store Q/A pair after each answer.
2. Run goal coverage estimation (embedding aggregate).
3. If coverage ≥ threshold → complete ("goal_coverage_met").
4. If question_count ≥ max_questions → complete ("max_questions_reached").
5. LLM-evaluate completion_criteria → complete ("completion_criteria_met").
6. User POST to `/exit` → complete ("user_exited").
7. Otherwise → generate next question.

---

## 5. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| LiteLLM + Agent SDK compatibility | Test integration early; pin versions |
| Gemini embedding rate limits | Cache embeddings; abstract behind protocol |
| Goal coverage estimation accuracy | Combine embedding + LLM evaluation; tune threshold |
| Validator false positives | Tunable thresholds; 3 retries; log rejections |
| SQLite concurrency under load | WAL mode; busy_timeout; document PostgreSQL migration path |
| Frontend-backend contract drift | Export openapi.json to shared/api/ |

---

## 6. Agent Assignments

| Agent | Module | Scope |
|-------|--------|-------|
| database | `database/` | Schema DDL, migrations, seed data |
| python-coder | `backend/` | FastAPI app, routes, services, repos, agents, config |
| frontend | `frontend/` | React SPA, admin + participant UI, API client |
| python-test | `backend/tests/` | Unit + integration tests |
| frontend-test | `frontend/` | Component + page tests |
| database-test | `database/` | Migration + query tests |
| backend-reviewer | `backend/` | Code quality review |
| frontend-reviewer | `frontend/` | UI/UX quality review |
| database-reviewer | `database/` | Schema design review |
| architecture-reviewer | cross-cutting | Module boundary + contract review |
| documentation | `docs/` | All documentation |
| github | repo | Branch, commits, push |
