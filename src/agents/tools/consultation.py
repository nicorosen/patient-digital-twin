"""
Consultation tool for agent-to-agent communication.

Enables the Medical Assistant to consult with the Primary Care specialist:
- Creates de-identified patient context
- Logs consultations for audit trail
- Returns structured clinical assessments
"""

from datetime import date
from typing import Optional
from uuid import UUID

from langchain_core.tools import tool

from src.agents.primary_care import SpecialistResponse, get_primary_care_specialist
from src.database import get_db
from src.database.repositories import (
    AllergyRepository,
    AuditLogRepository,
    ConditionRepository,
    MedicationRepository,
    PatientRepository,
)
from src.logging_config import get_logger
from src.schemas import DeidentifiedContext

logger = get_logger("agents.tools.consultation")


def calculate_age(birth_date: date) -> int:
    """Calculate age from birth date."""
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def create_deidentified_context(patient_id: UUID) -> DeidentifiedContext:
    """
    Create a de-identified context for specialist consultation.

    INCLUDED (de-identified):
    - Age (calculated from DOB, not DOB itself)
    - Gender
    - Condition names (no specific dates that could identify)
    - Medication names with dosages (no prescriber info)
    - Allergy substances

    EXCLUDED (identifying):
    - Name
    - Date of birth
    - Addresses
    - Contact info
    - Specific dates (use relative descriptions)

    Args:
        patient_id: UUID of the patient.

    Returns:
        De-identified context for specialist consultation.
    """
    logger.debug(f"Creating de-identified context for patient_id={patient_id}")
    with get_db() as db:
        patient = PatientRepository.get_by_id(db, patient_id)
        if not patient:
            logger.warning(f"Patient not found for de-identification: {patient_id}")
            raise ValueError(f"Patient not found: {patient_id}")

        # Get active conditions
        conditions = ConditionRepository.get_by_patient(db, patient_id, active_only=True)
        condition_names = [c.display_name for c in conditions]

        # Get active medications with dosage
        medications = MedicationRepository.get_by_patient(db, patient_id, active_only=True)
        medication_strs = []
        for med in medications:
            med_str = med.display_name
            if med.dosage:
                med_str += f" {med.dosage}"
            if med.frequency:
                med_str += f" ({med.frequency})"
            medication_strs.append(med_str)

        # Get allergies
        allergies = AllergyRepository.get_by_patient(db, patient_id)
        allergy_strs = []
        for allergy in allergies:
            allergy_str = allergy.substance
            if allergy.criticality:
                allergy_str += f" [{allergy.criticality}]"
            allergy_strs.append(allergy_str)

        context = DeidentifiedContext(
            age=calculate_age(patient.date_of_birth),
            gender=patient.gender,
            conditions=condition_names,
            medications=medication_strs,
            allergies=allergy_strs,
        )
        logger.debug(f"De-identified context created: age={context.age}, gender={context.gender}, "
                     f"conditions={len(condition_names)}, medications={len(medication_strs)}, "
                     f"allergies={len(allergy_strs)}")
        return context


def format_specialist_response(response: SpecialistResponse) -> str:
    """
    Format the specialist response for return to the agent.

    Args:
        response: Structured specialist response.

    Returns:
        Formatted string representation.
    """
    lines = [
        "## Specialist Consultation Response",
        "",
        f"**Confidence:** {response.confidence}",
        "",
        "### Assessment",
        response.assessment,
        "",
    ]

    if response.red_flags:
        lines.append("### ⚠️ Red Flags (Immediate Attention)")
        for flag in response.red_flags:
            lines.append(f"- {flag}")
        lines.append("")

    lines.append("### Recommendations")
    for i, rec in enumerate(response.recommendations, 1):
        priority_emoji = {"urgent": "🔴", "routine": "🟡", "optional": "🟢"}.get(
            rec.priority.lower(), "⚪"
        )
        lines.append(f"{i}. {priority_emoji} **{rec.action}** ({rec.priority})")
        lines.append(f"   *Rationale: {rec.rationale}*")
    lines.append("")

    if response.guidelines_referenced:
        lines.append("### Guidelines Referenced")
        for guideline in response.guidelines_referenced:
            lines.append(f"- {guideline}")
        lines.append("")

    if response.limitations:
        lines.append("### Limitations")
        lines.append(response.limitations)

    return "\n".join(lines)


@tool
def consult_primary_care(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Primary Care specialist for clinical guidance.

    Use when:
    - Patient asks clinical questions beyond basic health profile information
    - Symptoms or health concerns need professional assessment
    - Medication interactions need evaluation
    - Patient needs guidance on when to seek medical care
    - Questions about managing chronic conditions

    The specialist receives DE-IDENTIFIED data only (no name, DOB, or other identifiers).
    All consultations are logged for audit purposes.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address. Be specific about
            symptoms, concerns, or the clinical scenario.

    Returns:
        Structured clinical assessment from the specialist, including:
        - Assessment with clinical reasoning
        - Recommendations with priorities
        - Red flags to watch for
        - Referenced clinical guidelines
        - Confidence level and limitations
    """
    logger.info(f"consult_primary_care called: patient_id={patient_id}, question_length={len(clinical_question)}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    try:
        # Create de-identified context
        logger.debug("Creating de-identified context for consultation")
        context = create_deidentified_context(patient_uuid)

        # Get specialist consultation
        logger.info("Invoking Primary Care specialist")
        specialist = get_primary_care_specialist()
        response = specialist.consult(context, clinical_question)
        logger.info(f"Specialist response received: confidence={response.confidence}, "
                    f"recommendations={len(response.recommendations)}, red_flags={len(response.red_flags)}")

        # Log the consultation for audit
        logger.debug("Creating audit log entry")
        with get_db() as db:
            AuditLogRepository.create(
                db=db,
                patient_id=patient_uuid,
                specialist_type="primary_care",
                clinical_question=clinical_question,
                data_shared={
                    "age": context.age,
                    "gender": context.gender,
                    "conditions": context.conditions,
                    "medications": context.medications,
                    "allergies": context.allergies,
                },
                specialist_response={
                    "assessment": response.assessment,
                    "recommendations": [
                        {
                            "action": r.action,
                            "priority": r.priority,
                            "rationale": r.rationale,
                        }
                        for r in response.recommendations
                    ],
                    "red_flags": response.red_flags,
                    "guidelines_referenced": response.guidelines_referenced,
                    "confidence": response.confidence,
                    "limitations": response.limitations,
                },
            )
        logger.debug("Audit log entry created")

        formatted_response = format_specialist_response(response)
        logger.info(f"Consultation completed, response_length={len(formatted_response)}")
        return formatted_response

    except ValueError as e:
        logger.error(f"Value error in consultation: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error consulting specialist: {e}", exc_info=True)
        return f"Error consulting specialist: {str(e)}"


# List of consultation tools
CONSULTATION_TOOLS = [consult_primary_care]
