# E2E Testing Research Report — Conversational Survey Engine

## 1. Complete API Endpoint Map

All endpoints are under the FastAPI app. Health is mounted at root AND under `/api/v1`. All other business endpoints are under `/api/v1`.

| Method | Path | Tag | Request Body | Response Shape | Auth | Status Codes |
|--------|------|-----|-------------|---------------|------|-------------|
| `GET` | `/` | — | — | `{ name, version, docs, health, api }` | None | 200 |
| `GET` | `/health` | health | — | `{ status: "ok", version: "0.1.0" }` | None | 200 |
| `GET` | `/api/v1/health` | health | — | `{ status: "ok", version: "0.1.0" }` | None | 200 |
| `POST` | `/api/v1/admin/surveys` | admin | `CreateSurveyRequest` | `SurveyResponse` (201) | None | 201, 422 |
| `GET` | `/api/v1/admin/surveys` | admin | — (query: `skip`, `limit`) | `SurveyListResponse` | None | 200, 422 |
| `GET` | `/api/v1/admin/surveys/{survey_id}` | admin | — | `SurveyDetailResponse` | None | 200, 404 |
| `PUT` | `/api/v1/admin/surveys/{survey_id}` | admin | `UpdateSurveyRequest` | `SurveyResponse` | None | 200, 404, 422 |
| `DELETE` | `/api/v1/admin/surveys/{survey_id}` | admin | — | — (204) | None | 204, 404 |
| `GET` | `/api/v1/admin/surveys/{survey_id}/responses` | admin | — (query: `skip`, `limit`) | `ResponseListResponse` | None | 200, 404 |
| `GET` | `/api/v1/admin/surveys/{survey_id}/stats` | admin | — | `SurveyStatsResponse` | None | 200, 404 |
| `POST` | `/api/v1/admin/surveys/{survey_id}/generate-questions` | admin | — | `{ questions: [...], generated_at: str }` | None | 200, 400, 404 |
| `PUT` | `/api/v1/admin/surveys/{survey_id}/preset-questions` | admin | `{ questions: PresetQuestion[] }` | `{ status: "updated" }` | None | 200, 400, 404 |
| `POST` | `/api/v1/surveys/{survey_id}/sessions` | participant | `CreateSessionRequest` (optional body) | `SessionResponse` (201) | None | 201, 400, 404 |
| `POST` | `/api/v1/surveys/{survey_id}/sessions/{session_id}/respond` | participant | `SubmitAnswerRequest` | `NextQuestionResponse` | None | 200, 400, 404, 409, 429 |
| `GET` | `/api/v1/surveys/{survey_id}/sessions/{session_id}` | participant | — | `SessionDetailResponse` | None | 200, 404 |
| `POST` | `/api/v1/surveys/{survey_id}/sessions/{session_id}/exit` | participant | — | `SessionCompleteResponse` | None | 200, 404, 409 |

**NOTE**: There is NO authentication on any endpoint. All endpoints are fully open.

---

## 2. API Contract Details

### Request Schemas

#### `CreateSurveyRequest`
```json
{
  "title": "string (required)",
  "context": "string (required)",
  "goal": "string (required)",
  "constraints": ["string[]", "default: []"],
  "max_questions": "int (default: 10)",
  "completion_criteria": "string (default: '')",
  "goal_coverage_threshold": "float (default: 0.85)",
  "question_mode": "'preset' | 'dynamic' (default: 'dynamic')"
}
```

#### `UpdateSurveyRequest`
All fields optional — partial update:
```json
{
  "title?": "string",
  "context?": "string",
  "goal?": "string",
  "constraints?": ["string[]"],
  "max_questions?": "int",
  "completion_criteria?": "string",
  "goal_coverage_threshold?": "float",
  "question_mode?": "'preset' | 'dynamic'"
}
```

#### `CreateSessionRequest`
```json
{
  "participant_name?": "string | null",
  "metadata?": "Record<string, string> (default: {})"
}
```

#### `SubmitAnswerRequest`
```json
{
  "answer": "string (1–2000 chars, stripped)",
  "question_id?": "string | null",
  "question_text?": "string | null"
}
```

