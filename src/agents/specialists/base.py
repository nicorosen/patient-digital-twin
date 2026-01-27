"""
Base Specialist Agent.

Provides the common pattern for all specialist agents:
- Structured response models (Recommendation, SpecialistResponse)
- BaseSpecialist class with shared consultation logic
- Each subclass only provides specialty name + system prompt
"""

from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.llm import get_chat_model
from src.logging_config import get_logger
from src.schemas import DeidentifiedContext

logger = get_logger("agents.specialists.base")


class Recommendation(BaseModel):
    """A clinical recommendation from the specialist."""

    action: str = Field(description="The recommended action")
    priority: str = Field(description="Priority level: urgent, routine, or optional")
    rationale: str = Field(description="Clinical reasoning for the recommendation")


class SpecialistResponse(BaseModel):
    """Structured response from a specialist."""

    assessment: str = Field(description="Clinical reasoning and assessment")
    recommendations: List[Recommendation] = Field(
        description="List of recommended actions"
    )
    red_flags: List[str] = Field(
        default_factory=list,
        description="Warning signs that require immediate attention",
    )
    guidelines_referenced: List[str] = Field(
        default_factory=list,
        description="Clinical guidelines cited (e.g., 'ADA 2024', 'ACC/AHA 2023')",
    )
    confidence: str = Field(
        default="medium",
        description="Confidence level: high, medium, or low",
    )
    limitations: str = Field(
        default="",
        description="Limitations of this assessment",
    )


class BaseSpecialist:
    """Base class for all specialist agents."""

    specialty_name: str = "General"
    system_prompt: str = ""

    def __init__(self):
        """Initialize the specialist agent."""
        logger.info(f"Initializing {self.__class__.__name__}")
        self.llm = get_chat_model()
        self.structured_llm = self.llm.with_structured_output(SpecialistResponse)

    def _format_context(self, context: DeidentifiedContext) -> str:
        """Format the de-identified context for the specialist."""
        lines = [
            "## Patient Context (De-identified)",
            f"- Age: {context.age} years old",
            f"- Gender: {context.gender.capitalize()}",
            "",
            "### Active Conditions",
        ]

        if context.conditions:
            for condition in context.conditions:
                lines.append(f"- {condition}")
        else:
            lines.append("- None reported")

        lines.append("")
        lines.append("### Current Medications")

        if context.medications:
            for medication in context.medications:
                lines.append(f"- {medication}")
        else:
            lines.append("- None reported")

        lines.append("")
        lines.append("### Known Allergies")

        if context.allergies:
            for allergy in context.allergies:
                lines.append(f"- {allergy}")
        else:
            lines.append("- No known allergies")

        return "\n".join(lines)

    def consult(
        self,
        context: DeidentifiedContext,
        clinical_question: str,
    ) -> SpecialistResponse:
        """Consult the specialist with a clinical question."""
        logger.info(
            f"{self.specialty_name} consultation: age={context.age}, gender={context.gender}, "
            f"conditions={len(context.conditions)}, medications={len(context.medications)}"
        )

        formatted_context = self._format_context(context)
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=f"{formatted_context}\n\n## Clinical Question\n\n{clinical_question}"
            ),
        ]

        response = self.structured_llm.invoke(messages)
        logger.info(
            f"{self.specialty_name} consultation completed: confidence={response.confidence}, "
            f"recommendations={len(response.recommendations)}, red_flags={len(response.red_flags)}"
        )
        return response

    async def aconsult(
        self,
        context: DeidentifiedContext,
        clinical_question: str,
    ) -> SpecialistResponse:
        """Async version of consult."""
        logger.info(
            f"{self.specialty_name} async consultation: age={context.age}, gender={context.gender}, "
            f"conditions={len(context.conditions)}, medications={len(context.medications)}"
        )

        formatted_context = self._format_context(context)
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=f"{formatted_context}\n\n## Clinical Question\n\n{clinical_question}"
            ),
        ]

        response = await self.structured_llm.ainvoke(messages)
        logger.info(
            f"{self.specialty_name} async consultation completed: confidence={response.confidence}, "
            f"recommendations={len(response.recommendations)}, red_flags={len(response.red_flags)}"
        )
        return response
