"""Alembic — workflow de validacao de avaliacoes."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_avaliacao_status"
down_revision = "0008_pilar_desenvolvedor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "avaliacoes",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="submetida",
        ),
    )
    op.add_column("avaliacoes", sa.Column("validated_by_id", sa.Integer(), nullable=True))
    op.add_column("avaliacoes", sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("avaliacoes", sa.Column("reopened_by_id", sa.Integer(), nullable=True))
    op.add_column("avaliacoes", sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("avaliacoes", sa.Column("validation_note", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_avaliacoes_validated_by",
        "avaliacoes",
        "users",
        ["validated_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_avaliacoes_reopened_by",
        "avaliacoes",
        "users",
        ["reopened_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_avaliacoes_status", "avaliacoes", ["status"])


def downgrade() -> None:
    op.drop_index("ix_avaliacoes_status", table_name="avaliacoes")
    op.drop_constraint("fk_avaliacoes_reopened_by", "avaliacoes", type_="foreignkey")
    op.drop_constraint("fk_avaliacoes_validated_by", "avaliacoes", type_="foreignkey")
    op.drop_column("avaliacoes", "validation_note")
    op.drop_column("avaliacoes", "reopened_at")
    op.drop_column("avaliacoes", "reopened_by_id")
    op.drop_column("avaliacoes", "validated_at")
    op.drop_column("avaliacoes", "validated_by_id")
    op.drop_column("avaliacoes", "status")
