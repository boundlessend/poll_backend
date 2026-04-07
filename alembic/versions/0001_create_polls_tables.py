"""create polls tables

Revision ID: 0001_create_polls_tables
Revises:
Create Date: 2026-04-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_create_polls_tables"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "polls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "poll_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "poll_id",
            sa.Integer(),
            sa.ForeignKey("polls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
    )

    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "poll_id",
            sa.Integer(),
            sa.ForeignKey("polls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "option_id",
            sa.Integer(),
            sa.ForeignKey("poll_options.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("voter_id", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("poll_id", "voter_id", name="uq_votes_poll_voter"),
    )

    op.create_index("ix_votes_poll_id", "votes", ["poll_id"])
    op.create_index("ix_votes_option_id", "votes", ["option_id"])
    op.create_index("ix_poll_options_poll_id", "poll_options", ["poll_id"])


def downgrade() -> None:
    op.drop_index("ix_poll_options_poll_id", table_name="poll_options")
    op.drop_index("ix_votes_option_id", table_name="votes")
    op.drop_index("ix_votes_poll_id", table_name="votes")
    op.drop_table("votes")
    op.drop_table("poll_options")
    op.drop_table("polls")
