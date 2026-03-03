# Architecture

System architecture for the Conversational Survey Engine.

---

## System Overview

The system follows a **microservice architecture** with three independently deployable services:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Frontend (React + nginx)                            │
│        Admin Dashboard  |  Participant Survey  |  Landing Page          │
│                         nginx :80                                       │
│        /            → static SPA files                                  │
│        /api/*       → reverse proxy to backend:8000                     │
│        /health      → reverse proxy to backend:8000                     │
└──────────────────┬──────────────────────────────────────────────────────┘
                   │  HTTP (nginx reverse proxy)
                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Backend API (FastAPI) :8000                          │
│  /health  |  /api/v1/admin/surveys/*  |  /api/v1/surveys/*/sessions     │
├─────────────────────────────────────────────────────────────────────────┤
│  Services Layer                                                         │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐ │
│  │  survey_service  │ │  session_service │ │  question_service        │ │
│  └─────────────────┘ └──────────────────┘ └──────────┬───────────────┘ │
│                                                       │                 │
│  LLM Client (httpx) ─────────────────────────────────┘                 │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  backend/app/clients/llm_client.py                                │ │
│  │  HTTP POST to llm-service for all LLM operations                  │ │
│  │  Retry: 3 attempts, exponential backoff, 120s timeout             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│  Repository Layer                                                       │
│  survey_repo  |  session_repo  |  response_repo                         │
└──────────────────┬──────────────────────────────────────────────────────┘
                   │ SQLAlchemy (async)              │ HTTP (httpx)
                   ▼                                 ▼
  ┌──────────────────────────┐    ┌───────────────────────────────────────┐
  │  Database                │    │   LLM Service (FastAPI) :8001         │
  │  ┌────────────────────┐  │    ├───────────────────────────────────────┤
  │  │ NeonDB PostgreSQL  │  │    │  /generate-question                   │
  │  │ (production)       │  │    │  /validate-question                   │
  │  │ asyncpg + ssl      │  │    │  /check-guardrails                    │
  │  ├────────────────────┤  │    │  /generate-preset-questions            │
  │  │ SQLite (local dev) │  │    │  /health                              │
  │  │ aiosqlite          │  │    ├───────────────────────────────────────┤
  │  └────────────────────┘  │    │  Agents                               │
  └──────────────────────────┘    │  ┌─────────────────┐ ┌─────────────┐ │
                                  │  │ Generator Agent  │ │  Validator   │ │
                                  │  │ (OpenAI Agent SDK│ │  (Rules +   │ │
                                  │  │  + Gemini/LiteLLM│ │  Embeddings)│ │
                                  │  └─────────────────┘ └─────────────┘ │
                                  │  ┌─────────────────┐                 │
                                  │  │ Answer Guardrails│                 │
                                  │  └─────────────────┘                 │
                                  └───────────────────────────────────────┘
```

### Service Summary

| Service | Port | Responsibility | Stateful? |
|---------|------|---------------|-----------|
| **Frontend** | 80 | React SPA + nginx reverse proxy | No |
| **Backend** | 8000 | REST API, business logic, database access | Yes (DB) |
| **LLM Service** | 8001 | AI question generation, validation, guardrails | No |

### Inter-Service Communication

| From | To | Protocol | Path |
|------|----|----------|------|
| Browser | Frontend (nginx) | HTTPS/HTTP | `/*` |
| Frontend (nginx) | Backend | HTTP | `/api/*`, `/health` → `backend:8000` |
| Backend | LLM Service | HTTP (httpx) | `http://llm-service:8001/*` |
| Backend | Database | TCP | PostgreSQL (asyncpg) or SQLite (aiosqlite) |

---

## Components

### Frontend (React + TypeScript + Vite + nginx)

| Concern | Detail |
|---------|--------|
| Framework | React 18 with React Router v6 |
| Styling | Tailwind CSS |
| Build | Vite 6, multi-stage Docker build |
| Serving | nginx:alpine — static files + reverse proxy |
| Key pages | `AdminDashboard`, `SurveyCreator`, `SurveyDetail`, `ParticipantLanding`, `ParticipantSurvey`, `SurveyComplete` |
| API layer | `src/services/api.ts` — thin fetch wrapper targeting `/api/v1` |
| Proxy | nginx forwards `/api/*` and `/health` to `backend:8000` |

### Backend API (FastAPI)

| Concern | Detail |
|---------|--------|
| Framework | FastAPI with async support |
| Server | Uvicorn |
| Routers | `health` (GET /health), `admin` (CRUD under `/api/v1/admin/surveys`), `participant` (session lifecycle under `/api/v1/surveys/{id}/sessions`) |
| Middleware | CORS configured from `CORS_ORIGINS` env var |
| Lifespan | DB tables created on startup via `asynccontextmanager` |
| LLM calls | Delegated to LLM Service via `LLMClient` (httpx), no direct LiteLLM dependency |
| Database | Dual-dialect: PostgreSQL (asyncpg) for production, SQLite (aiosqlite) for local dev/test |

### LLM Service (FastAPI)

The LLM Service is a stateless microservice that encapsulates all AI/LLM operations. It can be scaled independently from the backend.

| Concern | Detail |
|---------|--------|
| Framework | FastAPI |
| Server | Uvicorn on port 8001 |
| AI SDK | OpenAI Agent SDK (`agents` package) + LiteLLM |
| Models | `vertex_ai/gemini-2.0-flash` (generation), `gemini/gemini-2.0-flash` (validation) |
| Auth | Google service account (`GOOGLE_APPLICATION_CREDENTIALS`) for Vertex AI; `GEMINI_API_KEY` for Google AI |
| Endpoints | `/generate-question`, `/validate-question`, `/check-guardrails`, `/generate-preset-questions`, `/health` |

### Question Generation Pipeline (inside LLM Service)

The orchestrator in the backend calls the LLM service for each turn:

1. **Generator Agent** — Produces a candidate question using Gemini via the OpenAI Agent SDK with a system prompt enforcing survey research best practices (single question, no leading, no compound, stay on-topic). Retries up to 3 times, feeding validator rejection feedback back into the prompt.
2. **Question Validator** — Validates the candidate: compound question detection (rule-based), leading question detection (regex), redundancy check (embedding similarity against prior questions), goal alignment (embedding similarity against survey goal).
3. **Answer Guardrails** — Checks participant answers for gibberish, injection attempts, and off-topic responses.

### Database

| Environment | Driver | Connection |
|-------------|--------|------------|
| **Production** | `asyncpg` | NeonDB PostgreSQL with `ssl=require` |
| **Local dev** | `aiosqlite` | SQLite file at `data/cse.db` (WAL mode) |
| **Tests** | `aiosqlite` | In-memory SQLite (`sqlite+aiosqlite://`) |

The dual-dialect is handled in `backend/app/core/database.py`, which detects the dialect from `DATABASE_URL` and conditionally applies SQLite-specific PRAGMA listeners, connect args, and data directory creation.

Migrations are managed by **Alembic** with `render_as_batch=True` for SQLite compatibility.

---

## LLM Service API Contract (port 8001)

### POST /generate-question
```json
// Request
{ "survey_context": "...", "goal": "...", "constraints": "...",
  "conversation_history": [["Q1", "A1"], ...],
  "question_number": 2, "max_questions": 10,
  "goal_coverage_threshold": 0.85, "rejection_guardrail_hint": null }

// Response
{ "question_text": "How do you feel about...?", "question_id": "uuid" }
```

### POST /validate-question
```json
// Request
{ "question": "...", "survey_context": "...", "goal": "...",
  "conversation_history": [["Q1", "A1"], ...] }

// Response
{ "is_valid": true, "issues": [] }
```

### POST /check-guardrails
```json
// Request
{ "answer": "...", "question": "..." }

// Response
{ "is_valid": true, "flags": [], "rejection_reason": null }
```

### POST /generate-preset-questions
```json
// Request
{ "survey_context": "...", "goal": "...", "constraints": "...", "count": 5 }

// Response
{ "questions": [{ "question_number": 1, "question_id": "uuid", "text": "..." }, ...] }
```

### GET /health
```json
{ "status": "healthy", "service": "cse-llm-service", "model": "vertex_ai/gemini-2.0-flash" }
```

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
         → llm_client.generate_question()           ← HTTP to LLM Service
           → LLM Service: generator_agent.generate_question()
             → Builds prompt with context, goal, constraints, history
             → Runner.run(agent, input=prompt)
             → Gemini generates candidate question
             → validator.validate(candidate, survey, history)
               → check_compound_question (rule-based)
               → check_leading_question (rule-based)
               → check_redundancy (embedding similarity)
               → check_goal_alignment (embedding similarity)
             → If invalid, retry with rejection feedback (up to 3×)
           → Returns {question_text, question_id}     ← HTTP response
         → Returns QuestionPayload
     → Returns SessionResponse with first question

3. Participant submits answer
   POST /api/v1/surveys/{survey_id}/sessions/{session_id}/respond
     → llm_client.check_guardrails(answer)           ← HTTP to LLM Service
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
| **SQLAlchemy 2 (async)** | Mature async ORM; dual-dialect PostgreSQL/SQLite support |
| **NeonDB PostgreSQL** | Managed serverless PostgreSQL for production (asyncpg driver) |
| **SQLite + aiosqlite** | Zero-config for local development and tests; WAL mode for concurrent reads |
| **httpx** | Async HTTP client for backend → LLM service communication |
| **OpenAI Agent SDK** | Structured agent framework with tool support and model swapping |
| **LiteLLM** | Unified interface to 100+ LLM providers; currently wired to Gemini |
| **Gemini 2.0 Flash** | Fast, cost-effective generation for conversational questions |
| **Gemini text-embedding-004** | High-quality embeddings for redundancy and goal alignment checks |
| **React + Vite** | Fast dev experience, modern tooling, broad ecosystem |
| **Tailwind CSS** | Utility-first CSS for rapid UI prototyping |
| **nginx** | Static file serving + reverse proxy for the frontend container |
| **Docker** | Containerization for all three services; multi-stage builds |
| **Kubernetes** | Production orchestration with health checks, scaling, and rolling updates |
| **Alembic** | Database migrations with dual-dialect support (batch mode for SQLite) |

---

## Deployment Architecture

### Docker Compose (local development)

```
docker-compose.yml
├── backend       (build: ./backend, port 8000)
├── llm-service   (build: ./llm-service, port 8001)
└── frontend      (build: ./frontend, port 80, depends_on: backend)
```

Service discovery uses Docker Compose DNS: `http://llm-service:8001`, `http://backend:8000`.

### Kubernetes (production)

```
Namespace: cse
├── ConfigMap: cse-config (CORS_ORIGINS, LOG_LEVEL, LLM_SERVICE_URL)
├── Secret: cse-secrets (DATABASE_URL, GEMINI_API_KEY, GCP credentials)
├── Job: alembic-migrate (runs before deployments)
├── Deployment: backend (2 replicas, ClusterIP :8000)
├── Deployment: llm-service (2 replicas, ClusterIP :8001)
└── Deployment: frontend (2 replicas, LoadBalancer :80)
```

Service discovery uses K8s DNS: `http://llm-service.cse.svc.cluster.local:8001`.

See [deployment.md](deployment.md) for the full Kubernetes deployment guide.

---

## Database Design

Four tables with the following relationships:

```
surveys 1──────┐
               ├──< sessions ──< responses
users 1────────┘
```

### `surveys`

Core configuration for each survey: title, context, goal, constraints (JSON array stored as TEXT), thresholds, and limits. Supports `question_mode` (`dynamic` or `preset`) and optional `preset_questions` JSON column.

### `users`

Lightweight participant record. Created per session with optional `participant_name` and a JSON `metadata` column.

### `sessions`

Tracks participant progress: links to survey + user, status (`active` / `completed` / `exited`), completion reason, and question count.

### `responses`

Individual Q&A pairs: question text, answer text, question number, and optional `answer_flags` column for guardrail results.

All IDs are UUIDv4 stored as TEXT. Timestamps are ISO 8601 strings in UTC.

See [database/schema.sql](../database/schema.sql) for the full DDL.
