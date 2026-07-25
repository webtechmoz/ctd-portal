"""Initial schema — users, pilares, avaliacoes.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-25
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("admin", "member", "visitor", name="user_role", native_enum=False, length=20), nullable=False),
        sa.Column("status", sa.Enum("active", "inactive", name="user_status", native_enum=False, length=20), nullable=False),
        sa.Column("profile_image_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "token_blacklist",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index("ix_token_blacklist_expires_at", "token_blacklist", ["expires_at"])

    op.create_table(
        "pilares",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("area", sa.String(length=150), nullable=False),
        sa.Column("fase", sa.String(length=100), nullable=False),
        sa.Column("obj_geral", sa.Text(), nullable=False),
        sa.Column("kpis", sa.Text(), nullable=False),
        sa.Column("beneficios", sa.Text(), nullable=False),
        sa.Column("plano_obs", sa.Text(), nullable=True),
        sa.Column("parceiros", sa.Text(), nullable=True),
        sa.Column("orc_aprovado", sa.Numeric(14, 2), nullable=True),
        sa.Column("orc_moeda", sa.String(length=10), nullable=False),
        sa.Column("orc_fonte", sa.String(length=255), nullable=True),
        sa.Column("data_inicio", sa.Date(), nullable=True),
        sa.Column("data_fim_prevista", sa.Date(), nullable=True),
        sa.Column("periodicidade_dias", sa.Integer(), nullable=False),
        sa.Column("dias_aberto", sa.Integer(), nullable=False),
        sa.Column("proxima_avaliacao", sa.Date(), nullable=True),
        sa.Column("prazo_limite", sa.Date(), nullable=True),
        sa.Column("status", sa.Enum("activo", "inactivo", name="pilar_status", native_enum=False, length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome"),
    )

    op.create_table(
        "pilar_responsaveis",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pilar_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pilar_id"], ["pilares.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilar_id", "user_id", name="uq_pilar_user"),
    )

    op.create_table(
        "pilar_objectivos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pilar_id", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pilar_id"], ["pilares.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pilar_objectivos_pilar_id", "pilar_objectivos", ["pilar_id"])

    op.create_table(
        "pilar_actividades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pilar_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("responsavel", sa.String(length=150), nullable=False),
        sa.Column("prioridade", sa.Enum("alta", "media", "baixa", name="prioridade", native_enum=False, length=20), nullable=False),
        sa.Column("data_inicio_prevista", sa.Date(), nullable=True),
        sa.Column("data_fim_prevista", sa.Date(), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("obs_planeamento", sa.Text(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pilar_id"], ["pilares.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pilar_actividades_pilar_id", "pilar_actividades", ["pilar_id"])

    op.create_table(
        "pilar_orcamento_categorias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pilar_id", sa.Integer(), nullable=False),
        sa.Column("categoria", sa.String(length=150), nullable=False),
        sa.Column("valor_alocado", sa.Numeric(14, 2), nullable=False),
        sa.Column("obs", sa.Text(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pilar_id"], ["pilares.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pilar_orcamento_categorias_pilar_id", "pilar_orcamento_categorias", ["pilar_id"])

    op.create_table(
        "pilar_riscos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pilar_id", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("probabilidade", sa.Enum("alta", "media", "baixa", name="probabilidade", native_enum=False, length=20), nullable=False),
        sa.Column("impacto", sa.Enum("alto", "medio", "baixo", name="impacto", native_enum=False, length=20), nullable=False),
        sa.Column("mitigacao", sa.Text(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pilar_id"], ["pilares.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pilar_riscos_pilar_id", "pilar_riscos", ["pilar_id"])

    op.create_table(
        "pilar_proximos_passos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pilar_id", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("responsavel", sa.String(length=150), nullable=False),
        sa.Column("prazo", sa.Date(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pilar_id"], ["pilares.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pilar_proximos_passos_pilar_id", "pilar_proximos_passos", ["pilar_id"])

    op.create_table(
        "avaliacoes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pilar_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("estado_geral", sa.Text(), nullable=False),
        sa.Column("desafios", sa.Text(), nullable=False),
        sa.Column("licoes", sa.Text(), nullable=False),
        sa.Column("orc_obs", sa.Text(), nullable=True),
        sa.Column("recomendacoes", sa.Text(), nullable=True),
        sa.Column("comentarios", sa.Text(), nullable=True),
        sa.Column("progresso", sa.Float(), nullable=False),
        sa.Column("assinatura", sa.String(length=255), nullable=True),
        sa.Column("data_sub", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["pilar_id"], ["pilares.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_avaliacoes_pilar_id", "avaliacoes", ["pilar_id"])
    op.create_index("ix_avaliacoes_user_id", "avaliacoes", ["user_id"])
    op.create_index("ix_avaliacoes_data_sub", "avaliacoes", ["data_sub"])

    op.create_table(
        "avaliacao_actividades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("avaliacao_id", sa.Integer(), nullable=False),
        sa.Column("pilar_actividade_id", sa.Integer(), nullable=False),
        sa.Column("estado", sa.Enum("pendente", "em_progresso", "concluida", name="actividade_estado", native_enum=False, length=20), nullable=False),
        sa.Column("pct_conclusao", sa.Integer(), nullable=False),
        sa.Column("data_inicio_real", sa.Date(), nullable=True),
        sa.Column("data_fim_real", sa.Date(), nullable=True),
        sa.Column("obs_execucao", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["avaliacao_id"], ["avaliacoes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pilar_actividade_id"], ["pilar_actividades.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("avaliacao_id", "pilar_actividade_id", name="uq_av_actividade"),
    )
    op.create_index("ix_avaliacao_actividades_avaliacao_id", "avaliacao_actividades", ["avaliacao_id"])

    op.create_table(
        "avaliacao_orcamentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("avaliacao_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("valor_executado", sa.Numeric(14, 2), nullable=False),
        sa.Column("forma_execucao", sa.String(length=255), nullable=True),
        sa.Column("obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["avaliacao_id"], ["avaliacoes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["categoria_id"], ["pilar_orcamento_categorias.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("avaliacao_id", "categoria_id", name="uq_av_orcamento"),
    )
    op.create_index("ix_avaliacao_orcamentos_avaliacao_id", "avaliacao_orcamentos", ["avaliacao_id"])

    op.create_table(
        "avaliacao_riscos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("avaliacao_id", sa.Integer(), nullable=False),
        sa.Column("risco_id", sa.Integer(), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["avaliacao_id"], ["avaliacoes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["risco_id"], ["pilar_riscos.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("avaliacao_id", "risco_id", name="uq_av_risco"),
    )
    op.create_index("ix_avaliacao_riscos_avaliacao_id", "avaliacao_riscos", ["avaliacao_id"])

    op.create_table(
        "avaliacao_proximos_passos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("avaliacao_id", sa.Integer(), nullable=False),
        sa.Column("passo_id", sa.Integer(), nullable=False),
        sa.Column("alcancado", sa.Boolean(), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["avaliacao_id"], ["avaliacoes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["passo_id"], ["pilar_proximos_passos.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("avaliacao_id", "passo_id", name="uq_av_passo"),
    )
    op.create_index("ix_avaliacao_proximos_passos_avaliacao_id", "avaliacao_proximos_passos", ["avaliacao_id"])


def downgrade() -> None:
    op.drop_table("avaliacao_proximos_passos")
    op.drop_table("avaliacao_riscos")
    op.drop_table("avaliacao_orcamentos")
    op.drop_table("avaliacao_actividades")
    op.drop_table("avaliacoes")
    op.drop_table("pilar_proximos_passos")
    op.drop_table("pilar_riscos")
    op.drop_table("pilar_orcamento_categorias")
    op.drop_table("pilar_actividades")
    op.drop_table("pilar_objectivos")
    op.drop_table("pilar_responsaveis")
    op.drop_table("pilares")
    op.drop_table("token_blacklist")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
