"""Response Pydantic schemas."""

from typing import Annotated, List, Optional

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.session import SessionDetailResponse

StrippedStr = Annotated[str, StringConstraints(strip_whitespace=True)]


class SubmitAnswerRequest(BaseModel):
    """Request schema for submitting an answer."""

    answer: StrippedStr = Field(min_length=1, max_length=2000)
    question_id: Optional[str] = None
    question_text: Optional[str] = None


class ResponseListResponse(BaseModel):
    """Response schema for listing session responses."""

    responses: List[SessionDetailResponse]
    total: int
    skip: int
    limit: int
