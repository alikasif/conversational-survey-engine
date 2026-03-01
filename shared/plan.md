# Project Name: conversational_survey_engine

## Branch: `feature/llm-validator`

---

## 1. Overview — LLM-Based Validator

### Problem
The validator currently uses embedding-based cosine similarity for 4 semantic checks (redundancy, goal alignment, context relevance, topic drift) plus a goal coverage estimator. This requires N+9 embedding API calls per validation (up to 18 at question 10), is semantically shallow, and the embedding auth setup has been problematic (Vertex AI OAuth vs API key issues).

### Solution
Replace all embedding-based checks with **a single LLM call** per validation. The LLM receives the full context (candidate question, survey goal, survey context, conversation history) and returns structured JSON with pass/fail for each criterion. Goal coverage estimation also moves to a separate LLM call.

### What stays the same
- Rule-based checks: compound question (regex), leading question (regex), max questions (integer)
- Generator agent interface: `validator.validate()` signature unchanged
- API contracts: zero changes
- Frontend: zero changes

### Key design decisions
1. **One combined LLM call** for 4 validation checks (not 4 separate calls)
2. **Separate LLM call** for goal coverage (runs at different time in pipeline)
3. **Fast/cheap model** for validation (Flash-tier), different from generator model
4. **Structured JSON output** with pass/fail per criterion + reasons
5. **Graceful fallback**: if LLM call fails, assume valid (same as current embedding error handling)

### Tech Stack
- **Backend:** Python 3.11+, FastAPI, OpenAI Agent SDK, LiteLLM, Gemini
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS (no changes)
- **Database:** SQLite (no changes)
- **Testing:** pytest + httpx (backend)

---

## 2. Modules Affected

| File | Change Type |
|------|------------|
| `backend/app/agents/validator.py` | **Major rewrite.** Remove embedding functions, replace 4 semantic checks with single `validate_with_llm()`, replace `estimate_goal_coverage()` with LLM-based version. Keep rule-based checks. |
| `backend/app/agents/prompts.py` | Add `VALIDATOR_SYSTEM_PROMPT`, `build_validator_prompt()`, `COVERAGE_SYSTEM_PROMPT`, `build_coverage_prompt()` |
| `backend/app/core/config.py` | Add `GEMINI_VALIDATOR_MODEL` setting |
| `backend/.env` | Add `GEMINI_VALIDATOR_MODEL` env var |
| `backend/tests/test_validator.py` | Rewrite embedding-mocking tests to LLM-mocking tests. Add error handling tests. |
| `backend/tests/test_generator_agent.py` | No changes — already mocks `validate()` at class level |
| `backend/tests/test_services.py` | Minimal — update mock path if needed |

---

## 3. Detailed Changes

### 3.1 — validator.py: Replace Embedding Checks with Single LLM Call

**Remove:**
- `cosine_similarity()` function
- `get_embedding()` function
- `check_redundancy()` method
- `check_goal_alignment()` method
- `check_context_relevance()` method
- `check_topic_drift()` method
- All threshold parameters from `__init__` (redundancy, goal_alignment, context_similarity, topic_drift)

**Add:**
- `validate_with_llm(candidate_question, survey, conversation_history)` — single `litellm.acompletion()` call that evaluates all 4 criteria. Returns `(is_valid, rejection_reason)`.
- `estimate_goal_coverage(conversation_history, goal)` — LLM-based replacement returning float 0.0–1.0.
- `_get_validator_model()` — helper to get model name from env.

**Update `validate()` flow:**
```
1. check_compound_question()   ← rule-based, keep
2. check_leading_question()    ← rule-based, keep
3. validate_with_llm()         ← NEW: replaces all 4 embedding checks
```

**LLM response JSON schema:**
```json
{
  "redundancy": {"pass": true, "reason": null},
  "goal_alignment": {"pass": true, "reason": null},
  "context_relevance": {"pass": true, "reason": null},
  "topic_drift": {"pass": true, "reason": null}
}
```

### 3.2 — prompts.py: Add Validator Prompts

**`VALIDATOR_SYSTEM_PROMPT`** — instructs LLM to evaluate 4 criteria and return structured JSON.

**`build_validator_prompt(candidate, goal, context, history)`** — assembles the validation context.

**`COVERAGE_SYSTEM_PROMPT`** — instructs LLM to estimate goal coverage as 0.0–1.0.

**`build_coverage_prompt(goal, conversation_history)`** — assembles coverage context.

### 3.3 — config.py: Add Validator Model Setting

Add `GEMINI_VALIDATOR_MODEL: str = "gemini/gemini-2.0-flash"` — fast model for validation.

### 3.4 — Tests

**Rewrite** all embedding-mocking tests to mock `litellm.acompletion`:
- Mock returns structured JSON response objects
- Test each validation criterion independently
- Test combined pass/fail scenarios
- Test JSON parse error fallback
- Test LLM call exception fallback
- Test goal coverage LLM estimate

**Keep unchanged:** all rule-based tests (compound, leading, max_questions)

---

## 4. API Contract Impact

**None.** Internal implementation change only. The `validate()` and `estimate_goal_coverage()` method signatures stay the same.

---

## 5. Dependencies

```
Phase 1 (independent, parallelizable):
  Task 2: prompts.py — add validator + coverage prompts
  Task 3: config.py + .env — add GEMINI_VALIDATOR_MODEL

Phase 2 (depends on Tasks 2 & 3):
  Task 4: validator.py — major rewrite using new prompts + config

Phase 3 (depends on Task 4):
  Task 5: test files — rewrite embedding tests to LLM mocks

Phase 4 (depends on all):
  Task 6: Reviews
```

---

## 6. Agent Assignments

| Agent | Scope |
|-------|-------|
| python_coder | validator.py, prompts.py, config.py, .env |
| python_test | test_validator.py, test_services.py |
| backend_reviewer | Review LLM prompts, error handling, JSON parsing |
| architecture_reviewer | Verify interface stability, no API breakage |
| github | Branch and push |
