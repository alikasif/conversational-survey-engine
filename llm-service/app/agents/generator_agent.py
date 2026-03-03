"""Generator agent using OpenAI Agent SDK with LiteLLM."""

import json
import logging
import re
from typing import List, Tuple
from uuid import uuid4

from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel

from .prompts import (
    GENERATOR_SYSTEM_PROMPT,
    build_generator_prompt,
    build_preset_generation_prompt,
)
from .validator import QuestionValidator
from ..config import settings

logger = logging.getLogger(__name__)

FALLBACK_QUESTION = "Could you tell me more about your experience with this topic?"
MAX_RETRIES = 3

# Output-guard patterns — detect system info leaking into generated questions
OUTPUT_LEAK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"system\s*prompt",
        r"\bgemini\b",
        r"\blitellm\b",
        r"\bopenai\b",
        r"\bvertex[_\s]?ai\b",
        r"you\s+are\s+an\s+expert\s+survey",
        r"GENERATOR_SYSTEM_PROMPT",
        r"VALIDATOR_SYSTEM_PROMPT",
        r"COVERAGE_SYSTEM_PROMPT",
        re.escape(settings.GEMINI_MODEL),
    ]
]


def _check_output_leakage(question: str) -> bool:
    """Return *True* if *question* contains leaked system information."""
    for pattern in OUTPUT_LEAK_PATTERNS:
        if pattern.search(question):
            logger.warning(
                "Output guard triggered (pattern=%s): %s",
                pattern.pattern,
                question[:120],
            )
            return True
    return False


def get_model(prefix="GEMINI"):
    """Get LitellmModel configured from settings."""
    model = settings.GEMINI_MODEL
    # For vertex_ai models, don't pass api_key — use service account credentials
    if model.startswith("vertex_ai/"):
        logger.info(f"Creating model: {model} (vertex_ai, using service account)")
        return LitellmModel(model=model)
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
        if isinstance(constraints_json, list):
            return constraints_json
        return []


async def generate_question(
    survey_context: str,
    goal: str,
    constraints: str | list,
    conversation_history: List[Tuple[str, str]],
    question_number: int = 1,
    max_questions: int = 10,
    goal_coverage_threshold: float = 0.85,
    rejection_guardrail_hint: str | None = None,
) -> str:
    """Generate a survey question using the agent with validation and retries."""
    agent = _create_agent()
    parsed_constraints = _parse_constraints(constraints) if isinstance(constraints, str) else constraints
    validator = QuestionValidator()
    rejection_feedback = ""

    for attempt in range(MAX_RETRIES):
        prompt = build_generator_prompt(
            survey_context=survey_context,
            goal=goal,
            constraints=parsed_constraints,
            conversation_history=conversation_history,
            rejection_feedback=rejection_feedback,
            question_number=question_number,
            max_questions=max_questions,
            rejection_guardrail_hint=rejection_guardrail_hint,
        )

        try:
            logger.info(f"Generating question (attempt {attempt + 1}/{MAX_RETRIES})")
            result = await Runner.run(agent, input=prompt)
            candidate = result.final_output.strip()
            logger.info(f"Agent returned: {candidate[:100]}")

            if not candidate:
                rejection_feedback = "Empty question generated."
                continue

            # Output guard
            if _check_output_leakage(candidate):
                rejection_feedback = (
                    "Question contained system information. "
                    "Generate a different question about the survey topic."
                )
                continue

            # Validate the candidate question
            is_valid, reason = await validator.validate(
                candidate_question=candidate,
                goal=goal,
                context=survey_context,
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


async def generate_preset_question_set(
    survey_context: str,
    goal: str,
    constraints: str | list,
    count: int,
) -> List[dict]:
    """Generate a fixed set of preset questions for a survey."""
    agent = _create_agent()
    parsed_constraints = _parse_constraints(constraints) if isinstance(constraints, str) else constraints
    validator = QuestionValidator()
    generated_so_far: List[dict] = []

    for i in range(1, count + 1):
        question_text = None

        for attempt in range(MAX_RETRIES):
            prompt = build_preset_generation_prompt(
                survey_context=survey_context,
                goal=goal,
                constraints=parsed_constraints,
                generated_so_far=generated_so_far,
                question_number=i,
                max_questions=count,
            )

            try:
                logger.info(
                    f"Generating preset question {i}/{count} "
                    f"(attempt {attempt + 1}/{MAX_RETRIES})"
                )
                result = await Runner.run(agent, input=prompt)
                candidate = result.final_output.strip()

                if not candidate:
                    logger.warning("Empty question generated for preset.")
                    continue

                if _check_output_leakage(candidate):
                    logger.warning("Output guard triggered during preset generation.")
                    continue

                # Build synthetic history for validator
                synthetic_history: List[Tuple[str, str]] = [
                    (q["text"], "[Not yet answered]") for q in generated_so_far
                ]

                # Rule-based checks
                is_compound, _ = validator.check_compound_question(candidate)
                if is_compound:
                    logger.warning(f"Preset Q{i} rejected: compound question.")
                    continue

                is_leading, _ = validator.check_leading_question(candidate)
                if is_leading:
                    logger.warning(f"Preset Q{i} rejected: leading question.")
                    continue

                # LLM-based validation
                is_valid, reason = await validator.validate_with_llm(
                    candidate, goal, survey_context, synthetic_history
                )
                if not is_valid:
                    logger.warning(
                        f"Preset Q{i} rejected by LLM validator: {reason}"
                    )
                    continue

                question_text = candidate
                break

            except Exception as e:
                logger.error(
                    f"Error generating preset question {i} "
                    f"(attempt {attempt + 1}): {e}"
                )

        if question_text is None:
            question_text = FALLBACK_QUESTION
            logger.warning(
                f"Using fallback for preset question {i} after exhausting retries."
            )

        generated_so_far.append(
            {
                "question_number": i,
                "question_id": str(uuid4()),
                "text": question_text,
            }
        )

    return generated_so_far
