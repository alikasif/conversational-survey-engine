"""Response Pydantic schemas."""

from typing import List, Optional

from pydantic import BaseModel

from app.schemas.session import SessionDetailResponse


class SubmitAnswerRequest(BaseModel):
    """Request schema for submitting an answer."""

    answer: str
    question_id: Optional[str] = None
    question_text: Optional[str] = None


class ResponseListResponse(BaseModel):
    """Response schema for listing session responses."""

    responses: List[SessionDetailResponse]
    total: int
    skip: int
    limit: int
