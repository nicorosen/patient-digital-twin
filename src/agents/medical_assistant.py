"""
Medical Assistant Agent.

The patient-facing agent that:
- Answers questions about patient health data
- Gathers new health information through conversation
- Consults specialists when needed (Phase 3)
- Translates clinical information to plain language
"""

import json
from typing import Callable, List, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from src.agents.tools import ALL_TOOLS
from src.llm import get_chat_model
from src.logging_config import get_logger, Colors, LLMColors

logger = get_logger("agents.medical_assistant")


def _format_messages_for_log(messages: List[BaseMessage]) -> str:
    """Format LangChain messages for readable logging with colors."""
    lines = []

    # Color mapping for message types
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
        # Truncate long content
        if isinstance(content, str) and len(content) > 500:
            content = content[:500] + f"... [truncated, {len(msg.content)} chars total]"

        # Format with colors
        idx = f"{Colors.DIM}[{i}]{Colors.RESET}"
        tag = f"{color}{Colors.BOLD}{label}{Colors.RESET}"
        text = f"{color}{content}{Colors.RESET}"
        lines.append(f"  {idx} {tag} {text}")

    return "\n".join(lines)


def _format_response_for_log(response) -> str:
    """Format LLM response for readable logging with colors."""
    parts = []

    # Header
    parts.append(f"{LLMColors.AI_RESPONSE}{Colors.BOLD}━━━ AI RESPONSE ━━━{Colors.RESET}")

    # Content
    if isinstance(response.content, str):
        content = response.content
        if len(content) > 1000:
            content = content[:1000] + f"... [truncated, {len(response.content)} chars total]"
        parts.append(f"  {Colors.DIM}Content:{Colors.RESET} {LLMColors.AI_RESPONSE}{content}{Colors.RESET}")
    elif isinstance(response.content, list):
        parts.append(f"  {Colors.DIM}Content blocks:{Colors.RESET} {len(response.content)}")
        for i, block in enumerate(response.content[:3]):  # Show first 3
            if isinstance(block, dict):
                parts.append(f"    {Colors.DIM}[{i}]{Colors.RESET} {block.get('type', 'unknown')}: {str(block)[:200]}")
            else:
                parts.append(f"    {Colors.DIM}[{i}]{Colors.RESET} {str(block)[:200]}")

    # Tool calls
    if hasattr(response, "tool_calls") and response.tool_calls:
        parts.append(f"\n  {LLMColors.TOOL_CALL}{Colors.BOLD}━━━ TOOL CALLS ({len(response.tool_calls)}) ━━━{Colors.RESET}")
        for tc in response.tool_calls:
            tool_name = tc.get("name")
            args_str = json.dumps(tc.get("args", {}), default=str)
            if len(args_str) > 200:
                args_str = args_str[:200] + "..."
            parts.append(f"    {LLMColors.TOOL_CALL}{Colors.BOLD}{tool_name}{Colors.RESET}: {Colors.DIM}{args_str}{Colors.RESET}")

    return "\n".join(parts)

