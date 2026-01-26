"""
Health Coach Agent.

The consumer-facing agent that:
- Provides health education in plain language
- Offers lifestyle and wellness guidance
- Helps patients understand their conditions and medications
- Motivates and supports healthy behaviors

Unlike the Medical Assistant, the Health Coach:
- Does NOT add or modify patient data
- Does NOT consult specialists for clinical questions
- Redirects clinical concerns to Medical Assistant
"""

from typing import List, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from src.agents.tools import HEALTH_COACH_TOOLS
from src.llm import get_chat_model
from src.logging_config import get_logger, Colors, LLMColors

logger = get_logger("agents.health_coach")


SYSTEM_PROMPT = """You are a Health Coach - a friendly, supportive guide helping patients understand and manage their health.

## Your Role

You help patients:
- **Understand their conditions** in simple, everyday language
- **Learn about their medications** - what they do and why they're important
- **Make healthy lifestyle choices** - diet, exercise, sleep, stress management
- **Stay motivated** with their health journey

## Your Personality

- Warm, encouraging, and empathetic
- Positive but realistic
- Patient and understanding
- Celebrates small wins
- Uses everyday language (6th grade reading level)
- Never judgmental about health choices

## Your Capabilities

1. **Health Education**: Explain conditions and medications in simple terms
2. **Lifestyle Guidance**: Suggest evidence-based healthy habits
3. **Motivation**: Provide encouragement and practical tips
4. **Support**: Listen to concerns and validate feelings

## What You DON'T Do

- **NO clinical advice**: If a patient asks about symptoms, new health concerns, or "should I see a doctor?", kindly redirect them: "For questions about symptoms or health concerns, please use the Medical Assistant - they can consult with clinical specialists."

- **NO data changes**: If a patient wants to add conditions, medications, or allergies, redirect: "To update your health record, please switch to the Medical Assistant."

- **NO diagnosis**: Never suggest what a condition might be or diagnose

## Guidelines

- Always use simple language - avoid medical jargon
- Explain WHY something matters, not just WHAT to do
- Give practical, actionable suggestions
- Acknowledge that everyone's health journey is different
- Be supportive even when discussing challenges
- When you don't know something, say so honestly

## Current Patient

You are coaching the patient whose ID will be provided. Use their profile to personalize your guidance.

## Response Format

- Keep responses conversational and warm
- Use bullet points for tips and suggestions
- Break down complex topics into simple steps
- End with an encouraging note when appropriate
"""


def _format_messages_for_log(messages: List[BaseMessage]) -> str:
    """Format LangChain messages for readable logging with colors."""
    lines = []

    type_styles = {
        "System": (LLMColors.SYSTEM_PROMPT, "SYS"),
        "Human": (LLMColors.HUMAN_INPUT, "USR"),
        "AI": (LLMColors.AI_RESPONSE, "AI "),
        "Tool": (LLMColors.TOOL_RESULT, "TLR"),
    }

    for i, msg in enumerate(messages):
        msg_type = type(msg).__name__.replace("Message", "")
        color, label = type_styles.get(msg_type, (Colors.WHITE, msg_type[:3].upper()))

        content = msg.content
        if isinstance(content, str) and len(content) > 500:
            content = content[:500] + f"... [truncated, {len(msg.content)} chars total]"

        idx = f"{Colors.DIM}[{i}]{Colors.RESET}"
        tag = f"{color}{Colors.BOLD}{label}{Colors.RESET}"
        text = f"{color}{content}{Colors.RESET}"
        lines.append(f"  {idx} {tag} {text}")

    return "\n".join(lines)


