"""Shared test fixtures for the Conversational Survey Engine backend."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base

# ---------------------------------------------------------------------------
# In-memory async SQLite for tests
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture()
async def db_engine():
    """Create a fresh in-memory SQLite engine, with all tables, per test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine):
    """Yield an async session bound to the test engine."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db_engine):
    """HTTPX AsyncClient wired to the FastAPI app with the test DB."""
    from app.core.dependencies import get_db
    from app.main import app

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Reusable test data helpers
# ---------------------------------------------------------------------------
SURVEY_PAYLOAD = {
    "title": "Employee Satisfaction Survey",
    "context": "We want to understand employee satisfaction with remote work policies.",
    "goal": "Identify key factors affecting employee satisfaction and productivity in remote work.",
    "constraints": ["Do not ask about salary", "Keep questions work-related"],
    "max_questions": 5,
    "completion_criteria": "Cover work environment, collaboration, and well-being.",
    "goal_coverage_threshold": 0.85,
}


@pytest.fixture()
def survey_payload():
    """Return a valid survey creation payload (dict)."""
    return SURVEY_PAYLOAD.copy()


async def create_test_survey(client: AsyncClient) -> dict:
    """Helper: create a survey via the API and return the response JSON."""
    resp = await client.post("/api/v1/admin/surveys", json=SURVEY_PAYLOAD)
    assert resp.status_code == 201
    return resp.json()


async def create_test_session(
    client: AsyncClient, survey_id: str, *, mock_question: str = "How do you feel about remote work?"
) -> dict:
    """Helper: create a session (mocking the LLM) and return the response JSON."""
    with patch(
        "app.services.question_service.generate_question",
        new_callable=AsyncMock,
        return_value=mock_question,
    ), patch(
        "app.services.question_service.validator.estimate_goal_coverage",
        new_callable=AsyncMock,
        return_value=0.1,
    ):
        resp = await client.post(
            f"/api/v1/surveys/{survey_id}/sessions",
            json={"participant_name": "Test User", "metadata": {"source": "unit-test"}},
        )
        assert resp.status_code == 201
        return resp.json()
