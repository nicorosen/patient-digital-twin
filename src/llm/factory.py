"""
LLM Factory for multi-provider support.

Creates LLM instances based on the configured provider, enabling
seamless switching between Anthropic, OpenAI, and Google models.
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger("llm.factory")


def get_chat_model(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> BaseChatModel:
    """
    Factory function to create an LLM instance based on provider.

    Args:
        provider: LLM provider override (anthropic, openai, google).
                  If not specified, uses settings.llm_provider.
        model: Model name override. If not specified, uses settings.model_name.
        max_tokens: Max tokens override. If not specified, uses settings.max_tokens.

    Returns:
        A configured LangChain chat model instance.

    Raises:
        ValueError: If the provider is unknown or required API key is missing.

    Examples:
        # Use default provider from settings
        llm = get_chat_model()

        # Override provider and model
        llm = get_chat_model(provider="openai", model="gpt-4o")

        # Override just max_tokens
        llm = get_chat_model(max_tokens=2048)
    """
    settings = get_settings()

    # Use provided values or fall back to settings
    provider = provider or settings.llm_provider
    model = model or settings.model_name
    max_tokens = max_tokens or settings.max_tokens

    logger.info(f"Creating LLM: provider={provider}, model={model}, max_tokens={max_tokens}")

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            logger.error("ANTHROPIC_API_KEY is missing")
            raise ValueError(
                "ANTHROPIC_API_KEY is required when using anthropic provider"
            )

        from langchain_anthropic import ChatAnthropic

        logger.debug("Initializing ChatAnthropic")
        return ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            max_tokens=max_tokens,
        )

    elif provider == "openai":
        if not settings.openai_api_key:
            logger.error("OPENAI_API_KEY is missing")
            raise ValueError("OPENAI_API_KEY is required when using openai provider")

        from langchain_openai import ChatOpenAI

        logger.debug("Initializing ChatOpenAI")
        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
            max_tokens=max_tokens,
        )

    elif provider == "google":
        if not settings.google_api_key:
            logger.error("GOOGLE_API_KEY is missing")
            raise ValueError("GOOGLE_API_KEY is required when using google provider")

        from langchain_google_genai import ChatGoogleGenerativeAI

        logger.debug("Initializing ChatGoogleGenerativeAI")
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.google_api_key,
            max_output_tokens=max_tokens,
        )

    else:
        logger.error(f"Unknown LLM provider: {provider}")
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Supported providers: anthropic, openai, google"
        )
