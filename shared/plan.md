# Project Name: conversational_survey_engine

## Branch: `feature/preset-questions`

---

## 1. Overview — Preset vs Dynamic Question Mode

### Problem
Currently all survey questions are generated dynamically via LLM based on the participant's responses and survey context. There is no option for an admin to pre-generate a fixed set of questions. Some use cases require all participants to answer the exact same questions for comparability.

### Solution
Add a `question_mode` field to surveys with two options:
1. **`dynamic`** (default) — Current behavior. Questions generated on-the-fly per participant.
2. **`preset`** — Admin triggers LLM to generate a fixed set of questions at setup time. All participants receive the same questions in the same order. No LLM calls during participant sessions.

### Key Design Decisions
- **Decoupled generation** — Survey creation does NOT auto-generate questions. Admin explicitly triggers generation via a "Generate Questions" button. This avoids blocking the create request for 30-60s.
- **Iterative generation with synthetic history** — Reuse existing `generate_question()` in a loop, building synthetic conversation history to get diversity + per-question validation. This reuses the validator naturally.
- **Preset questions stored as JSON on the survey** — `preset_questions` TEXT column stores a JSON array. No separate table needed (bounded by `max_questions`, max ~50).
- **Preset mode skips goal coverage** — All preset questions are always served. Goal coverage is a dynamic-mode concept.
- **Answer guardrails still apply** — Gibberish/injection checks run regardless of question mode.
- **Transparent to participants** — Same session/answer API. The service layer branches internally by mode.
- **Admin can edit preset questions** — PUT endpoint to manually adjust the generated question list.
- **Mode switch with active sessions** — Allowed with warning. Existing sessions continue with their current mode. New sessions use the new mode.

### What stays the same
- All participant-facing API shapes (session create, answer submit, session get)
- Participant frontend — zero changes (questions arrive through the same response shape)
- Answer guardrails, prompt hardening, output guard — unchanged
- Validator logic — reused during preset generation, skipped during preset serving

---

## 2. Modules Affected

### Backend — New/Modified

| File | Change Type |
|------|------------|
| `backend/alembic/versions/002_add_question_mode.py` | **NEW.** Migration: add `question_mode`, `preset_questions`, `preset_generated_at` columns to surveys |
| `backend/app/models/survey.py` | Add 3 columns: `question_mode`, `preset_questions`, `preset_generated_at` |
| `backend/app/schemas/survey.py` | Add `question_mode` to Create/Update/Response schemas. New `PresetQuestion` schema. |
| `backend/app/services/survey_service.py` | Add `generate_preset_questions()` and `update_preset_questions()` |
| `backend/app/services/question_service.py` | Branch `generate_next_question()` by survey mode — preset mode does a JSON lookup instead of LLM call |
| `backend/app/agents/generator_agent.py` | Add `generate_preset_question_set()` — iterative generation loop |
| `backend/app/agents/prompts.py` | Add `build_preset_generation_prompt()` — prompt for generating questions without real answers |
| `backend/app/api/admin.py` | New endpoints: `POST .../generate-questions`, `PUT .../preset-questions`. Update `_survey_to_response()`. |
| `backend/tests/test_preset_questions.py` | **NEW.** Tests for preset generation, mode branching, new endpoints |

### Frontend — Modified

| File | Change Type |
|------|------------|
| `frontend/src/types/survey.ts` | Add `question_mode`, `PresetQuestion`, `preset_questions`, `preset_generated_at` |
| `frontend/src/services/api.ts` | Add `generatePresetQuestions()`, `updatePresetQuestions()` API functions |
| `frontend/src/components/SurveyForm.tsx` | Add mode selector (radio: Dynamic / Preset) |
| `frontend/src/pages/SurveyDetail.tsx` | Show preset questions list, "Generate Questions" button, mode badge |
| `frontend/src/pages/AdminDashboard.tsx` | Show mode badge on survey cards |

### Frontend — Unchanged
| File | Reason |
|------|--------|
| `frontend/src/pages/ParticipantSurvey.tsx` | Questions arrive through same response shape |
| `frontend/src/hooks/useSurveySession.ts` | Hook works identically for both modes |
| `frontend/src/pages/ParticipantLanding.tsx` | No change |
| `frontend/src/pages/SurveyComplete.tsx` | No change |

---

## 3. Detailed Changes

### 3.1 — Migration: `002_add_question_mode.py`

