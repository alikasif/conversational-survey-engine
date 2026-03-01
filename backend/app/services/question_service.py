"""Question generation orchestration service."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.generator_agent import generate_question
from app.agents.validator import QuestionValidator
from app.models.response import Response
from app.models.session import Session
from app.models.survey import Survey
from app.repositories import response_repo, session_repo
from app.schemas.session import QuestionPayload

logger = logging.getLogger(__name__)

validator = QuestionValidator()


async def generate_next_question(
    session: Session,
    survey: Survey,
    db: AsyncSession,
) -> Optional[QuestionPayload]:
    """Generate the next question for a session.

    Core orchestration:
    1. Check if max questions reached
    2. Get conversation history from DB
    3. Invoke generator agent
    4. Return question payload
    """
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

    # Generate question
    question_number = session.question_count + 1
    question_text = await generate_question(
        survey=survey,
        conversation_history=conversation_history,
        question_number=question_number,
    )

    question_id = str(uuid.uuid4())

    # Update session question count
    await session_repo.update_question_count(db, session, question_number)

    return QuestionPayload(
        question_id=question_id,
        text=question_text,
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

    from app.repositories import survey_repo

    survey = await survey_repo.get_by_id(db, survey_id)
    if not survey:
        return {"error": "Survey not found"}

    now = datetime.now(timezone.utc).isoformat()

    # Store the response
    response = Response(
        id=str(uuid.uuid4()),
        session_id=session_id,
        survey_id=survey_id,
        user_id=session.user_id,
        question_id=question_id,
        question_text=question_text,
        answer_text=answer,
        question_number=question_number,
        created_at=now,
    )
    await response_repo.create(db, response)

    # Generate next question (handles stopping conditions internally)
    next_question = await generate_next_question(
        session=session, survey=survey, db=db
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
