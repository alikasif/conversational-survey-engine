"""Survey data access repository."""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.models.survey import Survey


async def create(db: AsyncSession, survey: Survey) -> Survey:
    """Create a new survey."""
    db.add(survey)
    await db.flush()
    return survey


async def get_by_id(db: AsyncSession, survey_id: str) -> Optional[Survey]:
    """Get a survey by ID."""
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.is_active == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def list_all(
    db: AsyncSession, skip: int = 0, limit: int = 20
) -> List[Survey]:
    """List all active surveys with pagination."""
    result = await db.execute(
        select(Survey)
        .where(Survey.is_active == True)  # noqa: E712
        .order_by(Survey.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_total(db: AsyncSession) -> int:
    """Count total active surveys."""
    result = await db.execute(
        select(func.count(Survey.id)).where(Survey.is_active == True)  # noqa: E712
    )
    return result.scalar_one()


async def update(db: AsyncSession, survey: Survey) -> Survey:
    """Update an existing survey."""
    await db.flush()
    return survey


async def soft_delete(db: AsyncSession, survey: Survey) -> Survey:
    """Soft delete a survey by setting is_active=False."""
    survey.is_active = False
    await db.flush()
    return survey


async def get_stats(db: AsyncSession, survey_id: str) -> dict:
    """Get statistics for a survey."""
    # Total sessions
    total_result = await db.execute(
        select(func.count(Session.id)).where(Session.survey_id == survey_id)
    )
    total_sessions = total_result.scalar_one()

    # Completed sessions
    completed_result = await db.execute(
        select(func.count(Session.id)).where(
            Session.survey_id == survey_id, Session.status == "completed"
        )
    )
    completed_sessions = completed_result.scalar_one()

    # Abandoned (exited) sessions
    abandoned_result = await db.execute(
        select(func.count(Session.id)).where(
            Session.survey_id == survey_id, Session.status == "exited"
        )
    )
    abandoned_sessions = abandoned_result.scalar_one()

    # Average questions per session
    avg_result = await db.execute(
        select(func.avg(Session.question_count)).where(
            Session.survey_id == survey_id
        )
    )
    avg_questions = avg_result.scalar_one() or 0.0

    return {
        "survey_id": survey_id,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "abandoned_sessions": abandoned_sessions,
        "avg_questions_per_session": round(float(avg_questions), 2),
        "avg_completion_time_seconds": 0.0,
        "top_themes": [],
    }
