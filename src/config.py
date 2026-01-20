"""
Configuration management using Pydantic Settings.

Loads configuration from environment variables and .env file.
All settings are validated on application startup.
"""

from functools import lru_cache
from typing import Optional

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

    # LLM Provider Selection
    llm_provider: str = "google"  # anthropic | openai | google

    # API Keys (only the selected provider's key is required)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    # Model Configuration
    model_name: str = "gemini-2.5-pro"
    max_tokens: int = 4096

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
