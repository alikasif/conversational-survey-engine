"""HTTP client for the LLM microservice."""

import asyncio
import logging
from typing import List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 120.0
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0


class LLMClient:
    """Async HTTP client for the CSE LLM microservice."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.LLM_SERVICE_URL).rstrip("/")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=_TIMEOUT)

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an HTTP request with retry logic."""
        last_error: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with self._client() as client:
                    response = await getattr(client, method)(path, **kwargs)
                    response.raise_for_status()
                    return response.json()
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                last_error = e
                wait = _BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(
                    "LLM service connection error (attempt %d/%d): %s — retrying in %.1fs",
                    attempt, _MAX_RETRIES, e, wait,
                )
                await asyncio.sleep(wait)
            except httpx.HTTPStatusError as e:
                logger.error("LLM service returned %s: %s", e.response.status_code, e.response.text[:500])
                raise RuntimeError(
                    f"LLM service error ({e.response.status_code}): {e.response.text[:200]}"
                ) from e
            except Exception as e:
                logger.error("LLM service request failed: %s", e)
                raise RuntimeError(f"LLM service request failed: {e}") from e

        raise RuntimeError(
            f"LLM service unreachable after {_MAX_RETRIES} attempts: {last_error}"
        )

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    async def generate_question(
        self,
        survey_context: str,
        goal: str,
        constraints: str,
        conversation_history: List[List[str]],
        question_number: int,
        max_questions: int = 10,
        goal_coverage_threshold: float = 0.85,
        rejection_guardrail_hint: Optional[str] = None,
    ) -> dict:
        """POST /generate-question → {question_text, question_id}."""
        payload = {
            "survey_context": survey_context,
            "goal": goal,
            "constraints": constraints,
            "conversation_history": conversation_history,
            "question_number": question_number,
            "max_questions": max_questions,
            "goal_coverage_threshold": goal_coverage_threshold,
            "rejection_guardrail_hint": rejection_guardrail_hint,
        }
        return await self._request("post", "/generate-question", json=payload)

    async def validate_question(
        self,
        question: str,
        survey_context: str = "",
        goal: str = "",
        conversation_history: Optional[List[List[str]]] = None,
    ) -> dict:
        """POST /validate-question → {is_valid, issues}."""
        payload = {
            "question": question,
            "survey_context": survey_context,
            "goal": goal,
            "conversation_history": conversation_history or [],
        }
        return await self._request("post", "/validate-question", json=payload)

    async def check_guardrails(self, answer: str, question: str = "") -> dict:
        """POST /check-guardrails → {is_valid, flags, rejection_reason}."""
        payload = {"answer": answer, "question": question}
        return await self._request("post", "/check-guardrails", json=payload)

    async def generate_preset_questions(
        self,
        survey_context: str,
        goal: str,
        constraints: str,
        count: int,
    ) -> List[dict]:
        """POST /generate-preset-questions → {questions: [...]}."""
        payload = {
            "survey_context": survey_context,
            "goal": goal,
            "constraints": constraints,
            "count": count,
        }
        data = await self._request("post", "/generate-preset-questions", json=payload)
        return data.get("questions", [])

    async def health_check(self) -> dict:
        """GET /health → {status, service, model}."""
        return await self._request("get", "/health")


# Module-level singleton
llm_client = LLMClient()
