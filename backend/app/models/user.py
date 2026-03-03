"""User ORM model."""

from sqlalchemy import Column, Text

from app.models import Base


class User(Base):
    """Participant user model."""

    __tablename__ = "users"

    id = Column(Text, primary_key=True)
    participant_name = Column(Text, nullable=True)
    metadata_ = Column("metadata", Text, default="{}")
    created_at = Column(Text, nullable=False)
