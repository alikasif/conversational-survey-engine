"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables and indexes."""
    op.create_table(
        "surveys",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("constraints", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("max_questions", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("completion_criteria", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "goal_coverage_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.85",
        ),
        sa.Column(
            "context_similarity_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.7",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("participant_name", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("survey_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("completion_reason", sa.Text(), nullable=True),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sessions_survey_id", "sessions", ["survey_id"])
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"])
    op.create_index("idx_sessions_survey_user", "sessions", ["survey_id", "user_id"])

    op.create_table(
        "responses",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("survey_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("question_id", sa.Text(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("question_embedding", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_responses_session_id", "responses", ["session_id"])
    op.create_index("idx_responses_survey_id", "responses", ["survey_id"])
    op.create_index("idx_responses_user_id", "responses", ["user_id"])
    op.create_index(
        "idx_responses_survey_user", "responses", ["survey_id", "user_id"]
    )


def downgrade() -> None:
    """Drop all tables and indexes."""
    op.drop_index("idx_responses_survey_user", table_name="responses")
    op.drop_index("idx_responses_user_id", table_name="responses")
    op.drop_index("idx_responses_survey_id", table_name="responses")
    op.drop_index("idx_responses_session_id", table_name="responses")
    op.drop_table("responses")

    op.drop_index("idx_sessions_survey_user", table_name="sessions")
    op.drop_index("idx_sessions_user_id", table_name="sessions")
    op.drop_index("idx_sessions_survey_id", table_name="sessions")
    op.drop_table("sessions")

    op.drop_table("users")
    op.drop_table("surveys")