#### `UpdatePresetQuestionsRequest`
```json
{
  "questions": [
    { "question_number": 1, "question_id": "uuid", "text": "..." }
  ]
}
```

### Response Schemas

#### `SurveyResponse`
```json
{
  "id": "string",
  "title": "string",
  "context": "string",
  "goal": "string",
  "constraints": ["string[]"],
  "max_questions": "int",
  "completion_criteria": "string",
  "goal_coverage_threshold": "float",
  "question_mode": "string ('preset' | 'dynamic')",
  "preset_questions?": [{ "question_number": 1, "question_id": "x", "text": "y" }],
  "preset_generated_at?": "string (ISO datetime) | null",
  "is_active": "bool",
  "created_at": "string (ISO datetime)",
  "updated_at": "string (ISO datetime)"
}
```

#### `SurveyDetailResponse` (extends SurveyResponse)
```json
{
  "...SurveyResponse",
  "total_sessions": "int",
  "completed_sessions": "int",
  "avg_questions_per_session": "float"
}
```

#### `SurveyListResponse`
```json
{
  "surveys": ["SurveyResponse[]"],
  "total": "int",
  "skip": "int",
  "limit": "int"
}
```

#### `SurveyStatsResponse`
```json
{
  "survey_id": "string",
  "total_sessions": "int",
  "completed_sessions": "int",
  "abandoned_sessions": "int",
  "avg_questions_per_session": "float",
  "avg_completion_time_seconds": "float",
  "top_themes": ["string[]"]
}
```

#### `SessionResponse` (on session creation)
```json
{
  "session_id": "string",
  "user_id": "string",
  "survey_id": "string",
  "status": "string",
  "current_question": { "question_id": "str", "text": "str", "question_number": "int" },
  "question_number": "int",
  "max_questions": "int",
  "created_at": "string"
}
```

#### `NextQuestionResponse` (on answer submission)
```json
{
  "session_id": "string",
  "status": "'active' | 'completed'",
  "question?": { "question_id": "str", "text": "str", "question_number": "int" } | null,
  "completion_reason?": "string | null",
  "question_number": "int",
  "max_questions": "int"
}
```

#### `SessionDetailResponse` (GET session)
```json
{
  "session_id": "string",
  "user_id": "string",
  "survey_id": "string",
  "status": "'active' | 'completed' | 'exited'",
  "conversation": [{
    "question_id": "string",
    "question_text": "string",
    "answer_text": "string",
    "question_number": "int",
    "answered_at": "string"
  }],
  "question_count": "int",
  "created_at": "string",
  "completed_at?": "string | null"
}
```

#### `SessionCompleteResponse` (on exit)
```json
{
  "session_id": "string",
  "status": "'exited'",
  "question_count": "int",
  "message": "string"
}
```

#### `ResponseListResponse` (admin: survey responses)
```json
{
  "responses": ["SessionDetailResponse[]"],
  "total": "int",
  "skip": "int",
  "limit": "int"
}
```

---

## 3. Frontend Route Map

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | Redirect → `/admin` | Default redirect |
| `/admin` | `AdminDashboard` | List all surveys, stats, delete, link to create/detail |
| `/admin/surveys/new` | `SurveyCreator` | Create survey form (SurveyForm component) |
| `/admin/surveys/:id` | `SurveyDetail` | Survey detail, stats, sessions, preset questions, share link |
| `/survey` | `ParticipantLanding` | Participant landing page (requires `?id=<survey_id>` query param) |
| `/survey/:surveyId/session/:sessionId` | `ParticipantSurvey` | Chat-style survey session UI |
| `/survey/:surveyId/complete` | `SurveyComplete` | Completion/exit summary page |

All routes are wrapped in a `<Layout />` component with `<Outlet />`.

---

## 4. User Flows

