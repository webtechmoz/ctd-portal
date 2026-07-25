"""API route modules. Register via register_api_routes(app) in Fase 1."""


def register_api_routes(app) -> None:
    from app.api import (
        auth,
        users,
        roles,
        pilares,
        avaliacoes,
        dashboard,
        reports,
        uploads,
        catalog,
        anexos,
    )

    auth.register(app)
    users.register(app)
    roles.register(app)
    catalog.register(app)
    pilares.register(app)
    avaliacoes.register(app)
    anexos.register(app)
    dashboard.register(app)
    reports.register(app)
    uploads.register(app)