SYSTEM_PROMPT = """You are a Medical Assistant helping a patient manage their health information.
You have access to the patient's health profile and can help them understand their conditions,
medications, and allergies.

## Your Capabilities

1. **Answer Questions**: Use the search and profile tools to answer questions about their health.
2. **Gather Information**: When a patient mentions new health information (conditions, medications,
   allergies, procedures/treatments), extract the details and confirm with them before adding to their record.
3. **Explain Clearly**: Always explain medical terms in plain language at a 6th grade reading level.
4. **Consult Specialists**: When a patient has clinical questions about symptoms, medication
   interactions, or health concerns, you can consult specialists on their behalf.
   All specialists receive only de-identified information (no name, birthdate, etc.).

   Available specialists:
   - **Primary Care**: General medicine, preventive care, chronic disease management
   - **Cardiology**: Chest pain, heart failure, arrhythmias, hypertension, cholesterol
   - **Endocrinology**: Diabetes, thyroid, hormonal disorders, metabolic syndrome
   - **Pulmonology**: Asthma, COPD, shortness of breath, chronic cough, sleep apnea
   - **Neurology**: Headaches, seizures, dizziness, numbness, memory concerns, stroke risk
   - **Gastroenterology**: Acid reflux, IBS, IBD, liver disease, digestive issues
   - **Oncology**: Cancer screening, suspicious symptoms, treatment side effects
   - **Psychiatry**: Depression, anxiety, mood changes, sleep problems, stress
   - **Orthopedics**: Joint pain, arthritis, back pain, fractures, sports injuries
   - **Nephrology**: Kidney disease, electrolyte imbalances, kidney stones
   - **Dermatology**: Rashes, eczema, psoriasis, skin lesions, drug reactions on skin

   Use `consult_medical_board` to consult multiple specialists at once when a question
   spans multiple domains.

5. **Search the Web**: When you need up-to-date medical information not available in
   the patient's records, use `search_medical_web` to look up:
   - Drug interactions, side effects, and contraindications
   - Clinical guidelines and treatment protocols
   - Medical conditions, symptoms, and latest research
   - Dosage information and medication details

   Always cite the source when sharing web search results with the patient.

## Guidelines

- Be empathetic and supportive, but professional
- Always confirm details before adding new information to the patient's record
- For clinical questions, choose the most appropriate specialist(s) based on the topic.
  Use consult_primary_care as a fallback when no specific specialty fits.
- When presenting specialist advice, translate clinical language to plain language (6th grade level)
- When extracting information, ask clarifying questions if details are unclear
- Never make up information - only report what's in the patient's health record

## Current Patient

You are assisting the patient whose ID will be provided. Always use this patient_id when calling tools.

## Response Format

- Use clear, simple language
- Break complex information into bullet points
- Highlight important warnings or allergies
- Keep responses concise but complete
"""

EXTRACTION_PROMPT = """
When a patient shares new health information, extract structured data:

1. **Conditions**: Look for diagnoses, medical conditions, health problems
   - Name of condition
   - When it started (onset)
   - Current status (active, resolved, etc.)
   - Severity if mentioned

2. **Medications**: Look for drugs, prescriptions, treatments
   - Medication name
   - Dosage (e.g., "500mg")
   - How often (e.g., "twice daily")
   - Why they take it

3. **Allergies**: Look for allergic reactions, intolerances
   - What they're allergic to
   - Type (medication, food, environmental)
   - Reaction description
   - Severity

After extraction, confirm with the patient:
"Let me confirm what I heard: [summarize]. Is this correct?"

Only add to their record after confirmation.
"""


