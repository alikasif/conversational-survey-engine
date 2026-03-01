"""Tests for the QuestionValidator (rule-based + mocked LLM checks)."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.validator import QuestionValidator


@pytest.fixture()
def validator():
    return QuestionValidator()


def _make_llm_response(content: dict | str) -> SimpleNamespace:
    """Build a mock LLM response object matching litellm's shape."""
    if isinstance(content, dict):
        content = json.dumps(content)
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )


def _all_pass_response() -> SimpleNamespace:
    """Return a mock response where all 4 criteria pass."""
    return _make_llm_response({
        "redundancy": {"pass": True, "reason": None},
        "goal_alignment": {"pass": True, "reason": None},
        "context_relevance": {"pass": True, "reason": None},
        "topic_drift": {"pass": True, "reason": None},
    })


def _fail_criterion(criterion: str, reason: str) -> SimpleNamespace:
    """Return a mock response where one specific criterion fails."""
    data = {
        "redundancy": {"pass": True, "reason": None},
        "goal_alignment": {"pass": True, "reason": None},
        "context_relevance": {"pass": True, "reason": None},
        "topic_drift": {"pass": True, "reason": None},
    }
    data[criterion] = {"pass": False, "reason": reason}
    return _make_llm_response(data)


class FakeSurvey:
    goal = "Understand employee satisfaction"
    constraints = "[]"
    context = "Employee well-being study"
    context_similarity_threshold = 0.7


# ---------------------------------------------------------------------------
# Compound-question checks (rule-based, no mocking needed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_compound_question_multiple_question_marks(validator):
    """Multiple question marks flag a compound question."""
    is_compound, reason = validator.check_compound_question(
        "What is your role? And how long have you been in it?"
    )
    assert is_compound is True
    assert "compound" in reason.lower()


@pytest.mark.asyncio
async def test_check_compound_question_interrogative_and(validator):
    """Two interrogative clauses joined by 'and' are flagged."""
    is_compound, reason = validator.check_compound_question(
        "What is your role and how long have you been in it"
    )
    assert is_compound is True


@pytest.mark.asyncio
async def test_check_not_compound(validator):
    """A simple single question passes the compound check."""
    is_compound, reason = validator.check_compound_question(
        "What is your current role?"
    )
    assert is_compound is False
    assert reason is None


# ---------------------------------------------------------------------------
# Leading-question checks (rule-based)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_leading_question_dont_you_think(validator):
    """'Don't you think ...' is flagged as leading."""
    is_leading, reason = validator.check_leading_question(
        "Don't you think remote work is bad?"
    )
    assert is_leading is True
    assert "leading" in reason.lower()


@pytest.mark.asyncio
async def test_check_leading_question_surely(validator):
    """'Surely you ...' is flagged as leading."""
    is_leading, reason = validator.check_leading_question(
        "Surely you agree that the policy is unfair?"
    )
    assert is_leading is True


@pytest.mark.asyncio
async def test_check_leading_question_everyone_knows(validator):
    """'Everyone knows ...' is flagged as leading."""
    is_leading, reason = validator.check_leading_question(
        "Everyone knows remote work is less productive, right?"
    )
    assert is_leading is True


@pytest.mark.asyncio
async def test_check_not_leading(validator):
    """A neutral question passes the leading check."""
    is_leading, reason = validator.check_leading_question(
        "What do you think about the remote work policy?"
    )
    assert is_leading is False
    assert reason is None


# ---------------------------------------------------------------------------
# Max-questions check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_max_questions_at_limit(validator):
    """At the limit, check_max_questions returns True."""
    assert validator.check_max_questions(10, 10) is True


@pytest.mark.asyncio
async def test_check_max_questions_over_limit(validator):
    """Over the limit, check_max_questions returns True."""
    assert validator.check_max_questions(11, 10) is True


@pytest.mark.asyncio
async def test_check_max_questions_under_limit(validator):
    """Under the limit, check_max_questions returns False."""
    assert validator.check_max_questions(3, 10) is False


# ---------------------------------------------------------------------------
# LLM-based validation (litellm.acompletion mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_with_llm_all_pass(validator):
    """All 4 LLM criteria pass → question is valid."""
    with patch(
        "app.agents.validator.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=_all_pass_response(),
    ):
        is_valid, reason = await validator.validate_with_llm(
            "How do you feel about the recent changes?",
            FakeSurvey(),
            [],
        )
    assert is_valid is True
    assert reason is None


@pytest.mark.asyncio
async def test_validate_with_llm_redundancy_fail(validator):
    """Redundancy criterion fails → question is rejected."""
    with patch(
        "app.agents.validator.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=_fail_criterion("redundancy", "Too similar to Q1."),
    ):
        is_valid, reason = await validator.validate_with_llm(
            "What is your role?",
            FakeSurvey(),
            [("What is your role?", "I'm a developer.")],
        )
    assert is_valid is False
    assert "similar" in reason.lower() or "redundancy" in reason.lower() or "Q1" in reason


