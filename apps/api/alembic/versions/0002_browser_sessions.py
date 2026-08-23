"""Add remote browser sessions and redacted action audits."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_browser_sessions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "browser_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bot_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("current_url", sa.String(4096), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("allowed_domains", sa.JSON(), nullable=False),
        sa.Column("viewport_width", sa.Integer(), nullable=False),
        sa.Column("viewport_height", sa.Integer(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_browser_sessions_bot_id", "browser_sessions", ["bot_id"])
    op.create_index("ix_browser_sessions_status", "browser_sessions", ["status"])
    op.create_table(
        "browser_actions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("result_url", sa.String(4096), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["browser_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_browser_actions_session_id", "browser_actions", ["session_id"])
    op.create_index("ix_browser_actions_kind", "browser_actions", ["kind"])


def downgrade() -> None:
    op.drop_table("browser_actions")
    op.drop_table("browser_sessions")
