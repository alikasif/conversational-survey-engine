"""Tests for the Admin API endpoints (/api/v1/admin/surveys)."""

import pytest

from tests.conftest import create_test_survey


# ---------------------------------------------------------------------------
# POST /api/v1/admin/surveys
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_survey(client, survey_payload):
    """Creating a survey with valid data returns 201 and all fields."""
    resp = await client.post("/api/v1/admin/surveys", json=survey_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == survey_payload["title"]
    assert data["context"] == survey_payload["context"]
    assert data["goal"] == survey_payload["goal"]
    assert data["constraints"] == survey_payload["constraints"]
    assert data["max_questions"] == survey_payload["max_questions"]
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_survey_validation_error(client):
    """Missing required fields returns 422."""
    resp = await client.post("/api/v1/admin/surveys", json={"title": "Incomplete"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/admin/surveys
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_surveys(client, survey_payload):
    """Listing surveys returns created surveys."""
    await client.post("/api/v1/admin/surveys", json=survey_payload)
    resp = await client.get("/api/v1/admin/surveys")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["surveys"]) >= 1


@pytest.mark.asyncio
async def test_list_surveys_empty(client):
    """Listing surveys when none exist returns an empty list."""
    resp = await client.get("/api/v1/admin/surveys")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["surveys"] == []


# ---------------------------------------------------------------------------
# GET /api/v1/admin/surveys/{survey_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_survey(client, survey_payload):
    """Fetching a survey by ID returns correct data with stats."""
    created = (await client.post("/api/v1/admin/surveys", json=survey_payload)).json()
    survey_id = created["id"]

    resp = await client.get(f"/api/v1/admin/surveys/{survey_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == survey_id
    assert data["title"] == survey_payload["title"]
    # Detail response includes stats fields
    assert "total_sessions" in data
    assert "completed_sessions" in data


@pytest.mark.asyncio
async def test_get_survey_not_found(client):
    """Fetching a nonexistent survey returns 404."""
    resp = await client.get("/api/v1/admin/surveys/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/v1/admin/surveys/{survey_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_survey(client, survey_payload):
    """Updating a survey changes its fields."""
    created = (await client.post("/api/v1/admin/surveys", json=survey_payload)).json()
    survey_id = created["id"]

    update_data = {"title": "Updated Title", "max_questions": 20}
    resp = await client.put(f"/api/v1/admin/surveys/{survey_id}", json=update_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Title"
    assert data["max_questions"] == 20
    # Unchanged fields stay the same
    assert data["goal"] == survey_payload["goal"]


@pytest.mark.asyncio
async def test_update_survey_not_found(client):
    """Updating a nonexistent survey returns 404."""
    resp = await client.put(
        "/api/v1/admin/surveys/nonexistent-id",
        json={"title": "X"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/admin/surveys/{survey_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_survey(client, survey_payload):
    """Deleting a survey returns 204 and it disappears from listing."""
    created = (await client.post("/api/v1/admin/surveys", json=survey_payload)).json()
    survey_id = created["id"]

    resp = await client.delete(f"/api/v1/admin/surveys/{survey_id}")
    assert resp.status_code == 204

    # Should no longer appear in listings (soft-deleted)
    resp = await client.get(f"/api/v1/admin/surveys/{survey_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_survey_not_found(client):
    """Deleting a nonexistent survey returns 404."""
    resp = await client.delete("/api/v1/admin/surveys/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/admin/surveys/{survey_id}/stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_survey_stats(client, survey_payload):
    """Stats endpoint returns expected structure."""
    created = (await client.post("/api/v1/admin/surveys", json=survey_payload)).json()
    survey_id = created["id"]

    resp = await client.get(f"/api/v1/admin/surveys/{survey_id}/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["survey_id"] == survey_id
    assert data["total_sessions"] == 0
    assert data["completed_sessions"] == 0
    assert data["abandoned_sessions"] == 0
    assert "avg_questions_per_session" in data
    assert "top_themes" in data


@pytest.mark.asyncio
async def test_get_survey_stats_not_found(client):
    """Stats for a nonexistent survey returns 404."""
    resp = await client.get("/api/v1/admin/surveys/nonexistent-id/stats")
    assert resp.status_code == 404
