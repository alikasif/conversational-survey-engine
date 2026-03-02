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
