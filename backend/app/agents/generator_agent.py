"""Generator agent using OpenAI Agent SDK with LiteLLM."""

import json
import logging
from typing import List, Tuple

from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel

from app.agents.prompts import GENERATOR_SYSTEM_PROMPT, build_generator_prompt
from app.agents.validator import QuestionValidator
from app.core.config import settings
from app.models.survey import Survey

logger = logging.getLogger(__name__)

FALLBACK_QUESTION = "Could you tell me more about your experience with this topic?"
MAX_RETRIES = 3


def get_model(prefix="GEMINI"):
    """Get LitellmModel configured from settings."""
    model = settings.GEMINI_MODEL
    api_key = settings.effective_api_key
    logger.info(f"Creating model: {model}, api_key={'set' if api_key else 'MISSING'}")
    return LitellmModel(model=model, api_key=api_key)


def _create_agent() -> Agent:
    """Create the generator agent with LiteLLM model."""
    return Agent(
        name="SurveyQuestionGenerator",
        instructions=GENERATOR_SYSTEM_PROMPT,
        model=get_model("GEMINI"),
    )


def _parse_constraints(constraints_json: str) -> List[str]:
    """Parse constraints JSON string to list."""
    try:
        return json.loads(constraints_json)
    except (json.JSONDecodeError, TypeError):
        return []


async def generate_question(
    survey: Survey,
    conversation_history: List[Tuple[str, str]],
    question_number: int = 1,
) -> str:
    """Generate a survey question using the agent with validation and retries.

    Args:
        survey: The survey configuration.
        conversation_history: List of (question, answer) tuples.
        question_number: The current question number (1-based).

    Returns:
        The generated question text.
    """
    agent = _create_agent()
    constraints = _parse_constraints(survey.constraints)
    validator = QuestionValidator()
    rejection_feedback = ""

    for attempt in range(MAX_RETRIES):
        prompt = build_generator_prompt(
            survey_context=survey.context,
            goal=survey.goal,
            constraints=constraints,
            conversation_history=conversation_history,
            rejection_feedback=rejection_feedback,
            question_number=question_number,
            max_questions=survey.max_questions,
        )

        try:
            logger.info(f"Generating question (attempt {attempt + 1}/{MAX_RETRIES})")
            result = await Runner.run(agent, input=prompt)
            candidate = result.final_output.strip()
            logger.info(f"Agent returned: {candidate[:100]}")

            if not candidate:
                rejection_feedback = "Empty question generated."
                continue

            # Validate the candidate question
            is_valid, reason = await validator.validate(
                candidate_question=candidate,
                survey=survey,
                conversation_history=conversation_history,
            )

            if is_valid:
                logger.info(
                    f"Question generated on attempt {attempt + 1}: {candidate[:80]}"
                )
                return candidate

            rejection_feedback = reason or "Question did not pass validation."
            logger.warning(
                f"Question rejected (attempt {attempt + 1}): {rejection_feedback}"
            )

        except Exception as e:
            logger.error(f"Agent error on attempt {attempt + 1}: {e}")
            rejection_feedback = f"Error generating question: {str(e)}"

    logger.warning("All retries exhausted, using fallback question.")
    return FALLBACK_QUESTION
