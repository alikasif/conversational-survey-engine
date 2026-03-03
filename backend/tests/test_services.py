"""Tests for the service layer (survey_service, session_service, question_service)."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.models.survey import Survey
from app.models.user import User
from app.schemas.session import CreateSessionRequest, QuestionPayload
from app.schemas.survey import CreateSurveyRequest, UpdateSurveyRequest
from app.services import question_service, session_service, survey_service


# ---------------------------------------------------------------------------
# survey_service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_survey_service_create(db_session: AsyncSession):
    """Creating a survey via the service returns a Survey with the correct fields."""
    req = CreateSurveyRequest(
        title="Test Survey",
        context="Testing context",
        goal="Test goal",
        constraints=["no salary questions"],
        max_questions=8,
    )
    survey = await survey_service.create_survey(req, db_session)
    await db_session.commit()

    assert survey.title == "Test Survey"
    assert survey.goal == "Test goal"
    assert survey.max_questions == 8
    assert survey.is_active is True
    assert survey.id is not None


@pytest.mark.asyncio
async def test_survey_service_get(db_session: AsyncSession):
    """get_survey returns the correct survey."""
    req = CreateSurveyRequest(
        title="Findable", context="ctx", goal="g",
    )
    created = await survey_service.create_survey(req, db_session)
    await db_session.commit()

    found = await survey_service.get_survey(created.id, db_session)
    assert found is not None
    assert found.id == created.id


@pytest.mark.asyncio
async def test_survey_service_list(db_session: AsyncSession):
    """list_surveys returns all created surveys."""
    for i in range(3):
        req = CreateSurveyRequest(
            title=f"Survey {i}", context="ctx", goal="g",
        )
        await survey_service.create_survey(req, db_session)
    await db_session.commit()

    surveys, total = await survey_service.list_surveys(db_session)
    assert total == 3
    assert len(surveys) == 3


@pytest.mark.asyncio
async def test_survey_service_update(db_session: AsyncSession):
    """Updating a survey changes the specified fields."""
    req = CreateSurveyRequest(
        title="Original", context="ctx", goal="g",
    )
    survey = await survey_service.create_survey(req, db_session)
    await db_session.commit()

    update_req = UpdateSurveyRequest(title="Updated")
    updated = await survey_service.update_survey(survey.id, update_req, db_session)
    await db_session.commit()

    assert updated.title == "Updated"


@pytest.mark.asyncio
async def test_survey_service_delete(db_session: AsyncSession):
    """Deleting a survey soft-deletes it (is_active=False)."""
    req = CreateSurveyRequest(
        title="ToDelete", context="ctx", goal="g",
    )
    survey = await survey_service.create_survey(req, db_session)
    await db_session.commit()

    deleted = await survey_service.delete_survey(survey.id, db_session)
    await db_session.commit()

    assert deleted.is_active is False
    # get_survey filters for is_active=True, so it should be None now
    assert await survey_service.get_survey(survey.id, db_session) is None


# ---------------------------------------------------------------------------
# session_service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_service_create(db_session: AsyncSession):
    """Creating a session returns a dict with session_id, user_id, and first question."""
    # Create a survey first
    req = CreateSurveyRequest(
        title="Sess Test", context="ctx", goal="g", max_questions=5,
    )
    survey = await survey_service.create_survey(req, db_session)
    await db_session.commit()

    mock_question = "What is your experience with remote work?"
    with patch(
        "app.services.question_service.generate_question",
        new_callable=AsyncMock,
        return_value=mock_question,
    ), patch(
        "app.services.question_service.validator.estimate_goal_coverage",
        new_callable=AsyncMock,
        return_value=0.1,
    ):
        result = await session_service.create_session(
            survey.id, CreateSessionRequest(participant_name="Alice"), db_session
        )
        await db_session.commit()

    assert result is not None
    assert "session_id" in result
    assert "user_id" in result
    assert result["survey_id"] == survey.id
    assert result["status"] == "active"
    # current_question is a QuestionPayload object
    assert result["current_question"].text == mock_question


@pytest.mark.asyncio
async def test_session_service_create_survey_not_found(db_session: AsyncSession):
    """Creating a session for a nonexistent survey returns None."""
    result = await session_service.create_session(
        "nonexistent", CreateSessionRequest(), db_session
    )
    assert result is None


@pytest.mark.asyncio
async def test_session_service_exit(db_session: AsyncSession):
    """Exiting an active session marks it as exited."""
    req = CreateSurveyRequest(
        title="Exit Test", context="ctx", goal="g",
    )
    survey = await survey_service.create_survey(req, db_session)
    await db_session.commit()

    with patch(
        "app.services.question_service.generate_question",
        new_callable=AsyncMock,
        return_value="First question?",
    ), patch(
        "app.services.question_service.validator.estimate_goal_coverage",
        new_callable=AsyncMock,
        return_value=0.1,
    ):
        session_data = await session_service.create_session(
            survey.id, CreateSessionRequest(participant_name="Bob"), db_session
        )
        await db_session.commit()

    result = await session_service.exit_session(session_data["session_id"], db_session)
    await db_session.commit()

    assert result is not None
    assert result["status"] == "exited"


# ---------------------------------------------------------------------------
# question_service  (orchestration: generate → validate → return)
# ---------------------------------------------------------------------------


async def _setup_active_session(db_session: AsyncSession):
    """Helper: create a survey + active session, return (survey, session)."""
    now = datetime.now(timezone.utc).isoformat()
    survey = Survey(
        id=str(uuid.uuid4()),
        title="Q-Service Test",
        context="ctx",
        goal="g",
        constraints="[]",
        max_questions=5,
        completion_criteria="",
        goal_coverage_threshold=0.85,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(survey)

    user = User(
        id=str(uuid.uuid4()),
        participant_name="Tester",
        metadata_="{}",
        created_at=now,
    )
    db_session.add(user)
    await db_session.flush()

    session = Session(
        id=str(uuid.uuid4()),
        survey_id=survey.id,
        user_id=user.id,
        status="active",
        question_count=0,
        created_at=now,
    )
    db_session.add(session)
    await db_session.flush()

    return survey, session


@pytest.mark.asyncio
async def test_question_service_generate_next_question(db_session: AsyncSession):
    """generate_next_question returns a QuestionPayload when under limit."""
    survey, session = await _setup_active_session(db_session)

    with patch(
        "app.services.question_service.generate_question",
        new_callable=AsyncMock,
        return_value="What motivates you at work?",
    ), patch(
        "app.services.question_service.validator.estimate_goal_coverage",
        new_callable=AsyncMock,
        return_value=0.1,
    ):
        payload = await question_service.generate_next_question(session, survey, db_session)

    assert payload is not None
    assert isinstance(payload, QuestionPayload)
    assert payload.text == "What motivates you at work?"
    assert payload.question_number == 1


@pytest.mark.asyncio
async def test_question_service_returns_none_at_max(db_session: AsyncSession):
    """generate_next_question returns None when max questions are reached."""
    survey, session = await _setup_active_session(db_session)
    session.question_count = survey.max_questions  # at limit

    with patch(
        "app.services.question_service.generate_question",
        new_callable=AsyncMock,
    ) as mock_gen:
        payload = await question_service.generate_next_question(session, survey, db_session)

    assert payload is None
    mock_gen.assert_not_called()


@pytest.mark.asyncio
async def test_question_service_process_answer(db_session: AsyncSession):
    """process_answer stores the response and returns the next question."""
    survey, session = await _setup_active_session(db_session)

    with patch(
        "app.services.question_service.generate_question",
        new_callable=AsyncMock,
        return_value="Follow-up question?",
    ), patch(
        "app.services.question_service.validator.estimate_goal_coverage",
        new_callable=AsyncMock,
        return_value=0.1,
    ):
        result = await question_service.process_answer(
            session_id=session.id,
            survey_id=survey.id,
            answer="My answer",
            question_id=str(uuid.uuid4()),
            question_text="First question?",
            question_number=1,
            db=db_session,
        )

    assert result["status"] == "active"
    assert result["question"]["text"] == "Follow-up question?"


@pytest.mark.asyncio
async def test_question_service_process_answer_completes(db_session: AsyncSession):
    """process_answer completes the session when max questions are reached."""
    survey, session = await _setup_active_session(db_session)
    # Set question_count to max so generate_next_question detects
    # the limit immediately (check happens before update)
    session.question_count = survey.max_questions

    with patch(
        "app.services.question_service.validator.estimate_goal_coverage",
        new_callable=AsyncMock,
        return_value=0.1,
    ):
        result = await question_service.process_answer(
            session_id=session.id,
            survey_id=survey.id,
            answer="Final answer",
            question_id=str(uuid.uuid4()),
            question_text="Last question?",
            question_number=survey.max_questions,
            db=db_session,
        )

    assert result["status"] == "completed"
    assert result["question"] is None
    assert result["completion_reason"] == "max_questions_reached"
