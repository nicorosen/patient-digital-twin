"""
Translation layer for clinical to patient-friendly language.

Translates specialist clinical responses into plain language
that patients can understand (6th grade reading level).
"""

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.primary_care import SpecialistResponse
from src.llm import get_chat_model
from src.logging_config import get_logger

logger = get_logger("agents.translation")

TRANSLATION_PROMPT = """You are a medical translator helping patients understand clinical information.

Your job is to translate specialist medical responses into plain, easy-to-understand language.

## Translation Rules

1. **Reading Level**: Use 6th grade reading level. Avoid medical jargon.

2. **Medical Terms**: Replace with simple words:
   - "Hypertension" → "high blood pressure"
   - "Myocardial infarction" → "heart attack"
   - "Contraindicated" → "should not be used with"
   - "Hyperlipidemia" → "high cholesterol"
   - "Orthostatic hypotension" → "dizziness when standing up"
   - "Bronchospasm" → "tightening of the airways"
   - "NSAID" → "pain relievers like ibuprofen"

3. **Structure**:
   - Lead with the most important point
   - Use bullet points for lists
   - Break complex recommendations into clear steps
   - Use bold for urgent items

4. **Context**: Explain WHY, not just WHAT
   - "Take aspirin daily" → "Taking aspirin daily helps prevent blood clots, which is important given your heart history"

5. **Limitations**: Always note this is for information only:
   - Include that this is not a substitute for professional medical advice
   - Recommend discussing with their doctor
   - Don't soften urgent warnings

6. **Tone**:
   - Empathetic but clear
   - Not alarmist, but honest about concerns
   - Supportive and actionable

## Response Format

Translate the specialist response into a patient-friendly message. Structure it as:

1. **Main Point** - What the patient most needs to know
2. **Details** - Key information explained simply
3. **Action Steps** - What they should do next
4. **Important Warnings** - Any red flags or urgent items (if applicable)
5. **Disclaimer** - Brief note about professional medical advice
"""


def translate_specialist_response(response: SpecialistResponse) -> str:
    """
    Translate a specialist response to patient-friendly language.

    Args:
        response: The structured specialist response.

    Returns:
        Patient-friendly translation of the response.
    """
    logger.info(f"Translating specialist response: recommendations={len(response.recommendations)}, "
                f"red_flags={len(response.red_flags)}, confidence={response.confidence}")

    llm = get_chat_model(max_tokens=2048)

    # Build the content to translate
    content_parts = [
        "## Specialist Response to Translate",
        "",
        f"**Assessment:** {response.assessment}",
        "",
        "**Recommendations:**",
    ]

    for rec in response.recommendations:
        content_parts.append(
            f"- [{rec.priority.upper()}] {rec.action} (Rationale: {rec.rationale})"
        )

    if response.red_flags:
        content_parts.append("")
        content_parts.append("**Red Flags:**")
        for flag in response.red_flags:
            content_parts.append(f"- {flag}")

    if response.guidelines_referenced:
        content_parts.append("")
        content_parts.append(f"**Guidelines:** {', '.join(response.guidelines_referenced)}")

    if response.limitations:
        content_parts.append("")
        content_parts.append(f"**Limitations:** {response.limitations}")

    content = "\n".join(content_parts)
    logger.debug(f"Content to translate: {len(content)} chars")

    messages = [
        SystemMessage(content=TRANSLATION_PROMPT),
        HumanMessage(content=content),
    ]

    logger.debug("Invoking LLM for translation")
    result = llm.invoke(messages)

    if isinstance(result.content, str):
        translated = result.content
    elif isinstance(result.content, list):
        text_parts = []
        for block in result.content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        translated = "\n".join(text_parts)
    else:
        translated = str(result.content)

    logger.info(f"Translation completed, result_length={len(translated)}")
    return translated


async def atranslate_specialist_response(response: SpecialistResponse) -> str:
    """
    Async version of translate_specialist_response.

    Args:
        response: The structured specialist response.

    Returns:
        Patient-friendly translation of the response.
    """
    logger.info(f"Async translating specialist response: recommendations={len(response.recommendations)}, "
                f"red_flags={len(response.red_flags)}, confidence={response.confidence}")

    llm = get_chat_model(max_tokens=2048)

    # Build the content to translate
    content_parts = [
        "## Specialist Response to Translate",
        "",
        f"**Assessment:** {response.assessment}",
        "",
        "**Recommendations:**",
    ]

    for rec in response.recommendations:
        content_parts.append(
            f"- [{rec.priority.upper()}] {rec.action} (Rationale: {rec.rationale})"
        )

    if response.red_flags:
        content_parts.append("")
        content_parts.append("**Red Flags:**")
        for flag in response.red_flags:
            content_parts.append(f"- {flag}")

    if response.guidelines_referenced:
        content_parts.append("")
        content_parts.append(f"**Guidelines:** {', '.join(response.guidelines_referenced)}")

    if response.limitations:
        content_parts.append("")
        content_parts.append(f"**Limitations:** {response.limitations}")

    content = "\n".join(content_parts)
    logger.debug(f"Content to translate: {len(content)} chars")

    messages = [
        SystemMessage(content=TRANSLATION_PROMPT),
        HumanMessage(content=content),
    ]

    logger.debug("Invoking LLM (async) for translation")
    result = await llm.ainvoke(messages)

    if isinstance(result.content, str):
        translated = result.content
    elif isinstance(result.content, list):
        text_parts = []
        for block in result.content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        translated = "\n".join(text_parts)
    else:
        translated = str(result.content)

    logger.info(f"Async translation completed, result_length={len(translated)}")
    return translated
