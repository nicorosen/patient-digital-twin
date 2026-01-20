"""
LangChain tools for patient data operations.

Provides agent tools for:
- Retrieving patient profiles
- Searching patient data using RAG
- Adding conditions, medications, and allergies
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from langchain_core.tools import tool

from src.database import get_db
from src.database.repositories import (
    AllergyRepository,
    ConditionRepository,
    MedicationRepository,
    PatientRepository,
)
from src.rag import get_retriever
from src.schemas import (
    AllergyCategory,
    AllergyCriticality,
    AllergyCreate,
    ClinicalStatus,
    ConditionCreate,
    MedicationCreate,
    MedicationStatus,
    Severity,
)


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a date string in various formats."""
    if not date_str:
        return None
    try:
        # Try common formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"]:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None
    except Exception:
        return None


@tool
def get_patient_profile(patient_id: str) -> str:
    """
    Retrieve the complete health profile for a patient.

    Returns demographics, conditions, medications, and allergies.
    Use this when you need a comprehensive view of the patient's health record.

    Args:
        patient_id: The UUID of the patient.

    Returns:
        A formatted string with the patient's complete health profile.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        return f"Error: Invalid patient ID format: {patient_id}"

    with get_db() as db:
        profile = PatientRepository.get_profile(db, patient_uuid)
        if not profile:
            return f"Error: Patient not found with ID: {patient_id}"

        patient = profile.patient
        lines = [
            f"# Patient Profile: {patient.first_name} {patient.last_name}",
            f"- Age: {patient.age} years old",
            f"- Gender: {patient.gender.value.capitalize()}",
            f"- Date of Birth: {patient.date_of_birth}",
            "",
        ]

        # Conditions
        lines.append("## Active Conditions")
        active_conditions = [c for c in profile.conditions if c.clinical_status == "active"]
        if active_conditions:
            for condition in active_conditions:
                severity = f" ({condition.severity})" if condition.severity else ""
                notes = f" - {condition.notes}" if condition.notes else ""
                lines.append(f"- {condition.display_name}{severity}{notes}")
        else:
            lines.append("- No active conditions recorded")
        lines.append("")

        # Medications
        lines.append("## Current Medications")
        active_meds = [m for m in profile.medications if m.status == "active"]
        if active_meds:
            for med in active_meds:
                dosage = f" {med.dosage}" if med.dosage else ""
                freq = f", {med.frequency}" if med.frequency else ""
                reason = f" (for {med.reason})" if med.reason else ""
                lines.append(f"- {med.display_name}{dosage}{freq}{reason}")
        else:
            lines.append("- No active medications recorded")
        lines.append("")

        # Allergies
        lines.append("## Allergies")
        if profile.allergies:
            for allergy in profile.allergies:
                crit = f" [{allergy.criticality}]" if allergy.criticality else ""
                reaction = f" - {allergy.reaction}" if allergy.reaction else ""
                lines.append(f"- {allergy.substance}{crit}{reaction}")
        else:
            lines.append("- No known allergies")

        return "\n".join(lines)


@tool
def search_patient_data(patient_id: str, query: str) -> str:
    """
    Search the patient's health records using natural language.

    Use this when the patient asks about specific aspects of their health,
    such as medications, conditions, or allergies.

    Args:
        patient_id: The UUID of the patient.
        query: Natural language search query (e.g., "blood pressure medications",
               "when was diabetes diagnosed", "allergies to medications").

    Returns:
        Relevant clinical information matching the query.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        return f"Error: Invalid patient ID format: {patient_id}"

    retriever = get_retriever()
    context = retriever.get_context(query, patient_uuid, n_results=5)
    return context


