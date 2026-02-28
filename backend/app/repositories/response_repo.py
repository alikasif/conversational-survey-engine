"""Response data access repository."""

from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.response import Response


async def create(db: AsyncSession, response: Response) -> Response:
    """Create a new response (atomic write)."""
    db.add(response)
    await db.flush()
    return response


async def get_by_session(db: AsyncSession, session_id: str) -> List[Response]:
    """Get all responses for a session ordered by question number."""
    result = await db.execute(
        select(Response)
        .where(Response.session_id == session_id)
        .order_by(Response.question_number.asc())
    )
    return list(result.scalars().all())


async def get_by_survey(
    db: AsyncSession, survey_id: str, skip: int = 0, limit: int = 20
) -> List[Response]:
    """Get all responses for a survey with pagination."""
    result = await db.execute(
        select(Response)
        .where(Response.survey_id == survey_id)
        .order_by(Response.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_by_survey(db: AsyncSession, survey_id: str) -> int:
    """Count total responses for a survey."""
    result = await db.execute(
        select(func.count(Response.id)).where(Response.survey_id == survey_id)
    )
    return result.scalar_one()