```sql
ALTER TABLE surveys ADD COLUMN question_mode TEXT NOT NULL DEFAULT 'dynamic';
ALTER TABLE surveys ADD COLUMN preset_questions TEXT NULL;
ALTER TABLE surveys ADD COLUMN preset_generated_at TEXT NULL;
```

### 3.2 — Survey Model: `models/survey.py`

Add:
```python
question_mode = Column(Text, nullable=False, default="dynamic")   # "preset" | "dynamic"
preset_questions = Column(Text, nullable=True)                     # JSON array of PresetQuestion
preset_generated_at = Column(Text, nullable=True)                  # ISO timestamp
```

### 3.3 — Survey Schemas: `schemas/survey.py`

- New `PresetQuestion` schema: `question_number: int`, `question_id: str`, `text: str`
- `CreateSurveyRequest`: add `question_mode: str = "dynamic"` with validation (`Literal["preset", "dynamic"]`)
- `UpdateSurveyRequest`: add `question_mode: Optional[str] = None`
- `SurveyResponse`: add `question_mode: str`, `preset_questions: Optional[list[PresetQuestion]]`, `preset_generated_at: Optional[str]`

### 3.4 — Generator Agent: `generator_agent.py`

New function `generate_preset_question_set(survey, count: int) -> list[dict]`:
1. Loop `count` times (= `survey.max_questions`).
2. Build synthetic conversation history from previously generated questions with placeholder answers `"[Not yet answered]"`.
3. Call existing `generate_question()` for each — gets validation for free.
4. Collect `{question_number, question_id (uuid4), text}` for each.
5. Return the list.

### 3.5 — Prompts: `prompts.py`

New function `build_preset_generation_prompt(survey, generated_so_far: list, question_number: int, max_questions: int) -> str`:
- Similar to `build_generator_prompt()` but uses synthetic history instead of real answers.
- Adds instruction: "You are generating a fixed question set for this survey. There are no real participant answers yet. Focus on covering all facets of the survey goal across {max_questions} questions."

### 3.6 — Survey Service: `survey_service.py`

New function `generate_preset_questions(survey_id, db) -> list[PresetQuestion]`:
1. Load survey.
2. Validate `question_mode == "preset"`.
3. Call `generate_preset_question_set(survey, survey.max_questions)`.
4. Store result as JSON in `survey.preset_questions`.
5. Set `survey.preset_generated_at = datetime.utcnow().isoformat()`.
6. Commit and return the questions.

New function `update_preset_questions(survey_id, questions: list[PresetQuestion], db) -> Survey`:
1. Load survey, validate mode is preset.
2. Replace `survey.preset_questions` with provided JSON.
3. Update `preset_generated_at`.
4. Commit and return.

### 3.7 — Question Service: `question_service.py`

Modify `generate_next_question()`:
```python
if survey.question_mode == "preset":
    return _get_next_preset_question(survey, session)
else:
    # existing dynamic generation logic
```

New helper `_get_next_preset_question(survey, session) -> str`:
1. Parse `survey.preset_questions` JSON.
2. Get question at index `session.question_count` (0-based).
3. If no questions generated yet, raise error "Preset questions not yet generated."
4. If all questions served, mark session complete.
5. Return the question text. Skip goal coverage check entirely.

### 3.8 — Admin API: `admin.py`

- Update `create_survey()` to accept `question_mode`.
- Update `_survey_to_response()` to include `question_mode`, `preset_questions` (parsed from JSON), `preset_generated_at`.
- New endpoint `POST /admin/surveys/{survey_id}/generate-questions`:
  - Calls `survey_service.generate_preset_questions()`.
  - Returns `{"questions": [...], "generated_at": "..."}`.
- New endpoint `PUT /admin/surveys/{survey_id}/preset-questions`:
  - Accepts `{"questions": [{"question_number": 1, "text": "..."}]}`.
  - Calls `survey_service.update_preset_questions()`.

### 3.9 — Frontend Types: `types/survey.ts`

```typescript
interface PresetQuestion {
  question_number: number;
  question_id: string;
  text: string;
}

// Add to CreateSurveyRequest:
question_mode?: 'preset' | 'dynamic';

// Add to SurveyResponse:
question_mode: 'preset' | 'dynamic';
preset_questions?: PresetQuestion[];
preset_generated_at?: string;
```

