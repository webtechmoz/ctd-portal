"""Alembic — flag passos criados na avaliacao."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_passo_criado_nesta"
down_revision = "0010_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "avaliacao_proximos_passos",
        sa.Column(
            "criado_nesta_avaliacao",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT ap.id AS ap_id, ap.passo_id, a.id AS aval_id, a.pilar_id, pp.id AS passo_row_id
            FROM avaliacao_proximos_passos ap
            INNER JOIN avaliacoes a ON a.id = ap.avaliacao_id
            INNER JOIN pilar_proximos_passos pp ON pp.id = ap.passo_id
            ORDER BY a.pilar_id, a.id, pp.id
            """
        )
    ).mappings().all()

    first_link: dict[int, int] = {}
    min_passo_by_pilar: dict[int, int] = {}
    for row in rows:
        pid = int(row["passo_id"])
        if pid not in first_link:
            first_link[pid] = int(row["aval_id"])
        pilar_id = int(row["pilar_id"])
        passo_row_id = int(row["passo_row_id"])
        if pilar_id not in min_passo_by_pilar or passo_row_id < min_passo_by_pilar[pilar_id]:
            min_passo_by_pilar[pilar_id] = passo_row_id

    to_mark: list[int] = []
    for row in rows:
        pid = int(row["passo_id"])
        aval_id = int(row["aval_id"])
        pilar_id = int(row["pilar_id"])
        passo_row_id = int(row["passo_row_id"])
        if first_link.get(pid) != aval_id:
            continue
        # Passos master/seed tendem a ser os mais antigos do pilar; os adicionados
        # na avaliacao ficam com id superior.
        if passo_row_id > min_passo_by_pilar.get(pilar_id, passo_row_id):
            to_mark.append(int(row["ap_id"]))

    for ap_id in to_mark:
        conn.execute(
            sa.text(
                "UPDATE avaliacao_proximos_passos SET criado_nesta_avaliacao = 1 WHERE id = :id"
            ),
            {"id": ap_id},
        )


def downgrade() -> None:
    op.drop_column("avaliacao_proximos_passos", "criado_nesta_avaliacao")