@pytest.mark.asyncio
async def test_validate_with_llm_goal_alignment_fail(validator):
    """Goal alignment criterion fails → question is rejected."""
    with patch(
        "app.agents.validator.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=_fail_criterion("goal_alignment", "Off-topic from the research goal."),
    ):
        is_valid, reason = await validator.validate_with_llm(
            "What is your favourite colour?",
            FakeSurvey(),
            [],
        )
    assert is_valid is False
    assert "off-topic" in reason.lower() or "goal" in reason.lower()


@pytest.mark.asyncio
async def test_validate_with_llm_context_relevance_fail(validator):
    """Context relevance criterion fails → question is rejected."""
    with patch(
        "app.agents.validator.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=_fail_criterion("context_relevance", "Drifts outside the survey context."),
    ):
        is_valid, reason = await validator.validate_with_llm(
            "How do you feel about football?",
            FakeSurvey(),
            [],
        )
    assert is_valid is False
    assert "context" in reason.lower() or "drift" in reason.lower()


@pytest.mark.asyncio
async def test_validate_with_llm_topic_drift_fail(validator):
    """Topic drift criterion fails → question is rejected."""
    with patch(
        "app.agents.validator.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=_fail_criterion("topic_drift", "Rabbit-holing into same subtopic."),
    ):
        is_valid, reason = await validator.validate_with_llm(
            "Tell me more about communication?",
            FakeSurvey(),
            [("How do you communicate remotely?", "We use Slack.")],
        )
    assert is_valid is False
    assert "rabbit" in reason.lower() or "topic" in reason.lower() or "subtopic" in reason.lower()


@pytest.mark.asyncio
async def test_validate_with_llm_json_parse_error_fallback(validator):
    """On bad JSON from LLM, gracefully fall back to valid."""
    with patch(
        "app.agents.validator.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=_make_llm_response("this is not json {{{"),
    ):
        is_valid, reason = await validator.validate_with_llm(
            "How do you feel about the changes?",
            FakeSurvey(),
            [],
        )
    assert is_valid is True
    assert reason is None


@pytest.mark.asyncio
async def test_validate_with_llm_exception_fallback(validator):
    """On LLM call exception, gracefully fall back to valid."""
    with patch(
        "app.agents.validator.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=RuntimeError("LLM service unavailable"),
    ):
        is_valid, reason = await validator.validate_with_llm(
            "How do you feel about the changes?",
            FakeSurvey(),
            [],
        )
    assert is_valid is True
    assert reason is None


# ---------------------------------------------------------------------------
# Full validate() pipeline (LLM mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_passes_good_question(validator):
    """A well-formed, LLM-approved question passes full validation."""
    with patch(
        "app.agents.validator.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=_all_pass_response(),
    ):
        is_valid, reason = await validator.validate(
            candidate_question="How do you feel about the recent changes?",
            survey=FakeSurvey(),
            conversation_history=[],
        )
    assert is_valid is True
    assert reason is None


@pytest.mark.asyncio
async def test_validate_rejects_compound(validator):
    """Compound questions are rejected before LLM call."""
    is_valid, reason = await validator.validate(
        candidate_question="What is your role? And how long have you been there?",
        survey=FakeSurvey(),
        conversation_history=[],
    )
    assert is_valid is False
    assert "compound" in reason.lower()


# ---------------------------------------------------------------------------
# Goal coverage estimation (LLM mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_estimate_goal_coverage_llm(validator):
    """LLM returns a coverage float."""
    coverage_response = _make_llm_response({
        "coverage": 0.65,
        "reasoning": "Covered aspects X and Y but not Z.",
    })
    with patch(
        "app.agents.validator.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=coverage_response,
    ):
        score = await validator.estimate_goal_coverage(
            [("How do you feel?", "Good overall.")],
            "Understand employee satisfaction",
        )
    assert score == pytest.approx(0.65)


@pytest.mark.asyncio
async def test_estimate_goal_coverage_empty_history(validator):
    """Empty conversation history returns 0.0 without LLM call."""
    score = await validator.estimate_goal_coverage([], "Understand employee satisfaction")
    assert score == 0.0


@pytest.mark.asyncio
async def test_estimate_goal_coverage_llm_error_fallback(validator):
    """On LLM error, coverage returns 0.0."""
    with patch(
        "app.agents.validator.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=RuntimeError("LLM unavailable"),
    ):
        score = await validator.estimate_goal_coverage(
            [("How do you feel?", "Fine.")],
            "Understand employee satisfaction",
        )
    assert score == 0.0
