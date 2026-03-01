"""Application configuration using Pydantic Settings."""

import json
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/cse.db"
    CORS_ORIGINS: str = '["http://localhost:5173"]'
    LOG_LEVEL: str = "info"
    GEMINI_MODEL: str = "vertex_ai/gemini-2.0-flash"
    GEMINI_EMBEDDING_MODEL: str = "vertex_ai/text-embedding-004"
    GEMINI_VALIDATOR_MODEL: str = "gemini/gemini-2.0-flash"

    @property
    def effective_api_key(self) -> str:
        """Return the best available API key for Gemini."""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS JSON string to list."""
        return json.loads(self.CORS_ORIGINS)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
