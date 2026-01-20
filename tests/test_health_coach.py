"""
Unit tests for Health Coach agent.

Tests:
- Health Coach initializes with read-only tools only
- Health Coach does not have access to data modification tools
- Health Coach does not have access to consultation tools
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


# =============================================================================
# HEALTH COACH TOOL BINDING TESTS
# =============================================================================


class TestHealthCoachToolBinding:
    """Tests for Health Coach tool binding."""

    @patch("src.agents.health_coach.get_chat_model")
    def test_initializes_with_read_only_tools(self, mock_get_chat_model):
        """Test that Health Coach initializes with read-only tools only."""
        from src.agents.health_coach import HealthCoach
        from src.agents.tools import HEALTH_COACH_TOOLS

        mock_llm = MagicMock()
        mock_get_chat_model.return_value = mock_llm

        patient_id = uuid4()
        coach = HealthCoach(patient_id)

        # Verify bind_tools was called with HEALTH_COACH_TOOLS
        mock_llm.bind_tools.assert_called_once_with(HEALTH_COACH_TOOLS)
        assert coach.patient_id == patient_id

    def test_health_coach_tools_are_read_only(self):
        """Test that HEALTH_COACH_TOOLS contains only read-only tools."""
        from src.agents.tools import HEALTH_COACH_TOOLS

        tool_names = [tool.name for tool in HEALTH_COACH_TOOLS]

        # Should have read-only tools
        assert "get_patient_profile" in tool_names
        assert "search_patient_data" in tool_names

        # Should NOT have write tools
        assert "add_condition" not in tool_names
        assert "add_medication" not in tool_names
        assert "add_allergy" not in tool_names

        # Should NOT have consultation tools
        assert "consult_primary_care" not in tool_names

    def test_health_coach_tools_count(self):
        """Test that HEALTH_COACH_TOOLS has exactly 2 tools."""
        from src.agents.tools import HEALTH_COACH_TOOLS

        assert len(HEALTH_COACH_TOOLS) == 2


# =============================================================================
# HEALTH COACH VS MEDICAL ASSISTANT TOOLS TESTS
# =============================================================================


class TestAgentToolDifferences:
    """Tests comparing Health Coach and Medical Assistant tools."""

    def test_medical_assistant_has_more_tools(self):
        """Test that Medical Assistant has more tools than Health Coach."""
        from src.agents.tools import ALL_TOOLS, HEALTH_COACH_TOOLS

        assert len(ALL_TOOLS) > len(HEALTH_COACH_TOOLS)

    def test_health_coach_tools_subset_of_all_tools(self):
        """Test that Health Coach tools are a subset of all tools."""
        from src.agents.tools import ALL_TOOLS, HEALTH_COACH_TOOLS

        all_tool_names = {tool.name for tool in ALL_TOOLS}
        health_coach_tool_names = {tool.name for tool in HEALTH_COACH_TOOLS}

        # All health coach tools should be in ALL_TOOLS
        assert health_coach_tool_names.issubset(all_tool_names)

    def test_medical_assistant_has_write_tools(self):
        """Test that Medical Assistant (ALL_TOOLS) has write tools."""
        from src.agents.tools import ALL_TOOLS

        tool_names = [tool.name for tool in ALL_TOOLS]

        # Medical Assistant should have write tools
        assert "add_condition" in tool_names
        assert "add_medication" in tool_names
        assert "add_allergy" in tool_names

    def test_medical_assistant_has_consultation_tools(self):
        """Test that Medical Assistant (ALL_TOOLS) has consultation tools."""
        from src.agents.tools import ALL_TOOLS

        tool_names = [tool.name for tool in ALL_TOOLS]

        # Medical Assistant should have consultation tools
        assert "consult_primary_care" in tool_names


# =============================================================================
# HEALTH COACH SYSTEM PROMPT TESTS
# =============================================================================


class TestHealthCoachSystemPrompt:
    """Tests for Health Coach system prompt content."""

    def test_system_prompt_exists(self):
        """Test that Health Coach has a system prompt."""
        from src.agents.health_coach import SYSTEM_PROMPT

        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_mentions_health_coach(self):
        """Test that system prompt identifies as Health Coach."""
        from src.agents.health_coach import SYSTEM_PROMPT

        assert "Health Coach" in SYSTEM_PROMPT

    def test_system_prompt_emphasizes_education(self):
        """Test that system prompt emphasizes education and understanding."""
        from src.agents.health_coach import SYSTEM_PROMPT

        # Should mention education-related concepts
        assert "education" in SYSTEM_PROMPT.lower() or "understand" in SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_no_clinical_advice(self):
        """Test that system prompt says not to give clinical advice."""
        from src.agents.health_coach import SYSTEM_PROMPT

        # Should mention not giving clinical advice
        assert "clinical" in SYSTEM_PROMPT.lower()
        assert "NO" in SYSTEM_PROMPT or "don't" in SYSTEM_PROMPT.lower() or "not" in SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_lifestyle(self):
        """Test that system prompt mentions lifestyle guidance."""
        from src.agents.health_coach import SYSTEM_PROMPT

        assert "lifestyle" in SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_motivation(self):
        """Test that system prompt mentions motivation."""
        from src.agents.health_coach import SYSTEM_PROMPT

        assert "motivat" in SYSTEM_PROMPT.lower()  # matches motivation, motivating, etc.


# =============================================================================
# HEALTH COACH MESSAGE BUILDING TESTS
# =============================================================================


class TestHealthCoachMessageBuilding:
    """Tests for Health Coach message building."""

    @patch("src.agents.health_coach.get_chat_model")
    def test_build_messages_includes_system_prompt(self, mock_get_chat_model):
        """Test that _build_messages includes the system prompt."""
        from src.agents.health_coach import HealthCoach, SYSTEM_PROMPT

        mock_llm = MagicMock()
        mock_get_chat_model.return_value = mock_llm

        patient_id = uuid4()
        coach = HealthCoach(patient_id)

        messages = coach._build_messages("Hello", None)

        # First message should be system prompt
        assert messages[0].content == SYSTEM_PROMPT

    @patch("src.agents.health_coach.get_chat_model")
    def test_build_messages_includes_patient_id(self, mock_get_chat_model):
        """Test that _build_messages includes patient ID."""
        from src.agents.health_coach import HealthCoach

        mock_llm = MagicMock()
        mock_get_chat_model.return_value = mock_llm

        patient_id = uuid4()
        coach = HealthCoach(patient_id)

        messages = coach._build_messages("Hello", None)

        # Second message should contain patient ID
        assert str(patient_id) in messages[1].content

    @patch("src.agents.health_coach.get_chat_model")
    def test_build_messages_includes_user_message(self, mock_get_chat_model):
        """Test that _build_messages includes the user message."""
        from src.agents.health_coach import HealthCoach

        mock_llm = MagicMock()
        mock_get_chat_model.return_value = mock_llm

        patient_id = uuid4()
        coach = HealthCoach(patient_id)

        user_message = "What is diabetes?"
        messages = coach._build_messages(user_message, None)

        # Last message should be the user message
        assert messages[-1].content == user_message

    @patch("src.agents.health_coach.get_chat_model")
    def test_build_messages_includes_conversation_history(self, mock_get_chat_model):
        """Test that _build_messages includes conversation history."""
        from src.agents.health_coach import HealthCoach

        mock_llm = MagicMock()
        mock_get_chat_model.return_value = mock_llm

        patient_id = uuid4()
        coach = HealthCoach(patient_id)

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        messages = coach._build_messages("What is diabetes?", history)

        # Should have system prompts + history + current message
        # 2 system messages + 2 history + 1 current = 5
        assert len(messages) == 5


# =============================================================================
# HEALTH COACH EXPORTS TESTS
# =============================================================================


class TestHealthCoachExports:
    """Tests for Health Coach exports."""

    def test_health_coach_exported_from_agents(self):
        """Test that HealthCoach is exported from src.agents."""
        from src.agents import HealthCoach

        assert HealthCoach is not None

    def test_health_coach_tools_exported_from_agents(self):
        """Test that HEALTH_COACH_TOOLS is exported from src.agents."""
        from src.agents import HEALTH_COACH_TOOLS

        assert HEALTH_COACH_TOOLS is not None
        assert len(HEALTH_COACH_TOOLS) == 2
