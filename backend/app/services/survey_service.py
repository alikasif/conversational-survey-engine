"""Survey CRUD service."""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.survey import Survey
from app.repositories import survey_repo
from app.schemas.survey import CreateSurveyRequest, UpdateSurveyRequest


async def create_survey(
    request: CreateSurveyRequest, db: AsyncSession
) -> Survey:
    """Create a new survey."""
    now = datetime.now(timezone.utc).isoformat()
    survey = Survey(
        id=str(uuid.uuid4()),
        title=request.title,
        context=request.context,
        goal=request.goal,
        constraints=json.dumps(request.constraints),
        max_questions=request.max_questions,
        completion_criteria=request.completion_criteria,
        goal_coverage_threshold=request.goal_coverage_threshold,
        context_similarity_threshold=request.context_similarity_threshold,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    return await survey_repo.create(db, survey)


async def get_survey(survey_id: str, db: AsyncSession) -> Optional[Survey]:
    """Get a survey by ID."""
    return await survey_repo.get_by_id(db, survey_id)


async def list_surveys(
    db: AsyncSession, skip: int = 0, limit: int = 20
) -> tuple[List[Survey], int]:
    """List all surveys with pagination."""
    surveys = await survey_repo.list_all(db, skip=skip, limit=limit)
    total = await survey_repo.count_total(db)
    return surveys, total


async def update_survey(
    survey_id: str, request: UpdateSurveyRequest, db: AsyncSession
) -> Optional[Survey]:
    """Update an existing survey."""
    survey = await survey_repo.get_by_id(db, survey_id)
    if not survey:
        return None

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "constraints" and value is not None:
            setattr(survey, field, json.dumps(value))
        else:
            setattr(survey, field, value)

    survey.updated_at = datetime.now(timezone.utc).isoformat()
    return await survey_repo.update(db, survey)


async def delete_survey(
    survey_id: str, db: AsyncSession
) -> Optional[Survey]:
    """Soft delete a survey."""
    survey = await survey_repo.get_by_id(db, survey_id)
    if not survey:
        return None
    return await survey_repo.soft_delete(db, survey)


async def get_survey_stats(survey_id: str, db: AsyncSession) -> Optional[dict]:
    """Get survey statistics."""
    survey = await survey_repo.get_by_id(db, survey_id)
    if not survey:
        return None
    return await survey_repo.get_stats(db, survey_id)