@tool
def add_condition(
    patient_id: str,
    display_name: str,
    clinical_status: str = "active",
    onset_date: Optional[str] = None,
    severity: Optional[str] = None,
    notes: Optional[str] = None,
    code: Optional[str] = None,
) -> str:
    """
    Add a new condition to the patient's problem list.

    IMPORTANT: Always confirm the details with the patient before calling this tool.
    Extract information from the patient's description and verify it's correct.

    Args:
        patient_id: The UUID of the patient.
        display_name: Human-readable name of the condition (e.g., "Type 2 Diabetes").
        clinical_status: Status of the condition. Options: active, inactive, resolved, remission.
            Default is "active".
        onset_date: When the condition started (format: YYYY-MM-DD). Optional.
        severity: Severity level. Options: mild, moderate, severe. Optional.
        notes: Additional clinical notes. Optional.
        code: Medical code (ICD-10 or SNOMED). Optional.

    Returns:
        Confirmation message with the added condition details.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        return f"Error: Invalid patient ID format: {patient_id}"

    # Parse clinical status
    try:
        status = ClinicalStatus(clinical_status.lower())
    except ValueError:
        return f"Error: Invalid clinical status '{clinical_status}'. Use: active, inactive, resolved, remission"

    # Parse severity if provided
    sev = None
    if severity:
        try:
            sev = Severity(severity.lower())
        except ValueError:
            return f"Error: Invalid severity '{severity}'. Use: mild, moderate, severe"

    # Parse onset date
    onset = _parse_date(onset_date)

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            return f"Error: Patient not found with ID: {patient_id}"

        # Create condition
        condition_data = ConditionCreate(
            patient_id=patient_uuid,
            code=code,
            display_name=display_name,
            clinical_status=status,
            onset_date=onset,
            severity=sev,
            notes=notes,
        )
        condition = ConditionRepository.create(db, condition_data)

        # Index in vector store
        retriever = get_retriever()
        retriever.add_condition_document(
            patient_id=patient_uuid,
            condition_id=condition.id,
            content=condition.to_document(),
        )

        return (
            f"Successfully added condition: {display_name}\n"
            f"- Status: {clinical_status}\n"
            f"- Onset: {onset or 'Not specified'}\n"
            f"- Severity: {severity or 'Not specified'}\n"
            f"- Notes: {notes or 'None'}"
        )


@tool
def add_medication(
    patient_id: str,
    display_name: str,
    dosage: Optional[str] = None,
    frequency: Optional[str] = None,
    route: Optional[str] = None,
    status: str = "active",
    start_date: Optional[str] = None,
    reason: Optional[str] = None,
    code: Optional[str] = None,
) -> str:
    """
    Add a new medication to the patient's medication list.

    IMPORTANT: Always confirm the details with the patient before calling this tool.
    Extract medication information from the patient's description and verify accuracy.

    Args:
        patient_id: The UUID of the patient.
        display_name: Name of the medication (e.g., "Metformin", "Lisinopril").
        dosage: Dosage amount (e.g., "500mg", "10mg"). Optional.
        frequency: How often to take (e.g., "twice daily", "once daily at bedtime"). Optional.
        route: Route of administration (e.g., "oral", "inhalation"). Optional.
        status: Medication status. Options: active, on-hold, discontinued. Default is "active".
        start_date: When the medication was started (format: YYYY-MM-DD). Optional.
        reason: Why the medication is prescribed (e.g., "for blood pressure"). Optional.
        code: RxNorm code. Optional.

    Returns:
        Confirmation message with the added medication details.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        return f"Error: Invalid patient ID format: {patient_id}"

    # Parse medication status
    try:
        med_status = MedicationStatus(status.lower().replace("_", "-"))
    except ValueError:
        return f"Error: Invalid status '{status}'. Use: active, on-hold, discontinued"

    # Parse start date
    start = _parse_date(start_date)

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            return f"Error: Patient not found with ID: {patient_id}"

        # Create medication
        medication_data = MedicationCreate(
            patient_id=patient_uuid,
            code=code,
            display_name=display_name,
            dosage=dosage,
            frequency=frequency,
            route=route or "oral",
            status=med_status,
            start_date=start,
            reason=reason,
        )
        medication = MedicationRepository.create(db, medication_data)

        # Index in vector store
        retriever = get_retriever()
        retriever.add_medication_document(
            patient_id=patient_uuid,
            medication_id=medication.id,
            content=medication.to_document(),
        )

        return (
            f"Successfully added medication: {display_name}\n"
            f"- Dosage: {dosage or 'Not specified'}\n"
            f"- Frequency: {frequency or 'Not specified'}\n"
            f"- Route: {route or 'oral'}\n"
            f"- Status: {status}\n"
            f"- Reason: {reason or 'Not specified'}"
        )


@tool
def add_allergy(
    patient_id: str,
    substance: str,
    category: str = "medication",
    criticality: Optional[str] = None,
    reaction: Optional[str] = None,
    onset_date: Optional[str] = None,
    code: Optional[str] = None,
) -> str:
    """
    Add a new allergy to the patient's allergy list.

    IMPORTANT: Always confirm the details with the patient before calling this tool.
    Allergies are critical safety information - verify accuracy carefully.

    Args:
        patient_id: The UUID of the patient.
        substance: What the patient is allergic to (e.g., "Penicillin", "Shellfish", "Pollen").
        category: Type of allergen. Options: medication, food, environment, biologic.
            Default is "medication".
        criticality: How dangerous the allergy is. Options: low, high. Optional.
        reaction: Description of allergic reaction (e.g., "hives", "anaphylaxis"). Optional.
        onset_date: When the allergy was first identified (format: YYYY-MM-DD). Optional.
        code: Allergen code (RxNorm for medications, other codes as applicable). Optional.

    Returns:
        Confirmation message with the added allergy details.
    """
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        return f"Error: Invalid patient ID format: {patient_id}"

    # Parse category
    try:
        cat = AllergyCategory(category.lower())
    except ValueError:
        return f"Error: Invalid category '{category}'. Use: medication, food, environment, biologic"

    # Parse criticality if provided
    crit = None
    if criticality:
        try:
            crit = AllergyCriticality(criticality.lower())
        except ValueError:
            return f"Error: Invalid criticality '{criticality}'. Use: low, high"

    # Parse onset date
    onset = _parse_date(onset_date)

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            return f"Error: Patient not found with ID: {patient_id}"

        # Create allergy
        allergy_data = AllergyCreate(
            patient_id=patient_uuid,
            code=code,
            substance=substance,
            category=cat,
            criticality=crit,
            reaction=reaction,
            onset_date=onset,
        )
        allergy = AllergyRepository.create(db, allergy_data)

        # Index in vector store
        retriever = get_retriever()
        retriever.add_allergy_document(
            patient_id=patient_uuid,
            allergy_id=allergy.id,
            content=allergy.to_document(),
        )

        crit_str = f" [{criticality}]" if criticality else ""
        return (
            f"Successfully added allergy: {substance}{crit_str}\n"
            f"- Category: {category}\n"
            f"- Reaction: {reaction or 'Not specified'}\n"
            f"- First identified: {onset or 'Not specified'}"
        )


# List of all tools for easy import
PATIENT_DATA_TOOLS = [
    get_patient_profile,
    search_patient_data,
    add_condition,
    add_medication,
    add_allergy,
]
