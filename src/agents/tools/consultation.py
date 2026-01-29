"""
Consultation tools for agent-to-agent communication.

Enables the Medical Assistant to consult with specialist agents:
- Creates de-identified patient context
- Logs consultations for audit trail
- Returns structured clinical assessments
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import UUID

from langchain_core.tools import tool

from src.agents.specialists import SpecialistResponse, get_specialist
from src.agents.translation import translate_specialist_response
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
    """
    logger.debug(f"Creating de-identified context for patient_id={patient_id}")
    with get_db() as db:
        patient = PatientRepository.get_by_id(db, patient_id)
        if not patient:
            logger.warning(f"Patient not found for de-identification: {patient_id}")
            raise ValueError(f"Patient not found: {patient_id}")

        conditions = ConditionRepository.get_by_patient(db, patient_id, active_only=True)
        condition_names = [c.display_name for c in conditions]

        medications = MedicationRepository.get_by_patient(db, patient_id, active_only=True)
        medication_strs = []
        for med in medications:
            med_str = med.display_name
            if med.dosage:
                med_str += f" {med.dosage}"
            if med.frequency:
                med_str += f" ({med.frequency})"
            medication_strs.append(med_str)

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
        logger.debug(
            f"De-identified context created: age={context.age}, gender={context.gender}, "
            f"conditions={len(condition_names)}, medications={len(medication_strs)}, "
            f"allergies={len(allergy_strs)}"
        )
        return context


def format_specialist_response(response: SpecialistResponse) -> str:
    """Format the specialist response for return to the agent."""
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
        lines.append("### Red Flags (Immediate Attention)")
        for flag in response.red_flags:
            lines.append(f"- {flag}")
        lines.append("")

    lines.append("### Recommendations")
    for i, rec in enumerate(response.recommendations, 1):
        priority_emoji = {"urgent": "!", "routine": "-", "optional": "~"}.get(
            rec.priority.lower(), "-"
        )
        lines.append(f"{i}. [{priority_emoji}] **{rec.action}** ({rec.priority})")
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


