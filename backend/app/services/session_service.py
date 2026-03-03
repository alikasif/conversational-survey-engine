"""Session lifecycle service."""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.models.user import User
from app.repositories import response_repo, session_repo, survey_repo
from app.schemas.session import (
    ConversationEntry,
    CreateSessionRequest,
    SessionDetailResponse,
)
from app.services import question_service


async def create_session(
    survey_id: str, request: CreateSessionRequest, db: AsyncSession
) -> dict:
    """Create a new session with user, and generate the first question."""
    # Verify survey exists
    survey = await survey_repo.get_by_id(db, survey_id)
    if not survey:
        return None

    now = datetime.now(timezone.utc).isoformat()

    # Create user
    user = User(
        id=str(uuid.uuid4()),
        participant_name=request.participant_name,
        metadata_=json.dumps(request.metadata),
        created_at=now,
    )
    db.add(user)
    await db.flush()

    # Create session
    session = Session(
        id=str(uuid.uuid4()),
        survey_id=survey_id,
        user_id=user.id,
        status="active",
        question_count=0,
        created_at=now,
    )
    await session_repo.create(db, session)

    # Commit user + session BEFORE the slow LLM call so we don't hold
    # the SQLite write lock during question generation.
    await db.commit()

    # Generate first question
    question_payload = await question_service.generate_next_question(
        session=session, survey=survey, db=db
    )

    return {
        "session_id": session.id,
        "user_id": user.id,
        "survey_id": survey_id,
        "status": session.status,
        "current_question": question_payload,
        "question_number": session.question_count,
        "max_questions": survey.max_questions,
        "created_at": session.created_at,
    }


async def get_session(
    session_id: str, db: AsyncSession
) -> Optional[SessionDetailResponse]:
    """Get session with conversation history."""
    session = await session_repo.get_by_id(db, session_id)
    if not session:
        return None

    responses = await response_repo.get_by_session(db, session_id)
    conversation = [
        ConversationEntry(
            question_id=r.question_id,
            question_text=r.question_text,
            answer_text=r.answer_text,
            question_number=r.question_number,
            answered_at=r.created_at,
        )
        for r in responses
    ]

    return SessionDetailResponse(
        session_id=session.id,
        user_id=session.user_id,
        survey_id=session.survey_id,
        status=session.status,
        conversation=conversation,
        question_count=session.question_count,
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


async def exit_session(session_id: str, db: AsyncSession) -> Optional[dict]:
    """Mark a session as exited."""
    session = await session_repo.get_by_id(db, session_id)
    if not session:
        return None

    if session.status != "active":
        return {"error": "Session is not active", "status": session.status}

    now = datetime.now(timezone.utc).isoformat()
    await session_repo.update_status(
        db, session, status="exited", completion_reason="user_exited", completed_at=now
    )

    return {
        "session_id": session.id,
        "status": "exited",
        "question_count": session.question_count,
        "message": "Session exited successfully. Thank you for your participation!",
    }


async def get_survey_sessions(
    survey_id: str, db: AsyncSession, skip: int = 0, limit: int = 20
) -> tuple[List[SessionDetailResponse], int]:
    """Get all sessions for a survey with conversation details."""
    sessions = await session_repo.get_by_survey(db, survey_id, skip=skip, limit=limit)
    total = await session_repo.count_by_survey(db, survey_id)

    result = []
    for session in sessions:
        responses = await response_repo.get_by_session(db, session.id)
        conversation = [
            ConversationEntry(
                question_id=r.question_id,
                question_text=r.question_text,
                answer_text=r.answer_text,
                question_number=r.question_number,
                answered_at=r.created_at,
            )
            for r in responses
        ]
        result.append(
            SessionDetailResponse(
                session_id=session.id,
                user_id=session.user_id,
                survey_id=session.survey_id,
                status=session.status,
                conversation=conversation,
                question_count=session.question_count,
                created_at=session.created_at,
                completed_at=session.completed_at,
            )
        )

    return result, total