class MedicalAssistant:
    """Medical Assistant agent for patient interaction."""

    def __init__(
        self,
        patient_id: UUID,
        user_role: str = "patient",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the Medical Assistant for a specific patient.

        Args:
            patient_id: UUID of the patient this assistant is helping.
            user_role: Role of the user ('patient' or 'doctor'). Doctors can
                      update and delete records, patients cannot.
            provider: LLM provider override (anthropic, openai, google).
            model: Model name override.
        """
        logger.info(f"Initializing MedicalAssistant for patient_id={patient_id}, role={user_role}, provider={provider}, model={model}")
        self.patient_id = patient_id
        self.user_role = user_role

        # Initialize LLM with tools using the provider factory
        self.llm = get_chat_model(provider=provider, model=model)

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(ALL_TOOLS)
        logger.debug(f"Bound {len(ALL_TOOLS)} tools to LLM")

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
        # Build role-specific permissions prompt
        if self.user_role == "doctor":
            role_prompt = """
## User Role: DOCTOR

You are assisting a doctor who has full access to this patient's records.
As a doctor, you CAN:
- View all patient data
- Add new conditions, medications, allergies, vital signs, lab results, etc.
- Update existing records (use update_* tools)
- Delete records that were added in error (use delete_* tools)

When the doctor asks to update or delete a record, you should help them do so.

When consulting specialists, propose which specialist(s) you plan to consult and
ask the doctor if they want to add or remove any before proceeding. Use
consult_medical_board to consult multiple specialists at once when requested.
"""
        else:
            role_prompt = """
## User Role: PATIENT

You are assisting the patient directly. Patients have limited permissions.
As a patient, you CAN:
- View your own health data
- Add new information (conditions, medications, allergies, symptoms)

As a patient, you CANNOT:
- Update existing records (only a doctor can do this)
- Delete records (only a doctor can do this)

If the patient asks to update or delete a record, politely explain that only
their doctor can make those changes, and suggest they discuss it at their
next appointment.

When consulting specialists, choose the appropriate specialist(s) automatically
based on the clinical question. Translate specialist responses to plain language
the patient can understand.
"""

        from datetime import date as _date
        date_context = f"\n\nToday's date is {_date.today().strftime('%B %d, %Y')}.\n"
        messages = [
            SystemMessage(content=SYSTEM_PROMPT + date_context + "\n" + EXTRACTION_PROMPT + "\n\n" + role_prompt),
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
        for tool in ALL_TOOLS:
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
        on_tool_start: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Process a chat message and return a response.

        Args:
            message: The user's message.
            conversation_history: Previous messages for context.

        Returns:
            The assistant's response.
        """
        logger.info(
            f"{LLMColors.HUMAN_INPUT}{Colors.BOLD}━━━ USER MESSAGE ━━━{Colors.RESET}\n"
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
        logger.debug(f"LLM response:\n{_format_response_for_log(response)}")

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
                tool_name = tool_call.get("name", "")
                if on_tool_start:
                    on_tool_start(tool_name)
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
            logger.debug(
                f"{Colors.BRIGHT_BLUE}{Colors.BOLD}━━━ LLM INVOCATION (post-tool, iteration {iteration}) ━━━{Colors.RESET}\n"
                f"{_format_messages_for_log(messages[-3:])}"
            )
            if on_tool_start:
                on_tool_start("__thinking__")
            response = self.llm_with_tools.invoke(messages)
            logger.debug(f"LLM response:\n{_format_response_for_log(response)}")

        if iteration >= max_iterations and response.tool_calls:
            logger.warning(f"{Colors.YELLOW}Max iterations ({max_iterations}) reached, still has pending tool calls{Colors.RESET}")

        # Extract text content from response
        if isinstance(response.content, str):
            final_response = response.content
        elif isinstance(response.content, list):
            # Handle list of content blocks
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
            f"{LLMColors.AI_RESPONSE}{Colors.BOLD}━━━ CHAT COMPLETED ━━━{Colors.RESET}\n"
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
            The assistant's response.
        """
        logger.info(
            f"{LLMColors.HUMAN_INPUT}{Colors.BOLD}━━━ USER MESSAGE (ASYNC) ━━━{Colors.RESET}\n"
            f"  {Colors.DIM}Patient:{Colors.RESET} {self.patient_id}\n"
            f"  {Colors.DIM}Message:{Colors.RESET} {LLMColors.HUMAN_INPUT}{message[:200]}{'...' if len(message) > 200 else ''}{Colors.RESET}"
        )
        logger.debug(f"Conversation history: {len(conversation_history or [])} messages")

        messages = self._build_messages(message, conversation_history)

        # Get initial response
        logger.debug(
            f"{Colors.BRIGHT_BLUE}{Colors.BOLD}━━━ LLM INVOCATION ASYNC ({len(messages)} messages) ━━━{Colors.RESET}\n"
            f"{_format_messages_for_log(messages)}"
        )
        response = await self.llm_with_tools.ainvoke(messages)
        logger.debug(f"LLM response:\n{_format_response_for_log(response)}")

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
            logger.debug(
                f"{Colors.BRIGHT_BLUE}{Colors.BOLD}━━━ LLM INVOCATION ASYNC (post-tool, iteration {iteration}) ━━━{Colors.RESET}\n"
                f"{_format_messages_for_log(messages[-3:])}"
            )
            response = await self.llm_with_tools.ainvoke(messages)
            logger.debug(f"LLM response:\n{_format_response_for_log(response)}")

        if iteration >= max_iterations and response.tool_calls:
            logger.warning(f"{Colors.YELLOW}Max iterations ({max_iterations}) reached, still has pending tool calls{Colors.RESET}")

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
            f"{LLMColors.AI_RESPONSE}{Colors.BOLD}━━━ ASYNC CHAT COMPLETED ━━━{Colors.RESET}\n"
            f"  {Colors.DIM}Response length:{Colors.RESET} {len(final_response)} chars\n"
            f"  {Colors.DIM}Tool iterations:{Colors.RESET} {iteration}"
        )
        return final_response