def _consult_specialist(specialist_name: str, patient_id: str, clinical_question: str) -> str:
    """Shared helper to consult any specialist."""
    logger.info(f"consult_{specialist_name} called: patient_id={patient_id}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    try:
        context = create_deidentified_context(patient_uuid)
        specialist = get_specialist(specialist_name)
        response = specialist.consult(context, clinical_question)
        logger.info(
            f"{specialist_name} response: confidence={response.confidence}, "
            f"recommendations={len(response.recommendations)}, red_flags={len(response.red_flags)}"
        )

        # Log the consultation for audit
        with get_db() as db:
            AuditLogRepository.create(
                db=db,
                patient_id=patient_uuid,
                specialist_type=specialist_name,
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

        translated_response = translate_specialist_response(response)
        return translated_response

    except ValueError as e:
        logger.error(f"Value error in consultation: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error consulting {specialist_name}: {e}", exc_info=True)
        return f"Error consulting specialist: {str(e)}"


@tool
def consult_primary_care(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Primary Care specialist for clinical guidance.

    Use for: general health questions, preventive care, chronic disease management,
    medication reviews, when-to-seek-care advice, and questions that don't clearly
    fit another specialty.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
    """
    return _consult_specialist("primary_care", patient_id, clinical_question)


@tool
def consult_cardiology(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Cardiology specialist for cardiovascular guidance.

    Use for: chest pain, heart failure, arrhythmias, palpitations, hypertension management,
    high cholesterol, peripheral vascular disease, cardiac risk assessment.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
    """
    return _consult_specialist("cardiology", patient_id, clinical_question)


@tool
def consult_endocrinology(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Endocrinology specialist for metabolic/hormonal guidance.

    Use for: diabetes management, thyroid disorders, hormonal imbalances, metabolic syndrome,
    osteoporosis, PCOS, adrenal issues, blood sugar concerns.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
    """
    return _consult_specialist("endocrinology", patient_id, clinical_question)


@tool
def consult_pulmonology(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Pulmonology specialist for respiratory guidance.

    Use for: asthma, COPD, shortness of breath, chronic cough, sleep apnea,
    respiratory infections, lung disease, breathing difficulties.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
    """
    return _consult_specialist("pulmonology", patient_id, clinical_question)


@tool
def consult_neurology(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Neurology specialist for neurological guidance.

    Use for: headaches, migraines, seizures, dizziness, vertigo, numbness/tingling,
    memory concerns, tremors, stroke risk, neuropathy.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
    """
    return _consult_specialist("neurology", patient_id, clinical_question)


@tool
def consult_gastroenterology(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Gastroenterology specialist for GI guidance.

    Use for: acid reflux, GERD, abdominal pain, IBS, IBD, liver disease,
    digestive issues, nausea, colorectal screening, celiac disease.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
    """
    return _consult_specialist("gastroenterology", patient_id, clinical_question)


@tool
def consult_oncology(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Oncology specialist for cancer-related guidance.

    Use for: cancer screening, suspicious symptoms (unexplained weight loss, lumps),
    cancer treatment side effects, survivorship care, genetic risk assessment.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
    """
    return _consult_specialist("oncology", patient_id, clinical_question)


@tool
def consult_psychiatry(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Psychiatry specialist for mental health guidance.

    Use for: depression, anxiety, mood changes, sleep problems, stress,
    medication for mental health, PTSD, ADHD, behavioral concerns.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
    """
    return _consult_specialist("psychiatry", patient_id, clinical_question)


@tool
def consult_orthopedics(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Orthopedics specialist for musculoskeletal guidance.

    Use for: joint pain, arthritis, back/neck pain, fractures, sports injuries,
    tendinitis, carpal tunnel, bone health, gout, mobility issues.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
    """
    return _consult_specialist("orthopedics", patient_id, clinical_question)


@tool
def consult_nephrology(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Nephrology specialist for kidney-related guidance.

    Use for: kidney disease, abnormal kidney function, electrolyte imbalances,
    kidney stones, medication dosing in renal impairment, dialysis questions.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
    """
    return _consult_specialist("nephrology", patient_id, clinical_question)


@tool
def consult_dermatology(patient_id: str, clinical_question: str) -> str:
    """
    Consult the Dermatology specialist for skin-related guidance.

    Use for: rashes, eczema, psoriasis, acne, skin infections, suspicious moles,
    drug reactions on skin, wound healing, hair/nail issues.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
    """
    return _consult_specialist("dermatology", patient_id, clinical_question)


@tool
def consult_medical_board(patient_id: str, clinical_question: str, specialists: list[str]) -> str:
    """
    Consult multiple specialists simultaneously on a clinical question.

    Use when the question spans multiple domains or the doctor wants opinions
    from several specialists at once. Returns combined responses from all
    requested specialists.

    Args:
        patient_id: The UUID of the patient.
        clinical_question: The clinical question to address.
        specialists: List of specialist names to consult.
            Available: primary_care, cardiology, endocrinology, pulmonology,
            neurology, gastroenterology, oncology, psychiatry, orthopedics,
            nephrology, dermatology
    """
    logger.info(f"consult_medical_board called: specialists={specialists}")

    def _run_one(spec_name: str) -> str:
        header = f"## {spec_name.replace('_', ' ').title()} Opinion\n\n"
        result = _consult_specialist(spec_name, patient_id, clinical_question)
        return header + result

    with ThreadPoolExecutor(max_workers=len(specialists)) as executor:
        results = list(executor.map(_run_one, specialists))

    return "\n\n---\n\n".join(results)


# List of all consultation tools
CONSULTATION_TOOLS = [
    consult_primary_care,
    consult_cardiology,
    consult_endocrinology,
    consult_pulmonology,
    consult_neurology,
    consult_gastroenterology,
    consult_oncology,
    consult_psychiatry,
    consult_orthopedics,
    consult_nephrology,
    consult_dermatology,
    consult_medical_board,
]
