"""Alembic — catalog_options (listas de sistema)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_catalog"
down_revision = "0003_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_options",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=150), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category", "code", name="uq_catalog_category_code"),
    )
    op.create_index("ix_catalog_options_category", "catalog_options", ["category"])


def downgrade() -> None:
    op.drop_index("ix_catalog_options_category", table_name="catalog_options")
    op.drop_table("catalog_options")
