"""Application configuration using Pydantic Settings."""

import json
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    GEMINI_API_KEY: str = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/cse.db"
    CORS_ORIGINS: str = '["http://localhost:5173"]'
    LOG_LEVEL: str = "info"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS JSON string to list."""
        return json.loads(self.CORS_ORIGINS)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
