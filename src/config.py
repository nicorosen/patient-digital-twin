"""
Configuration management using Pydantic Settings.

Loads configuration from environment variables and .env file.
All settings are validated on application startup.
"""

from functools import lru_cache
from typing import Dict, List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# High-reasoning models only — no Flash models
SUPPORTED_MODELS: Dict[str, List[str]] = {
    "google": ["gemini-2.5-pro"],
    "anthropic": ["claude-opus-4-5-20251101", "claude-sonnet-4-20250514"],
    "openai": ["o3", "gpt-4.1"],
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars (e.g., Supabase keys)
    )

    # Database
    database_url: str = "postgresql://localhost:5432/patient_twin"

    @model_validator(mode="after")
    def check_streamlit_secrets(self) -> "Settings":
        """Override database_url from Streamlit secrets if available."""
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
                # Use object.__setattr__ to bypass frozen validation if any
                object.__setattr__(self, "database_url", st.secrets["DATABASE_URL"])
        except Exception:
            pass
        return self

    # LLM Provider Selection
    llm_provider: str = "google"  # anthropic | openai | google

    # API Keys (only the selected provider's key is required)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    # Model Configuration
    model_name: str = "gemini-2.5-pro"
    max_tokens: int = 4096

    # Specialist model (faster/cheaper model for specialist consultations)
    specialist_provider: Optional[str] = None  # Falls back to llm_provider
    specialist_model: Optional[str] = None  # Falls back to model_name

    # Web Search (Tavily)
    tavily_api_key: Optional[str] = None

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
