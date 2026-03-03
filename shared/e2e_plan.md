# Project Name: conversational_survey_engine

## Branch: `test/e2e-full-application`

---

## 1. Overview — End-to-End Testing of Full Application

### Goal
Execute comprehensive E2E tests against the running backend API to verify the entire application stack works correctly: API → Service → Repository → Database. Tests cover both dynamic and preset question modes, all CRUD operations, participant flows, error handling, and edge cases.

### Approach
- **API-level testing**: All tests hit the real HTTP endpoints on `http://localhost:8000`
- **Real database**: Tests use the actual SQLite database (not mocks)
- **LLM dependency**: Dynamic mode tests that trigger LLM calls will need the server running with proper credentials. Preset mode tests can use manually-set questions to avoid LLM dependency.
- **Isolation**: Each test scenario creates its own survey with a unique title to avoid cross-contamination
- **Sequential execution**: Scenarios execute in dependency order

### Server Requirements
- Backend must be running at `http://localhost:8000` from the `backend/` directory
- `GOOGLE_APPLICATION_CREDENTIALS` env var must be set for LLM-dependent tests
- Database must be initialized (migrations applied)

---

## 2. API Endpoint Map

### Admin Endpoints (prefix: `/api/v1/admin/surveys`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/admin/surveys` | Create survey |
| GET | `/api/v1/admin/surveys` | List surveys (paginated) |
| GET | `/api/v1/admin/surveys/{id}` | Get survey detail + stats |
| PUT | `/api/v1/admin/surveys/{id}` | Update survey |
| DELETE | `/api/v1/admin/surveys/{id}` | Soft-delete survey |
| GET | `/api/v1/admin/surveys/{id}/responses` | Get survey responses |
| GET | `/api/v1/admin/surveys/{id}/stats` | Get survey statistics |
| POST | `/api/v1/admin/surveys/{id}/generate-questions` | Generate preset questions (LLM) |
| PUT | `/api/v1/admin/surveys/{id}/preset-questions` | Update preset questions manually |

### Participant Endpoints (prefix: `/api/v1/surveys`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/surveys/{id}/sessions` | Start session, get first question |
| POST | `/api/v1/surveys/{id}/sessions/{sid}/respond` | Submit answer, get next question |
| GET | `/api/v1/surveys/{id}/sessions/{sid}` | Get session detail |
| POST | `/api/v1/surveys/{id}/sessions/{sid}/exit` | Exit session early |

### Other
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/` | Root info |

---

## 3. E2E Test Scenarios

### Phase 1: Infrastructure & Health
- **S001**: GET /health → 200, status=ok
- **S002**: GET / → 200, has name, version, docs fields

### Phase 2: Admin CRUD (Dynamic Mode)
- **S003**: POST create dynamic survey → 201, correct fields returned
- **S004**: GET list surveys → 200, newly created survey appears
- **S005**: GET survey detail → 200, includes stats (0 sessions initially)
- **S006**: PUT update survey title/goal → 200, updated fields returned
- **S007**: GET survey stats → 200, all stat fields present
- **S008**: DELETE survey → 204, survey no longer in list

### Phase 3: Admin CRUD (Preset Mode)
- **S009**: POST create preset survey → 201, question_mode=preset
- **S010**: PUT preset-questions (manually set 3 questions) → 200, status=updated
- **S011**: GET survey detail → preset_questions array has 3 items
- **S012**: POST generate-questions on dynamic survey → 400 (wrong mode)

### Phase 4: Participant Flow — Preset Mode
- **S013**: POST create session on preset survey → 201, first question matches preset Q1
- **S014**: POST respond with valid answer → 200, next question matches preset Q2
- **S015**: POST respond to complete all questions → session status=completed
- **S016**: GET session detail → conversation has all Q&A pairs
- **S017**: POST respond on completed session → 409

### Phase 5: Participant Flow — Dynamic Mode (LLM-dependent)
- **S018**: POST create session on dynamic survey → 201, has current_question
- **S019**: POST respond with valid answer → 200, has next question or completion

### Phase 6: Error Handling
- **S020**: POST create session on non-existent survey → 404
- **S021**: GET non-existent survey → 404
- **S022**: POST create survey with invalid question_mode → 422
- **S023**: POST respond with empty answer → 422
- **S024**: POST exit session → 200, status=exited
- **S025**: POST respond on exited session → 409

### Phase 7: Cross-Layer Verification
- **S026**: GET survey responses after completing a session → responses list contains session
- **S027**: GET survey detail after sessions → stats show correct session counts
- **S028**: Pagination: GET list surveys with skip/limit → correct pagination

---

## 4. Selected Agents

| Agent | Role |
|-------|------|
| e2e_tester | Creates e2e_scenarios.json, executes all scenarios, reports results |
| project_structure | Scaffolds any needed test infrastructure files |
| github | Commits E2E test artifacts to branch |

---

## 5. Known Issues / Gotchas (from learnings.md)

1. **Server must run from backend/ directory** — relative DB path resolves differently otherwise
2. **Rate limiting**: 2-second cooldown per session on `/respond` — tests must add delays between answers
3. **LLM calls may fail** — dynamic mode tests should tolerate LLM errors gracefully
4. **Preset questions must be generated/set before starting a session** — otherwise error
5. **GOOGLE_APPLICATION_CREDENTIALS** must be set for Vertex AI LLM calls
