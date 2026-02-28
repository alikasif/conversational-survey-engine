"""Session ORM model."""

from sqlalchemy import Column, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import relationship

from app.models import Base


class Session(Base):
    """Survey session model."""

    __tablename__ = "sessions"

    id = Column(Text, primary_key=True)
    survey_id = Column(Text, ForeignKey("surveys.id"), nullable=False)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    status = Column(Text, nullable=False, default="active")
    completion_reason = Column(Text, nullable=True)
    question_count = Column(Integer, nullable=False, default=0)
    created_at = Column(Text, nullable=False)
    completed_at = Column(Text, nullable=True)

    survey = relationship("Survey", lazy="selectin")
    user = relationship("User", lazy="selectin")
    responses = relationship("Response", back_populates="session", lazy="selectin")

    __table_args__ = (
        Index("idx_sessions_survey_id", "survey_id"),
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_survey_user", "survey_id", "user_id"),
    )
