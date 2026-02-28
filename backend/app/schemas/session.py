"""Session Pydantic schemas."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Request schema for creating a session."""

    participant_name: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class QuestionPayload(BaseModel):
    """Question data payload."""

    question_id: str
    text: str
    question_number: int


class SessionResponse(BaseModel):
    """Response schema after creating a session."""

    session_id: str
    user_id: str
    survey_id: str
    status: str
    current_question: QuestionPayload
    question_number: int
    max_questions: int
    created_at: str


class NextQuestionResponse(BaseModel):
    """Response schema for the next question or completion."""

    session_id: str
    status: str
    question: Optional[QuestionPayload] = None
    completion_reason: Optional[str] = None
    question_number: int
    max_questions: int


class ConversationEntry(BaseModel):
    """A single Q&A entry in the conversation."""

    question_id: str
    question_text: str
    answer_text: str
    question_number: int
    answered_at: str


class SessionDetailResponse(BaseModel):
    """Detailed session response with conversation history."""

    session_id: str
    user_id: str
    survey_id: str
    status: str
    conversation: List[ConversationEntry]
    question_count: int
    created_at: str
    completed_at: Optional[str] = None


class SessionCompleteResponse(BaseModel):
    """Response schema for exiting a session."""

    session_id: str
    status: str
    question_count: int
    message: str
