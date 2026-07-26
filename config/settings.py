"""Application settings loaded from environment."""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Normalize Railway/Postgres URLs for SQLAlchemy + psycopg.

    Railway injects values like:
      postgresql://user:pass@host:5432/railway
      postgres://user:pass@host:5432/railway
    SQLAlchemy needs:
      postgresql+psycopg://...
    """
    url = url.strip()
    if not url:
        return url

    if url.startswith("postgres://"):
        url = "postgresql://" + url.removeprefix("postgres://")

    if url.startswith("postgresql+psycopg://"):
        return url

    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")

    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "local"
    APP_NAME: str = "CTD Portal"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8800
    # Railway injects PORT; prefer it when present
    PORT: int | None = None

    SECRET_KEY: str = "change-me"
    JWT_TTL_HOURS: int = 8
    CORS_ORIGINS: str = "http://localhost:8800"
    ALLOWED_EMAIL_DOMAIN: str = ""
    # Dominios permitidos (virgula). Vazio / * / any / off = sem restricao.
    # Ex.: gapi.co.mz  ou  gapi.co.mz,parceiro.mz

    # Local MySQL (discrete fields — preferred in APP_ENV=local)
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "ctd_portal"
    MYSQL_CHARSET: str = "utf8mb4"

    # Production / Railway Postgres (reference: ${{Postgres.DATABASE_URL}})
    # Raw value has no +psycopg driver — normalized in sqlalchemy_database_url
    DATABASE_URL: str = ""

    # Auto-run Alembic on boot (must stay true — no manual migrate in deploy)
    AUTO_MIGRATE: bool = True

    SEED_ADMIN_EMAIL: str = "admin@gapi.co.mz"
    SEED_ADMIN_NAME: str = "Administrador CTD"
    SEED_ADMIN_PASSWORD: str = "Admin@CTD2026"
    # Demo pilares/master — so local. Em producao e sempre ignorado.
    SEED_SAMPLE_DATA: bool = False

    RESEND_API_KEY: str = ""
    RESEND_FROM: str = "CTD GAPI <noreply@gapi.co.mz>"

    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = "ctd-portal"
    # Ex.: https://<accountid>.r2.cloudflarestorage.com  (account id ja vai no host)
    R2_ENDPOINT_URL: str = ""

    # Local file uploads (used when R2 is not configured)
    UPLOAD_DIR: str = "uploads"

    # Python 3.13+ no Windows: relax VERIFY_X509_STRICT if CA store is broken
    SSL_RELAX_X509_STRICT: bool = False

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in {"production", "prod"}

    def validate_for_boot(self) -> None:
        """Fail fast on unsafe production configuration."""
        if not self.is_production:
            return
        weak_secrets = {
            "",
            "change-me",
            "change-me-to-a-long-random-string",
            "secret",
            "secret_key",
        }
        if self.SECRET_KEY.strip() in weak_secrets or len(self.SECRET_KEY.strip()) < 24:
            raise RuntimeError(
                "Producao: SECRET_KEY fraca ou em falta. Defina uma chave longa e aleatoria."
            )
        if not self.DATABASE_URL.strip():
            raise RuntimeError(
                "Producao: DATABASE_URL em falta (Postgres Railway)."
            )
        r2_ok = bool(
            self.R2_ENDPOINT_URL.strip()
            and self.R2_ACCESS_KEY_ID.strip()
            and self.R2_SECRET_ACCESS_KEY.strip()
            and self.R2_BUCKET.strip()
        )
        if not r2_ok:
            raise RuntimeError(
                "Producao: configure R2 (R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, "
                "R2_SECRET_ACCESS_KEY, R2_BUCKET) — disco local e efemero no Railway."
            )

    @property
    def bind_port(self) -> int:
        return self.PORT if self.PORT is not None else self.APP_PORT

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_email_domains(self) -> list[str]:
        """Lista de dominios permitidos. Vazia = sem restricao de dominio."""
        raw = (self.ALLOWED_EMAIL_DOMAIN or "").strip().lower()
        if not raw or raw in {"*", "any", "off", "false", "none"}:
            return []
        return [d.strip().lstrip("@") for d in raw.split(",") if d.strip()]

    def email_domain_allowed(self, email: str) -> bool:
        domains = self.allowed_email_domains
        if not domains:
            return True
        email_norm = (email or "").strip().lower()
        return any(email_norm.endswith(f"@{d}") for d in domains)

    @property
    def uses_mysql(self) -> bool:
        """MySQL when no DATABASE_URL (local). Postgres when DATABASE_URL is set."""
        return not bool(self.DATABASE_URL.strip())

    @property
    def mysql_url(self) -> str:
        user = quote_plus(self.MYSQL_USER)
        password = quote_plus(self.MYSQL_PASSWORD)
        return (
            f"mysql+pymysql://{user}:{password}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset={self.MYSQL_CHARSET}"
        )

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.DATABASE_URL.strip():
            return normalize_database_url(self.DATABASE_URL)
        return self.mysql_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
