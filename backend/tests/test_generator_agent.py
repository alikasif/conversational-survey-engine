"""Tests for the generator agent (all LLM calls mocked)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.generator_agent import generate_question, FALLBACK_QUESTION


def _make_fake_survey(**overrides):
    """Return a minimal Survey-like object."""
    defaults = {
        "context": "We are studying employee well-being.",
        "goal": "Understand factors affecting well-being in remote work.",
        "constraints": '["Do not ask about salary"]',
        "max_questions": 10,
        "context_similarity_threshold": 0.7,
    }
    defaults.update(overrides)
    survey = MagicMock()
    for k, v in defaults.items():
        setattr(survey, k, v)
    return survey


# ---------------------------------------------------------------------------
# generate_question
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_question_returns_string():
    """generate_question returns the agent's output when valid."""
    expected = "How would you describe your daily routine while working remotely?"

    mock_result = MagicMock()
    mock_result.final_output = expected

    with patch(
        "app.agents.generator_agent.Runner.run",
        new_callable=AsyncMock,
        return_value=mock_result,
    ), patch(
        "app.agents.generator_agent.QuestionValidator.validate",
        new_callable=AsyncMock,
        return_value=(True, None),
    ):
        question = await generate_question(
            survey=_make_fake_survey(),
            conversation_history=[],
        )

    assert question == expected
    assert isinstance(question, str)


@pytest.mark.asyncio
async def test_generate_question_with_history():
    """Conversation history is forwarded and a question is still generated."""
    expected = "Can you elaborate on the collaboration challenges?"

    mock_result = MagicMock()
    mock_result.final_output = expected

    history = [
        ("How do you feel about remote work?", "It's mostly positive."),
        ("What challenges do you face?", "Collaboration can be hard."),
    ]

    with patch(
        "app.agents.generator_agent.Runner.run",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_run, patch(
        "app.agents.generator_agent.QuestionValidator.validate",
        new_callable=AsyncMock,
        return_value=(True, None),
    ):
        question = await generate_question(
            survey=_make_fake_survey(),
            conversation_history=history,
        )

    assert question == expected
    # The runner should have been called with a prompt containing the history
    call_kwargs = mock_run.call_args
    prompt_text = call_kwargs.kwargs.get("input") or call_kwargs.args[1]
    assert "Collaboration can be hard" in prompt_text
    # Anti-rabbit-hole: prompt should include survey progress section
    assert "Survey Progress" in prompt_text


@pytest.mark.asyncio
async def test_generate_question_retries_on_validation_failure():
    """When the first attempt fails validation, a retry succeeds."""
    bad_result = MagicMock()
    bad_result.final_output = "Don't you think remote work is bad?"

    good_result = MagicMock()
    good_result.final_output = "How do you feel about remote work?"

    with patch(
        "app.agents.generator_agent.Runner.run",
        new_callable=AsyncMock,
        side_effect=[bad_result, good_result],
    ), patch(
        "app.agents.generator_agent.QuestionValidator.validate",
        new_callable=AsyncMock,
        side_effect=[(False, "Leading question"), (True, None)],
    ):
        question = await generate_question(
            survey=_make_fake_survey(),
            conversation_history=[],
        )

    assert question == "How do you feel about remote work?"


@pytest.mark.asyncio
async def test_generate_question_fallback_after_exhausted_retries():
    """After all retries are exhausted, the fallback question is returned."""
    bad_result = MagicMock()
    bad_result.final_output = "Don't you think X?"

    with patch(
        "app.agents.generator_agent.Runner.run",
        new_callable=AsyncMock,
        return_value=bad_result,
    ), patch(
        "app.agents.generator_agent.QuestionValidator.validate",
        new_callable=AsyncMock,
        return_value=(False, "Leading question"),
    ):
        question = await generate_question(
            survey=_make_fake_survey(),
            conversation_history=[],
        )

    assert question == FALLBACK_QUESTION


@pytest.mark.asyncio
async def test_generate_question_fallback_on_exception():
    """If the runner raises, we eventually get the fallback."""
    with patch(
        "app.agents.generator_agent.Runner.run",
        new_callable=AsyncMock,
        side_effect=RuntimeError("LLM unavailable"),
    ):
        question = await generate_question(
            survey=_make_fake_survey(),
            conversation_history=[],
        )

    assert question == FALLBACK_QUESTION
