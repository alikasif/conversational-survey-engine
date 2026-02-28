"""Tests for the Participant API endpoints (/api/v1/surveys)."""

from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import create_test_session, create_test_survey


MOCK_QUESTION_1 = "How do you feel about remote work?"
MOCK_QUESTION_2 = "What challenges do you face working from home?"


def _agent_patches(question_text: str = MOCK_QUESTION_2, coverage: float = 0.1):
    """Return a context-manager stack that mocks all LLM-dependent code."""
    return (
        patch(
            "app.services.question_service.generate_question",
            new_callable=AsyncMock,
            return_value=question_text,
        ),
        patch(
            "app.services.question_service.validator.estimate_goal_coverage",
            new_callable=AsyncMock,
            return_value=coverage,
        ),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/surveys/{survey_id}/sessions  (create session)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session(client, survey_payload):
    """Creating a session returns 201, session_id, and the first question."""
    survey = await create_test_survey(client)
    session = await create_test_session(client, survey["id"])

    assert "session_id" in session
    assert session["survey_id"] == survey["id"]
    assert session["status"] == "active"
    assert session["current_question"]["text"] == MOCK_QUESTION_1
    assert session["current_question"]["question_number"] == 1


@pytest.mark.asyncio
async def test_create_session_survey_not_found(client):
    """Creating a session for a nonexistent survey returns 404."""
    with _agent_patches()[0], _agent_patches()[1]:
        resp = await client.post(
            "/api/v1/surveys/nonexistent/sessions",
            json={"participant_name": "Nobody"},
        )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/surveys/{id}/sessions/{sid}/respond  (submit answer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_answer(client, survey_payload):
    """Submitting an answer returns the next question with active status."""
    survey = await create_test_survey(client)
    session = await create_test_session(client, survey["id"])
    session_id = session["session_id"]
    q = session["current_question"]

    p1, p2 = _agent_patches(MOCK_QUESTION_2, 0.2)
    with p1, p2:
        resp = await client.post(
            f"/api/v1/surveys/{survey['id']}/sessions/{session_id}/respond",
            json={
                "answer": "I enjoy working from home.",
                "question_id": q["question_id"],
                "question_text": q["text"],
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert data["question"]["text"] == MOCK_QUESTION_2


@pytest.mark.asyncio
async def test_submit_answer_completes_session(client, survey_payload):
    """When max questions are reached the session status becomes completed."""
    # Create survey with max_questions=1 so it completes after first answer
    payload = survey_payload.copy()
    payload["max_questions"] = 1
    resp = await client.post("/api/v1/admin/surveys", json=payload)
    assert resp.status_code == 201
    survey = resp.json()

    session = await create_test_session(client, survey["id"])
    session_id = session["session_id"]
    q = session["current_question"]

    # After answering, generate_next_question will see question_count == 1 == max
    p1, p2 = _agent_patches()
    with p1, p2:
        resp = await client.post(
            f"/api/v1/surveys/{survey['id']}/sessions/{session_id}/respond",
            json={
                "answer": "It's great.",
                "question_id": q["question_id"],
                "question_text": q["text"],
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["question"] is None
    assert data["completion_reason"] == "max_questions_reached"


# ---------------------------------------------------------------------------
# GET /api/v1/surveys/{id}/sessions/{sid}  (get session)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_session(client, survey_payload):
    """Getting a session returns its current state."""
    survey = await create_test_survey(client)
    session = await create_test_session(client, survey["id"])
    session_id = session["session_id"]

    resp = await client.get(
        f"/api/v1/surveys/{survey['id']}/sessions/{session_id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["status"] == "active"
    assert isinstance(data["conversation"], list)


@pytest.mark.asyncio
async def test_get_session_not_found(client, survey_payload):
    """Getting a nonexistent session returns 404."""
    survey = await create_test_survey(client)
    resp = await client.get(
        f"/api/v1/surveys/{survey['id']}/sessions/nonexistent-sid"
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/surveys/{id}/sessions/{sid}/exit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exit_session(client, survey_payload):
    """Exiting an active session returns success."""
    survey = await create_test_survey(client)
    session = await create_test_session(client, survey["id"])
    session_id = session["session_id"]

    resp = await client.post(
        f"/api/v1/surveys/{survey['id']}/sessions/{session_id}/exit"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "exited"
    assert "message" in data


@pytest.mark.asyncio
async def test_exit_session_not_found(client, survey_payload):
    """Exiting a nonexistent session returns 404."""
    survey = await create_test_survey(client)
    resp = await client.post(
        f"/api/v1/surveys/{survey['id']}/sessions/nonexistent-sid/exit"
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_respond_to_completed_session(client, survey_payload):
    """Responding to a completed/exited session returns 409."""
    survey = await create_test_survey(client)
    session = await create_test_session(client, survey["id"])
    session_id = session["session_id"]

    # Exit the session first
    await client.post(
        f"/api/v1/surveys/{survey['id']}/sessions/{session_id}/exit"
    )

    # Now try to answer — should be 409
    resp = await client.post(
        f"/api/v1/surveys/{survey['id']}/sessions/{session_id}/respond",
        json={"answer": "Late answer"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_respond_session_not_found(client, survey_payload):
    """Responding to a nonexistent session returns 404."""
    survey = await create_test_survey(client)
    resp = await client.post(
        f"/api/v1/surveys/{survey['id']}/sessions/nonexistent-sid/respond",
        json={"answer": "Hello"},
    )
    assert resp.status_code == 404
