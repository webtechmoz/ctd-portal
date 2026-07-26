"""RBAC permission catalog and role defaults."""

from __future__ import annotations

# code, name, description, group
PERMISSION_CATALOG: list[tuple[str, str, str, str]] = [
    ("dashboard.view", "Ver dashboard", "Visao geral e KPIs globais", "portal"),
    ("resultados.view", "Ver resultados", "KPIs por projecto", "portal"),
    ("situacao.view", "Ver ponto de situacao", "Calendario e prazos", "portal"),
    ("projectos.view", "Ver base de projectos", "Consultar dados mestre", "projectos"),
    ("projectos.manage", "Gerir projectos", "Criar/editar dados mestre", "projectos"),
    ("projectos.deactivate", "Desactivar projectos", "Marcar projectos como inactivos", "projectos"),
    ("projectos.delete", "Apagar projectos", "Eliminar projectos sem avaliacoes", "projectos"),
    ("avaliacao.submit", "Submeter avaliacao", "Registar acompanhamento", "avaliacoes"),
    ("avaliacao.view", "Ver avaliacoes", "Listar avaliacoes", "avaliacoes"),
    ("avaliacao.validate", "Validar avaliacoes", "Validar ou reabrir avaliacoes submetidas", "avaliacoes"),
    ("account.change_password", "Alterar palavra-passe", "Alterar a propria palavra-passe", "conta"),
    ("users.view", "Ver utilizadores", "Listar contas", "admin"),
    ("users.manage", "Gerir utilizadores", "Criar/editar contas", "admin"),
    ("roles.manage", "Gerir perfis", "Criar perfis e atribuir permissoes", "admin"),
    ("catalog.manage", "Gerir listas de sistema", "Criar/editar/activar/remover opcoes", "admin"),
    ("reports.view", "Ver relatorios", "Overview e exports", "admin"),
    ("admin.access", "Aceder ao admin", "Entrar no painel de administracao", "admin"),
]

# slug -> list of permission codes (* = all)
ROLE_DEFAULTS: dict[str, dict] = {
    "admin": {
        "name": "Administrador",
        "description": "Acesso total ao portal",
        "is_system": True,
        "permissions": ["*"],
    },
    "member": {
        "name": "Membro",
        "description": "Avaliacao e consulta dos seus projectos",
        "is_system": True,
        "permissions": [
            "dashboard.view",
            "resultados.view",
            "situacao.view",
            "projectos.view",
            "avaliacao.submit",
            "avaliacao.view",
            "account.change_password",
            "reports.view",
        ],
    },
    "visitor": {
        "name": "Visitante",
        "description": "Apenas consulta",
        "is_system": True,
        "permissions": [
            "dashboard.view",
            "resultados.view",
            "situacao.view",
            "projectos.view",
            "avaliacao.view",
            "account.change_password",
            "reports.view",
        ],
    },
    "coordenador": {
        "name": "Coordenador CTD",
        "description": "Valida avaliacoes e acompanha projectos",
        "is_system": True,
        "permissions": [
            "dashboard.view",
            "resultados.view",
            "situacao.view",
            "projectos.view",
            "projectos.manage",
            "avaliacao.submit",
            "avaliacao.view",
            "avaliacao.validate",
            "account.change_password",
            "users.view",
            "reports.view",
            "admin.access",
        ],
    },
}
