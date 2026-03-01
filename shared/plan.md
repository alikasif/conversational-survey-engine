# Project Name: conversational_survey_engine

## Branch: `chore/arch-cleanup`

---

## 1. Overview — Architecture Cleanup

### Problem
An architecture review found 6 issues: duplicate `get_db`, dual config loading (`load_dotenv` + Pydantic Settings), dead config/columns from the embedding era, duplicate health route, and an inline import.

### Solution
Surgical cleanup across backend files. All changes are deletions or simplifications — no new features.

### What stays the same
- All API endpoints and their behavior
- All LLM agent logic (generator + validator)
- Frontend — zero changes
- Database data — no migration (column removal is model-only for now)

### Fixes
1. Delete duplicate `get_db` from `database.py` (keep in `dependencies.py`)
2. Remove `load_dotenv`/`os.getenv` from agent files, use `settings` exclusively
3. Remove dead `context_similarity_threshold` from model, schemas, API helpers
4. Remove dead `question_embedding` from Response model
5. Remove dead `GEMINI_EMBEDDING_MODEL` from config
6. Remove health router duplicate from `api_router`
7. Move inline import to top of `question_service.py`

---

## 2. Modules Affected

| File | Change Type |
|------|------------|
| `backend/app/core/database.py` | Remove duplicate `get_db()` function |
| `backend/app/agents/validator.py` | Remove `load_dotenv` import and call |
| `backend/app/agents/generator_agent.py` | Remove `load_dotenv`, `os.getenv`; use `settings` for model config |
| `backend/app/core/config.py` | Remove `GEMINI_EMBEDDING_MODEL` |
| `backend/app/models/survey.py` | Remove `context_similarity_threshold` column |
| `backend/app/models/response.py` | Remove `question_embedding` column |
| `backend/app/schemas/survey.py` | Remove `context_similarity_threshold` from all schemas |
| `backend/app/api/admin.py` | Remove `context_similarity_threshold` from `_survey_to_response` |
| `backend/app/services/survey_service.py` | Remove `context_similarity_threshold` from `create_survey` |
| `backend/app/api/router.py` | Remove health_router import and include |
| `backend/app/services/question_service.py` | Move inline `survey_repo` import to top |

---

## 3. Detailed Changes

### Fix 1 — Delete duplicate `get_db` from database.py
Remove the `get_db()` function and its `AsyncGenerator` import from `backend/app/core/database.py`. The canonical version lives in `dependencies.py`.

### Fix 2 — Remove `load_dotenv`/`os.getenv`, use `settings` only
- `validator.py`: Remove `from dotenv import load_dotenv` and `load_dotenv(override=True)`.
- `generator_agent.py`: Remove `from dotenv import load_dotenv`, `load_dotenv(override=True)`, and `import os`. Rewrite `get_model()` to use `settings.GEMINI_MODEL` and `settings.effective_api_key` instead of `os.getenv()`.

### Fix 3 — Remove dead `context_similarity_threshold`
- `models/survey.py`: Remove the `context_similarity_threshold` Column.
- `schemas/survey.py`: Remove from `CreateSurveyRequest`, `UpdateSurveyRequest`, `SurveyResponse`.
- `api/admin.py`: Remove from `_survey_to_response()`.
- `services/survey_service.py`: Remove from `create_survey()`.

### Fix 4 — Remove dead `question_embedding`
- `models/response.py`: Remove the `question_embedding` Column.

### Fix 5 — Remove dead `GEMINI_EMBEDDING_MODEL`
- `core/config.py`: Remove `GEMINI_EMBEDDING_MODEL` line.

### Fix 6 — Remove health router from api_router
- `api/router.py`: Remove `health_router` import and `api_router.include_router(health_router)`. Health is already mounted directly in `main.py`.

### Fix 7 — Move inline import
- `services/question_service.py`: Move `from app.repositories import survey_repo` from inside `process_answer()` to the top-level imports.

---

## 4. API Contract Impact

**Minor:** `context_similarity_threshold` is removed from survey create/update/response schemas. This field was vestigial (unused by any logic). Frontend currently sends it in `SurveyCreator` — that field will be silently ignored by Pydantic (`extra = "ignore"` or simply missing from schema).

---

## 5. Dependencies

All fixes are independent — they can be done in any order in a single task.

---

## 6. Agent Assignments

| Agent | Scope |
|-------|-------|
| python_coder | All 7 fixes across backend files |
| python_test | Run tests, fix any broken mocks |
| backend_reviewer | Verify cleanup completeness |
| github | Branch and push |
