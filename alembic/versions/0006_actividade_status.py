"""Alembic — status de planeamento nas actividades (activa/cancelada)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_actividade_status"
down_revision = "0005_anexos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pilar_actividades",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="activa",
        ),
    )


def downgrade() -> None:
    op.drop_column("pilar_actividades", "status")