class HealthCoach:
    """Health Coach agent for patient education and motivation."""

    def __init__(
        self,
        patient_id: UUID,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the Health Coach for a specific patient.

        Args:
            patient_id: UUID of the patient this coach is helping.
            provider: LLM provider override (anthropic, openai, google).
            model: Model name override.
        """
        logger.info(f"Initializing HealthCoach for patient_id={patient_id}, provider={provider}, model={model}")
        self.patient_id = patient_id

        # Initialize LLM with tools
        self.llm = get_chat_model(provider=provider, model=model)

        # Bind only read-only tools (no data modification, no specialist consultation)
        self.llm_with_tools = self.llm.bind_tools(HEALTH_COACH_TOOLS)
        logger.debug(f"Bound {len(HEALTH_COACH_TOOLS)} read-only tools to LLM")

    def _build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> List[BaseMessage]:
        """
        Build the message list for the LLM.

        Args:
            user_message: The current user message.
            conversation_history: Previous messages in the conversation.

        Returns:
            List of LangChain messages.
        """
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            SystemMessage(content=f"Current patient_id: {self.patient_id}"),
        ]

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        # Add current message
        messages.append(HumanMessage(content=user_message))

        return messages

    def _execute_tool_call(self, tool_call: dict) -> str:
        """
        Execute a tool call and return the result.

        Args:
            tool_call: The tool call from the LLM.

        Returns:
            Tool execution result as string.
        """
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})
        logger.debug(
            f"{LLMColors.TOOL_CALL}{Colors.BOLD}━━━ EXECUTING TOOL ━━━{Colors.RESET}\n"
            f"  {Colors.DIM}Name:{Colors.RESET} {LLMColors.TOOL_CALL}{tool_name}{Colors.RESET}\n"
            f"  {Colors.DIM}Args:{Colors.RESET} {Colors.DIM}{list(tool_args.keys())}{Colors.RESET}"
        )

        # Find and execute the tool
        for tool in HEALTH_COACH_TOOLS:
            if tool.name == tool_name:
                # Inject patient_id if not provided
                if "patient_id" in tool.args_schema.model_fields:
                    if "patient_id" not in tool_args:
                        tool_args["patient_id"] = str(self.patient_id)
                try:
                    result = tool.invoke(tool_args)
                    result_preview = str(result)[:500] + "..." if len(str(result)) > 500 else str(result)
                    logger.info(f"{LLMColors.TOOL_RESULT}Tool {tool_name} executed successfully{Colors.RESET}")
                    logger.debug(
                        f"{LLMColors.TOOL_RESULT}{Colors.BOLD}━━━ TOOL RESULT ━━━{Colors.RESET}\n"
                        f"  {Colors.DIM}Tool:{Colors.RESET} {LLMColors.TOOL_CALL}{tool_name}{Colors.RESET}\n"
                        f"  {Colors.DIM}Result:{Colors.RESET} {LLMColors.TOOL_RESULT}{result_preview}{Colors.RESET}"
                    )
                    return result
                except Exception as e:
                    logger.error(f"Tool {tool_name} failed: {e}")
                    raise

        logger.warning(f"Unknown tool requested: {tool_name}")
        return f"Error: Unknown tool '{tool_name}'"

    def chat(
        self,
        message: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> str:
        """
        Process a chat message and return a response.

        Args:
            message: The user's message.
            conversation_history: Previous messages for context.

        Returns:
            The coach's response.
        """
        logger.info(
            f"{LLMColors.HUMAN_INPUT}{Colors.BOLD}━━━ HEALTH COACH MESSAGE ━━━{Colors.RESET}\n"
            f"  {Colors.DIM}Patient:{Colors.RESET} {self.patient_id}\n"
            f"  {Colors.DIM}Message:{Colors.RESET} {LLMColors.HUMAN_INPUT}{message[:200]}{'...' if len(message) > 200 else ''}{Colors.RESET}"
        )
        logger.debug(f"Conversation history: {len(conversation_history or [])} messages")

        messages = self._build_messages(message, conversation_history)

        # Get initial response
        logger.debug(
            f"{Colors.BRIGHT_BLUE}{Colors.BOLD}━━━ LLM INVOCATION ({len(messages)} messages) ━━━{Colors.RESET}\n"
            f"{_format_messages_for_log(messages)}"
        )
        response = self.llm_with_tools.invoke(messages)

        # Handle tool calls if present
        max_iterations = 5
        iteration = 0

        while response.tool_calls and iteration < max_iterations:
            iteration += 1
            logger.info(
                f"{LLMColors.TOOL_CALL}{Colors.BOLD}━━━ TOOL LOOP (iteration {iteration}/{max_iterations}) ━━━{Colors.RESET}\n"
                f"  {Colors.DIM}Tools to execute:{Colors.RESET} {len(response.tool_calls)}"
            )

            # Execute all tool calls
            tool_results = []
            for tool_call in response.tool_calls:
                result = self._execute_tool_call(tool_call)
                tool_results.append(
                    {
                        "tool_call_id": tool_call.get("id"),
                        "output": result,
                    }
                )

            # Add tool call and results to messages
            messages.append(response)
            for i, tool_call in enumerate(response.tool_calls):
                from langchain_core.messages import ToolMessage

                messages.append(
                    ToolMessage(
                        content=tool_results[i]["output"],
                        tool_call_id=tool_call.get("id"),
                    )
                )

            # Get next response
            response = self.llm_with_tools.invoke(messages)

        if iteration >= max_iterations and response.tool_calls:
            logger.warning(f"{Colors.YELLOW}Max iterations ({max_iterations}) reached{Colors.RESET}")

        # Extract text content from response
        if isinstance(response.content, str):
            final_response = response.content
        elif isinstance(response.content, list):
            text_parts = []
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            final_response = "\n".join(text_parts)
        else:
            final_response = str(response.content)

        logger.info(
            f"{LLMColors.AI_RESPONSE}{Colors.BOLD}━━━ HEALTH COACH COMPLETED ━━━{Colors.RESET}\n"
            f"  {Colors.DIM}Response length:{Colors.RESET} {len(final_response)} chars\n"
            f"  {Colors.DIM}Tool iterations:{Colors.RESET} {iteration}"
        )
        return final_response

    async def achat(
        self,
        message: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> str:
        """
        Async version of chat.

        Args:
            message: The user's message.
            conversation_history: Previous messages for context.

        Returns:
            The coach's response.
        """
        logger.info(
            f"{LLMColors.HUMAN_INPUT}{Colors.BOLD}━━━ HEALTH COACH MESSAGE (ASYNC) ━━━{Colors.RESET}\n"
            f"  {Colors.DIM}Patient:{Colors.RESET} {self.patient_id}\n"
            f"  {Colors.DIM}Message:{Colors.RESET} {LLMColors.HUMAN_INPUT}{message[:200]}{'...' if len(message) > 200 else ''}{Colors.RESET}"
        )
        logger.debug(f"Conversation history: {len(conversation_history or [])} messages")

        messages = self._build_messages(message, conversation_history)

        # Get initial response
        response = await self.llm_with_tools.ainvoke(messages)

        # Handle tool calls if present
        max_iterations = 5
        iteration = 0

        while response.tool_calls and iteration < max_iterations:
            iteration += 1
            logger.info(
                f"{LLMColors.TOOL_CALL}{Colors.BOLD}━━━ TOOL LOOP ASYNC (iteration {iteration}/{max_iterations}) ━━━{Colors.RESET}\n"
                f"  {Colors.DIM}Tools to execute:{Colors.RESET} {len(response.tool_calls)}"
            )

            # Execute all tool calls
            tool_results = []
            for tool_call in response.tool_calls:
                result = self._execute_tool_call(tool_call)
                tool_results.append(
                    {
                        "tool_call_id": tool_call.get("id"),
                        "output": result,
                    }
                )

            # Add tool call and results to messages
            messages.append(response)
            for i, tool_call in enumerate(response.tool_calls):
                from langchain_core.messages import ToolMessage

                messages.append(
                    ToolMessage(
                        content=tool_results[i]["output"],
                        tool_call_id=tool_call.get("id"),
                    )
                )

            # Get next response
            response = await self.llm_with_tools.ainvoke(messages)

        if iteration >= max_iterations and response.tool_calls:
            logger.warning(f"{Colors.YELLOW}Max iterations ({max_iterations}) reached{Colors.RESET}")

        # Extract text content from response
        if isinstance(response.content, str):
            final_response = response.content
        elif isinstance(response.content, list):
            text_parts = []
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            final_response = "\n".join(text_parts)
        else:
            final_response = str(response.content)

        logger.info(
            f"{LLMColors.AI_RESPONSE}{Colors.BOLD}━━━ ASYNC HEALTH COACH COMPLETED ━━━{Colors.RESET}\n"
            f"  {Colors.DIM}Response length:{Colors.RESET} {len(final_response)} chars\n"
            f"  {Colors.DIM}Tool iterations:{Colors.RESET} {iteration}"
        )
        return final_response