### Flow A: Admin Creates Dynamic Survey → View → Share
1. Admin navigates to `/admin` → sees dashboard with survey list
2. Clicks "+ Create New Survey" → goes to `/admin/surveys/new`
3. Fills out `SurveyForm`: title, context, goal, constraints, max_questions, completion_criteria, goal_coverage_threshold, question_mode = "dynamic"
4. Clicks "Create Survey" → `POST /api/v1/admin/surveys` with `CreateSurveyRequest`
5. Backend creates survey, returns `SurveyResponse` with generated UUID `id`
6. Frontend navigates to `/admin/surveys/{id}` (SurveyDetail)
7. SurveyDetail fetches in parallel: `GET /api/v1/admin/surveys/{id}`, `GET /api/v1/admin/surveys/{id}/stats`, `GET /api/v1/admin/surveys/{id}/responses`
8. Admin sees survey config, empty stats (0 sessions), and participant link: `{origin}/survey?id={survey_id}`
9. Admin copies link via "Copy Link" button

### Flow B: Admin Creates Preset Survey → Generate Questions → View/Edit → Share
1. Steps 1–6 same as Flow A, except `question_mode = "preset"`
2. On SurveyDetail page, the "Preset Questions" section appears
3. Initially shows warning: "Questions not generated yet"
4. Admin clicks "Generate Questions" → `POST /api/v1/admin/surveys/{id}/generate-questions`
5. Backend calls LLM to generate `max_questions` preset questions (30–60s)
6. Returns `{ questions: PresetQuestion[], generated_at: string }`
7. Page auto-refreshes survey via `GET /api/v1/admin/surveys/{id}` to show generated questions
8. Questions displayed as numbered list
9. Admin can manually update questions → `PUT /api/v1/admin/surveys/{id}/preset-questions`
10. Admin copies participant link

### Flow C: Participant Takes Survey (Dynamic Mode)
1. Participant opens `{origin}/survey?id={survey_id}`
2. `ParticipantLanding` fetches survey details: `GET /api/v1/admin/surveys/{survey_id}`
3. Shows survey title, context, max_questions info, optional name input
4. Participant clicks "Start Survey" → `POST /api/v1/surveys/{survey_id}/sessions` with optional `participant_name`
5. Backend creates User + Session, generates first question via LLM, returns `SessionResponse`
6. Frontend navigates to `/survey/{surveyId}/session/{sessionId}`
7. `ParticipantSurvey` renders chat UI with first question as bot bubble
8. Participant types answer, hits send → `POST /api/v1/surveys/{survey_id}/sessions/{session_id}/respond` with `{ answer }` — the `question_id` and `question_text` from currentQuestion are also sent
9. Backend stores response, checks guardrails, generates next question (or completes session)
10. Returns `NextQuestionResponse` — if `status: "active"`, shows next question; if `status: "completed"`, shows thank-you
11. Repeat steps 8–10 until completion (goal coverage met OR max_questions reached)
12. On completion, the UI shows "Thank you!" message, then auto-navigates to `/survey/{surveyId}/complete` after 3.5s
13. `SurveyComplete` shows summary with question count and status

**Exit Flow**: At any time, participant can click "Exit Survey" → `POST .../exit` → session marked "exited" → navigates to completion page

### Flow D: Participant Takes Survey (Preset Mode)
Same as Flow C except:
- Questions come from the stored preset list, no LLM generation per answer
- Session completes with `all_preset_questions_served` when all preset questions answered
- **Critically**: If preset questions haven't been generated yet, `create_session` will fail with a ValueError

### Flow E: Admin Views Survey Results
1. Admin navigates to `/admin/surveys/{id}` (SurveyDetail)
2. Fetches stats: `GET /api/v1/admin/surveys/{id}/stats` → total/completed/abandoned sessions, avg questions, top themes
3. Fetches responses: `GET /api/v1/admin/surveys/{id}/responses` → list of `SessionDetailResponse` with full conversation history
4. Sessions table shows session ID (truncated), status badge, question count, started/completed times

---

## 5. Configuration

