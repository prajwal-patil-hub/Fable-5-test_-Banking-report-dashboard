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
    # Off by default — deterministic-first is a product principle.
    # Providers:
    #   anthropic (default) — needs ANTHROPIC_API_KEY + `pip install -e ".[llm]"`
    #   ollama              — local model, no API key, no extra deps
    #                         (SOVEREIGN_LLM_PROVIDER=ollama; model pulled via `ollama pull`)
    llm_extraction_enabled: bool = False
    llm_provider: str = "anthropic"  # anthropic | ollama
    # Model id; defaults per provider when unset
    # (anthropic: claude-sonnet-5, ollama: llama3.1:8b).
    llm_model: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    # Display-only conversion rate for the currency layer (INR per USD).
    # Warehouse storage is always ₹ crore; USD is computed at read time.
    usd_inr_rate: float = 83.5

    model_config = {"env_prefix": "SOVEREIGN_", "env_file": ".env"}


settings = Settings()
