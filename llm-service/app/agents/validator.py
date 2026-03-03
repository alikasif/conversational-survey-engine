"""Question validator with LLM-based semantic checks and rule-based checks."""

import json
import logging
import re
from typing import List, Optional, Tuple

import litellm

from .prompts import (
    COVERAGE_SYSTEM_PROMPT,
    VALIDATOR_SYSTEM_PROMPT,
    build_coverage_prompt,
    build_validator_prompt,
)
from ..config import settings

logger = logging.getLogger(__name__)


def _get_validator_model() -> str:
    """Return the model name to use for validation calls."""
    return settings.GEMINI_VALIDATOR_MODEL


class QuestionValidator:
    """Validates candidate survey questions against multiple criteria."""

    def __init__(self) -> None:
        pass

    async def validate(
        self,
        candidate_question: str,
        goal: str,
        context: str,
        conversation_history: List[Tuple[str, str]],
    ) -> Tuple[bool, Optional[str]]:
        """Run all validation checks on a candidate question."""
        # Check compound question (rule-based)
        is_compound, reason = self.check_compound_question(candidate_question)
        if is_compound:
            return False, reason

        # Check leading question (rule-based)
        is_leading, reason = self.check_leading_question(candidate_question)
        if is_leading:
            return False, reason

        # LLM-based semantic checks
        is_valid, reason = await self.validate_with_llm(
            candidate_question, goal, context, conversation_history
        )
        if not is_valid:
            return False, reason

        return True, None

    async def validate_with_llm(
        self,
        candidate_question: str,
        goal: str,
        context: str,
        conversation_history: List[Tuple[str, str]],
    ) -> Tuple[bool, Optional[str]]:
        """Run all 4 semantic checks via a single LLM call."""
        try:
            user_prompt = build_validator_prompt(
                candidate_question=candidate_question,
                goal=goal,
                context=context or "",
                conversation_history=conversation_history,
            )

            model = _get_validator_model()
            api_key = settings.effective_api_key
            kwargs: dict = {
                "model": model,
                "messages": [
                    {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }
            if api_key and not model.startswith("vertex_ai/"):
                kwargs["api_key"] = api_key

            response = await litellm.acompletion(**kwargs)
            raw = response.choices[0].message.content
            result = json.loads(raw)

            for criterion in ("redundancy", "goal_alignment", "context_relevance", "topic_drift"):
                entry = result.get(criterion, {})
                if not entry.get("pass", True):
                    reason = entry.get("reason") or f"Failed {criterion} check."
                    return False, reason

            return True, None

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Validator LLM JSON parse error: {e} — falling back to valid")
            return True, None
        except Exception as e:
            logger.warning(f"Validator LLM call failed: {e} — falling back to valid")
            return True, None

    def check_compound_question(
        self, question: str
    ) -> Tuple[bool, Optional[str]]:
        """Rule-based check for compound questions."""
        if question.count("?") > 1:
            return True, (
                "Compound question detected (multiple question marks). "
                "Ask only one question at a time."
            )

        compound_patterns = [
            r"\b(what|how|why|when|where|who|which)\b.+\band\b.+\b(what|how|why|when|where|who|which)\b",
            r"\b(do you|are you|have you|can you|would you)\b.+\band\b.+\b(do you|are you|have you|can you|would you)\b",
        ]
        for pattern in compound_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return True, (
                    "Compound question detected (multiple clauses joined by 'and'). "
                    "Ask only one question at a time."
                )

        return False, None

    def check_leading_question(
        self, question: str
    ) -> Tuple[bool, Optional[str]]:
        """Rule-based check for leading questions."""
        leading_patterns = [
            r"\bdon'?t you (think|agree|feel|believe)\b",
            r"\bisn'?t it (true|obvious|clear)\b",
            r"\bwouldn'?t you (say|agree)\b",
            r"\bsurely you\b",
            r"\bit'?s (clear|obvious|evident) that\b",
            r"\beveryone (knows|agrees|thinks)\b",
            r"\byou must (think|feel|agree)\b",
        ]
        for pattern in leading_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return True, (
                    "Leading question detected. Rephrase to be neutral "
                    "without suggesting a particular answer."
                )

        return False, None

    async def estimate_goal_coverage(
        self,
        conversation_history: List[Tuple[str, str]],
        goal: str,
    ) -> float:
        """Estimate how well the conversation covers the survey goal using an LLM."""
        if not conversation_history:
            return 0.0

        try:
            user_prompt = build_coverage_prompt(goal, conversation_history)
            model = _get_validator_model()
            api_key = settings.effective_api_key
            kwargs: dict = {
                "model": model,
                "messages": [
                    {"role": "system", "content": COVERAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }
            if api_key and not model.startswith("vertex_ai/"):
                kwargs["api_key"] = api_key

            response = await litellm.acompletion(**kwargs)
            raw = response.choices[0].message.content
            result = json.loads(raw)
            coverage = float(result.get("coverage", 0.0))
            return max(0.0, min(1.0, coverage))

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Coverage LLM JSON parse error: {e} — returning 0.0")
            return 0.0
        except Exception as e:
            logger.warning(f"Coverage LLM call failed: {e} — returning 0.0")
            return 0.0
