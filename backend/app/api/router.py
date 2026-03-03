"""API router aggregation."""

from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.participant import router as participant_router

api_router = APIRouter()

api_router.include_router(admin_router)
api_router.include_router(participant_router)
