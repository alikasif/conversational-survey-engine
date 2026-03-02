"""Add question mode columns to surveys

Revision ID: 002
Revises: 001
Create Date: 2026-03-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add question_mode, preset_questions, preset_generated_at to surveys."""
    op.add_column(
        "surveys",
        sa.Column(
            "question_mode",
            sa.Text(),
            nullable=False,
            server_default="dynamic",
        ),
    )
    op.add_column(
        "surveys",
        sa.Column("preset_questions", sa.Text(), nullable=True),
    )
    op.add_column(
        "surveys",
        sa.Column("preset_generated_at", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove question_mode, preset_questions, preset_generated_at from surveys."""
    with op.batch_alter_table("surveys") as batch_op:
        batch_op.drop_column("preset_generated_at")
        batch_op.drop_column("preset_questions")
        batch_op.drop_column("question_mode")
