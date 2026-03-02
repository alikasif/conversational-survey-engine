"""Response ORM model."""

from sqlalchemy import Column, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import relationship

from app.models import Base


class Response(Base):
    """Question-answer response model."""

    __tablename__ = "responses"

    id = Column(Text, primary_key=True)
    session_id = Column(Text, ForeignKey("sessions.id"), nullable=False)
    survey_id = Column(Text, ForeignKey("surveys.id"), nullable=False)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    question_id = Column(Text, nullable=False)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    question_number = Column(Integer, nullable=False)
    answer_flags = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)

    session = relationship("Session", back_populates="responses")

    __table_args__ = (
        Index("idx_responses_session_id", "session_id"),
        Index("idx_responses_survey_id", "survey_id"),
        Index("idx_responses_user_id", "user_id"),
        Index("idx_responses_survey_user", "survey_id", "user_id"),
    )
