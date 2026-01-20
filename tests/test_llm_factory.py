"""
Unit tests for LLM factory.

Tests:
- Provider selection (anthropic, openai, google)
- Missing API key error handling
- Configuration overrides
"""

from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# LLM FACTORY TESTS
# =============================================================================


class TestGetChatModel:
    """Tests for get_chat_model factory function."""

    @patch("src.llm.factory.get_settings")
    @patch("src.llm.factory.ChatAnthropic", create=True)
    def test_anthropic_provider(self, mock_chat_anthropic, mock_settings):
        """Test creating Anthropic chat model."""
        mock_settings.return_value.llm_provider = "anthropic"
        mock_settings.return_value.model_name = "claude-sonnet-4-20250514"
        mock_settings.return_value.max_tokens = 4096
        mock_settings.return_value.anthropic_api_key = "test-anthropic-key"

        mock_llm = MagicMock()
        mock_chat_anthropic.return_value = mock_llm

        # Patch the import within the function
        with patch.dict("sys.modules", {"langchain_anthropic": MagicMock(ChatAnthropic=mock_chat_anthropic)}):
            from src.llm.factory import get_chat_model
            result = get_chat_model()

        mock_chat_anthropic.assert_called_once_with(
            model="claude-sonnet-4-20250514",
            api_key="test-anthropic-key",
            max_tokens=4096,
        )
        assert result == mock_llm

    @patch("src.llm.factory.get_settings")
    def test_anthropic_missing_api_key(self, mock_settings):
        """Test error when Anthropic API key is missing."""
        mock_settings.return_value.llm_provider = "anthropic"
        mock_settings.return_value.model_name = "claude-sonnet-4-20250514"
        mock_settings.return_value.max_tokens = 4096
        mock_settings.return_value.anthropic_api_key = None

        from src.llm.factory import get_chat_model

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
            get_chat_model()

    @patch("src.llm.factory.get_settings")
    @patch("src.llm.factory.ChatOpenAI", create=True)
    def test_openai_provider(self, mock_chat_openai, mock_settings):
        """Test creating OpenAI chat model."""
        mock_settings.return_value.llm_provider = "openai"
        mock_settings.return_value.model_name = "gpt-4o"
        mock_settings.return_value.max_tokens = 4096
        mock_settings.return_value.openai_api_key = "test-openai-key"

        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm

        with patch.dict("sys.modules", {"langchain_openai": MagicMock(ChatOpenAI=mock_chat_openai)}):
            from src.llm.factory import get_chat_model
            result = get_chat_model()

        mock_chat_openai.assert_called_once_with(
            model="gpt-4o",
            api_key="test-openai-key",
            max_tokens=4096,
        )

    @patch("src.llm.factory.get_settings")
    def test_openai_missing_api_key(self, mock_settings):
        """Test error when OpenAI API key is missing."""
        mock_settings.return_value.llm_provider = "openai"
        mock_settings.return_value.model_name = "gpt-4o"
        mock_settings.return_value.max_tokens = 4096
        mock_settings.return_value.openai_api_key = None

        from src.llm.factory import get_chat_model

        with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
            get_chat_model()

    @patch("src.llm.factory.get_settings")
    @patch("src.llm.factory.ChatGoogleGenerativeAI", create=True)
    def test_google_provider(self, mock_chat_google, mock_settings):
        """Test creating Google chat model."""
        mock_settings.return_value.llm_provider = "google"
        mock_settings.return_value.model_name = "gemini-2.5-pro"
        mock_settings.return_value.max_tokens = 4096
        mock_settings.return_value.google_api_key = "test-google-key"

        mock_llm = MagicMock()
        mock_chat_google.return_value = mock_llm

        with patch.dict("sys.modules", {"langchain_google_genai": MagicMock(ChatGoogleGenerativeAI=mock_chat_google)}):
            from src.llm.factory import get_chat_model
            result = get_chat_model()

        mock_chat_google.assert_called_once_with(
            model="gemini-2.5-pro",
            google_api_key="test-google-key",
            max_output_tokens=4096,
        )

    @patch("src.llm.factory.get_settings")
    def test_google_missing_api_key(self, mock_settings):
        """Test error when Google API key is missing."""
        mock_settings.return_value.llm_provider = "google"
        mock_settings.return_value.model_name = "gemini-2.5-pro"
        mock_settings.return_value.max_tokens = 4096
        mock_settings.return_value.google_api_key = None

        from src.llm.factory import get_chat_model

        with pytest.raises(ValueError, match="GOOGLE_API_KEY is required"):
            get_chat_model()

    @patch("src.llm.factory.get_settings")
    def test_unknown_provider(self, mock_settings):
        """Test error for unknown provider."""
        mock_settings.return_value.llm_provider = "unknown_provider"
        mock_settings.return_value.model_name = "some-model"
        mock_settings.return_value.max_tokens = 4096

        from src.llm.factory import get_chat_model

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_chat_model()

    @patch("src.llm.factory.get_settings")
    @patch("src.llm.factory.ChatAnthropic", create=True)
    def test_provider_override(self, mock_chat_anthropic, mock_settings):
        """Test overriding provider via parameter."""
        # Settings say google, but we override to anthropic
        mock_settings.return_value.llm_provider = "google"
        mock_settings.return_value.model_name = "gemini-2.5-pro"
        mock_settings.return_value.max_tokens = 4096
        mock_settings.return_value.anthropic_api_key = "test-key"

        mock_llm = MagicMock()
        mock_chat_anthropic.return_value = mock_llm

        with patch.dict("sys.modules", {"langchain_anthropic": MagicMock(ChatAnthropic=mock_chat_anthropic)}):
            from src.llm.factory import get_chat_model
            result = get_chat_model(provider="anthropic")

        # Should use anthropic despite settings saying google
        mock_chat_anthropic.assert_called_once()

    @patch("src.llm.factory.get_settings")
    @patch("src.llm.factory.ChatAnthropic", create=True)
    def test_model_override(self, mock_chat_anthropic, mock_settings):
        """Test overriding model via parameter."""
        mock_settings.return_value.llm_provider = "anthropic"
        mock_settings.return_value.model_name = "claude-sonnet-4-20250514"
        mock_settings.return_value.max_tokens = 4096
        mock_settings.return_value.anthropic_api_key = "test-key"

        mock_llm = MagicMock()
        mock_chat_anthropic.return_value = mock_llm

        with patch.dict("sys.modules", {"langchain_anthropic": MagicMock(ChatAnthropic=mock_chat_anthropic)}):
            from src.llm.factory import get_chat_model
            result = get_chat_model(model="claude-opus-4-20250514")

        call_kwargs = mock_chat_anthropic.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-20250514"

    @patch("src.llm.factory.get_settings")
    @patch("src.llm.factory.ChatAnthropic", create=True)
    def test_max_tokens_override(self, mock_chat_anthropic, mock_settings):
        """Test overriding max_tokens via parameter."""
        mock_settings.return_value.llm_provider = "anthropic"
        mock_settings.return_value.model_name = "claude-sonnet-4-20250514"
        mock_settings.return_value.max_tokens = 4096
        mock_settings.return_value.anthropic_api_key = "test-key"

        mock_llm = MagicMock()
        mock_chat_anthropic.return_value = mock_llm

        with patch.dict("sys.modules", {"langchain_anthropic": MagicMock(ChatAnthropic=mock_chat_anthropic)}):
            from src.llm.factory import get_chat_model
            result = get_chat_model(max_tokens=2048)

        call_kwargs = mock_chat_anthropic.call_args[1]
        assert call_kwargs["max_tokens"] == 2048

    @patch("src.llm.factory.get_settings")
    @patch("src.llm.factory.ChatAnthropic", create=True)
    def test_all_overrides(self, mock_chat_anthropic, mock_settings):
        """Test overriding all parameters."""
        mock_settings.return_value.llm_provider = "google"
        mock_settings.return_value.model_name = "gemini-2.5-pro"
        mock_settings.return_value.max_tokens = 4096
        mock_settings.return_value.anthropic_api_key = "test-key"

        mock_llm = MagicMock()
        mock_chat_anthropic.return_value = mock_llm

        with patch.dict("sys.modules", {"langchain_anthropic": MagicMock(ChatAnthropic=mock_chat_anthropic)}):
            from src.llm.factory import get_chat_model
            result = get_chat_model(
                provider="anthropic",
                model="claude-opus-4-20250514",
                max_tokens=8192,
            )

        mock_chat_anthropic.assert_called_once_with(
            model="claude-opus-4-20250514",
            api_key="test-key",
            max_tokens=8192,
        )
