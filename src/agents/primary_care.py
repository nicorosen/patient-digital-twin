"""
Primary Care Specialist Agent.

A stateless specialist agent that:
- Receives de-identified patient context
- Analyzes clinical questions
- Returns structured clinical assessments
- References clinical guidelines when applicable
"""

from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.llm import get_chat_model
from src.logging_config import get_logger
from src.schemas import DeidentifiedContext

logger = get_logger("agents.primary_care")


class Recommendation(BaseModel):
    """A clinical recommendation from the specialist."""

    action: str = Field(description="The recommended action")
    priority: str = Field(description="Priority level: urgent, routine, or optional")
    rationale: str = Field(description="Clinical reasoning for the recommendation")


class SpecialistResponse(BaseModel):
    """Structured response from the Primary Care specialist."""

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


SPECIALIST_SYSTEM_PROMPT = """You are a Primary Care Physician AI consultant providing clinical decision support.
You receive de-identified patient context and clinical questions from Medical Assistant agents.

## Your Role

1. **Analyze the clinical picture**: Consider the patient's age, gender, conditions, medications, and allergies
2. **Provide evidence-based assessment**: Base your analysis on clinical guidelines and best practices
3. **Recommend next steps with rationale**: Explain why you're making each recommendation
4. **Flag urgent concerns (red flags)**: Highlight warning signs that need immediate attention
5. **Cite clinical guidelines**: Reference relevant guidelines (e.g., ADA for diabetes, ACC/AHA for cardiac)

## Important Limitations

- You are decision SUPPORT, not decision MAKER
- Always recommend professional consultation for definitive care
- Note uncertainties and limitations in your assessment
- Never claim to diagnose or prescribe - only provide guidance
- The data you receive is de-identified - you don't know the patient's name or other identifying information

## Response Format

Provide your response as a structured assessment including:
- Clinical assessment with reasoning
- Specific recommendations with priorities (urgent/routine/optional)
- Red flags to watch for
- Referenced guidelines
- Confidence level and limitations
"""


class PrimaryCareSpecialist:
    """Primary Care Specialist agent for clinical consultation."""

    def __init__(self):
        """Initialize the specialist agent."""
        logger.info("Initializing PrimaryCareSpecialist")
        # Initialize LLM using the provider factory
        self.llm = get_chat_model()

        # Bind structured output
        self.structured_llm = self.llm.with_structured_output(SpecialistResponse)
        logger.debug("Bound structured output schema to LLM")

    def _format_context(self, context: DeidentifiedContext) -> str:
        """
        Format the de-identified context for the specialist.

        Args:
            context: De-identified patient context.

        Returns:
            Formatted context string.
        """
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
        """
        Consult the specialist with a clinical question.

        Args:
            context: De-identified patient context.
            clinical_question: The clinical question to address.

        Returns:
            Structured specialist response.
        """
        logger.info(f"Consultation request: age={context.age}, gender={context.gender}, "
                    f"conditions={len(context.conditions)}, medications={len(context.medications)}, "
                    f"allergies={len(context.allergies)}")
        logger.debug(f"Clinical question length: {len(clinical_question)}")

        formatted_context = self._format_context(context)

        messages = [
            SystemMessage(content=SPECIALIST_SYSTEM_PROMPT),
            HumanMessage(
                content=f"{formatted_context}\n\n## Clinical Question\n\n{clinical_question}"
            ),
        ]

        logger.debug("Invoking LLM for structured specialist response")
        response = self.structured_llm.invoke(messages)
        logger.info(f"Consultation completed: confidence={response.confidence}, "
                    f"recommendations={len(response.recommendations)}, red_flags={len(response.red_flags)}")
        return response

    async def aconsult(
        self,
        context: DeidentifiedContext,
        clinical_question: str,
    ) -> SpecialistResponse:
        """
        Async version of consult.

        Args:
            context: De-identified patient context.
            clinical_question: The clinical question to address.

        Returns:
            Structured specialist response.
        """
        logger.info(f"Async consultation request: age={context.age}, gender={context.gender}, "
                    f"conditions={len(context.conditions)}, medications={len(context.medications)}, "
                    f"allergies={len(context.allergies)}")
        logger.debug(f"Clinical question length: {len(clinical_question)}")

        formatted_context = self._format_context(context)

        messages = [
            SystemMessage(content=SPECIALIST_SYSTEM_PROMPT),
            HumanMessage(
                content=f"{formatted_context}\n\n## Clinical Question\n\n{clinical_question}"
            ),
        ]

        logger.debug("Invoking LLM (async) for structured specialist response")
        response = await self.structured_llm.ainvoke(messages)
        logger.info(f"Async consultation completed: confidence={response.confidence}, "
                    f"recommendations={len(response.recommendations)}, red_flags={len(response.red_flags)}")
        return response


# Singleton instance
_specialist: Optional[PrimaryCareSpecialist] = None


def get_primary_care_specialist() -> PrimaryCareSpecialist:
    """Get the singleton specialist instance."""
    global _specialist
    if _specialist is None:
        logger.debug("Creating new PrimaryCareSpecialist singleton instance")
        _specialist = PrimaryCareSpecialist()
    return _specialist
