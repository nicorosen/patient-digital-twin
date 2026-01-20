"""
Configuration management using Pydantic Settings.

Loads configuration from environment variables and .env file.
All settings are validated on application startup.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql://localhost:5432/patient_twin"

    # LLM / Anthropic
    anthropic_api_key: str
    model_name: str = "claude-sonnet-4-20250514"

    # Vector DB (Chroma)
    chroma_persist_dir: str = "./data/embeddings"
    embedding_model: str = "all-MiniLM-L6-v2"

    # Application
    log_level: str = "INFO"
    environment: str = "development"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once,
    improving performance and ensuring consistency.
    """
    return Settings()
