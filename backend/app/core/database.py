"""Async SQLAlchemy engine and session factory."""

import logging
import os

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models import Base

logger = logging.getLogger(__name__)

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Build engine kwargs based on dialect
_engine_kwargs: dict = {"echo": False}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"timeout": 30}

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# SQLite-specific PRAGMA listener — only registered for SQLite
if _is_sqlite:

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable WAL mode and set busy_timeout for SQLite."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

logger.info("Database dialect: %s", "sqlite" if _is_sqlite else "postgresql")


async def init_db() -> None:
    """Create all tables if they don't exist."""
    if _is_sqlite:
        os.makedirs("data", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