### Backend (FastAPI)
- **Port**: 8000 (uvicorn)
- **Database**: SQLite via `aiosqlite`, path = `sqlite+aiosqlite:///./data/cse.db` (relative to cwd, which MUST be `backend/`)
- **CORS**: Configured via `settings.cors_origins_list`, default: `["http://localhost:5173"]`
- **Models**: Vertex AI Gemini (`vertex_ai/gemini-2.0-flash` for generation, `gemini/gemini-2.0-flash` for validation)
- **Env vars**: `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `LOG_LEVEL`, `GEMINI_MODEL`, `GEMINI_VALIDATOR_MODEL`
- **DB init**: `init_db()` on lifespan startup; creates `data/` directory

### Frontend (Vite + React)
- **Port**: 5173 (default Vite)
- **API Base URL**: `import.meta.env.VITE_API_BASE_URL || "/api/v1"` — defaults to `/api/v1` (relative)
- **Proxy**: Vite dev server proxies `/api` → `http://localhost:8000` (configured in `vite.config.ts`)
- **No CORS issues in dev** because of the Vite proxy

### Database Schema (SQLite)
Tables: `surveys`, `users`, `sessions`, `responses`
- `surveys`: id, title, context, goal, constraints (JSON string), max_questions, completion_criteria, goal_coverage_threshold, question_mode, preset_questions (JSON string), preset_generated_at, is_active, created_at, updated_at
- `users`: id, participant_name, metadata (JSON string), created_at
- `sessions`: id, survey_id (FK), user_id (FK), status, completion_reason, question_count, created_at, completed_at
- `responses`: id, session_id (FK), survey_id (FK), user_id (FK), question_id, question_text, answer_text, question_number, answer_flags (JSON string), created_at

**NOTE**: The `database/schema.sql` has `context_similarity_threshold` column on surveys, but this was removed from the ORM model per learnings. The actual running DB may or may not have it depending on migration state.

---

## 6. Known Issues (from learnings.md)

1. **Alembic migration drift**: DB was bootstrapped by `create_all()`, not Alembic. Migrations 001/002 may not be applied. Need `alembic stamp` + `alembic upgrade head` to sync.

2. **Relative DB path**: `sqlite+aiosqlite:///./data/cse.db` resolves relative to cwd. If uvicorn starts from workspace root instead of `backend/`, it creates a DIFFERENT database file. **Always start uvicorn from `backend/` directory.**

3. **Uvicorn --reload stale code**: `--reload` from workspace root causes `ModuleNotFoundError` silently, serving stale code. Use `--reload` only when cwd is `backend/`, or run without `--reload`.

4. **`context_similarity_threshold` removed from ORM but possibly still in DB**: If the DB still has this column as NOT NULL with no default, INSERTs will fail with `IntegrityError`. The ORM model dropped it, but the DB column may remain unless manually altered.

5. **LLM model config in `.env`**: A previous bad `.env` value (`GEMINI_MODEL=gemini-3-pro-preview`) caused silent fallback to generic questions. The actual model must be `vertex_ai/gemini-2.0-flash`.

6. **Vertex AI auth**: `vertex_ai/` models use `GOOGLE_APPLICATION_CREDENTIALS` for service account auth — NOT API keys. Passing `api_key` causes 401 errors.

7. **Frontend sends `context_similarity_threshold`**: The `SurveyForm.tsx` sends `context_similarity_threshold` in the `CreateSurveyRequest`, and `SurveyDetail.tsx` reads `survey.context_similarity_threshold` — but the backend schema `CreateSurveyRequest` does NOT include this field (it has `extra = "ignore"` via Pydantic). The frontend `types/survey.ts` includes it. This is a frontend/backend contract mismatch but is harmless because the backend ignores extra fields.

8. **Rate limiting**: The `submit_answer` endpoint has a per-session in-memory rate limit of 2 seconds between submissions. E2E tests must account for this delay.

---

## 7. Recommended E2E Test Scenarios

### 7.1 Happy Path: Full Dynamic Survey Flow
**Scenario**: Admin creates dynamic survey → participant completes it → admin views results

Steps:
1. `POST /api/v1/admin/surveys` with `question_mode: "dynamic"`, `max_questions: 3`
2. Verify 201, response has `id`, `question_mode: "dynamic"`, `is_active: true`
3. `GET /api/v1/admin/surveys/{id}` → verify detail response, `total_sessions: 0`
4. `POST /api/v1/surveys/{id}/sessions` with `{ participant_name: "Test User" }`
5. Verify 201, response has `session_id`, `current_question` with text and `question_number: 1`
6. Loop: `POST /api/v1/surveys/{id}/sessions/{session_id}/respond` with meaningful answer
   - Verify `NextQuestionResponse` with `status: "active"` and next question, OR `status: "completed"`
   - Respect 2s rate limit between submissions
