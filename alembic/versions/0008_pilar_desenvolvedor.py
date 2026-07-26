"""Alembic — desenvolvedor no projecto."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_pilar_desenvolvedor"
down_revision = "0007_must_change_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pilares",
        sa.Column("desenvolvedor", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pilares", "desenvolvedor")
