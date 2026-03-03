"""Question generation orchestration service."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.llm_client import llm_client
from app.agents.answer_guardrails import check_answer, flags_to_json
from app.agents.validator import QuestionValidator
from app.models.response import Response
from app.models.session import Session
from app.models.survey import Survey
from app.repositories import response_repo, session_repo, survey_repo
from app.schemas.session import QuestionPayload

logger = logging.getLogger(__name__)

validator = QuestionValidator()


async def generate_next_question(
    session: Session,
    survey: Survey,
    db: AsyncSession,
    rejection_guardrail_hint: str | None = None,
) -> Optional[QuestionPayload]:
    """Generate the next question for a session.

    Core orchestration:
    1. Branch by survey question_mode (preset vs dynamic)
    2. For dynamic: check stopping conditions, generate via LLM
    3. For preset: serve from pre-generated question list
    """
    # Preset mode — serve from stored question list, no LLM calls
    if survey.question_mode == "preset":
        return await _get_next_preset_question(survey, session, db)

    # Dynamic mode — existing behavior below
    # Check max questions
    if validator.check_max_questions(session.question_count, survey.max_questions):
        now = datetime.now(timezone.utc).isoformat()
        await session_repo.update_status(
            db,
            session,
            status="completed",
            completion_reason="max_questions_reached",
            completed_at=now,
        )
        return None

    # Get conversation history
    responses = await response_repo.get_by_session(db, session.id)
    conversation_history = [
        (r.question_text, r.answer_text) for r in responses
    ]

    # Check goal coverage
    if conversation_history:
        coverage = await validator.estimate_goal_coverage(
            conversation_history, survey.goal
        )
        if coverage >= survey.goal_coverage_threshold:
            now = datetime.now(timezone.utc).isoformat()
            await session_repo.update_status(
                db,
                session,
                status="completed",
                completion_reason="goal_coverage_met",
                completed_at=now,
            )
            return None

    # Generate question via LLM service
    question_number = session.question_count + 1
    result = await llm_client.generate_question(
        survey_context=survey.context,
        goal=survey.goal,
        constraints=survey.constraints,
        conversation_history=[
            [q, a] for q, a in conversation_history
        ],
        question_number=question_number,
        max_questions=survey.max_questions,
        goal_coverage_threshold=survey.goal_coverage_threshold,
        rejection_guardrail_hint=rejection_guardrail_hint,
    )

    question_text = result["question_text"]
    question_id = result["question_id"]

    # Update session question count
    await session_repo.update_question_count(db, session, question_number)

    return QuestionPayload(
        question_id=question_id,
        text=question_text,
        question_number=question_number,
    )


async def _get_next_preset_question(
    survey: Survey, session: Session, db: AsyncSession
) -> Optional[QuestionPayload]:
    """Serve the next preset question from the stored list.

    No LLM calls, no goal coverage check — just JSON lookup.

    Returns:
        QuestionPayload for the next question, or None if all served.

    Raises:
        ValueError: If preset questions haven't been generated yet.
    """
    if not survey.preset_questions:
        raise ValueError("Preset questions not yet generated for this survey.")

    questions = json.loads(survey.preset_questions)
    current_index = session.question_count  # 0-based

    if current_index >= len(questions):
        now = datetime.now(timezone.utc).isoformat()
        await session_repo.update_status(
            db,
            session,
            status="completed",
            completion_reason="all_preset_questions_served",
            completed_at=now,
        )
        return None

    preset_q = questions[current_index]
    question_number = current_index + 1

    # Update session question count
    await session_repo.update_question_count(db, session, question_number)

    return QuestionPayload(
        question_id=preset_q.get("question_id", str(uuid.uuid4())),
        text=preset_q["text"],
        question_number=question_number,
    )


async def process_answer(
    session_id: str,
    survey_id: str,
    answer: str,
    question_id: str,
    question_text: str,
    question_number: int,
    db: AsyncSession,
) -> dict:
    """Process an answer and generate the next question.

    1. Store Q/A pair
    2. Check stopping conditions
    3. Generate next question if needed
    """
    session = await session_repo.get_by_id(db, session_id)
    if not session:
        return {"error": "Session not found"}

    if session.status != "active":
        return {
            "error": "Session is not active",
            "session_id": session_id,
            "status": session.status,
        }

    survey = await survey_repo.get_by_id(db, survey_id)
    if not survey:
        return {"error": "Survey not found"}

    now = datetime.now(timezone.utc).isoformat()

    # --- Guardrail check ---
    guardrail_result = check_answer(answer)

    # Store the response (always — never reject)
    response = Response(
        id=str(uuid.uuid4()),
        session_id=session_id,
        survey_id=survey_id,
        user_id=session.user_id,
        question_id=question_id,
        question_text=question_text,
        answer_text=answer,
        question_number=question_number,
        answer_flags=flags_to_json(guardrail_result.flags),
        created_at=now,
    )
    await response_repo.create(db, response)

    # Generate next question (handles stopping conditions internally)
    next_question = await generate_next_question(
        session=session,
        survey=survey,
        db=db,
        rejection_guardrail_hint=guardrail_result.rejection_hint,
    )

    if next_question is None:
        # Session completed
        # Refresh session to get updated status
        session = await session_repo.get_by_id(db, session_id)
        return {
            "session_id": session_id,
            "status": session.status,
            "question": None,
            "completion_reason": session.completion_reason,
            "question_number": session.question_count,
            "max_questions": survey.max_questions,
        }

    return {
        "session_id": session_id,
        "status": "active",
        "question": {
            "question_id": next_question.question_id,
            "text": next_question.text,
            "question_number": next_question.question_number,
        },
        "completion_reason": None,
        "question_number": next_question.question_number,
        "max_questions": survey.max_questions,
    }