7. After completion, verify `status: "completed"`, `completion_reason` is `"max_questions_reached"` or `"goal_coverage_met"`
8. `GET /api/v1/surveys/{id}/sessions/{session_id}` → verify `SessionDetailResponse` with full conversation
9. `GET /api/v1/admin/surveys/{id}/responses` → verify session appears in list with correct conversation
10. `GET /api/v1/admin/surveys/{id}/stats` → verify `total_sessions >= 1`, `completed_sessions >= 1`

### 7.2 Happy Path: Full Preset Survey Flow
**Scenario**: Admin creates preset survey → generates questions → participant completes → admin views

Steps:
1. `POST /api/v1/admin/surveys` with `question_mode: "preset"`, `max_questions: 3`
2. Verify survey created with `question_mode: "preset"`, `preset_questions: null`
3. `POST /api/v1/admin/surveys/{id}/generate-questions`
4. Verify response `{ questions: [...], generated_at: "..." }` with exactly `max_questions` questions
5. `GET /api/v1/admin/surveys/{id}` → verify `preset_questions` is populated, `preset_generated_at` is set
6. `POST /api/v1/surveys/{id}/sessions`
7. Verify first question matches first preset question text
8. Submit answers for each preset question (respecting 2s rate limit)
   - Verify each `NextQuestionResponse.question.text` matches the expected preset question
9. After last preset question answered, verify `status: "completed"`, `completion_reason: "all_preset_questions_served"`
10. Verify responses via admin endpoints

### 7.3 Preset: Manual Question Update
**Scenario**: Admin manually sets preset questions instead of generating

Steps:
1. Create preset survey
2. `PUT /api/v1/admin/surveys/{id}/preset-questions` with custom questions
3. Verify `{ status: "updated" }`
4. `GET /api/v1/admin/surveys/{id}` → verify custom questions are stored
5. Start session → verify first question matches custom question

### 7.4 Error: Create Session on Non-Existent Survey
- `POST /api/v1/surveys/nonexistent-id/sessions` → expect 404

### 7.5 Error: Create Session on Preset Survey Without Generated Questions
- Create preset survey (no question generation)
- `POST /api/v1/surveys/{id}/sessions` → expect 400 (ValueError: "Preset questions not yet generated")

### 7.6 Error: Submit Answer to Non-Existent Session
- `POST /api/v1/surveys/{id}/sessions/bad-session-id/respond` → expect 404

### 7.7 Error: Submit Answer to Completed Session
1. Complete a session (all questions answered)
2. Submit another answer to same session → expect 409 with "Session is already completed"

### 7.8 Error: Submit Answer to Wrong Survey
1. Create sessions for survey A
2. Submit answer using survey B's ID but session A's session_id → expect 404

### 7.9 Error: Submit Empty/Too-Long Answer
- `POST .../respond` with `{ answer: "" }` → expect 422 (Pydantic validation: min_length=1)
- `POST .../respond` with `{ answer: "x".repeat(2001) }` → expect 422 (max_length=2000)

### 7.10 Error: Generate Questions for Dynamic Survey
- Create dynamic survey
- `POST /api/v1/admin/surveys/{id}/generate-questions` → expect 400 "Survey is not in preset mode"

### 7.11 Error: Update Non-Existent Survey
- `PUT /api/v1/admin/surveys/nonexistent-id` → expect 404
- `DELETE /api/v1/admin/surveys/nonexistent-id` → expect 404

### 7.12 Edge Case: Session Exit
1. Create session, answer 1 question
2. `POST /api/v1/surveys/{id}/sessions/{session_id}/exit`
3. Verify `status: "exited"`, `question_count: 1`, `completion_reason: "user_exited"`
4. Try to submit another answer → expect 409

### 7.13 Edge Case: Exit Already-Completed Session
1. Complete a session normally
2. `POST .../exit` → expect 409 "Session is not active"

