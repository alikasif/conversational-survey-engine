"""Survey Pydantic schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CreateSurveyRequest(BaseModel):
    """Request schema for creating a survey."""

    title: str
    context: str
    goal: str
    constraints: List[str] = Field(default_factory=list)
    max_questions: int = 10
    completion_criteria: str = ""
    goal_coverage_threshold: float = 0.85
    context_similarity_threshold: float = 0.7


class UpdateSurveyRequest(BaseModel):
    """Request schema for updating a survey."""

    title: Optional[str] = None
    context: Optional[str] = None
    goal: Optional[str] = None
    constraints: Optional[List[str]] = None
    max_questions: Optional[int] = None
    completion_criteria: Optional[str] = None
    goal_coverage_threshold: Optional[float] = None
    context_similarity_threshold: Optional[float] = None


class SurveyResponse(BaseModel):
    """Response schema for a survey."""

    id: str
    title: str
    context: str
    goal: str
    constraints: List[str]
    max_questions: int
    completion_criteria: str
    goal_coverage_threshold: float
    context_similarity_threshold: float
    is_active: bool
    created_at: str
    updated_at: str


class SurveyListResponse(BaseModel):
    """Response schema for listing surveys."""

    surveys: List[SurveyResponse]
    total: int
    skip: int
    limit: int


class SurveyDetailResponse(SurveyResponse):
    """Response schema for survey detail with stats."""

    total_sessions: int = 0
    completed_sessions: int = 0
    avg_questions_per_session: float = 0.0


class SurveyStatsResponse(BaseModel):
    """Response schema for survey statistics."""

    survey_id: str
    total_sessions: int
    completed_sessions: int
    abandoned_sessions: int
    avg_questions_per_session: float
    avg_completion_time_seconds: float
    top_themes: List[str]
