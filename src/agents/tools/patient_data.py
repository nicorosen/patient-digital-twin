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
    FamilyHistoryRepository,
    LabResultRepository,
    MedicationRepository,
    PatientRepository,
    SocialHistoryRepository,
    VitalSignsRepository,
)
from src.logging_config import get_logger
from src.rag import get_retriever
from src.schemas import (
    AllergyCategory,
    AllergyCriticality,
    AllergyCreate,
    AllergyUpdate,
    ClinicalStatus,
    ConditionCreate,
    ConditionUpdate,
    FamilyHistoryCreate,
    FamilyHistoryUpdate,
    FamilyRelationship,
    LabInterpretation,
    LabResultCreate,
    LabResultUpdate,
    MedicationCreate,
    MedicationStatus,
    MedicationUpdate,
    Severity,
    SocialHistoryCategory,
    SocialHistoryCreate,
    SocialHistoryStatus,
    SocialHistoryUpdate,
    VitalSignsCreate,
    VitalSignsUpdate,
)

logger = get_logger("agents.tools.patient_data")


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
    logger.info(f"get_patient_profile called for patient_id={patient_id}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    with get_db() as db:
        profile = PatientRepository.get_profile(db, patient_uuid)
        if not profile:
            logger.warning(f"Patient not found: {patient_id}")
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
        lines.append("")

        # Latest Vital Signs
        lines.append("## Latest Vital Signs")
        if profile.vital_signs:
            latest = sorted(profile.vital_signs, key=lambda v: v.recorded_at, reverse=True)[0]
            lines.append(f"- Recorded: {latest.recorded_at.strftime('%Y-%m-%d %H:%M')}")
            if latest.systolic_bp and latest.diastolic_bp:
                lines.append(f"- Blood Pressure: {latest.systolic_bp}/{latest.diastolic_bp} mmHg")
            if latest.heart_rate:
                lines.append(f"- Heart Rate: {latest.heart_rate} bpm")
            if latest.temperature:
                lines.append(f"- Temperature: {latest.temperature}°C")
            if latest.weight_kg:
                lines.append(f"- Weight: {latest.weight_kg} kg")
            if latest.oxygen_saturation:
                lines.append(f"- Oxygen Saturation: {latest.oxygen_saturation}%")
        else:
            lines.append("- No vital signs recorded")
        lines.append("")

        # Family History
        lines.append("## Family History")
        if profile.family_history:
            for fh in profile.family_history:
                age_str = f" (diagnosed at age {fh.onset_age})" if fh.onset_age else ""
                lines.append(f"- {fh.relation.capitalize()}: {fh.condition_name}{age_str}")
        else:
            lines.append("- No family history recorded")
        lines.append("")

        # Social History
        lines.append("## Social History")
        if profile.social_history:
            for sh in profile.social_history:
                desc = f": {sh.description}" if sh.description else ""
                lines.append(f"- {sh.category.capitalize()}: {sh.status}{desc}")
        else:
            lines.append("- No social history recorded")

        logger.debug(f"Retrieved profile: conditions={len(profile.conditions)}, "
                     f"medications={len(profile.medications)}, allergies={len(profile.allergies)}")
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
    logger.info(f"search_patient_data called: patient_id={patient_id}")
    logger.info(f"  Query: '{query}'")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    retriever = get_retriever()
    context = retriever.get_context(query, patient_uuid, n_results=5)
    logger.info(f"search_patient_data result: {len(context)} chars")
    logger.debug(f"Full RAG context:\n{context}")
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
    logger.info(f"add_condition called: patient_id={patient_id}, condition={display_name}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    # Parse clinical status
    try:
        status = ClinicalStatus(clinical_status.lower())
    except ValueError:
        logger.warning(f"Invalid clinical status: {clinical_status}")
        return f"Error: Invalid clinical status '{clinical_status}'. Use: active, inactive, resolved, remission"

    # Parse severity if provided
    sev = None
    if severity:
        try:
            sev = Severity(severity.lower())
        except ValueError:
            logger.warning(f"Invalid severity: {severity}")
            return f"Error: Invalid severity '{severity}'. Use: mild, moderate, severe"

    # Parse onset date
    onset = _parse_date(onset_date)

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
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
        logger.debug(f"Created condition in database: id={condition.id}")

        # Index in vector store
        retriever = get_retriever()
        retriever.add_condition_document(
            patient_id=patient_uuid,
            condition_id=condition.id,
            content=condition.to_document(),
        )
        logger.debug("Indexed condition in vector store")

        logger.info(f"Successfully added condition: {display_name} for patient {patient_id}")
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
    logger.info(f"add_medication called: patient_id={patient_id}, medication={display_name}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    # Parse medication status
    try:
        med_status = MedicationStatus(status.lower().replace("_", "-"))
    except ValueError:
        logger.warning(f"Invalid medication status: {status}")
        return f"Error: Invalid status '{status}'. Use: active, on-hold, discontinued"

    # Parse start date
    start = _parse_date(start_date)

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
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
        logger.debug(f"Created medication in database: id={medication.id}")

        # Index in vector store
        retriever = get_retriever()
        retriever.add_medication_document(
            patient_id=patient_uuid,
            medication_id=medication.id,
            content=medication.to_document(),
        )
        logger.debug("Indexed medication in vector store")

        logger.info(f"Successfully added medication: {display_name} for patient {patient_id}")
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
    logger.info(f"add_allergy called: patient_id={patient_id}, substance={substance}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    # Parse category
    try:
        cat = AllergyCategory(category.lower())
    except ValueError:
        logger.warning(f"Invalid allergy category: {category}")
        return f"Error: Invalid category '{category}'. Use: medication, food, environment, biologic"

    # Parse criticality if provided
    crit = None
    if criticality:
        try:
            crit = AllergyCriticality(criticality.lower())
        except ValueError:
            logger.warning(f"Invalid allergy criticality: {criticality}")
            return f"Error: Invalid criticality '{criticality}'. Use: low, high"

    # Parse onset date
    onset = _parse_date(onset_date)

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
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
        logger.debug(f"Created allergy in database: id={allergy.id}")

        # Index in vector store
        retriever = get_retriever()
        retriever.add_allergy_document(
            patient_id=patient_uuid,
            allergy_id=allergy.id,
            content=allergy.to_document(),
        )
        logger.debug("Indexed allergy in vector store")

        crit_str = f" [{criticality}]" if criticality else ""
        logger.info(f"Successfully added allergy: {substance} for patient {patient_id}")
        return (
            f"Successfully added allergy: {substance}{crit_str}\n"
            f"- Category: {category}\n"
            f"- Reaction: {reaction or 'Not specified'}\n"
            f"- First identified: {onset or 'Not specified'}"
        )


@tool
def add_vital_signs(
    patient_id: str,
    systolic_bp: Optional[int] = None,
    diastolic_bp: Optional[int] = None,
    heart_rate: Optional[int] = None,
    temperature: Optional[float] = None,
    weight_kg: Optional[float] = None,
    height_cm: Optional[float] = None,
    oxygen_saturation: Optional[int] = None,
    recorded_at: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Record vital signs for the patient.

    Use this to capture blood pressure, heart rate, temperature, weight,
    height, or oxygen saturation readings.

    Args:
        patient_id: The UUID of the patient.
        systolic_bp: Systolic blood pressure in mmHg (e.g., 120).
        diastolic_bp: Diastolic blood pressure in mmHg (e.g., 80).
        heart_rate: Heart rate in beats per minute (e.g., 72).
        temperature: Body temperature in Celsius (e.g., 37.0).
        weight_kg: Weight in kilograms (e.g., 70.5).
        height_cm: Height in centimeters (e.g., 175).
        oxygen_saturation: SpO2 percentage (e.g., 98).
        recorded_at: When measurements were taken (format: YYYY-MM-DD HH:MM).
            Defaults to current time if not specified.
        notes: Additional notes about the measurements.

    Returns:
        Confirmation message with recorded vital signs.
    """
    logger.info(f"add_vital_signs called for patient_id={patient_id}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    # Parse recorded_at datetime
    if recorded_at:
        try:
            for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y"]:
                try:
                    record_time = datetime.strptime(recorded_at, fmt)
                    break
                except ValueError:
                    continue
            else:
                record_time = datetime.now()
        except Exception:
            record_time = datetime.now()
    else:
        record_time = datetime.now()

    with get_db() as db:
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        vital_signs_data = VitalSignsCreate(
            patient_id=patient_uuid,
            recorded_at=record_time,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            heart_rate=heart_rate,
            temperature=temperature,
            weight_kg=weight_kg,
            height_cm=height_cm,
            oxygen_saturation=oxygen_saturation,
            notes=notes,
        )
        vital_signs = VitalSignsRepository.create(db, vital_signs_data)
        logger.debug(f"Created vital signs in database: id={vital_signs.id}")

        # Index in vector store
        retriever = get_retriever()
        retriever.add_document(
            patient_id=patient_uuid,
            doc_id=vital_signs.id,
            content=vital_signs.to_document(),
            doc_type="vital_signs",
        )
        logger.debug("Indexed vital signs in vector store")

        # Build response
        lines = ["Successfully recorded vital signs:"]
        if systolic_bp and diastolic_bp:
            lines.append(f"- Blood Pressure: {systolic_bp}/{diastolic_bp} mmHg")
        if heart_rate:
            lines.append(f"- Heart Rate: {heart_rate} bpm")
        if temperature:
            lines.append(f"- Temperature: {temperature}°C")
        if weight_kg:
            lines.append(f"- Weight: {weight_kg} kg")
        if height_cm:
            lines.append(f"- Height: {height_cm} cm")
        if oxygen_saturation:
            lines.append(f"- Oxygen Saturation: {oxygen_saturation}%")
        lines.append(f"- Recorded at: {record_time.strftime('%Y-%m-%d %H:%M')}")

        logger.info(f"Successfully added vital signs for patient {patient_id}")
        return "\n".join(lines)


@tool
def get_vital_signs(patient_id: str, limit: int = 5) -> str:
    """
    Get recent vital signs for the patient.

    Args:
        patient_id: The UUID of the patient.
        limit: Maximum number of records to return (default 5).

    Returns:
        List of recent vital sign recordings.
    """
    logger.info(f"get_vital_signs called for patient_id={patient_id}, limit={limit}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    with get_db() as db:
        vital_signs = VitalSignsRepository.get_by_patient(db, patient_uuid, limit=limit)
        if not vital_signs:
            return "No vital signs recorded for this patient."

        lines = [f"## Recent Vital Signs (last {len(vital_signs)} records)"]
        for vs in vital_signs:
            lines.append(f"\n### {vs.recorded_at.strftime('%Y-%m-%d %H:%M')}")
            lines.append(f"ID: {vs.id}")
            if vs.systolic_bp and vs.diastolic_bp:
                lines.append(f"- Blood Pressure: {vs.systolic_bp}/{vs.diastolic_bp} mmHg")
            if vs.heart_rate:
                lines.append(f"- Heart Rate: {vs.heart_rate} bpm")
            if vs.temperature:
                lines.append(f"- Temperature: {vs.temperature}°C")
            if vs.weight_kg:
                lines.append(f"- Weight: {vs.weight_kg} kg")
            if vs.height_cm:
                lines.append(f"- Height: {vs.height_cm} cm")
            if vs.oxygen_saturation:
                lines.append(f"- Oxygen Saturation: {vs.oxygen_saturation}%")
            if vs.notes:
                lines.append(f"- Notes: {vs.notes}")

        return "\n".join(lines)


@tool
def add_lab_result(
    patient_id: str,
    test_name: str,
    value: str,
    result_date: Optional[str] = None,
    value_numeric: Optional[float] = None,
    unit: Optional[str] = None,
    reference_range_low: Optional[float] = None,
    reference_range_high: Optional[float] = None,
    interpretation: Optional[str] = None,
    test_code: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Add a laboratory test result for the patient.

    Use this to record blood tests, urine tests, and other lab work.

    Args:
        patient_id: The UUID of the patient.
        test_name: Name of the test (e.g., "HbA1c", "Blood Glucose", "Cholesterol").
        value: Result value as string (e.g., "5.7", "142", "Positive").
        result_date: When the test was performed (format: YYYY-MM-DD).
            Defaults to today if not specified.
        value_numeric: Numeric value for comparison (optional).
        unit: Unit of measurement (e.g., "mg/dL", "%", "mmol/L").
        reference_range_low: Lower bound of normal range.
        reference_range_high: Upper bound of normal range.
        interpretation: Result interpretation. Options: normal, abnormal, critical.
        test_code: LOINC code for the test (optional).
        notes: Additional notes about the result.

    Returns:
        Confirmation message with the lab result details.
    """
    logger.info(f"add_lab_result called: patient_id={patient_id}, test={test_name}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    # Parse result date
    if result_date:
        parsed_date = _parse_date(result_date)
        if parsed_date:
            result_datetime = datetime.combine(parsed_date, datetime.min.time())
        else:
            result_datetime = datetime.now()
    else:
        result_datetime = datetime.now()

    # Parse interpretation
    interp = None
    if interpretation:
        try:
            interp = LabInterpretation(interpretation.lower())
        except ValueError:
            logger.warning(f"Invalid interpretation: {interpretation}")
            return f"Error: Invalid interpretation '{interpretation}'. Use: normal, abnormal, critical"

    with get_db() as db:
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        lab_result_data = LabResultCreate(
            patient_id=patient_uuid,
            test_name=test_name,
            test_code=test_code,
            value=value,
            value_numeric=value_numeric,
            unit=unit,
            reference_range_low=reference_range_low,
            reference_range_high=reference_range_high,
            interpretation=interp,
            result_date=result_datetime,
            notes=notes,
        )
        lab_result = LabResultRepository.create(db, lab_result_data)
        logger.debug(f"Created lab result in database: id={lab_result.id}")

        # Index in vector store
        retriever = get_retriever()
        retriever.add_document(
            patient_id=patient_uuid,
            doc_id=lab_result.id,
            content=lab_result.to_document(),
            doc_type="lab_result",
        )
        logger.debug("Indexed lab result in vector store")

        # Build response
        unit_str = f" {unit}" if unit else ""
        ref_str = ""
        if reference_range_low is not None and reference_range_high is not None:
            ref_str = f" (reference: {reference_range_low}-{reference_range_high}{unit_str})"

        logger.info(f"Successfully added lab result: {test_name} for patient {patient_id}")
        return (
            f"Successfully added lab result:\n"
            f"- Test: {test_name}\n"
            f"- Result: {value}{unit_str}{ref_str}\n"
            f"- Date: {result_datetime.strftime('%Y-%m-%d')}\n"
            f"- Interpretation: {interpretation or 'Not specified'}\n"
            f"- Notes: {notes or 'None'}"
        )


@tool
def get_lab_results(
    patient_id: str,
    test_name: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    Get laboratory results for the patient.

    Args:
        patient_id: The UUID of the patient.
        test_name: Filter by test name (partial match). Optional.
        limit: Maximum number of results to return (default 10).

    Returns:
        List of lab results, optionally filtered by test name.
    """
    logger.info(f"get_lab_results called: patient_id={patient_id}, test_name={test_name}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    with get_db() as db:
        lab_results = LabResultRepository.get_by_patient(
            db, patient_uuid, test_name=test_name, limit=limit
        )
        if not lab_results:
            filter_msg = f" for '{test_name}'" if test_name else ""
            return f"No lab results found{filter_msg}."

        filter_msg = f" matching '{test_name}'" if test_name else ""
        lines = [f"## Lab Results{filter_msg} (last {len(lab_results)} records)"]
        for lr in lab_results:
            unit_str = f" {lr.unit}" if lr.unit else ""
            interp_str = f" [{lr.interpretation}]" if lr.interpretation else ""
            lines.append(f"\n### {lr.test_name} - {lr.result_date.strftime('%Y-%m-%d')}")
            lines.append(f"ID: {lr.id}")
            lines.append(f"- Result: {lr.value}{unit_str}{interp_str}")
            if lr.reference_range_low is not None and lr.reference_range_high is not None:
                lines.append(
                    f"- Reference Range: {lr.reference_range_low}-{lr.reference_range_high}{unit_str}"
                )
            if lr.notes:
                lines.append(f"- Notes: {lr.notes}")

        return "\n".join(lines)


@tool
def add_family_history(
    patient_id: str,
    relationship: str,
    condition_name: str,
    onset_age: Optional[int] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Add family medical history for the patient.

    Important for assessing genetic risk factors.

    Args:
        patient_id: The UUID of the patient.
        relationship: Relationship to patient. Options: mother, father, sibling,
            maternal_grandmother, maternal_grandfather, paternal_grandmother,
            paternal_grandfather, aunt, uncle, child, other.
        condition_name: Name of the medical condition (e.g., "Heart Disease", "Diabetes").
        onset_age: Age when the relative was diagnosed (optional).
        notes: Additional notes about the family history.

    Returns:
        Confirmation message with the family history details.
    """
    logger.info(f"add_family_history called: patient_id={patient_id}, relationship={relationship}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    # Parse relationship
    try:
        rel = FamilyRelationship(relationship.lower().replace(" ", "_"))
    except ValueError:
        logger.warning(f"Invalid relationship: {relationship}")
        valid = ", ".join([r.value for r in FamilyRelationship])
        return f"Error: Invalid relationship '{relationship}'. Use: {valid}"

    with get_db() as db:
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        family_history_data = FamilyHistoryCreate(
            patient_id=patient_uuid,
            relation=rel,
            condition_name=condition_name,
            onset_age=onset_age,
            notes=notes,
        )
        family_history = FamilyHistoryRepository.create(db, family_history_data)
        logger.debug(f"Created family history in database: id={family_history.id}")

        # Index in vector store
        retriever = get_retriever()
        retriever.add_document(
            patient_id=patient_uuid,
            doc_id=family_history.id,
            content=family_history.to_document(),
            doc_type="family_history",
        )
        logger.debug("Indexed family history in vector store")

        age_str = f" (diagnosed at age {onset_age})" if onset_age else ""
        logger.info(f"Successfully added family history for patient {patient_id}")
        return (
            f"Successfully added family history:\n"
            f"- Relationship: {relationship.capitalize()}\n"
            f"- Condition: {condition_name}{age_str}\n"
            f"- Notes: {notes or 'None'}"
        )


@tool
def add_social_history(
    patient_id: str,
    category: str,
    status: str,
    description: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Add social/lifestyle history for the patient.

    Use this for smoking status, alcohol use, exercise habits, diet, etc.

    Args:
        patient_id: The UUID of the patient.
        category: Category of social history. Options: smoking, alcohol, drugs,
            exercise, diet, occupation, living_situation, stress, sleep, other.
        status: Current status. Options: current, former, never, occasional, daily, unknown.
        description: Detailed description (e.g., "1 pack per day for 10 years").
        notes: Additional notes.

    Returns:
        Confirmation message with the social history details.
    """
    logger.info(f"add_social_history called: patient_id={patient_id}, category={category}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    # Parse category
    try:
        cat = SocialHistoryCategory(category.lower().replace(" ", "_"))
    except ValueError:
        logger.warning(f"Invalid category: {category}")
        valid = ", ".join([c.value for c in SocialHistoryCategory])
        return f"Error: Invalid category '{category}'. Use: {valid}"

    # Parse status
    try:
        stat = SocialHistoryStatus(status.lower())
    except ValueError:
        logger.warning(f"Invalid status: {status}")
        valid = ", ".join([s.value for s in SocialHistoryStatus])
        return f"Error: Invalid status '{status}'. Use: {valid}"

    with get_db() as db:
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        social_history_data = SocialHistoryCreate(
            patient_id=patient_uuid,
            category=cat,
            status=stat,
            description=description,
            notes=notes,
        )
        social_history = SocialHistoryRepository.create(db, social_history_data)
        logger.debug(f"Created social history in database: id={social_history.id}")

        # Index in vector store
        retriever = get_retriever()
        retriever.add_document(
            patient_id=patient_uuid,
            doc_id=social_history.id,
            content=social_history.to_document(),
            doc_type="social_history",
        )
        logger.debug("Indexed social history in vector store")

        logger.info(f"Successfully added social history for patient {patient_id}")
        return (
            f"Successfully added social history:\n"
            f"- Category: {category.capitalize()}\n"
            f"- Status: {status}\n"
            f"- Description: {description or 'Not specified'}\n"
            f"- Notes: {notes or 'None'}"
        )


@tool
def search_clinical_history(patient_id: str, query: str) -> str:
    """
    Search past clinical conversations for context.

    Use this to find information from previous clinical consultations
    when helping the patient understand their health situation.
    This searches past conversations with the Medical Assistant.

    Args:
        patient_id: The UUID of the patient.
        query: What to search for (e.g., "diabetes management",
               "medication discussion", "recent symptoms").

    Returns:
        Relevant context from past clinical conversations.
    """
    logger.info(f"search_clinical_history called: patient_id={patient_id}")
    logger.info(f"  Query: '{query}'")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    retriever = get_retriever()
    context = retriever.get_clinical_context(query, patient_uuid, n_results=3)
    logger.info(f"search_clinical_history result: {len(context)} chars")
    return context


@tool
def get_conditions(patient_id: str, status: Optional[str] = None) -> str:
    """
    Get all conditions/diagnoses for the patient.

    Use this when the patient asks about their conditions, diagnoses,
    or medical problems. Returns all conditions from the problem list.

    Args:
        patient_id: The UUID of the patient.
        status: Optional filter by clinical status (active, inactive, resolved, remission).
            If not specified, returns all conditions.

    Returns:
        List of all conditions for the patient.
    """
    logger.info(f"get_conditions called: patient_id={patient_id}, status={status}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    with get_db() as db:
        conditions = ConditionRepository.get_by_patient(db, patient_uuid)
        if not conditions:
            return "No conditions recorded for this patient."

        # Filter by status if provided
        if status:
            try:
                filter_status = ClinicalStatus(status.lower())
                conditions = [c for c in conditions if c.clinical_status == filter_status]
            except ValueError:
                logger.warning(f"Invalid status filter: {status}")
                return f"Error: Invalid status '{status}'. Use: active, inactive, resolved, remission"

        if not conditions:
            return f"No {status} conditions found for this patient."

        lines = [f"## Patient Conditions ({len(conditions)} total)"]
        for condition in conditions:
            # Handle both enum objects and string values
            status_val = condition.clinical_status.value if hasattr(condition.clinical_status, 'value') else condition.clinical_status
            severity_val = condition.severity.value if hasattr(condition.severity, 'value') else condition.severity
            status_str = f"[{status_val}]" if condition.clinical_status else ""
            severity_str = f" - {severity_val}" if condition.severity else ""
            onset_str = f" (onset: {condition.onset_date})" if condition.onset_date else ""
            notes_str = f"\n  Notes: {condition.notes}" if condition.notes else ""
            lines.append(f"\n- **{condition.display_name}** {status_str}{severity_str}{onset_str}")
            lines.append(f"  ID: {condition.id}")
            if condition.notes:
                lines.append(f"  Notes: {condition.notes}")

        return "\n".join(lines)


@tool
def get_medications(patient_id: str, status: Optional[str] = None) -> str:
    """
    Get all medications for the patient.

    Use this when the patient asks about their medications, prescriptions,
    or what drugs they are taking. Returns all medications.

    Args:
        patient_id: The UUID of the patient.
        status: Optional filter by status (active, on-hold, discontinued).
            If not specified, returns all medications.

    Returns:
        List of all medications for the patient.
    """
    logger.info(f"get_medications called: patient_id={patient_id}, status={status}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    with get_db() as db:
        medications = MedicationRepository.get_by_patient(db, patient_uuid)
        if not medications:
            return "No medications recorded for this patient."

        # Filter by status if provided
        if status:
            try:
                filter_status = MedicationStatus(status.lower().replace("_", "-"))
                medications = [m for m in medications if m.status == filter_status]
            except ValueError:
                logger.warning(f"Invalid status filter: {status}")
                return f"Error: Invalid status '{status}'. Use: active, on-hold, discontinued"

        if not medications:
            return f"No {status} medications found for this patient."

        lines = [f"## Patient Medications ({len(medications)} total)"]
        for med in medications:
            # Handle both enum objects and string values
            status_val = med.status.value if hasattr(med.status, 'value') else med.status
            status_str = f"[{status_val}]" if med.status else ""
            dosage_str = f" {med.dosage}" if med.dosage else ""
            freq_str = f", {med.frequency}" if med.frequency else ""
            reason_str = f" (for {med.reason})" if med.reason else ""
            route_str = f" via {med.route}" if med.route else ""
            start_str = f"\n  Started: {med.start_date}" if med.start_date else ""
            lines.append(f"\n- **{med.display_name}**{dosage_str}{freq_str}{route_str} {status_str}{reason_str}")
            lines.append(f"  ID: {med.id}")
            if med.start_date:
                lines.append(f"  Started: {med.start_date}")

        return "\n".join(lines)


@tool
def get_allergies(patient_id: str) -> str:
    """
    Get all allergies for the patient.

    Use this when the patient asks about their allergies or what they
    are allergic to. This is critical safety information.

    Args:
        patient_id: The UUID of the patient.

    Returns:
        List of all allergies for the patient.
    """
    logger.info(f"get_allergies called: patient_id={patient_id}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    with get_db() as db:
        allergies = AllergyRepository.get_by_patient(db, patient_uuid)
        if not allergies:
            return "No known allergies recorded for this patient."

        lines = [f"## Patient Allergies ({len(allergies)} total)"]
        for allergy in allergies:
            # Handle both enum objects and string values
            category_val = allergy.category.value if hasattr(allergy.category, 'value') else allergy.category
            crit_val = allergy.criticality.value if hasattr(allergy.criticality, 'value') else allergy.criticality
            category_str = f"[{category_val}]" if allergy.category else ""
            crit_str = f" - Criticality: {crit_val}" if allergy.criticality else ""
            lines.append(f"\n- **{allergy.substance}** {category_str}{crit_str}")
            lines.append(f"  ID: {allergy.id}")
            if allergy.reaction:
                lines.append(f"  Reaction: {allergy.reaction}")
            if allergy.onset_date:
                lines.append(f"  First identified: {allergy.onset_date}")

        return "\n".join(lines)


@tool
def get_family_history(patient_id: str) -> str:
    """
    Get family medical history for the patient.

    Use this when the patient asks about their family history or
    genetic risk factors. Important for assessing hereditary conditions.

    Args:
        patient_id: The UUID of the patient.

    Returns:
        List of family medical history entries.
    """
    logger.info(f"get_family_history called: patient_id={patient_id}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    with get_db() as db:
        family_history = FamilyHistoryRepository.get_by_patient(db, patient_uuid)
        if not family_history:
            return "No family history recorded for this patient."

        lines = [f"## Family Medical History ({len(family_history)} entries)"]
        for fh in family_history:
            # Handle both enum objects and string values
            relation_val = fh.relation.value if hasattr(fh.relation, 'value') else fh.relation
            relation_str = relation_val.replace("_", " ").capitalize() if relation_val else "Unknown"
            age_str = f" (diagnosed at age {fh.onset_age})" if fh.onset_age else ""
            lines.append(f"\n- **{relation_str}**: {fh.condition_name}{age_str}")
            lines.append(f"  ID: {fh.id}")
            if fh.notes:
                lines.append(f"  Notes: {fh.notes}")

        return "\n".join(lines)


@tool
def get_social_history(patient_id: str, category: Optional[str] = None) -> str:
    """
    Get social and lifestyle history for the patient.

    Use this when the patient asks about their lifestyle factors,
    smoking status, alcohol use, exercise habits, etc.

    Args:
        patient_id: The UUID of the patient.
        category: Optional filter by category (smoking, alcohol, drugs,
            exercise, diet, occupation, living_situation, stress, sleep, other).

    Returns:
        List of social history entries.
    """
    logger.info(f"get_social_history called: patient_id={patient_id}, category={category}")
    try:
        patient_uuid = UUID(patient_id)
    except ValueError:
        logger.warning(f"Invalid patient ID format: {patient_id}")
        return f"Error: Invalid patient ID format: {patient_id}"

    with get_db() as db:
        social_history = SocialHistoryRepository.get_by_patient(db, patient_uuid)
        if not social_history:
            return "No social history recorded for this patient."

        # Filter by category if provided
        if category:
            try:
                filter_cat = SocialHistoryCategory(category.lower().replace(" ", "_"))
                social_history = [sh for sh in social_history if sh.category == filter_cat]
            except ValueError:
                logger.warning(f"Invalid category filter: {category}")
                valid = ", ".join([c.value for c in SocialHistoryCategory])
                return f"Error: Invalid category '{category}'. Use: {valid}"

        if not social_history:
            return f"No {category} history found for this patient."

        lines = [f"## Social/Lifestyle History ({len(social_history)} entries)"]
        for sh in social_history:
            # Handle both enum objects and string values
            cat_val = sh.category.value if hasattr(sh.category, 'value') else sh.category
            status_val = sh.status.value if hasattr(sh.status, 'value') else sh.status
            cat_str = cat_val.replace("_", " ").capitalize() if cat_val else "Unknown"
            status_str = status_val if status_val else "unknown"
            desc_str = f": {sh.description}" if sh.description else ""
            lines.append(f"\n- **{cat_str}**: {status_str}{desc_str}")
            lines.append(f"  ID: {sh.id}")
            if sh.notes:
                lines.append(f"  Notes: {sh.notes}")

        return "\n".join(lines)


# ============================================================================
# UPDATE TOOLS - Modify existing records
# ============================================================================


@tool
def update_condition(
    patient_id: str,
    condition_id: str,
    clinical_status: Optional[str] = None,
    severity: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Update an existing condition in the patient's problem list.

    IMPORTANT: Before calling this tool, you MUST first call get_conditions() to retrieve
    the actual condition IDs from the database. Never guess or fabricate UUIDs.

    Use this to change the status, severity, or notes of a condition.
    For example: mark a condition as resolved, change severity from mild to moderate.

    Args:
        patient_id: The UUID of the patient.
        condition_id: The UUID of the condition to update (obtained from get_conditions).
        clinical_status: New status. Options: active, inactive, resolved, remission.
        severity: New severity level. Options: mild, moderate, severe.
        notes: Updated clinical notes.

    Returns:
        Confirmation message with the updated condition details.
    """
    logger.info(f"update_condition called: patient_id={patient_id}, condition_id={condition_id}")
    try:
        patient_uuid = UUID(patient_id)
        condition_uuid = UUID(condition_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    # Parse clinical status if provided
    status = None
    if clinical_status:
        try:
            status = ClinicalStatus(clinical_status.lower())
        except ValueError:
            logger.warning(f"Invalid clinical status: {clinical_status}")
            return f"Error: Invalid clinical status '{clinical_status}'. Use: active, inactive, resolved, remission"

    # Parse severity if provided
    sev = None
    if severity:
        try:
            sev = Severity(severity.lower())
        except ValueError:
            logger.warning(f"Invalid severity: {severity}")
            return f"Error: Invalid severity '{severity}'. Use: mild, moderate, severe"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify condition exists and belongs to patient
        condition = ConditionRepository.get_by_id(db, condition_uuid)
        if not condition:
            logger.warning(f"Condition not found: {condition_id}")
            return f"Error: Condition not found with ID: {condition_id}"
        if condition.patient_id != patient_uuid:
            logger.warning(f"Condition {condition_id} does not belong to patient {patient_id}")
            return f"Error: Condition does not belong to this patient"

        # Build update data
        update_data = ConditionUpdate(
            clinical_status=status,
            severity=sev,
            notes=notes,
        )

        # Update condition
        updated = ConditionRepository.update(db, condition_uuid, update_data)
        if not updated:
            return "Error: Failed to update condition"

        # Update RAG index
        retriever = get_retriever()
        retriever.remove_document("condition", condition_uuid)
        retriever.add_condition_document(
            patient_id=patient_uuid,
            condition_id=condition_uuid,
            content=updated.to_document(),
        )

        logger.info(f"Successfully updated condition: {updated.display_name}")
        return (
            f"Successfully updated condition: {updated.display_name}\n"
            f"- Status: {updated.clinical_status}\n"
            f"- Severity: {updated.severity or 'Not specified'}\n"
            f"- Notes: {updated.notes or 'None'}"
        )


@tool
def update_medication(
    patient_id: str,
    medication_id: str,
    dosage: Optional[str] = None,
    frequency: Optional[str] = None,
    status: Optional[str] = None,
    reason: Optional[str] = None,
) -> str:
    """
    Update an existing medication in the patient's medication list.

    IMPORTANT: Before calling this tool, you MUST first call get_medications() to retrieve
    the actual medication IDs from the database. Never guess or fabricate UUIDs.

    Use this to change dosage, frequency, status, or reason for a medication.
    For example: increase dosage, discontinue a medication, change frequency.

    Args:
        patient_id: The UUID of the patient.
        medication_id: The UUID of the medication to update (obtained from get_medications).
        dosage: New dosage amount (e.g., "1000mg").
        frequency: New frequency (e.g., "twice daily").
        status: New status. Options: active, on-hold, discontinued.
        reason: Updated reason for prescription.

    Returns:
        Confirmation message with the updated medication details.
    """
    logger.info(f"update_medication called: patient_id={patient_id}, medication_id={medication_id}")
    try:
        patient_uuid = UUID(patient_id)
        medication_uuid = UUID(medication_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    # Parse medication status if provided
    med_status = None
    if status:
        try:
            med_status = MedicationStatus(status.lower().replace("_", "-"))
        except ValueError:
            logger.warning(f"Invalid medication status: {status}")
            return f"Error: Invalid status '{status}'. Use: active, on-hold, discontinued"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify medication exists and belongs to patient
        medication = MedicationRepository.get_by_id(db, medication_uuid)
        if not medication:
            logger.warning(f"Medication not found: {medication_id}")
            return f"Error: Medication not found with ID: {medication_id}"
        if medication.patient_id != patient_uuid:
            logger.warning(f"Medication {medication_id} does not belong to patient {patient_id}")
            return f"Error: Medication does not belong to this patient"

        # Build update data
        update_data = MedicationUpdate(
            dosage=dosage,
            frequency=frequency,
            status=med_status,
            reason=reason,
        )

        # Update medication
        updated = MedicationRepository.update(db, medication_uuid, update_data)
        if not updated:
            return "Error: Failed to update medication"

        # Update RAG index
        retriever = get_retriever()
        retriever.remove_document("medication", medication_uuid)
        retriever.add_medication_document(
            patient_id=patient_uuid,
            medication_id=medication_uuid,
            content=updated.to_document(),
        )

        logger.info(f"Successfully updated medication: {updated.display_name}")
        return (
            f"Successfully updated medication: {updated.display_name}\n"
            f"- Dosage: {updated.dosage or 'Not specified'}\n"
            f"- Frequency: {updated.frequency or 'Not specified'}\n"
            f"- Status: {updated.status}\n"
            f"- Reason: {updated.reason or 'Not specified'}"
        )


@tool
def update_allergy(
    patient_id: str,
    allergy_id: str,
    criticality: Optional[str] = None,
    reaction: Optional[str] = None,
) -> str:
    """
    Update an existing allergy in the patient's allergy list.

    IMPORTANT: Before calling this tool, you MUST first call get_allergies() to retrieve
    the actual allergy IDs from the database. Never guess or fabricate UUIDs.

    Use this to change criticality level or reaction description.

    Args:
        patient_id: The UUID of the patient.
        allergy_id: The UUID of the allergy to update (obtained from get_allergies).
        criticality: New criticality level. Options: low, high.
        reaction: Updated reaction description.

    Returns:
        Confirmation message with the updated allergy details.
    """
    logger.info(f"update_allergy called: patient_id={patient_id}, allergy_id={allergy_id}")
    try:
        patient_uuid = UUID(patient_id)
        allergy_uuid = UUID(allergy_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    # Parse criticality if provided
    crit = None
    if criticality:
        try:
            crit = AllergyCriticality(criticality.lower())
        except ValueError:
            logger.warning(f"Invalid criticality: {criticality}")
            return f"Error: Invalid criticality '{criticality}'. Use: low, high"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify allergy exists and belongs to patient
        allergy = AllergyRepository.get_by_id(db, allergy_uuid)
        if not allergy:
            logger.warning(f"Allergy not found: {allergy_id}")
            return f"Error: Allergy not found with ID: {allergy_id}"
        if allergy.patient_id != patient_uuid:
            logger.warning(f"Allergy {allergy_id} does not belong to patient {patient_id}")
            return f"Error: Allergy does not belong to this patient"

        # Build update data
        update_data = AllergyUpdate(
            criticality=crit,
            reaction=reaction,
        )

        # Update allergy
        updated = AllergyRepository.update(db, allergy_uuid, update_data)
        if not updated:
            return "Error: Failed to update allergy"

        # Update RAG index
        retriever = get_retriever()
        retriever.remove_document("allergy", allergy_uuid)
        retriever.add_allergy_document(
            patient_id=patient_uuid,
            allergy_id=allergy_uuid,
            content=updated.to_document(),
        )

        logger.info(f"Successfully updated allergy: {updated.substance}")
        return (
            f"Successfully updated allergy: {updated.substance}\n"
            f"- Criticality: {updated.criticality or 'Not specified'}\n"
            f"- Reaction: {updated.reaction or 'Not specified'}"
        )


@tool
def update_vital_signs(
    patient_id: str,
    vital_signs_id: str,
    systolic_bp: Optional[int] = None,
    diastolic_bp: Optional[int] = None,
    heart_rate: Optional[int] = None,
    temperature: Optional[float] = None,
    weight_kg: Optional[float] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Update existing vital signs record.

    IMPORTANT: Before calling this tool, you MUST first call get_vital_signs() to retrieve
    the actual vital signs IDs from the database. Never guess or fabricate UUIDs.

    Use this to correct or update vital sign measurements.

    Args:
        patient_id: The UUID of the patient.
        vital_signs_id: The UUID of the vital signs record to update (obtained from get_vital_signs).
        systolic_bp: Corrected systolic blood pressure in mmHg.
        diastolic_bp: Corrected diastolic blood pressure in mmHg.
        heart_rate: Corrected heart rate in bpm.
        temperature: Corrected temperature in Celsius.
        weight_kg: Corrected weight in kilograms.
        notes: Updated notes.

    Returns:
        Confirmation message with the updated vital signs.
    """
    logger.info(f"update_vital_signs called: patient_id={patient_id}, vital_signs_id={vital_signs_id}")
    try:
        patient_uuid = UUID(patient_id)
        vital_signs_uuid = UUID(vital_signs_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify vital signs exists and belongs to patient
        vital_signs = VitalSignsRepository.get_by_id(db, vital_signs_uuid)
        if not vital_signs:
            logger.warning(f"Vital signs not found: {vital_signs_id}")
            return f"Error: Vital signs not found with ID: {vital_signs_id}"
        if vital_signs.patient_id != patient_uuid:
            logger.warning(f"Vital signs {vital_signs_id} does not belong to patient {patient_id}")
            return f"Error: Vital signs do not belong to this patient"

        # Build update data
        update_data = VitalSignsUpdate(
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            heart_rate=heart_rate,
            temperature=temperature,
            weight_kg=weight_kg,
            notes=notes,
        )

        # Update vital signs
        updated = VitalSignsRepository.update(db, vital_signs_uuid, update_data)
        if not updated:
            return "Error: Failed to update vital signs"

        # Update RAG index
        retriever = get_retriever()
        retriever.remove_document("vital_signs", vital_signs_uuid)
        retriever.add_document(
            patient_id=patient_uuid,
            doc_id=vital_signs_uuid,
            content=updated.to_document(),
            doc_type="vital_signs",
        )

        logger.info(f"Successfully updated vital signs for patient {patient_id}")
        lines = ["Successfully updated vital signs:"]
        if updated.systolic_bp and updated.diastolic_bp:
            lines.append(f"- Blood Pressure: {updated.systolic_bp}/{updated.diastolic_bp} mmHg")
        if updated.heart_rate:
            lines.append(f"- Heart Rate: {updated.heart_rate} bpm")
        if updated.temperature:
            lines.append(f"- Temperature: {updated.temperature}°C")
        if updated.weight_kg:
            lines.append(f"- Weight: {updated.weight_kg} kg")
        if updated.notes:
            lines.append(f"- Notes: {updated.notes}")
        return "\n".join(lines)


@tool
def update_lab_result(
    patient_id: str,
    lab_result_id: str,
    value: Optional[str] = None,
    value_numeric: Optional[float] = None,
    interpretation: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Update an existing lab result.

    IMPORTANT: Before calling this tool, you MUST first call get_lab_results() to retrieve
    the actual lab result IDs from the database. Never guess or fabricate UUIDs.

    Use this to correct values or update interpretation/notes.

    Args:
        patient_id: The UUID of the patient.
        lab_result_id: The UUID of the lab result to update (obtained from get_lab_results).
        value: Corrected result value.
        value_numeric: Corrected numeric value.
        interpretation: Updated interpretation. Options: normal, abnormal, critical.
        notes: Updated notes.

    Returns:
        Confirmation message with the updated lab result.
    """
    logger.info(f"update_lab_result called: patient_id={patient_id}, lab_result_id={lab_result_id}")
    try:
        patient_uuid = UUID(patient_id)
        lab_result_uuid = UUID(lab_result_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    # Parse interpretation if provided
    interp = None
    if interpretation:
        try:
            interp = LabInterpretation(interpretation.lower())
        except ValueError:
            logger.warning(f"Invalid interpretation: {interpretation}")
            return f"Error: Invalid interpretation '{interpretation}'. Use: normal, abnormal, critical"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify lab result exists and belongs to patient
        lab_result = LabResultRepository.get_by_id(db, lab_result_uuid)
        if not lab_result:
            logger.warning(f"Lab result not found: {lab_result_id}")
            return f"Error: Lab result not found with ID: {lab_result_id}"
        if lab_result.patient_id != patient_uuid:
            logger.warning(f"Lab result {lab_result_id} does not belong to patient {patient_id}")
            return f"Error: Lab result does not belong to this patient"

        # Build update data
        update_data = LabResultUpdate(
            value=value,
            value_numeric=value_numeric,
            interpretation=interp,
            notes=notes,
        )

        # Update lab result
        updated = LabResultRepository.update(db, lab_result_uuid, update_data)
        if not updated:
            return "Error: Failed to update lab result"

        # Update RAG index
        retriever = get_retriever()
        retriever.remove_document("lab_result", lab_result_uuid)
        retriever.add_document(
            patient_id=patient_uuid,
            doc_id=lab_result_uuid,
            content=updated.to_document(),
            doc_type="lab_result",
        )

        logger.info(f"Successfully updated lab result: {updated.test_name}")
        return (
            f"Successfully updated lab result: {updated.test_name}\n"
            f"- Value: {updated.value} {updated.unit or ''}\n"
            f"- Interpretation: {updated.interpretation or 'Not specified'}\n"
            f"- Notes: {updated.notes or 'None'}"
        )


@tool
def update_family_history(
    patient_id: str,
    family_history_id: str,
    condition_name: Optional[str] = None,
    onset_age: Optional[int] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Update an existing family history entry.

    IMPORTANT: Before calling this tool, you MUST first call get_family_history() to retrieve
    the actual family history IDs from the database. Never guess or fabricate UUIDs.

    Use this to correct or update family medical history details.

    Args:
        patient_id: The UUID of the patient.
        family_history_id: The UUID of the family history entry to update (obtained from get_family_history).
        condition_name: Corrected condition name.
        onset_age: Corrected age of onset.
        notes: Updated notes.

    Returns:
        Confirmation message with the updated family history.
    """
    logger.info(f"update_family_history called: patient_id={patient_id}, family_history_id={family_history_id}")
    try:
        patient_uuid = UUID(patient_id)
        family_history_uuid = UUID(family_history_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify family history exists and belongs to patient
        family_history = FamilyHistoryRepository.get_by_id(db, family_history_uuid)
        if not family_history:
            logger.warning(f"Family history not found: {family_history_id}")
            return f"Error: Family history not found with ID: {family_history_id}"
        if family_history.patient_id != patient_uuid:
            logger.warning(f"Family history {family_history_id} does not belong to patient {patient_id}")
            return f"Error: Family history does not belong to this patient"

        # Build update data
        update_data = FamilyHistoryUpdate(
            condition_name=condition_name,
            onset_age=onset_age,
            notes=notes,
        )

        # Update family history
        updated = FamilyHistoryRepository.update(db, family_history_uuid, update_data)
        if not updated:
            return "Error: Failed to update family history"

        # Update RAG index
        retriever = get_retriever()
        retriever.remove_document("family_history", family_history_uuid)
        retriever.add_document(
            patient_id=patient_uuid,
            doc_id=family_history_uuid,
            content=updated.to_document(),
            doc_type="family_history",
        )

        logger.info(f"Successfully updated family history for patient {patient_id}")
        age_str = f" (diagnosed at age {updated.onset_age})" if updated.onset_age else ""
        return (
            f"Successfully updated family history:\n"
            f"- Relationship: {updated.relation}\n"
            f"- Condition: {updated.condition_name}{age_str}\n"
            f"- Notes: {updated.notes or 'None'}"
        )


@tool
def update_social_history(
    patient_id: str,
    social_history_id: str,
    status: Optional[str] = None,
    description: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Update an existing social history entry.

    IMPORTANT: Before calling this tool, you MUST first call get_social_history() to retrieve
    the actual social history IDs from the database. Never guess or fabricate UUIDs.

    Use this to change status or update description/notes.
    For example: change smoking status from 'current' to 'former'.

    Args:
        patient_id: The UUID of the patient.
        social_history_id: The UUID of the social history entry to update (obtained from get_social_history).
        status: New status. Options: current, former, never, occasional, daily, unknown.
        description: Updated description.
        notes: Updated notes.

    Returns:
        Confirmation message with the updated social history.
    """
    logger.info(f"update_social_history called: patient_id={patient_id}, social_history_id={social_history_id}")
    try:
        patient_uuid = UUID(patient_id)
        social_history_uuid = UUID(social_history_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    # Parse status if provided
    stat = None
    if status:
        try:
            stat = SocialHistoryStatus(status.lower())
        except ValueError:
            logger.warning(f"Invalid status: {status}")
            valid = ", ".join([s.value for s in SocialHistoryStatus])
            return f"Error: Invalid status '{status}'. Use: {valid}"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify social history exists and belongs to patient
        social_history = SocialHistoryRepository.get_by_id(db, social_history_uuid)
        if not social_history:
            logger.warning(f"Social history not found: {social_history_id}")
            return f"Error: Social history not found with ID: {social_history_id}"
        if social_history.patient_id != patient_uuid:
            logger.warning(f"Social history {social_history_id} does not belong to patient {patient_id}")
            return f"Error: Social history does not belong to this patient"

        # Build update data
        update_data = SocialHistoryUpdate(
            status=stat,
            description=description,
            notes=notes,
        )

        # Update social history
        updated = SocialHistoryRepository.update(db, social_history_uuid, update_data)
        if not updated:
            return "Error: Failed to update social history"

        # Update RAG index
        retriever = get_retriever()
        retriever.remove_document("social_history", social_history_uuid)
        retriever.add_document(
            patient_id=patient_uuid,
            doc_id=social_history_uuid,
            content=updated.to_document(),
            doc_type="social_history",
        )

        logger.info(f"Successfully updated social history for patient {patient_id}")
        return (
            f"Successfully updated social history:\n"
            f"- Category: {updated.category}\n"
            f"- Status: {updated.status}\n"
            f"- Description: {updated.description or 'Not specified'}\n"
            f"- Notes: {updated.notes or 'None'}"
        )


# ============================================================================
# DELETE TOOLS - Remove records
# ============================================================================


@tool
def delete_condition(patient_id: str, condition_id: str) -> str:
    """
    Delete a condition from the patient's problem list.

    IMPORTANT: Before calling this tool, you MUST first call get_conditions() to retrieve
    the actual condition IDs from the database. Never guess or fabricate UUIDs.

    Use this to remove a condition that was added in error or is no longer relevant.
    This permanently removes the condition from the patient's record.

    Args:
        patient_id: The UUID of the patient.
        condition_id: The UUID of the condition to delete (obtained from get_conditions).

    Returns:
        Confirmation message.
    """
    logger.info(f"delete_condition called: patient_id={patient_id}, condition_id={condition_id}")
    try:
        patient_uuid = UUID(patient_id)
        condition_uuid = UUID(condition_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify condition exists and belongs to patient
        condition = ConditionRepository.get_by_id(db, condition_uuid)
        if not condition:
            logger.warning(f"Condition not found: {condition_id}")
            return f"Error: Condition not found with ID: {condition_id}"
        if condition.patient_id != patient_uuid:
            logger.warning(f"Condition {condition_id} does not belong to patient {patient_id}")
            return f"Error: Condition does not belong to this patient"

        condition_name = condition.display_name

        # Delete from database
        if not ConditionRepository.delete(db, condition_uuid):
            return "Error: Failed to delete condition"

        # Remove from RAG index
        retriever = get_retriever()
        retriever.remove_document("condition", condition_uuid)

        logger.info(f"Successfully deleted condition: {condition_name}")
        return f"Successfully deleted condition: {condition_name}"


@tool
def delete_medication(patient_id: str, medication_id: str) -> str:
    """
    Delete a medication from the patient's medication list.

    IMPORTANT: Before calling this tool, you MUST first call get_medications() to retrieve
    the actual medication IDs from the database. Never guess or fabricate UUIDs.

    Use this to remove a medication that was added in error.
    Consider using update_medication to set status to 'discontinued' instead.

    Args:
        patient_id: The UUID of the patient.
        medication_id: The UUID of the medication to delete (obtained from get_medications).

    Returns:
        Confirmation message.
    """
    logger.info(f"delete_medication called: patient_id={patient_id}, medication_id={medication_id}")
    try:
        patient_uuid = UUID(patient_id)
        medication_uuid = UUID(medication_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify medication exists and belongs to patient
        medication = MedicationRepository.get_by_id(db, medication_uuid)
        if not medication:
            logger.warning(f"Medication not found: {medication_id}")
            return f"Error: Medication not found with ID: {medication_id}"
        if medication.patient_id != patient_uuid:
            logger.warning(f"Medication {medication_id} does not belong to patient {patient_id}")
            return f"Error: Medication does not belong to this patient"

        medication_name = medication.display_name

        # Delete from database
        if not MedicationRepository.delete(db, medication_uuid):
            return "Error: Failed to delete medication"

        # Remove from RAG index
        retriever = get_retriever()
        retriever.remove_document("medication", medication_uuid)

        logger.info(f"Successfully deleted medication: {medication_name}")
        return f"Successfully deleted medication: {medication_name}"


@tool
def delete_allergy(patient_id: str, allergy_id: str) -> str:
    """
    Delete an allergy from the patient's allergy list.

    IMPORTANT: Before calling this tool, you MUST first call get_allergies() to retrieve
    the actual allergy IDs from the database. Never guess or fabricate UUIDs.

    CAUTION: Only delete allergies that were added in error.
    Allergies are critical safety information.

    Args:
        patient_id: The UUID of the patient.
        allergy_id: The UUID of the allergy to delete (obtained from get_allergies).

    Returns:
        Confirmation message.
    """
    logger.info(f"delete_allergy called: patient_id={patient_id}, allergy_id={allergy_id}")
    try:
        patient_uuid = UUID(patient_id)
        allergy_uuid = UUID(allergy_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify allergy exists and belongs to patient
        allergy = AllergyRepository.get_by_id(db, allergy_uuid)
        if not allergy:
            logger.warning(f"Allergy not found: {allergy_id}")
            return f"Error: Allergy not found with ID: {allergy_id}"
        if allergy.patient_id != patient_uuid:
            logger.warning(f"Allergy {allergy_id} does not belong to patient {patient_id}")
            return f"Error: Allergy does not belong to this patient"

        allergy_substance = allergy.substance

        # Delete from database
        if not AllergyRepository.delete(db, allergy_uuid):
            return "Error: Failed to delete allergy"

        # Remove from RAG index
        retriever = get_retriever()
        retriever.remove_document("allergy", allergy_uuid)

        logger.info(f"Successfully deleted allergy: {allergy_substance}")
        return f"Successfully deleted allergy: {allergy_substance}"


@tool
def delete_vital_signs(patient_id: str, vital_signs_id: str) -> str:
    """
    Delete a vital signs record.

    IMPORTANT: Before calling this tool, you MUST first call get_vital_signs() to retrieve
    the actual vital signs IDs from the database. Never guess or fabricate UUIDs.

    Use this to remove a vital signs entry that was added in error.

    Args:
        patient_id: The UUID of the patient.
        vital_signs_id: The UUID of the vital signs record to delete (obtained from get_vital_signs).

    Returns:
        Confirmation message.
    """
    logger.info(f"delete_vital_signs called: patient_id={patient_id}, vital_signs_id={vital_signs_id}")
    try:
        patient_uuid = UUID(patient_id)
        vital_signs_uuid = UUID(vital_signs_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify vital signs exists and belongs to patient
        vital_signs = VitalSignsRepository.get_by_id(db, vital_signs_uuid)
        if not vital_signs:
            logger.warning(f"Vital signs not found: {vital_signs_id}")
            return f"Error: Vital signs not found with ID: {vital_signs_id}"
        if vital_signs.patient_id != patient_uuid:
            logger.warning(f"Vital signs {vital_signs_id} does not belong to patient {patient_id}")
            return f"Error: Vital signs do not belong to this patient"

        recorded_at = vital_signs.recorded_at.strftime('%Y-%m-%d %H:%M')

        # Delete from database
        if not VitalSignsRepository.delete(db, vital_signs_uuid):
            return "Error: Failed to delete vital signs"

        # Remove from RAG index
        retriever = get_retriever()
        retriever.remove_document("vital_signs", vital_signs_uuid)

        logger.info(f"Successfully deleted vital signs from {recorded_at}")
        return f"Successfully deleted vital signs recorded at {recorded_at}"


@tool
def delete_lab_result(patient_id: str, lab_result_id: str) -> str:
    """
    Delete a lab result.

    IMPORTANT: Before calling this tool, you MUST first call get_lab_results() to retrieve
    the actual lab result IDs from the database. Never guess or fabricate UUIDs.

    Use this to remove a lab result that was added in error.

    Args:
        patient_id: The UUID of the patient.
        lab_result_id: The UUID of the lab result to delete (obtained from get_lab_results).

    Returns:
        Confirmation message.
    """
    logger.info(f"delete_lab_result called: patient_id={patient_id}, lab_result_id={lab_result_id}")
    try:
        patient_uuid = UUID(patient_id)
        lab_result_uuid = UUID(lab_result_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify lab result exists and belongs to patient
        lab_result = LabResultRepository.get_by_id(db, lab_result_uuid)
        if not lab_result:
            logger.warning(f"Lab result not found: {lab_result_id}")
            return f"Error: Lab result not found with ID: {lab_result_id}"
        if lab_result.patient_id != patient_uuid:
            logger.warning(f"Lab result {lab_result_id} does not belong to patient {patient_id}")
            return f"Error: Lab result does not belong to this patient"

        test_name = lab_result.test_name
        result_date = lab_result.result_date.strftime('%Y-%m-%d')

        # Delete from database
        if not LabResultRepository.delete(db, lab_result_uuid):
            return "Error: Failed to delete lab result"

        # Remove from RAG index
        retriever = get_retriever()
        retriever.remove_document("lab_result", lab_result_uuid)

        logger.info(f"Successfully deleted lab result: {test_name}")
        return f"Successfully deleted lab result: {test_name} from {result_date}"


@tool
def delete_family_history(patient_id: str, family_history_id: str) -> str:
    """
    Delete a family history entry.

    IMPORTANT: Before calling this tool, you MUST first call get_family_history() to retrieve
    the actual family history IDs from the database. Never guess or fabricate UUIDs.

    Use this to remove a family history entry that was added in error.

    Args:
        patient_id: The UUID of the patient.
        family_history_id: The UUID of the family history entry to delete (obtained from get_family_history).

    Returns:
        Confirmation message.
    """
    logger.info(f"delete_family_history called: patient_id={patient_id}, family_history_id={family_history_id}")
    try:
        patient_uuid = UUID(patient_id)
        family_history_uuid = UUID(family_history_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify family history exists and belongs to patient
        family_history = FamilyHistoryRepository.get_by_id(db, family_history_uuid)
        if not family_history:
            logger.warning(f"Family history not found: {family_history_id}")
            return f"Error: Family history not found with ID: {family_history_id}"
        if family_history.patient_id != patient_uuid:
            logger.warning(f"Family history {family_history_id} does not belong to patient {patient_id}")
            return f"Error: Family history does not belong to this patient"

        relation = family_history.relation
        condition = family_history.condition_name

        # Delete from database
        if not FamilyHistoryRepository.delete(db, family_history_uuid):
            return "Error: Failed to delete family history"

        # Remove from RAG index
        retriever = get_retriever()
        retriever.remove_document("family_history", family_history_uuid)

        logger.info(f"Successfully deleted family history: {relation} - {condition}")
        return f"Successfully deleted family history: {relation} with {condition}"


@tool
def delete_social_history(patient_id: str, social_history_id: str) -> str:
    """
    Delete a social history entry.

    IMPORTANT: Before calling this tool, you MUST first call get_social_history() to retrieve
    the actual social history IDs from the database. Never guess or fabricate UUIDs.

    Use this to remove a social history entry that was added in error.

    Args:
        patient_id: The UUID of the patient.
        social_history_id: The UUID of the social history entry to delete (obtained from get_social_history).

    Returns:
        Confirmation message.
    """
    logger.info(f"delete_social_history called: patient_id={patient_id}, social_history_id={social_history_id}")
    try:
        patient_uuid = UUID(patient_id)
        social_history_uuid = UUID(social_history_id)
    except ValueError as e:
        logger.warning(f"Invalid UUID format: {e}")
        return f"Error: Invalid UUID format"

    with get_db() as db:
        # Verify patient exists
        patient = PatientRepository.get_by_id(db, patient_uuid)
        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            return f"Error: Patient not found with ID: {patient_id}"

        # Verify social history exists and belongs to patient
        social_history = SocialHistoryRepository.get_by_id(db, social_history_uuid)
        if not social_history:
            logger.warning(f"Social history not found: {social_history_id}")
            return f"Error: Social history not found with ID: {social_history_id}"
        if social_history.patient_id != patient_uuid:
            logger.warning(f"Social history {social_history_id} does not belong to patient {patient_id}")
            return f"Error: Social history does not belong to this patient"

        category = social_history.category

        # Delete from database
        if not SocialHistoryRepository.delete(db, social_history_uuid):
            return "Error: Failed to delete social history"

        # Remove from RAG index
        retriever = get_retriever()
        retriever.remove_document("social_history", social_history_uuid)

        logger.info(f"Successfully deleted social history: {category}")
        return f"Successfully deleted social history: {category}"


# List of all tools for easy import
PATIENT_DATA_TOOLS = [
    get_patient_profile,
    search_patient_data,
    # Getter tools for specific data types (deterministic results)
    get_conditions,
    get_medications,
    get_allergies,
    get_vital_signs,
    get_lab_results,
    get_family_history,
    get_social_history,
    # Write tools for adding new data
    add_condition,
    add_medication,
    add_allergy,
    add_vital_signs,
    add_lab_result,
    add_family_history,
    add_social_history,
    # Update tools for modifying existing data
    update_condition,
    update_medication,
    update_allergy,
    update_vital_signs,
    update_lab_result,
    update_family_history,
    update_social_history,
    # Delete tools for removing data
    delete_condition,
    delete_medication,
    delete_allergy,
    delete_vital_signs,
    delete_lab_result,
    delete_family_history,
    delete_social_history,
]

# Read-only tools for Health Coach (no write operations)
HEALTH_COACH_TOOLS = [
    get_patient_profile,
    search_patient_data,
    # Getter tools for specific data types (deterministic results)
    get_conditions,
    get_medications,
    get_allergies,
    get_vital_signs,
    get_lab_results,
    get_family_history,
    get_social_history,
    # Clinical history search for cross-mode context
    search_clinical_history,
]
