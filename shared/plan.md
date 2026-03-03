# Project Name: conversational_survey_engine

## Branch: `feature/devops-migration`

---

## 1. Overview - DB Migration, Microservice Split & K8s Deployment

### Problem
The current Conversational Survey Engine runs as a monolithic FastAPI app backed by SQLite. This blocks production deployment (SQLite is single-writer, no horizontal scaling) and makes it impossible to independently scale the compute-heavy LLM operations.

### Solution
A four-phase migration:
1. **Database Migration** - SQLite to NeonDB PostgreSQL. Dual-dialect support for dev/test.
2. **Microservice Split** - Extract LLM agent logic into a standalone llm-service FastAPI app. Backend calls it via HTTP.
3. **Containerization** - Dockerfiles for backend, llm-service, and frontend (nginx). Docker Compose for local dev.
4. **Kubernetes Deployment** - K8s manifests (namespace, configmap, secrets, deployments, services, migration job) + deploy script.

### Key Design Decisions
- **NeonDB as managed PostgreSQL** - No self-hosted DB container. NeonDB URL already provisioned.
- **asyncpg driver** - Replaces aiosqlite for PostgreSQL. NeonDB requires ssl=require (not sslmode). channel_binding=require is NOT supported by asyncpg and must be stripped.
- **Dual-dialect database.py** - SQLite pragmas applied only when dialect is sqlite. Tests continue using in-memory SQLite for speed.
- **LLM service boundary** - All LLM calls (question generation, validation, guardrails, preset generation) extracted to llm-service/. Backend uses an httpx client. This enables independent scaling of GPU/LLM-heavy work.
- **Backend stays monolithic otherwise** - Admin + participant APIs remain in one backend service. Splitting them is deferred to a future iteration.
- **Frontend via nginx** - Vite build served by nginx. API proxied to backend via nginx reverse proxy.
- **Schema reconciliation first** - Migration 003 fixes drift: add answer_flags to responses, drop context_similarity_threshold from surveys, drop question_embedding from responses.
- **K8s manifests are templates** - Secrets use placeholder values. Actual values injected at deploy time.

---

## 2. NeonDB Connection Details

- **Console**: https://console.neon.tech/app/projects/fancy-queen-31793093/branches/br-curly-mouse-adntl23v/tables?database=neondb
- **Raw URL**: postgresql://neondb_owner:npg_yWTbwc2E8vIO@ep-wandering-king-ad37hpwu-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
- **asyncpg URL**: postgresql+asyncpg://neondb_owner:npg_yWTbwc2E8vIO@ep-wandering-king-ad37hpwu-pooler.c-2.us-east-1.aws.neon.tech/neondb?ssl=require
  - sslmode=require becomes ssl=require
  - channel_binding=require is REMOVED (not supported by asyncpg)

---

## 3. Schema Drift - Migration 003

| Issue | Table | Column | In ORM | In Migration | Action |
|-------|-------|--------|--------|-------------|--------|
| Missing column | responses | answer_flags | YES (Text, nullable) | NO | ADD |
| Extra column | surveys | context_similarity_threshold | NO | YES (migration 001) | DROP |
| Extra column | responses | question_embedding | NO | YES (migration 001) | DROP |

---

## 4. Files Requiring PostgreSQL Changes

| File | Current SQLite-specific code | Required change |
|------|------------------------------|----------------|
| backend/app/core/database.py | PRAGMA listener, connect_args timeout, os.makedirs data | Dialect detection: apply pragmas only for SQLite, remove hardcoded connect_args, conditional data dir |
| backend/app/core/config.py | DATABASE_URL default sqlite+aiosqlite:///./data/cse.db | Keep as fallback for local dev |
| backend/app/main.py | os.makedirs data in lifespan | Conditional: only for SQLite |
| backend/alembic.ini | sqlalchemy.url = sqlite+aiosqlite:///./data/cse.db | Use env override |
| backend/alembic/env.py | render_as_batch=True (SQLite workaround) | Conditional: batch mode only for SQLite |
| backend/pyproject.toml | aiosqlite only | ADD asyncpg>=0.30.0 |

---

## 5. New Project Structure (post-migration)

