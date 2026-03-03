"""Pydantic request/response models for the LLM service API."""

from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# /generate-question
# ---------------------------------------------------------------------------

class GenerateQuestionRequest(BaseModel):
    """Request body for POST /generate-question."""

    survey_context: str
    goal: str
    constraints: str | list = "[]"
    conversation_history: List[List[str]] = Field(
        default_factory=list,
        description="List of [question, answer] pairs",
    )
    question_number: int = 1
    max_questions: int = 10
    goal_coverage_threshold: float = 0.85
    rejection_guardrail_hint: Optional[str] = None

    @property
    def history_tuples(self) -> List[Tuple[str, str]]:
        """Convert list-of-lists to list-of-tuples for agent functions."""
        return [(h[0], h[1]) for h in self.conversation_history if len(h) >= 2]


class GenerateQuestionResponse(BaseModel):
    """Response body for POST /generate-question."""

    question_text: str
    question_id: str


# ---------------------------------------------------------------------------
# /validate-question
# ---------------------------------------------------------------------------

class ValidateQuestionRequest(BaseModel):
    """Request body for POST /validate-question."""

    question: str
    survey_context: str = ""
    goal: str = ""
    conversation_history: List[List[str]] = Field(default_factory=list)

    @property
    def history_tuples(self) -> List[Tuple[str, str]]:
        return [(h[0], h[1]) for h in self.conversation_history if len(h) >= 2]


class ValidateQuestionResponse(BaseModel):
    """Response body for POST /validate-question."""

    is_valid: bool
    issues: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# /check-guardrails
# ---------------------------------------------------------------------------

class CheckGuardrailsRequest(BaseModel):
    """Request body for POST /check-guardrails."""

    answer: str
    question: str = ""


class CheckGuardrailsResponse(BaseModel):
    """Response body for POST /check-guardrails."""

    is_valid: bool
    flags: List[str] = Field(default_factory=list)
    rejection_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# /generate-preset-questions
# ---------------------------------------------------------------------------

class GeneratePresetRequest(BaseModel):
    """Request body for POST /generate-preset-questions."""

    survey_context: str
    goal: str
    constraints: str | list = "[]"
    count: int = 10


class PresetQuestion(BaseModel):
    question_number: int
    question_id: str
    text: str


class GeneratePresetResponse(BaseModel):
    """Response body for POST /generate-preset-questions."""

    questions: List[PresetQuestion]
