"""Tests for the QuestionValidator (rule-based + mocked embedding checks)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.validator import QuestionValidator


@pytest.fixture()
def validator():
    return QuestionValidator()


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
# Redundancy check (embedding mocked)
# ---------------------------------------------------------------------------

MOCK_EMBEDDING_A = [0.1, 0.2, 0.3, 0.4]
MOCK_EMBEDDING_B = [0.1, 0.2, 0.3, 0.4]  # identical → similarity ≈ 1.0
MOCK_EMBEDDING_C = [-0.4, -0.3, -0.2, -0.1]  # very different


@pytest.mark.asyncio
async def test_check_redundancy_detects_similar(validator):
    """Highly similar embeddings are flagged as redundant."""
    with patch(
        "app.agents.validator.get_embedding",
        new_callable=AsyncMock,
        side_effect=[MOCK_EMBEDDING_A, MOCK_EMBEDDING_B],
    ):
        is_redundant, reason = await validator.check_redundancy(
            "What is your role?", ["What is your role?"], threshold=0.85
        )
    assert is_redundant is True
    assert "similar" in reason.lower()


@pytest.mark.asyncio
async def test_check_redundancy_passes_different(validator):
    """Dissimilar embeddings pass the redundancy check."""
    with patch(
        "app.agents.validator.get_embedding",
        new_callable=AsyncMock,
        side_effect=[MOCK_EMBEDDING_A, MOCK_EMBEDDING_C],
    ):
        is_redundant, reason = await validator.check_redundancy(
            "What is your role?",
            ["How productive do you feel?"],
            threshold=0.85,
        )
    assert is_redundant is False


# ---------------------------------------------------------------------------
# Goal-alignment check (embedding mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_goal_alignment_passes(validator):
    """Aligned question passes goal alignment check."""
    # Same direction → high similarity
    with patch(
        "app.agents.validator.get_embedding",
        new_callable=AsyncMock,
        side_effect=[MOCK_EMBEDDING_A, MOCK_EMBEDDING_A],
    ):
        is_aligned, reason = await validator.check_goal_alignment(
            "How satisfied are you with remote work?",
            "Understand employee satisfaction with remote work",
        )
    assert is_aligned is True
    assert reason is None


@pytest.mark.asyncio
async def test_check_goal_alignment_fails(validator):
    """Off-topic question fails goal alignment check."""
    with patch(
        "app.agents.validator.get_embedding",
        new_callable=AsyncMock,
        side_effect=[MOCK_EMBEDDING_A, MOCK_EMBEDDING_C],
    ):
        v = QuestionValidator(goal_alignment_threshold=0.3)
        is_aligned, reason = await v.check_goal_alignment(
            "What is your favourite colour?",
            "Understand employee satisfaction with remote work",
        )
    assert is_aligned is False
    assert "off-topic" in reason.lower()


# ---------------------------------------------------------------------------
# Full validate() pipeline (all embedding calls mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_passes_good_question(validator):
    """A well-formed, aligned, non-redundant question passes validation."""
    # Build a minimal Survey-like object
    class FakeSurvey:
        goal = "Understand employee satisfaction"
        constraints = "[]"
        context = "Employee well-being study"
        context_similarity_threshold = 0.7

    with patch(
        "app.agents.validator.get_embedding",
        new_callable=AsyncMock,
        return_value=MOCK_EMBEDDING_A,
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
    """Compound questions are rejected during full validation."""

    class FakeSurvey:
        goal = "Understand employee satisfaction"
        constraints = "[]"
        context = "Employee well-being study"
        context_similarity_threshold = 0.7

    is_valid, reason = await validator.validate(
        candidate_question="What is your role? And how long have you been there?",
        survey=FakeSurvey(),
        conversation_history=[],
    )
    assert is_valid is False
    assert "compound" in reason.lower()


# ---------------------------------------------------------------------------
# Context-relevance check (embedding mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_context_relevance_passes(validator):
    """Question relevant to the survey context passes the check."""
    with patch(
        "app.agents.validator.get_embedding",
        new_callable=AsyncMock,
        side_effect=[MOCK_EMBEDDING_A, MOCK_EMBEDDING_A],
    ):
        is_relevant, reason = await validator.check_context_relevance(
            "How satisfied are you with remote work?",
            "Employee well-being study",
            threshold=0.7,
        )
    assert is_relevant is True
    assert reason is None


@pytest.mark.asyncio
async def test_check_context_relevance_fails(validator):
    """Question irrelevant to the survey context is rejected."""
    with patch(
        "app.agents.validator.get_embedding",
        new_callable=AsyncMock,
        side_effect=[MOCK_EMBEDDING_A, MOCK_EMBEDDING_C],
    ):
        is_relevant, reason = await validator.check_context_relevance(
            "What is your favourite colour?",
            "Employee well-being study",
            threshold=0.7,
        )
    assert is_relevant is False
    assert "context" in reason.lower()


# ---------------------------------------------------------------------------
# Topic drift check (embedding mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_topic_drift_detects_rabbit_hole(validator):
    """A question too similar to the last one is flagged as topic drift."""
    with patch(
        "app.agents.validator.get_embedding",
        new_callable=AsyncMock,
        side_effect=[MOCK_EMBEDDING_A, MOCK_EMBEDDING_B],
    ):
        is_drifting, reason = await validator.check_topic_drift(
            "Tell me more about remote work communication?",
            ["How do you communicate while working remotely?"],
        )
    assert is_drifting is True
    assert "rabbit-holing" in reason.lower()


@pytest.mark.asyncio
async def test_check_topic_drift_passes_diverse(validator):
    """A diverse question passes the topic drift check."""
    with patch(
        "app.agents.validator.get_embedding",
        new_callable=AsyncMock,
        side_effect=[MOCK_EMBEDDING_A, MOCK_EMBEDDING_C],
    ):
        is_drifting, reason = await validator.check_topic_drift(
            "What tools help you stay productive?",
            ["How do you communicate while working remotely?"],
        )
    assert is_drifting is False
    assert reason is None
