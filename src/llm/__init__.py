"""
LLM Provider abstraction layer.

Provides a factory function to create LLM instances based on configuration,
enabling switching between providers (Anthropic, OpenAI, Google) without code changes.
"""

from src.llm.factory import get_chat_model

__all__ = ["get_chat_model"]
