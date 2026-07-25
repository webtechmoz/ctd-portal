"""Add composite indexes for hot query paths.

Revision ID: 0002_indexes
Revises: 0001_initial
Create Date: 2026-07-25
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002_indexes"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_users_status_role", "users", ["status", "role"])
    op.create_index("ix_pilares_status_nome", "pilares", ["status", "nome"])
    op.create_index(
        "ix_avaliacoes_pilar_data_sub_id",
        "avaliacoes",
        ["pilar_id", "data_sub", "id"],
    )
    op.create_index(
        "ix_avaliacoes_user_data_sub",
        "avaliacoes",
        ["user_id", "data_sub"],
    )


def downgrade() -> None:
    op.drop_index("ix_avaliacoes_user_data_sub", table_name="avaliacoes")
    op.drop_index("ix_avaliacoes_pilar_data_sub_id", table_name="avaliacoes")
    op.drop_index("ix_pilares_status_nome", table_name="pilares")
    op.drop_index("ix_users_status_role", table_name="users")
