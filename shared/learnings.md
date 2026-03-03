# Learnings

### [2026-03-02] agent:lead | task:preset_questions_debug
**Problem:** Alembic migration 002 was never applied — `question_mode`, `preset_questions`, `preset_generated_at` columns missing from the DB.
**Root Cause:** DB was bootstrapped by SQLAlchemy `create_all()`, not Alembic. Alembic had no version table and didn't know the DB existed. Subagent tests used fresh in-memory DBs so the gap was invisible.
**Fix:** `alembic stamp 001` to mark existing state, then `alembic upgrade head` to apply migration 002.
**Lesson:** When transitioning from `create_all()` to Alembic, stamp the current state. Add a startup check that verifies pending migrations.

### [2026-03-02] agent:lead | task:preset_questions_debug
**Problem:** Relative DB path `sqlite+aiosqlite:///./data/cse.db` resolved to two different files depending on uvicorn's working directory, causing alternating schema errors.
**Root Cause:** Starting uvicorn from workspace root vs `backend/` produced `data/cse.db` (root) vs `backend/data/cse.db` — two separate databases with different schemas.
**Fix:** Always start uvicorn from `backend/` directory using `Push-Location` or `cd`.
**Lesson:** Use absolute paths for DATABASE_URL or log the resolved DB path at startup so drift is immediately visible.

### [2026-03-02] agent:lead | task:preset_questions_debug
**Problem:** Uvicorn `--reload` served stale code silently — new endpoints not visible despite being in the source.
**Root Cause:** File changes triggered reload from workspace root, which failed with `ModuleNotFoundError: No module named 'app'`. The old process kept serving stale code without surfacing the error to clients.
**Fix:** Start uvicorn without `--reload` or ensure it runs from `backend/` directory.
**Lesson:** After server restart, always verify routes via `GET /openapi.json`. Check server logs for silent reload failures.

### [2026-03-02] agent:lead | task:preset_questions_debug
**Problem:** `IntegrityError: NOT NULL constraint failed: surveys.context_similarity_threshold` on every INSERT.
**Root Cause:** Architecture cleanup removed `context_similarity_threshold` from the ORM model but never created an Alembic migration to drop it from the DB. Column was NOT NULL with no default.
**Fix:** `ALTER TABLE surveys DROP COLUMN context_similarity_threshold`.
**Lesson:** Every ORM model column removal must have a corresponding Alembic migration. Add a CI check comparing ORM models to actual DB schema.

### [2026-03-02] agent:lead | task:preset_questions_debug
**Problem:** All preset questions returned fallback text — every LLM call failed silently.
**Root Cause:** `.env` had `GEMINI_MODEL=gemini-3-pro-preview` (non-existent model) overriding the correct default `vertex_ai/gemini-2.0-flash`. Subagents only modified Python source, never validated `.env`.
**Fix:** Renamed to `GEMINI3_PRO_MODEL` in `.env` so it doesn't override the `GEMINI_MODEL` config key.
**Lesson:** Subagents must read and validate `.env` files. Log the resolved model name at startup. Consider failing fast instead of falling back to generic questions.

### [2026-03-02] agent:lead | task:preset_questions_debug
**Problem:** `401 Unauthorized — API keys are not supported by this API` when calling Vertex AI.
**Root Cause:** `get_model()` always passed `api_key` to `LitellmModel`. For `vertex_ai/` models, LiteLLM uses service account auth via `GOOGLE_APPLICATION_CREDENTIALS` — passing an api_key caused auth conflicts.
**Fix:** Updated `get_model()` to skip `api_key` when model starts with `vertex_ai/`.
**Lesson:** Different LiteLLM providers have different auth mechanisms. The model factory must be auth-aware. Test with the actual provider, not just mocked responses.

---

### [2026-03-03] agent:backend_reviewer + architecture_reviewer | task:13,14 — Code & Architecture Review

#### MAJOR Findings

**M1: Incomplete LLM extraction — backend still calls LiteLLM directly for goal coverage**
`backend/app/services/question_service.py` imports `QuestionValidator` from `backend/app/agents/validator.py`, which calls `litellm.acompletion()` directly for `estimate_goal_coverage()`. This means:
- Backend still depends on `litellm` and `openai-agents` (confirmed in `backend/pyproject.toml`)
- Backend still needs `GEMINI_VALIDATOR_MODEL` and API keys / service account credentials
- The LLM service has no `/estimate-coverage` endpoint
- The microservice boundary is leaky: question generation goes through HTTP to llm-service, but coverage estimation bypasses it

**Recommendation:** Add a `POST /estimate-coverage` endpoint to the LLM service, add a corresponding `estimate_goal_coverage()` method to `LLMClient`, and remove the direct litellm import from the backend. Then drop `litellm` and `openai-agents` from `backend/pyproject.toml`.

**M2: K8s manifest image names don't include registry prefix**
K8s deployment manifests use bare image names (e.g., `image: cse-backend:latest`) but `deploy.ps1` builds images with registry prefix (e.g., `$Registry/cse-backend:$Tag`). The deploy script never updates the image references in the manifests using `kubectl set image` or sed-style replacements.
**Impact:** Deployments will pull the wrong (local/missing) image in a real K8s cluster.
**Recommendation:** Either use `kubectl set image` in the deploy script after `kubectl apply`, or template the manifests with envsubst/kustomize.

