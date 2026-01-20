"""
Medical Assistant Agent.

The patient-facing agent that:
- Answers questions about patient health data
- Gathers new health information through conversation
- Consults specialists when needed (Phase 3)
- Translates clinical information to plain language
"""

from typing import List, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from src.agents.tools import ALL_TOOLS
from src.llm import get_chat_model

SYSTEM_PROMPT = """You are a Medical Assistant helping a patient manage their health information.
You have access to the patient's health profile and can help them understand their conditions,
medications, and allergies.

## Your Capabilities

1. **Answer Questions**: Use the search and profile tools to answer questions about their health.
2. **Gather Information**: When a patient mentions new health information (conditions, medications,
   allergies), extract the details and confirm with them before adding to their record.
3. **Explain Clearly**: Always explain medical terms in plain language at a 6th grade reading level.
4. **Consult Specialists**: When a patient has clinical questions about symptoms, medication
   interactions, or health concerns, you can consult with a Primary Care specialist on their behalf.
   The specialist only receives de-identified information (no name, birthdate, etc.).

## Guidelines

- Be empathetic and supportive, but professional
- Always confirm details before adding new information to the patient's record
- For clinical questions (symptoms, medication concerns, when to seek care), use the
  consult_primary_care tool to get specialist guidance
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

    def __init__(self, patient_id: UUID):
        """
        Initialize the Medical Assistant for a specific patient.

        Args:
            patient_id: UUID of the patient this assistant is helping.
        """
        self.patient_id = patient_id

        # Initialize LLM with tools using the provider factory
        self.llm = get_chat_model()

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(ALL_TOOLS)

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
            SystemMessage(content=SYSTEM_PROMPT + "\n\n" + EXTRACTION_PROMPT),
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

        # Find and execute the tool
        for tool in ALL_TOOLS:
            if tool.name == tool_name:
                # Inject patient_id if not provided
                if "patient_id" in tool.args_schema.model_fields:
                    if "patient_id" not in tool_args:
                        tool_args["patient_id"] = str(self.patient_id)
                return tool.invoke(tool_args)

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
            The assistant's response.
        """
        messages = self._build_messages(message, conversation_history)

        # Get initial response
        response = self.llm_with_tools.invoke(messages)

        # Handle tool calls if present
        max_iterations = 5
        iteration = 0

        while response.tool_calls and iteration < max_iterations:
            iteration += 1

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

        # Extract text content from response
        if isinstance(response.content, str):
            return response.content
        elif isinstance(response.content, list):
            # Handle list of content blocks
            text_parts = []
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            return "\n".join(text_parts)
        else:
            return str(response.content)

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
        messages = self._build_messages(message, conversation_history)

        # Get initial response
        response = await self.llm_with_tools.ainvoke(messages)

        # Handle tool calls if present
        max_iterations = 5
        iteration = 0

        while response.tool_calls and iteration < max_iterations:
            iteration += 1

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

        # Extract text content from response
        if isinstance(response.content, str):
            return response.content
        elif isinstance(response.content, list):
            text_parts = []
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            return "\n".join(text_parts)
        else:
            return str(response.content)