`
conversational-survey-engine/
  backend/                    # Main API service (admin + participant)
    Dockerfile
    app/
      clients/                # NEW: HTTP clients for inter-service calls
        llm_client.py         # httpx client to llm-service
      agents/                 # KEPT as fallback / shared types
      api/
      core/
      models/
      repositories/
      schemas/
      services/
    alembic/
  llm-service/                # NEW: LLM microservice
    Dockerfile
    pyproject.toml
    app/
      main.py
      config.py
      routes.py               # HTTP endpoints for LLM operations
      agents/                 # Moved from backend/app/agents/
        generator_agent.py
        validator.py
        answer_guardrails.py
        prompts.py
  frontend/                   # React SPA
    Dockerfile
    nginx.conf
  k8s/                        # NEW: Kubernetes manifests
    namespace.yaml
    configmap.yaml
    secrets.yaml              # Template - values injected at deploy
    backend-deployment.yaml
    backend-service.yaml
    llm-service-deployment.yaml
    llm-service-service.yaml
    frontend-deployment.yaml
    frontend-service.yaml
    migration-job.yaml
  docker-compose.yml          # NEW: Local dev orchestration
  docker-compose.dev.yml      # NEW: Dev overrides
  deploy.ps1                  # NEW: K8s deployment script
  .env.example                # UPDATED with new vars
`

---

## 6. Phase Summary

### Phase 1: Schema & DB Migration (Foundation)
- Migration 003 to fix schema drift
- PostgreSQL dual-dialect support across all backend files
- Update pyproject.toml with asyncpg

### Phase 2: Microservice Refactor
- Extract llm-service/ with its own FastAPI app and LLM agent logic
- Create HTTP client in backend to call llm-service
- Backend agent imports replaced with HTTP calls via httpx

### Phase 3: Containerization
- Dockerfiles for backend, llm-service, frontend
- nginx.conf for frontend (static + API proxy)
- docker-compose.yml for local multi-service development

### Phase 4: K8s & Deployment
- Full K8s manifests (namespace, configmap, secrets, deployments, services)
- Alembic migration job for pre-deploy schema sync
- deploy.ps1 PowerShell deployment script

### Phase 5: Review & Verification
- Backend code review
- Architecture review
- E2E test verification (all 28 scenarios must pass)
- Documentation updates

---

## 7. LLM Service Internal API Contract (port 8001)

POST /generate-question
  Request: { survey: {...}, history: [...], question_number: int }
  Response: { question_text: str, question_id: str }

POST /validate-question
  Request: { question: str, survey_context: str }
  Response: { is_valid: bool, issues: [...] }

POST /check-guardrails
  Request: { answer: str, question: str }
  Response: { is_valid: bool, flags: [...], rejection_reason: str|null }

POST /generate-preset-questions
  Request: { survey: {...}, count: int }
  Response: { questions: [{ question_number: int, question_id: str, text: str }] }

GET /health
  Response: { status: healthy, model: str }

---

## 8. Agent Assignments

| Agent | Tasks |
|-------|-------|
| project_structure | Scaffold new directories and files |
| python_coder | Migration 003, PostgreSQL dual-dialect support |
| python_refactorer | Extract LLM service, refactor backend to use HTTP client |
| devops | Dockerfiles, nginx, docker-compose, K8s manifests, deploy script |
| backend_reviewer | Review all backend + LLM service code changes |
| architecture_reviewer | Review microservice boundaries, K8s topology |
| e2e_tester | Verify all 28 scenarios pass post-refactor |
| documentation | Update architecture, setup, deployment docs |
| github | Commit and push to feature/devops-migration |

---

## 9. Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| NeonDB rejects connections without channel_binding | Test connection string before full migration. NeonDB pooler supports ssl=require without channel_binding. |
| Tests break with PG-specific SQL | Keep test suite on in-memory SQLite. Accept divergence risk for now. |
| LLM service HTTP overhead adds latency | LLM calls already take 2-10s. HTTP overhead (~5ms) is negligible. |
| Microservice split breaks existing tests | Run existing pytest suite after refactor. Backend tests mock llm_client. |
| Boolean defaults server_default 1 on PG | PG accepts 1 for boolean. Non-idiomatic but functional. Tech debt tracked. |
