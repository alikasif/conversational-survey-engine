"""Survey ORM model."""

from sqlalchemy import Boolean, Column, Float, Integer, Text

from app.models import Base


class Survey(Base):
    """Survey configuration model."""

    __tablename__ = "surveys"

    id = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    context = Column(Text, nullable=False)
    goal = Column(Text, nullable=False)
    constraints = Column(Text, nullable=False, default="[]")
    max_questions = Column(Integer, nullable=False, default=10)
    completion_criteria = Column(Text, nullable=False, default="")
    goal_coverage_threshold = Column(Float, nullable=False, default=0.85)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
