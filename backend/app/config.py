"""
OrgIntel Configuration Module
Centralized settings management using pydantic-settings.
"""

from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    # Product Metadata
    APP_NAME: str = "OrgIntel"
    APP_TAGLINE: str = "AI-powered company intelligence"
    VERSION: str = "1.0.0"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "*"

    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DATABASE_PATH: Path = DATA_DIR / "orgintel.db"

    # HTTP & Challenge Constraints
    HTTP_TIMEOUT_SECONDS: float = 12.0
    HTTP_MAX_RETRIES: int = 2
    HTTP_CONCURRENCY_LIMIT: int = 10
    HTTP_USER_AGENT: str = "OrgIntel-CompanyIntelligence/1.0 (+https://builderr.ai)"

    # Caching
    CACHE_ENABLED: bool = True
    CACHE_TTL_HOURS: int = 48

    # LLM Settings
    LLM_PROVIDER: str = "mock"  # 'groq', 'openai', 'mock', 'none'
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_API_KEY: Optional[str] = None
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 1024

    # External APIs (Authoritative Registries)
    BRREG_BASE_URL: str = "https://data.brreg.no/enhetsregisteret/api"
    BRREG_REGNSKAP_BASE_URL: str = "https://data.brreg.no/regnskapsregisteret"
    BRREG_RATE_LIMIT_RPS: int = 5

    # Budget & Resource Guardrails (Hackathon limits: 2000 requests, $10 budget, 45m time)
    MAX_OUTBOUND_REQUESTS_PER_RUN: int = 25
    MAX_ESTIMATED_COST_PER_RUN_USD: float = 0.02

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "cache").mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "snapshots").mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "exports").mkdir(parents=True, exist_ok=True)
