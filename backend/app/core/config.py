"""Application settings.

DATABASE_URL defaults to a local SQLite file so the platform runs with zero
infrastructure; point it at PostgreSQL in production (SQLAlchemy 2.0 makes the
swap configuration-only — no dialect-specific SQL is used anywhere).
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Sovereign Banking Intelligence Platform"
    version: str = "0.1.0"
    database_url: str = "sqlite:///./sovereign.db"
    cors_origins: list[str] = ["http://localhost:3000"]
    upload_dir: str = "./uploads"
    # If set, all /api requests must carry a matching X-API-Key header.
    # Production deployments should front this with real SSO/OIDC + RBAC.
    api_key: str | None = None
    seed_demo_data: bool = True

    model_config = {"env_prefix": "SOVEREIGN_", "env_file": ".env"}


settings = Settings()
