"""Alembic — anexos (ficheiros carregados)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_anexos"
down_revision = "0004_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anexos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("source_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("pilar_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pilar_id"], ["pilares.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_anexos_source", "anexos", ["source_type", "source_id"])
    op.create_index("ix_anexos_pilar_id", "anexos", ["pilar_id"])
    op.create_index("ix_anexos_original_name", "anexos", ["original_name"])
    op.create_index("ix_anexos_uploaded_by_id", "anexos", ["uploaded_by_id"])


def downgrade() -> None:
    op.drop_index("ix_anexos_uploaded_by_id", table_name="anexos")
    op.drop_index("ix_anexos_original_name", table_name="anexos")
    op.drop_index("ix_anexos_pilar_id", table_name="anexos")
    op.drop_index("ix_anexos_source", table_name="anexos")
    op.drop_table("anexos")
