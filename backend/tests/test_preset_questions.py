"""Tests for the preset questions feature (question_mode, generation, serving)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.prompts import build_preset_generation_prompt
from app.api.participant import _rate_limit_tracker
from app.models.session import Session
from app.models.survey import Survey
from app.models.user import User
from app.schemas.survey import CreateSurveyRequest
from app.services import question_service, survey_service
from tests.conftest import SURVEY_PAYLOAD, create_test_survey


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PRESET_SURVEY_PAYLOAD = {
    **SURVEY_PAYLOAD,
    "question_mode": "preset",
}

SAMPLE_PRESET_QUESTIONS = [
    {"question_number": 1, "question_id": "q1-id", "text": "How satisfied are you with remote work?"},
    {"question_number": 2, "question_id": "q2-id", "text": "What tools help your productivity?"},
    {"question_number": 3, "question_id": "q3-id", "text": "How do you maintain work-life balance?"},
    {"question_number": 4, "question_id": "q4-id", "text": "What collaboration challenges do you face?"},
    {"question_number": 5, "question_id": "q5-id", "text": "How could the company improve remote work support?"},
]


async def _create_preset_survey(client, *, with_questions=False):
    """Create a preset-mode survey via the API. Optionally store preset questions."""
    resp = await client.post("/api/v1/admin/surveys", json=PRESET_SURVEY_PAYLOAD)
    assert resp.status_code == 201
    survey = resp.json()

    if with_questions:
        # Directly update via the PUT endpoint (mock-free)
        put_resp = await client.put(
            f"/api/v1/admin/surveys/{survey['id']}/preset-questions",
            json={"questions": SAMPLE_PRESET_QUESTIONS},
        )
        assert put_resp.status_code == 200
        # Refresh
        survey = (await client.get(f"/api/v1/admin/surveys/{survey['id']}")).json()

    return survey


async def _create_preset_session(client, survey_id: str, mock_question: str = "preset"):
    """Create a session on a preset survey (no LLM mocks needed for preset)."""
    # For preset surveys the first question is served from JSON, not via LLM.
    # But session creation still calls generate_next_question which will go through
    # the preset branch if question_mode == 'preset'.
    resp = await client.post(
        f"/api/v1/surveys/{survey_id}/sessions",
        json={"participant_name": "Test User", "metadata": {"source": "unit-test"}},
    )
    return resp


# ---------------------------------------------------------------------------
# 1. test_create_survey_default_mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_survey_default_mode(client):
    """Creating a survey without question_mode defaults to 'dynamic'."""
    resp = await client.post("/api/v1/admin/surveys", json=SURVEY_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["question_mode"] == "dynamic"
    assert data["preset_questions"] is None
    assert data["preset_generated_at"] is None


# ---------------------------------------------------------------------------
# 2. test_create_survey_preset_mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_survey_preset_mode(client):
    """Creating a survey with question_mode='preset' stores it correctly."""
    resp = await client.post("/api/v1/admin/surveys", json=PRESET_SURVEY_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["question_mode"] == "preset"


# ---------------------------------------------------------------------------
# 3. test_create_survey_invalid_mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_survey_invalid_mode(client):
    """Creating a survey with an invalid question_mode returns 422."""
    payload = {**SURVEY_PAYLOAD, "question_mode": "invalid"}
    resp = await client.post("/api/v1/admin/surveys", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 4. test_generate_preset_questions_endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_preset_questions_endpoint(client):
    """POST generate-questions on a preset survey generates and stores questions."""
    survey = await _create_preset_survey(client)
    survey_id = survey["id"]

    mock_questions = SAMPLE_PRESET_QUESTIONS

    with patch(
        "app.clients.llm_client.llm_client.generate_preset_questions",
        new_callable=AsyncMock,
        return_value=mock_questions,
    ):
        resp = await client.post(
            f"/api/v1/admin/surveys/{survey_id}/generate-questions"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "questions" in data
    assert len(data["questions"]) == 5
    assert "generated_at" in data

    # Verify questions stored on the survey
    get_resp = await client.get(f"/api/v1/admin/surveys/{survey_id}")
    survey_data = get_resp.json()
    assert survey_data["preset_questions"] is not None
    assert len(survey_data["preset_questions"]) == 5
    assert survey_data["preset_generated_at"] is not None


# ---------------------------------------------------------------------------
# 5. test_generate_preset_questions_wrong_mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_preset_questions_wrong_mode(client):
    """POST generate-questions on a dynamic survey returns 400."""
    survey = await create_test_survey(client)  # dynamic by default
    resp = await client.post(
        f"/api/v1/admin/surveys/{survey['id']}/generate-questions"
    )
    assert resp.status_code == 400
    assert "not in preset mode" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 6. test_preset_question_serving
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preset_question_serving(client):
    """Preset questions are served in order from the stored list."""
    survey = await _create_preset_survey(client, with_questions=True)
    survey_id = survey["id"]

    # Create session — first question should come from preset list
    resp = await _create_preset_session(client, survey_id)
    assert resp.status_code == 201
    session = resp.json()
    assert session["current_question"]["text"] == SAMPLE_PRESET_QUESTIONS[0]["text"]
    assert session["current_question"]["question_number"] == 1

    # Submit answer — next question should be preset #2
    _rate_limit_tracker.clear()  # avoid rate-limit 429 in tests
    session_id = session["session_id"]
    q = session["current_question"]
    resp = await client.post(
        f"/api/v1/surveys/{survey_id}/sessions/{session_id}/respond",
        json={
            "answer": "I enjoy working from home.",
            "question_id": q["question_id"],
            "question_text": q["text"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert data["question"]["text"] == SAMPLE_PRESET_QUESTIONS[1]["text"]
    assert data["question"]["question_number"] == 2


# ---------------------------------------------------------------------------
# 7. test_preset_mode_skips_coverage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preset_mode_skips_coverage(client):
    """Preset mode does NOT call estimate_goal_coverage or generate_question."""
    survey = await _create_preset_survey(client, with_questions=True)
    survey_id = survey["id"]

    with patch(
        "app.services.question_service.validator.estimate_goal_coverage",
        new_callable=AsyncMock,
    ) as mock_coverage, patch(
        "app.services.question_service.llm_client.generate_question",
        new_callable=AsyncMock,
    ) as mock_gen:
        resp = await _create_preset_session(client, survey_id)
        assert resp.status_code == 201

    mock_coverage.assert_not_called()
    mock_gen.assert_not_called()


# ---------------------------------------------------------------------------
# 8. test_update_preset_questions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_preset_questions(client):
    """PUT preset-questions updates the stored questions."""
    survey = await _create_preset_survey(client, with_questions=True)
    survey_id = survey["id"]

    new_questions = [
        {"question_number": 1, "question_id": "new-q1", "text": "Updated question 1?"},
        {"question_number": 2, "question_id": "new-q2", "text": "Updated question 2?"},
    ]

    resp = await client.put(
        f"/api/v1/admin/surveys/{survey_id}/preset-questions",
        json={"questions": new_questions},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "updated"

    # Verify update persisted
    get_resp = await client.get(f"/api/v1/admin/surveys/{survey_id}")
    data = get_resp.json()
    assert len(data["preset_questions"]) == 2
    assert data["preset_questions"][0]["text"] == "Updated question 1?"


# ---------------------------------------------------------------------------
# 9. test_preset_completion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preset_completion(client):
    """All preset questions served -> session completes."""
    # Create a preset survey with only 2 questions
    payload = {**PRESET_SURVEY_PAYLOAD, "max_questions": 2}
    resp = await client.post("/api/v1/admin/surveys", json=payload)
    assert resp.status_code == 201
    survey = resp.json()
    survey_id = survey["id"]

    two_questions = SAMPLE_PRESET_QUESTIONS[:2]
    await client.put(
        f"/api/v1/admin/surveys/{survey_id}/preset-questions",
        json={"questions": two_questions},
    )

    # Create session -> Q1
    session_resp = await _create_preset_session(client, survey_id)
    assert session_resp.status_code == 201
    session = session_resp.json()
    session_id = session["session_id"]
    q1 = session["current_question"]
    assert q1["text"] == two_questions[0]["text"]

    # Answer Q1 -> Q2
    _rate_limit_tracker.clear()
    resp = await client.post(
        f"/api/v1/surveys/{survey_id}/sessions/{session_id}/respond",
        json={"answer": "Good", "question_id": q1["question_id"], "question_text": q1["text"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    q2 = data["question"]
    assert q2["text"] == two_questions[1]["text"]

    # Answer Q2 -> session complete
    _rate_limit_tracker.clear()
    resp = await client.post(
        f"/api/v1/surveys/{survey_id}/sessions/{session_id}/respond",
        json={"answer": "Fine", "question_id": q2["question_id"], "question_text": q2["text"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["question"] is None
    assert data["completion_reason"] == "all_preset_questions_served"


# ---------------------------------------------------------------------------
# 10. test_preset_no_questions_generated
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preset_no_questions_generated(client):
    """Starting a session on a preset survey with no questions -> 400 error."""
    survey = await _create_preset_survey(client, with_questions=False)
    survey_id = survey["id"]

    resp = await _create_preset_session(client, survey_id)
    assert resp.status_code == 400
    assert "not yet generated" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 11. test_survey_response_includes_mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_survey_response_includes_mode(client):
    """GET survey includes question_mode field."""
    survey = await create_test_survey(client)
    resp = await client.get(f"/api/v1/admin/surveys/{survey['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert "question_mode" in data
    assert data["question_mode"] == "dynamic"


# ---------------------------------------------------------------------------
# 12. test_build_preset_generation_prompt
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_preset_generation_prompt():
    """build_preset_generation_prompt produces coherent prompt text."""
    prompt = build_preset_generation_prompt(
        survey_context="Employee satisfaction research",
        goal="Understand remote work challenges",
        constraints=["No salary questions"],
        generated_so_far=[
            {"question_number": 1, "text": "How do you feel about remote work?"},
        ],
        question_number=2,
        max_questions=5,
    )

    assert "Employee satisfaction research" in prompt
    assert "Understand remote work challenges" in prompt
    assert "No salary questions" in prompt
    assert "How do you feel about remote work?" in prompt
    assert "question 2 of 5" in prompt
    assert "SECURITY" in prompt
    assert "fixed question set" in prompt


# ---------------------------------------------------------------------------
# Additional: test_update_preset_questions_wrong_mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_preset_questions_wrong_mode(client):
    """PUT preset-questions on a dynamic survey returns 400."""
    survey = await create_test_survey(client)  # dynamic
    resp = await client.put(
        f"/api/v1/admin/surveys/{survey['id']}/preset-questions",
        json={"questions": [{"question_number": 1, "question_id": "x", "text": "Q?"}]},
    )
    assert resp.status_code == 400
    assert "not in preset mode" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Additional: test_generate_preset_questions_not_found
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_preset_questions_not_found(client):
    """POST generate-questions for nonexistent survey returns 404."""
    resp = await client.post(
        "/api/v1/admin/surveys/nonexistent-id/generate-questions"
    )
    assert resp.status_code == 404