#### MINOR Findings

**m1: Redundant `os.makedirs("data")` call**
Both `app/main.py` (lifespan) and `app/core/database.py` (`init_db()`) create the `data/` directory for SQLite. Harmless but duplicated logic.

**m2: LLM client creates a new `httpx.AsyncClient` per request**
`LLMClient._client()` instantiates a new `AsyncClient` on every call. This skips connection reuse/pooling. Acceptable for low-volume LLM calls but suboptimal at scale.
**Recommendation:** Consider a long-lived client created in an `async with` lifespan context.

**m3: Error message from LLM client may expose llm-service internals**
`LLMClient._request()` includes `e.response.text[:200]` in the RuntimeError for HTTPStatusError. If this propagates to the API response, it could leak LLM service internal error details. Currently the routes catch generic exceptions and return 500, so it's partially mitigated but not guaranteed.

**m4: Backend `/health` doesn't check downstream LLM service**
The health endpoint returns `{"status": "ok"}` without verifying llm-service connectivity. In K8s, the backend could appear healthy while the LLM service is down. Consider adding a `deep=true` query param option.

**m5: No PodDisruptionBudget or HorizontalPodAutoscaler**
K8s manifests have static 2 replicas with no PDB or HPA. Fine for initial deployment but should be added for production resilience.

**m6: Docker Compose `version: '3.8'` is deprecated**
Docker Compose V2 ignores the version field. Not a functional issue but a lint warning.

**m7: `CORS_ORIGINS='["*"]'` in backend Dockerfile ENV default**
The Dockerfile bakes in a wildcard CORS default. This is overridden at runtime but means a misconfigured deployment exposes open CORS. Lower risk since it's an internal API.

#### INFO Findings

**i1: Migration 003 is correct and well-structured.** Upgrade/downgrade are symmetrical. `batch_alter_table` used for DROP COLUMN (SQLite compat). `server_default` provided on restore.

**i2: Dual-dialect detection works correctly.** `_is_sqlite = settings.DATABASE_URL.startswith("sqlite")` correctly gates SQLite-specific PRAGMA listeners, connect_args, and data dir creation. No SQLite leaks to PostgreSQL path.

**i3: alembic `env.py` env-based URL override is correct.** `DATABASE_URL` env var properly overrides `alembic.ini` fallback. `render_as_batch` conditional on dialect.

**i4: LLM client retry logic is sound.** Exponential backoff (1s, 2s, 4s) with 3 retries for connection-level errors. Non-retryable HTTP errors (4xx, 5xx) fail immediately with descriptive message.

**i5: Service boundaries are correct for the extracted scope.** Backend handles DB access, llm-service is stateless. No circular dependencies. Frontend → Backend → LLM Service flow is one-directional.

**i6: K8s service discovery is correct.** ConfigMap sets `LLM_SERVICE_URL=http://llm-service.cse.svc.cluster.local:8001`. Docker Compose uses `http://llm-service:8001`. Both resolve correctly within their respective networks.

**i7: nginx proxy config is correct.** `proxy_pass http://backend:8000` matches Docker Compose/K8s service name. SPA routing with `try_files` fallback. 120s proxy_read_timeout suitable for LLM call latency.

**i8: Multi-stage Docker builds are efficient.** Builder stages install build deps, runtime stages copy only installed packages. Non-root users. Health checks in Dockerfiles. Backend properly installs `libpq-dev` (build) and `libpq5` (runtime) for asyncpg.

**i9: Secrets management is correct.** No secrets baked into images or code. K8s secrets.yaml uses REPLACE placeholders with clear warnings. Docker Compose passes env vars from host. GCP credentials volume-mounted in both Docker Compose and K8s.

**i10: Security measures are comprehensive.** Output leak detection in generator agent. XML-tagged participant answers in prompts. Injection pattern detection in guardrails. LLM service route handlers return generic error messages ("Failed to generate question") without leaking internals.

**i11: LLM service schemas are well-designed.** `history_tuples` property converts wire format (list-of-lists) to Python tuples. Proper defaults and Field descriptions. Union types for `constraints` (str | list) handle both formats.

**i12: Test infrastructure correctly mocks LLM calls.** `conftest.py` patches `llm_client.generate_question` and `validator.estimate_goal_coverage` with AsyncMock. Tests never hit real LLM service. In-memory SQLite used for DB isolation.

**i13: Failure mode when LLM service is down:** Backend retries 3× (total ~7s), then raises RuntimeError. API endpoints return 500. Docker Compose prevents backend from starting until llm-service is healthy. K8s has readiness probes but no startup dependency ordering — backend could receive traffic before llm-service is ready (mitigated by readiness probe failing on first LLM call timeout).

**i14: deploy.ps1 is well-structured.** DryRun support, ordered manifest application, migration job with wait condition, rollout verification. Error handling stops on first failure.
