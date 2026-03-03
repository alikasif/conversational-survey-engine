"""Session data access repository."""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


async def create(db: AsyncSession, session: Session) -> Session:
    """Create a new session."""
    db.add(session)
    await db.flush()
    return session


async def get_by_id(db: AsyncSession, session_id: str) -> Optional[Session]:
    """Get a session by ID."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    return result.scalar_one_or_none()


async def update_status(
    db: AsyncSession,
    session: Session,
    status: str,
    completion_reason: Optional[str] = None,
    completed_at: Optional[str] = None,
) -> Session:
    """Update session status."""
    session.status = status
    if completion_reason:
        session.completion_reason = completion_reason
    if completed_at:
        session.completed_at = completed_at
    await db.flush()
    return session


async def update_question_count(
    db: AsyncSession, session: Session, count: int
) -> Session:
    """Update the question count for a session."""
    session.question_count = count
    await db.flush()
    return session


async def get_by_survey(
    db: AsyncSession, survey_id: str, skip: int = 0, limit: int = 20
) -> List[Session]:
    """List sessions for a survey."""
    result = await db.execute(
        select(Session)
        .where(Session.survey_id == survey_id)
        .order_by(Session.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_by_survey(db: AsyncSession, survey_id: str) -> int:
    """Count sessions for a survey."""
    result = await db.execute(
        select(func.count(Session.id)).where(Session.survey_id == survey_id)
    )
    return result.scalar_one()
