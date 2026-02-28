"""Question validator with embedding similarity, rule-based checks, and goal coverage."""

import json
import logging
import math
import re
from typing import List, Optional, Tuple

import litellm

from app.core.config import settings
from app.models.survey import Survey

logger = logging.getLogger(__name__)


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors without numpy."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


async def get_embedding(text: str) -> List[float]:
    """Get embedding vector for text using LiteLLM."""
    try:
        response = await litellm.aembedding(
            model="gemini/text-embedding-004",
            input=[text],
            api_key=settings.GEMINI_API_KEY,
        )
        return response.data[0]["embedding"]
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return []


class QuestionValidator:
    """Validates candidate survey questions against multiple criteria."""

    def __init__(
        self,
        redundancy_threshold: float = 0.85,
        goal_alignment_threshold: float = 0.3,
    ):
        self.redundancy_threshold = redundancy_threshold
        self.goal_alignment_threshold = goal_alignment_threshold

    async def validate(
        self,
        candidate_question: str,
        survey: Survey,
        conversation_history: List[Tuple[str, str]],
    ) -> Tuple[bool, Optional[str]]:
        """Run all validation checks on a candidate question.

        Returns:
            Tuple of (is_valid, rejection_reason).
        """
        # Check compound question (rule-based — no API call)
        is_compound, reason = self.check_compound_question(candidate_question)
        if is_compound:
            return False, reason

        # Check leading question (rule-based — no API call)
        is_leading, reason = self.check_leading_question(candidate_question)
        if is_leading:
            return False, reason

        # Check redundancy against prior questions (requires embedding)
        prior_questions = [q for q, _ in conversation_history]
        if prior_questions:
            is_redundant, reason = await self.check_redundancy(
                candidate_question, prior_questions, self.redundancy_threshold
            )
            if is_redundant:
                return False, reason

        # Check goal alignment (requires embedding)
        try:
            is_aligned, reason = await self.check_goal_alignment(
                candidate_question, survey.goal
            )
            if not is_aligned:
                return False, reason
        except Exception as e:
            logger.warning(f"Goal alignment check failed: {e}, skipping")

        return True, None

    async def check_redundancy(
        self,
        question: str,
        prior_questions: List[str],
        threshold: float = 0.85,
    ) -> Tuple[bool, Optional[str]]:
        """Check if question is too similar to prior questions."""
        try:
            q_embedding = await get_embedding(question)
            if not q_embedding:
                return False, None

            for prior in prior_questions:
                prior_embedding = await get_embedding(prior)
                if not prior_embedding:
                    continue
                sim = cosine_similarity(q_embedding, prior_embedding)
                if sim > threshold:
                    return True, (
                        f"Question too similar to a previous question "
                        f"(similarity: {sim:.2f}). Ask something different."
                    )
        except Exception as e:
            logger.warning(f"Redundancy check failed: {e}")

        return False, None

    async def check_goal_alignment(
        self, question: str, goal: str
    ) -> Tuple[bool, Optional[str]]:
        """Check if question is aligned with the survey goal."""
        try:
            q_embedding = await get_embedding(question)
            g_embedding = await get_embedding(goal)
            if not q_embedding or not g_embedding:
                return True, None  # Can't check, assume aligned

            sim = cosine_similarity(q_embedding, g_embedding)
            if sim < self.goal_alignment_threshold:
                return False, (
                    f"Question appears off-topic relative to the survey goal "
                    f"(similarity: {sim:.2f}). Stay focused on the goal."
                )
        except Exception as e:
            logger.warning(f"Goal alignment check failed: {e}")

        return True, None

    def check_compound_question(
        self, question: str
    ) -> Tuple[bool, Optional[str]]:
        """Rule-based check for compound questions."""
        # Multiple question marks
        if question.count("?") > 1:
            return True, (
                "Compound question detected (multiple question marks). "
                "Ask only one question at a time."
            )

        # "and" joining two interrogative clauses
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

    def check_max_questions(
        self, question_count: int, max_questions: int
    ) -> bool:
        """Check if max questions limit has been reached."""
        return question_count >= max_questions

    async def estimate_goal_coverage(
        self,
        conversation_history: List[Tuple[str, str]],
        goal: str,
    ) -> float:
        """Estimate how well the conversation covers the survey goal.

        Returns a score between 0.0 and 1.0.
        """
        if not conversation_history:
            return 0.0

        try:
            goal_embedding = await get_embedding(goal)
            if not goal_embedding:
                return 0.0

            # Combine all Q&A into a single text and check similarity to goal
            combined = " ".join(
                f"{q} {a}" for q, a in conversation_history
            )
            combined_embedding = await get_embedding(combined)
            if not combined_embedding:
                return 0.0

            coverage = cosine_similarity(goal_embedding, combined_embedding)
            return max(0.0, min(1.0, coverage))
        except Exception as e:
            logger.warning(f"Goal coverage estimation failed: {e}")
            return 0.0
