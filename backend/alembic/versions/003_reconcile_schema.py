"""Reconcile schema drift: add answer_flags, drop stale columns

Revision ID: 003
Revises: 002
Create Date: 2026-03-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add answer_flags to responses; drop stale columns from surveys and responses."""
    # Add answer_flags column to responses
    op.add_column(
        "responses",
        sa.Column("answer_flags", sa.Text(), nullable=True),
    )

    # Drop context_similarity_threshold from surveys (no longer in ORM)
    with op.batch_alter_table("surveys") as batch_op:
        batch_op.drop_column("context_similarity_threshold")

    # Drop question_embedding from responses (no longer in ORM)
    with op.batch_alter_table("responses") as batch_op:
        batch_op.drop_column("question_embedding")


def downgrade() -> None:
    """Reverse: restore dropped columns, remove answer_flags."""
    # Restore context_similarity_threshold on surveys
    op.add_column(
        "surveys",
        sa.Column(
            "context_similarity_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.7",
        ),
    )

    # Restore question_embedding on responses
    op.add_column(
        "responses",
        sa.Column("question_embedding", sa.Text(), nullable=True),
    )

    # Drop answer_flags from responses
    with op.batch_alter_table("responses") as batch_op:
        batch_op.drop_column("answer_flags")
