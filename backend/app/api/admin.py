"""Admin API endpoints for survey management."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.response import ResponseListResponse
from app.schemas.survey import (
    CreateSurveyRequest,
    SurveyDetailResponse,
    SurveyListResponse,
    SurveyResponse,
    SurveyStatsResponse,
    UpdateSurveyRequest,
)
from app.services import session_service, survey_service

router = APIRouter(prefix="/admin/surveys", tags=["admin"])


def _survey_to_response(survey) -> SurveyResponse:
    """Convert a Survey ORM model to SurveyResponse."""
    constraints = survey.constraints
    if isinstance(constraints, str):
        try:
            constraints = json.loads(constraints)
        except (json.JSONDecodeError, TypeError):
            constraints = []
    return SurveyResponse(
        id=survey.id,
        title=survey.title,
        context=survey.context,
        goal=survey.goal,
        constraints=constraints,
        max_questions=survey.max_questions,
        completion_criteria=survey.completion_criteria,
        goal_coverage_threshold=survey.goal_coverage_threshold,
        context_similarity_threshold=survey.context_similarity_threshold,
        is_active=survey.is_active,
        created_at=survey.created_at,
        updated_at=survey.updated_at,
    )


@router.post("", response_model=SurveyResponse, status_code=201)
async def create_survey(
    request: CreateSurveyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new survey."""
    survey = await survey_service.create_survey(request, db)
    return _survey_to_response(survey)


@router.get("", response_model=SurveyListResponse)
async def list_surveys(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all surveys with pagination."""
    surveys, total = await survey_service.list_surveys(db, skip=skip, limit=limit)
    return SurveyListResponse(
        surveys=[_survey_to_response(s) for s in surveys],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{survey_id}", response_model=SurveyDetailResponse)
async def get_survey(
    survey_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a survey by ID with session stats."""
    survey = await survey_service.get_survey(survey_id, db)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    stats = await survey_service.get_survey_stats(survey_id, db)
    base = _survey_to_response(survey)
    return SurveyDetailResponse(
        **base.model_dump(),
        total_sessions=stats["total_sessions"],
        completed_sessions=stats["completed_sessions"],
        avg_questions_per_session=stats["avg_questions_per_session"],
    )


@router.put("/{survey_id}", response_model=SurveyResponse)
async def update_survey(
    survey_id: str,
    request: UpdateSurveyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing survey."""
    survey = await survey_service.update_survey(survey_id, request, db)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return _survey_to_response(survey)


@router.delete("/{survey_id}", status_code=204)
async def delete_survey(
    survey_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete (soft) a survey."""
    survey = await survey_service.delete_survey(survey_id, db)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return None


@router.get("/{survey_id}/responses", response_model=ResponseListResponse)
async def get_survey_responses(
    survey_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get all responses for a survey."""
    survey = await survey_service.get_survey(survey_id, db)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    sessions, total = await session_service.get_survey_sessions(
        survey_id, db, skip=skip, limit=limit
    )
    return ResponseListResponse(
        responses=sessions,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{survey_id}/stats", response_model=SurveyStatsResponse)
async def get_survey_stats(
    survey_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get statistics for a survey."""
    stats = await survey_service.get_survey_stats(survey_id, db)
    if not stats:
        raise HTTPException(status_code=404, detail="Survey not found")
    return SurveyStatsResponse(**stats)