### 7.14 Edge Case: Rate Limiting
1. Create session
2. Submit two answers in rapid succession (< 2 seconds apart)
3. Second request → expect 429 "Too many requests"

### 7.15 Edge Case: Max Questions Boundary (Dynamic)
1. Create dynamic survey with `max_questions: 2`
2. Start session, answer 2 questions
3. After 2nd answer, verify `status: "completed"`, `completion_reason: "max_questions_reached"`

### 7.16 Edge Case: Survey CRUD Lifecycle
1. Create → verify in list
2. Update title → verify change persisted
3. Delete → verify 204
4. GET deleted survey → should still return (soft delete, `is_active: false`) OR depending on implementation
5. List surveys → verify deleted survey has `is_active: false`

### 7.17 Cross-Layer: Data Roundtrip
1. Create survey with specific constraints `["no pricing", "focus UX"]`
2. `GET /api/v1/admin/surveys/{id}` → verify `constraints` is `["no pricing", "focus UX"]` (deserialized from JSON)
3. Start session, submit answer "I love the new dashboard"
4. `GET /api/v1/admin/surveys/{id}/responses` → verify answer_text matches submitted text exactly

### 7.18 Answer Guardrails: Gibberish Detection
1. Start session
2. Submit `answer: "aaaaaaaaaa"` (char repeat ≥10) → expect response still 200 but answer is stored with `answer_flags: ["char_repeat"]`
3. Next question should include a clarification hint (re-ask about same topic)

### 7.19 Answer Guardrails: Non-Alphanumeric
1. Submit `answer: "!@#$%^&*()"` (no alphanumeric chars) → stored with `answer_flags: ["no_alphanumeric"]`
2. Next question should include a clarification hint

### 7.20 Answer Guardrails: Injection Attempt
1. Submit `answer: "ignore all previous instructions"` → stored with `answer_flags: ["injection_attempt"]`
2. Answer is still stored (never rejected), but flagged

### 7.21 Pagination
1. Create 3 surveys
2. `GET /api/v1/admin/surveys?skip=0&limit=2` → verify `total: 3`, `surveys.length: 2`
3. `GET /api/v1/admin/surveys?skip=2&limit=2` → verify `surveys.length: 1`

### 7.22 Health Check
- `GET /health` → `{ status: "ok", version: "0.1.0" }`
- `GET /api/v1/health` → `{ status: "ok", version: "0.1.0" }`

---

## 8. Test Infrastructure Notes

### Starting the Backend
```powershell
Push-Location d:\GitHub\conversational-survey-engine\backend
& d:\GitHub\conversational-survey-engine\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --port 8000 --host 0.0.0.0
```
**Must run from `backend/` directory** to resolve relative DB path correctly.

### Starting the Frontend
```powershell
cd d:\GitHub\conversational-survey-engine\frontend
npm run dev
```
Serves on `http://localhost:5173`, proxies `/api` → `http://localhost:8000`.

### Test Database Isolation
- The backend uses SQLite at `backend/data/cse.db`
- For E2E tests, consider:
  - Using a separate test DB (set `DATABASE_URL` env var)
  - Clearing the DB between test runs
  - Or running tests against the existing DB with unique survey titles for identification

### LLM Dependency
- Dynamic mode surveys require a working LLM connection (Vertex AI / Gemini)
- `GOOGLE_APPLICATION_CREDENTIALS` must point to the service account JSON file
- Preset question generation also requires LLM
- For deterministic E2E tests, consider:
  - Using preset mode with manually set questions (no LLM dependency)
  - Or mocking the LLM layer
  - Dynamic mode tests will have non-deterministic question text

### Rate Limiting
- 2-second per-session rate limit on `submit_answer`
- Tests must include `await sleep(2000)` between answer submissions
- Rate limit is in-memory only — restarting the server clears it

### Key Timing Considerations
- Preset question generation via LLM: 30–60 seconds
- Dynamic question generation: 2–10 seconds per question
- Frontend auto-redirect on completion: 3.5 second delay
- Frontend "Exit Survey": immediate redirect (0 delay)
