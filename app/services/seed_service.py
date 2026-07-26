"""Initial data seed (RBAC, catalog, optional admin, optional sample pilares).

Safe to call on every boot. Sample projectos are NEVER created unless
SEED_SAMPLE_DATA=true. Avaliacoes are never seeded.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db import bootstrap as db
from app.models.enums import (
    Impacto,
    PilarStatus,
    Prioridade,
    Probabilidade,
    UserRole,
    UserStatus,
)
from app.models.pilar import (
    Pilar,
    PilarActividade,
    PilarObjectivo,
    PilarOrcamentoCategoria,
    PilarProximoPasso,
    PilarResponsavel,
    PilarRisco,
)
from app.models.user import User
from app.services.auth_service import hash_password
from app.services.catalog_service import ensure_catalog_seed
from app.services.rbac_service import ensure_rbac_seed
from config.settings import settings

logger = logging.getLogger(__name__)

# Demo data — only when SEED_SAMPLE_DATA=true (local). Never in production.
DEFAULT_PILARES = [
    {
        "nome": "meuCredito",
        "descricao": "Plataforma de credito digital",
        "area": "Servicos Financeiros",
        "fase": "Implementacao",
        "obj_geral": "Digitalizar o acesso ao credito",
        "kpis": "Utilizadores activos; volume de credito",
        "beneficios": "Acesso mais rapido e transparente",
    },
    {
        "nome": "DHIS2",
        "descricao": "Sistema de informacao de saude",
        "area": "Saude",
        "fase": "Operacao",
        "obj_geral": "Melhorar a gestao de dados de saude",
        "kpis": "Relatorios atempadamente; cobertura de unidades",
        "beneficios": "Decisao baseada em dados",
    },
    {
        "nome": "Starlink",
        "descricao": "Conectividade satelite",
        "area": "Infraestrutura",
        "fase": "Expansao",
        "obj_geral": "Garantir conectividade em zonas remotas",
        "kpis": "Sites ligados; uptime",
        "beneficios": "Continuidade operacional",
    },
    {
        "nome": "Microsoft 365",
        "descricao": "Colaboracao e produtividade (M365 / SharePoint)",
        "area": "Produtividade",
        "fase": "Adocao",
        "obj_geral": "Padronizar ferramentas de colaboracao",
        "kpis": "Taxa de adocao; sites activos",
        "beneficios": "Trabalho colaborativo eficiente",
    },
    {
        "nome": "PHC",
        "descricao": "Sistema de gestao empresarial PHC",
        "area": "Gestao",
        "fase": "Operacao",
        "obj_geral": "Integrar processos administrativos e financeiros",
        "kpis": "Processos digitalizados; tempo de ciclo",
        "beneficios": "Controlo e rastreabilidade",
    },
]

_UNSAFE_PASSWORDS = {
    "",
    "Admin@CTD2026",
    "admin",
    "password",
    "123456",
}


def _ensure_master(session, pilar: Pilar) -> None:
    """Fill demo master rows for a sample pilar that has no actividades yet."""
    if pilar.actividades:
        return

    pilar.objectivos.append(
        PilarObjectivo(descricao=f"Objectivo especifico 1 — {pilar.nome}", ordem=1)
    )
    pilar.objectivos.append(
        PilarObjectivo(descricao=f"Objectivo especifico 2 — {pilar.nome}", ordem=2)
    )
    pilar.actividades.append(
        PilarActividade(
            nome="Actividade A — arranque",
            responsavel="Equipa CTD",
            prioridade=Prioridade.alta,
            descricao="Preparacao e arranque",
            ordem=1,
        )
    )
    pilar.actividades.append(
        PilarActividade(
            nome="Actividade B — implementacao",
            responsavel="Equipa tecnica",
            prioridade=Prioridade.media,
            descricao="Implementacao operacional",
            ordem=2,
        )
    )
    pilar.orcamento_categorias.append(
        PilarOrcamentoCategoria(
            categoria="Equipamento",
            valor_alocado=Decimal("100000.00"),
            ordem=1,
        )
    )
    pilar.orcamento_categorias.append(
        PilarOrcamentoCategoria(
            categoria="Formacao",
            valor_alocado=Decimal("25000.00"),
            ordem=2,
        )
    )
    pilar.riscos.append(
        PilarRisco(
            descricao="Atraso na disponibilizacao de recursos",
            probabilidade=Probabilidade.media,
            impacto=Impacto.alto,
            mitigacao="Plano de contingencia e priorizacao",
            ordem=1,
        )
    )
    pilar.proximos_passos.append(
        PilarProximoPasso(
            descricao="Revisao de indicadores com stakeholders",
            responsavel="Coordenador CTD",
            ordem=1,
        )
    )
    if not pilar.orc_aprovado:
        pilar.orc_aprovado = Decimal("125000.00")
        pilar.orc_fonte = "Orcamento GAPI"
    logger.info("Seed master criado para pilar %s", pilar.nome)


def _seed_sample_pilares(session, admin: User | None) -> None:
    sample_names = {d["nome"] for d in DEFAULT_PILARES}
    for data in DEFAULT_PILARES:
        pilar = session.scalar(select(Pilar).where(Pilar.nome == data["nome"]))
        if not pilar:
            pilar = Pilar(
                **data,
                status=PilarStatus.activo,
                periodicidade_dias=90,
                dias_aberto=7,
                orc_moeda="MZN",
            )
            session.add(pilar)
            session.flush()
            logger.info("Seed pilar criado: %s", data["nome"])

    pilares = session.scalars(
        select(Pilar)
        .where(Pilar.nome.in_(sample_names))
        .options(
            selectinload(Pilar.actividades),
            selectinload(Pilar.objectivos),
            selectinload(Pilar.orcamento_categorias),
            selectinload(Pilar.riscos),
            selectinload(Pilar.proximos_passos),
            selectinload(Pilar.responsaveis),
        )
    ).all()

    for pilar in pilares:
        _ensure_master(session, pilar)
        if admin:
            linked = any(r.user_id == admin.id for r in pilar.responsaveis)
            if not linked:
                session.add(PilarResponsavel(pilar_id=pilar.id, user_id=admin.id))


def run_seed(*, force_admin: bool = False, sample_data: bool | None = None) -> None:
    if db.SessionLocal is None:
        raise RuntimeError("Database not initialized")

    if sample_data is None:
        sample_data = bool(settings.SEED_SAMPLE_DATA)

    # Never seed demo projectos in production, even if misconfigured
    if settings.is_production and sample_data:
        logger.warning(
            "SEED_SAMPLE_DATA ignorado em producao — projectos demo nao serao criados."
        )
        sample_data = False

    admin_email = settings.SEED_ADMIN_EMAIL.strip().lower()
    admin_name = settings.SEED_ADMIN_NAME
    admin_password = settings.SEED_ADMIN_PASSWORD

    session = db.SessionLocal()
    try:
        ensure_rbac_seed(session)
        ensure_catalog_seed(session)

        user_count = session.scalar(select(func.count()).select_from(User)) or 0
        admin = session.scalar(select(User).where(User.email == admin_email))

        if user_count == 0 or force_admin:
            if settings.is_production and admin_password in _UNSAFE_PASSWORDS:
                raise RuntimeError(
                    "Producao: defina SEED_ADMIN_PASSWORD forte antes do primeiro arranque "
                    "(password por omissao nao e permitida)."
                )
            if not admin:
                admin = User(
                    name=admin_name,
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    role=UserRole.admin,
                    status=UserStatus.active,
                    must_change_password=False,
                )
                session.add(admin)
                session.flush()
                logger.info("Seed admin criado: %s", admin_email)
            elif force_admin:
                if settings.is_production and admin_password in _UNSAFE_PASSWORDS:
                    raise RuntimeError(
                        "Producao: SEED_ADMIN_PASSWORD insegura — recusado actualizar admin."
                    )
                admin.password_hash = hash_password(admin_password)
                admin.name = admin_name
                admin.status = UserStatus.active
                admin.role = UserRole.admin
                logger.info("Seed admin actualizado: %s", admin_email)

        if not admin:
            admin = session.scalar(select(User).where(User.email == admin_email))

        if sample_data:
            _seed_sample_pilares(session, admin)
        else:
            logger.info(
                "Seed de projectos demo desactivado (SEED_SAMPLE_DATA=false). "
                "Avaliacoes nunca sao seed."
            )

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