### 3.10 — Frontend API Service: `api.ts`

```typescript
generatePresetQuestions(surveyId: string): Promise<{questions: PresetQuestion[], generated_at: string}>
updatePresetQuestions(surveyId: string, questions: PresetQuestion[]): Promise<void>
```

### 3.11 — Frontend SurveyForm: `SurveyForm.tsx`

Add a radio group after the existing form fields:
- **Question Mode**: `Dynamic (AI generates unique questions per participant)` / `Preset (AI generates fixed questions once)`
- Info text explaining each mode.
- Wire `question_mode` into the form state and submit payload.

### 3.12 — Frontend SurveyDetail: `SurveyDetail.tsx`

- Show `question_mode` badge ("Dynamic" / "Preset") in header area.
- If preset mode:
  - Show generated questions as numbered list.
  - "Generate Questions" button → calls API, shows loading spinner during generation.
  - "Regenerate" button if questions already exist (with confirmation dialog).
  - Show `preset_generated_at` timestamp.
  - If no questions generated yet, show alert: "Questions not yet generated. Click Generate to create the question set."
- If survey context/goal changed after `preset_generated_at`, show warning banner.

### 3.13 — Frontend AdminDashboard: `AdminDashboard.tsx`

- Show small badge/pill on each survey card: "Dynamic" or "Preset".

---

## 4. API Contract Changes

| Change | Endpoint | Details |
|--------|----------|---------|
| Modified | `POST /api/v1/admin/surveys` | Body adds `question_mode` (default `"dynamic"`) |
| Modified | `PUT /api/v1/admin/surveys/{id}` | Body adds `question_mode` |
| Modified | `GET /api/v1/admin/surveys/{id}` | Response adds `question_mode`, `preset_questions`, `preset_generated_at` |
| Modified | `GET /api/v1/admin/surveys` | Each survey includes `question_mode` |
| **New** | `POST /api/v1/admin/surveys/{id}/generate-questions` | Trigger preset generation. Returns `{questions: [...], generated_at: str}` |
| **New** | `PUT /api/v1/admin/surveys/{id}/preset-questions` | Set preset questions manually. Body: `{questions: [{question_number, text}]}` |
| Unchanged | `POST /api/v1/surveys/{id}/sessions` | Same shape — faster for preset (no LLM) |
| Unchanged | `POST /api/v1/surveys/{id}/sessions/{sid}/respond` | Same shape — mode branching is internal |

---

## 5. Dependencies & Execution Order

```
Phase 1: github
  Task 1: Create branch feature/preset-questions

Phase 2: python_coder (backend implementation)
  Task 2: Migration + model + schemas                    [blocked_by: 1]
  Task 3: Generator agent + prompts (preset generation)  [blocked_by: 1]
  Task 4: Survey service (preset logic)                  [blocked_by: 2, 3]
  Task 5: Question service (mode branching)              [blocked_by: 2]
  Task 6: Admin API (new endpoints + serialization)      [blocked_by: 4, 5]

Phase 3: python_test
  Task 7: Backend tests                                  [blocked_by: 6]

Phase 4: backend_reviewer
  Task 8: Backend code review                            [blocked_by: 7]

Phase 5: frontend
  Task 9: Frontend implementation                        [blocked_by: 6]

Phase 6: frontend_test
  Task 10: Frontend tests                                [blocked_by: 9]

Phase 7: frontend_reviewer
  Task 11: Frontend code review                          [blocked_by: 10]

Phase 8: architecture_reviewer
  Task 12: Cross-layer architecture review               [blocked_by: 8, 11]

Phase 9: github
  Task 13: Push branch                                   [blocked_by: 12]
```

---

## 6. Agent Assignments

| Agent | Scope |
|-------|-------|
| github | Branch creation (Task 1) and push (Task 13) |
| python_coder | Tasks 2–6: migration, models, schemas, services, agents, prompts, API |
| python_test | Task 7: backend tests for preset generation, mode branching, endpoints |
| backend_reviewer | Task 8: review backend logic, API design, preset generation quality |
| frontend | Task 9: types, API client, SurveyForm mode selector, SurveyDetail preset display, AdminDashboard badges |
| frontend_test | Task 10: frontend component tests |
| frontend_reviewer | Task 11: review UI implementation, UX flow |
| architecture_reviewer | Task 12: cross-layer review — DB→backend→API contract→frontend consistency |
