"""Application configuration for the LLM service."""

import json
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """LLM service settings loaded from environment variables."""

    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "vertex_ai/gemini-2.0-flash"
    GEMINI_VALIDATOR_MODEL: str = "gemini/gemini-2.0-flash"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    LOG_LEVEL: str = "info"

    @property
    def effective_api_key(self) -> str:
        """Return the best available API key for Gemini."""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
