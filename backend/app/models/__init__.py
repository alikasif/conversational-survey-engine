"""ORM models package."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


# Import all models so they register with Base.metadata
from app.models.survey import Survey  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.models.session import Session  # noqa: E402, F401
from app.models.response import Response  # noqa: E402, F401

__all__ = ["Base", "Survey", "User", "Session", "Response"]
