"""
LLM Factory for multi-provider support.

Creates LLM instances based on the configured provider, enabling
seamless switching between Anthropic, OpenAI, and Google models.
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel

from src.config import SUPPORTED_MODELS, get_settings
from src.logging_config import get_logger

logger = get_logger("llm.factory")


def get_chat_model(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    streaming: bool = False,
) -> BaseChatModel:
    """
    Factory function to create an LLM instance based on provider.

    Args:
        provider: LLM provider override (anthropic, openai, google).
                  If not specified, uses settings.llm_provider.
        model: Model name override. If not specified, uses settings.model_name.
        max_tokens: Max tokens override. If not specified, uses settings.max_tokens.
        streaming: Whether to enable streaming responses. Default False.

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

    # Validate model against supported high-reasoning models
    if provider in SUPPORTED_MODELS and model not in SUPPORTED_MODELS[provider]:
        supported = ", ".join(SUPPORTED_MODELS[provider])
        logger.warning(
            f"Model '{model}' is not in the supported high-reasoning models for "
            f"'{provider}'. Supported: {supported}"
        )

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
            streaming=streaming,
            model_kwargs={"extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"}},
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
            streaming=streaming,
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
            streaming=streaming,
        )

    else:
        logger.error(f"Unknown LLM provider: {provider}")
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Supported providers: anthropic, openai, google"
        )
