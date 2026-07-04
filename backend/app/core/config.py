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
    # LLM fallback extraction (document_intelligence.extractors.LlmExtractor).
    # Off by default — deterministic-first is a product principle. Requires
    # ANTHROPIC_API_KEY in the environment and `pip install -e ".[llm]"`.
    llm_extraction_enabled: bool = False
    llm_model: str = "claude-sonnet-5"

    model_config = {"env_prefix": "SOVEREIGN_", "env_file": ".env"}


settings = Settings()
