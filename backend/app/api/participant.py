"""Participant API endpoints for survey sessions."""

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.repositories import session_repo
from app.schemas.response import SubmitAnswerRequest
from app.schemas.session import (
    CreateSessionRequest,
    NextQuestionResponse,
    SessionCompleteResponse,
    SessionDetailResponse,
    SessionResponse,
)
from app.services import question_service, session_service

router = APIRouter(prefix="/surveys", tags=["participant"])

# ---------------------------------------------------------------------------
# Per-session rate limiting (in-memory)
# ---------------------------------------------------------------------------
_rate_limit_tracker: dict[str, float] = {}
RATE_LIMIT_SECONDS = 2.0


def check_rate_limit(session_id: str) -> None:
    """Raise HTTP 429 if the same session submits faster than the threshold."""
    now = time.monotonic()
    last = _rate_limit_tracker.get(session_id)
    if last is not None and (now - last) < RATE_LIMIT_SECONDS:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait before submitting another answer.",
        )
    _rate_limit_tracker[session_id] = now

    # Periodic cleanup — keep tracker from growing unbounded
    if len(_rate_limit_tracker) > 1000:
        cutoff = now - 60.0
        stale = [k for k, v in _rate_limit_tracker.items() if v < cutoff]
        for k in stale:
            del _rate_limit_tracker[k]


@router.post(
    "/{survey_id}/sessions",
    response_model=SessionResponse,
    status_code=201,
)
async def create_session(
    survey_id: str,
    request: CreateSessionRequest = CreateSessionRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Start a new survey session and get the first question."""
    result = await session_service.create_session(survey_id, request, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Survey not found")
    return SessionResponse(**result)


@router.post(
    "/{survey_id}/sessions/{session_id}/respond",
    response_model=NextQuestionResponse,
)
async def submit_answer(
    survey_id: str,
    session_id: str,
    request: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit an answer and get the next question or completion."""
    # Rate-limit check
    check_rate_limit(session_id)

    # Verify session exists and is active
    session = await session_repo.get_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(
            status_code=409,
            detail=f"Session is already {session.status}",
        )
    if session.survey_id != survey_id:
        raise HTTPException(status_code=404, detail="Session not found for this survey")

    # Get current question number based on existing responses
    from app.repositories import response_repo as resp_repo

    responses = await resp_repo.get_by_session(db, session_id)
    question_number = len(responses) + 1

    question_id = request.question_id or str(uuid.uuid4())
    question_text = request.question_text or f"Question {question_number}"

    result = await question_service.process_answer(
        session_id=session_id,
        survey_id=survey_id,
        answer=request.answer,
        question_id=question_id,
        question_text=question_text,
        question_number=question_number,
        db=db,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return NextQuestionResponse(**result)


@router.get(
    "/{survey_id}/sessions/{session_id}",
    response_model=SessionDetailResponse,
)
async def get_session(
    survey_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the current state of a session."""
    session_detail = await session_service.get_session(session_id, db)
    if not session_detail:
        raise HTTPException(status_code=404, detail="Session not found")
    if session_detail.survey_id != survey_id:
        raise HTTPException(status_code=404, detail="Session not found for this survey")
    return session_detail


@router.post(
    "/{survey_id}/sessions/{session_id}/exit",
    response_model=SessionCompleteResponse,
)
async def exit_session(
    survey_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Exit a session early."""
    result = await session_service.exit_session(session_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return SessionCompleteResponse(**result)
