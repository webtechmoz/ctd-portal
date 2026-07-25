"""Upload routes (R2) — Fase 4."""

API_PREFIX = "/api/v1"


def register(app) -> None:
    @app.route(f"{API_PREFIX}/uploads/avatar", methods=["POST"])
    def upload_avatar():
        return {"error": {"code": "NOT_IMPLEMENTED", "message": "Fase 4"}}
