"""Alembic — must_change_password em users."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_must_change_password"
down_revision = "0006_actividade_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
