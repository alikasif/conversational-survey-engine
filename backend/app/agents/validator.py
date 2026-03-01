"""Question validator with embedding similarity, rule-based checks, and goal coverage."""

import json
import logging
import math
import os
import re
from typing import List, Optional, Tuple

import litellm
from dotenv import load_dotenv

from app.models.survey import Survey

load_dotenv(override=True)

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
        model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini/text-embedding-004")
        api_key = os.getenv("GEMINI_API_KEY")
        response = await litellm.aembedding(
            model=model,
            input=[text],
            api_key=api_key,
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
        goal_alignment_threshold: float = 0.45,
        context_similarity_threshold: float = 0.7,
        topic_drift_threshold: float = 0.80,
    ):
        self.redundancy_threshold = redundancy_threshold
        self.goal_alignment_threshold = goal_alignment_threshold
        self.context_similarity_threshold = context_similarity_threshold
        self.topic_drift_threshold = topic_drift_threshold

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

        # Check context relevance (requires embedding)
        context = getattr(survey, "context", None)
        if context:
            threshold = getattr(
                survey,
                "context_similarity_threshold",
                self.context_similarity_threshold,
            )
            is_relevant, reason = await self.check_context_relevance(
                candidate_question, context, threshold=threshold
            )
            if not is_relevant:
                return False, reason

        # Check topic drift (requires embedding)
        if prior_questions:
            is_drifting, reason = await self.check_topic_drift(
                candidate_question, prior_questions
            )
            if is_drifting:
                return False, reason

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

    async def check_context_relevance(
        self,
        question: str,
        context: str,
        threshold: float = 0.7,
    ) -> Tuple[bool, Optional[str]]:
        """Check if question is relevant to the survey context.

        Returns:
            Tuple of (is_relevant, rejection_reason).
        """
        try:
            q_embedding = await get_embedding(question)
            c_embedding = await get_embedding(context)
            if not q_embedding or not c_embedding:
                return True, None  # Can't check, assume relevant

            sim = cosine_similarity(q_embedding, c_embedding)
            if sim < threshold:
                return False, (
                    f"Question drifts outside the survey context "
                    f"(similarity: {sim:.2f}). Keep the question grounded "
                    f"in the survey's subject matter."
                )
        except Exception as e:
            logger.warning(f"Context relevance check failed: {e}")

        return True, None

    async def check_topic_drift(
        self,
        question: str,
        prior_questions: List[str],
    ) -> Tuple[bool, Optional[str]]:
        """Check if question is too similar to the last question asked.

        Returns:
            Tuple of (is_drifting, rejection_reason).
        """
        if not prior_questions:
            return False, None

        try:
            last_question = prior_questions[-1]
            q_embedding = await get_embedding(question)
            last_embedding = await get_embedding(last_question)
            if not q_embedding or not last_embedding:
                return False, None

            sim = cosine_similarity(q_embedding, last_embedding)
            if sim > self.topic_drift_threshold:
                return True, (
                    f"Question is too similar to the last question asked "
                    f"(similarity: {sim:.2f}). This looks like rabbit-holing "
                    f"into the same subtopic. Move to a different aspect of "
                    f"the research goal."
                )
        except Exception as e:
            logger.warning(f"Topic drift check failed: {e}")

        return False, None

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
