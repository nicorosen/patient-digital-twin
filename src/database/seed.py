"""
Seed database with synthetic patient data.

Creates 3 test patients with realistic clinical data:
1. Maria Garcia (45F) - Type 2 Diabetes, Hypertension
2. James Thompson (62M) - CAD, Hyperlipidemia, Penicillin allergy
3. Sarah Chen (28F) - Asthma, Anxiety, Shellfish allergy

Usage:
    python -m src.database.seed
"""

from datetime import date

from src.database.connection import create_tables, get_db
from src.database.repositories import (
    AllergyRepository,
    ConditionRepository,
    MedicationRepository,
    PatientRepository,
)
from src.schemas import (
    AllergyCategory,
    AllergyCriticality,
    AllergyCreate,
    ClinicalStatus,
    ConditionCreate,
    Gender,
    MedicationCreate,
    MedicationStatus,
    PatientCreate,
    Severity,
)


def seed_maria_garcia(db) -> None:
    """Create Maria Garcia - 45F with metabolic conditions."""
    print("Creating Maria Garcia...")

    # Create patient
    patient = PatientRepository.create(
        db,
        PatientCreate(
            first_name="Maria",
            last_name="Garcia",
            date_of_birth=date(1981, 3, 15),
            gender=Gender.FEMALE,
        ),
    )
    patient_id = patient.id

    # Add conditions
    ConditionRepository.create(
        db,
        ConditionCreate(
            patient_id=patient_id,
            code="E11.9",  # ICD-10
            display_name="Type 2 Diabetes Mellitus",
            clinical_status=ClinicalStatus.ACTIVE,
            onset_date=date(2019, 6, 1),
            severity=Severity.MODERATE,
            notes="Well-controlled with medication. Last HbA1c: 6.8%",
        ),
    )
    ConditionRepository.create(
        db,
        ConditionCreate(
            patient_id=patient_id,
            code="I10",  # ICD-10
            display_name="Essential Hypertension",
            clinical_status=ClinicalStatus.ACTIVE,
            onset_date=date(2020, 2, 15),
            severity=Severity.MILD,
            notes="Blood pressure typically 130/85 on medication",
        ),
    )

    # Add medications
    MedicationRepository.create(
        db,
        MedicationCreate(
            patient_id=patient_id,
            code="860975",  # RxNorm
            display_name="Metformin",
            dosage="500mg",
            frequency="twice daily",
            route="oral",
            status=MedicationStatus.ACTIVE,
            start_date=date(2019, 6, 15),
            reason="Type 2 Diabetes management",
        ),
    )
    MedicationRepository.create(
        db,
        MedicationCreate(
            patient_id=patient_id,
            code="314076",  # RxNorm
            display_name="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            route="oral",
            status=MedicationStatus.ACTIVE,
            start_date=date(2020, 3, 1),
            reason="Blood pressure control",
        ),
    )

    print(f"  Created patient: {patient.full_name} (ID: {patient.id})")


def seed_james_thompson(db) -> None:
    """Create James Thompson - 62M with cardiac conditions and allergy."""
    print("Creating James Thompson...")

    # Create patient
    patient = PatientRepository.create(
        db,
        PatientCreate(
            first_name="James",
            last_name="Thompson",
            date_of_birth=date(1963, 8, 22),
            gender=Gender.MALE,
        ),
    )
    patient_id = patient.id

    # Add conditions
    ConditionRepository.create(
        db,
        ConditionCreate(
            patient_id=patient_id,
            code="I25.10",  # ICD-10
            display_name="Coronary Artery Disease",
            clinical_status=ClinicalStatus.ACTIVE,
            onset_date=date(2018, 11, 5),
            severity=Severity.MODERATE,
            notes="History of stent placement in 2018. Regular cardiology follow-up.",
        ),
    )
    ConditionRepository.create(
        db,
        ConditionCreate(
            patient_id=patient_id,
            code="E78.5",  # ICD-10
            display_name="Hyperlipidemia",
            clinical_status=ClinicalStatus.ACTIVE,
            onset_date=date(2015, 3, 10),
            severity=Severity.MILD,
            notes="LDL well-controlled on statin therapy",
        ),
    )

    # Add medications
    MedicationRepository.create(
        db,
        MedicationCreate(
            patient_id=patient_id,
            code="243670",  # RxNorm
            display_name="Aspirin",
            dosage="81mg",
            frequency="once daily",
            route="oral",
            status=MedicationStatus.ACTIVE,
            start_date=date(2018, 11, 10),
            reason="Cardiovascular protection",
        ),
    )
    MedicationRepository.create(
        db,
        MedicationCreate(
            patient_id=patient_id,
            code="617312",  # RxNorm
            display_name="Atorvastatin",
            dosage="40mg",
            frequency="once daily at bedtime",
            route="oral",
            status=MedicationStatus.ACTIVE,
            start_date=date(2015, 4, 1),
            reason="Cholesterol management",
        ),
    )

    # Add allergy
    AllergyRepository.create(
        db,
        AllergyCreate(
            patient_id=patient_id,
            code="70618",  # RxNorm for Penicillin
            substance="Penicillin",
            category=AllergyCategory.MEDICATION,
            criticality=AllergyCriticality.HIGH,
            reaction="Anaphylaxis - throat swelling, difficulty breathing",
            onset_date=date(1985, 7, 20),
        ),
    )

    print(f"  Created patient: {patient.full_name} (ID: {patient.id})")


def seed_sarah_chen(db) -> None:
    """Create Sarah Chen - 28F with respiratory and mental health conditions."""
    print("Creating Sarah Chen...")

    # Create patient
    patient = PatientRepository.create(
        db,
        PatientCreate(
            first_name="Sarah",
            last_name="Chen",
            date_of_birth=date(1997, 12, 3),
            gender=Gender.FEMALE,
        ),
    )
    patient_id = patient.id

    # Add conditions
    ConditionRepository.create(
        db,
        ConditionCreate(
            patient_id=patient_id,
            code="J45.20",  # ICD-10
            display_name="Mild Persistent Asthma",
            clinical_status=ClinicalStatus.ACTIVE,
            onset_date=date(2010, 5, 1),
            severity=Severity.MILD,
            notes="Exercise-induced symptoms. Uses rescue inhaler 2-3x/month.",
        ),
    )
    ConditionRepository.create(
        db,
        ConditionCreate(
            patient_id=patient_id,
            code="F41.1",  # ICD-10
            display_name="Generalized Anxiety Disorder",
            clinical_status=ClinicalStatus.ACTIVE,
            onset_date=date(2020, 3, 15),
            severity=Severity.MODERATE,
            notes="Onset during pandemic. Responding well to SSRI therapy.",
        ),
    )

    # Add medications
    MedicationRepository.create(
        db,
        MedicationCreate(
            patient_id=patient_id,
            code="435",  # RxNorm
            display_name="Albuterol Inhaler",
            dosage="90mcg",
            frequency="as needed for breathing difficulty",
            route="inhalation",
            status=MedicationStatus.ACTIVE,
            start_date=date(2010, 5, 15),
            reason="Asthma rescue medication",
        ),
    )
    MedicationRepository.create(
        db,
        MedicationCreate(
            patient_id=patient_id,
            code="36437",  # RxNorm
            display_name="Sertraline",
            dosage="50mg",
            frequency="once daily in the morning",
            route="oral",
            status=MedicationStatus.ACTIVE,
            start_date=date(2020, 4, 1),
            reason="Anxiety management",
        ),
    )

    # Add allergy
    AllergyRepository.create(
        db,
        AllergyCreate(
            patient_id=patient_id,
            substance="Shellfish",
            category=AllergyCategory.FOOD,
            criticality=AllergyCriticality.LOW,
            reaction="Hives and mild stomach upset",
            onset_date=date(2015, 8, 10),
        ),
    )

    print(f"  Created patient: {patient.full_name} (ID: {patient.id})")


def seed_database() -> None:
    """Seed the database with all synthetic patients."""
    print("\n" + "=" * 60)
    print("Seeding Patient Digital Twin Database")
    print("=" * 60 + "\n")

    # Create tables
    print("Creating database tables...")
    create_tables()
    print("Tables created.\n")

    # Seed patients
    with get_db() as db:
        # Check if data already exists
        existing = PatientRepository.get_all(db)
        if existing:
            print(f"Database already has {len(existing)} patients.")
            print("To reset, run: python -m src.database.reset\n")
            return

        seed_maria_garcia(db)
        seed_james_thompson(db)
        seed_sarah_chen(db)

        # Auto-index all patients for RAG search
        print("\nIndexing patients for RAG search...")
        from src.rag import get_retriever

        retriever = get_retriever()
        patients = PatientRepository.get_all(db)
        total_docs = 0
        for patient in patients:
            count = retriever.index_patient(db, patient.id)
            total_docs += count
        print(f"Indexed {total_docs} documents for {len(patients)} patients.")

        print("\n" + "-" * 60)
        print("Database seeded and indexed successfully!")
        print("-" * 60)

        # Print summary
        patients = PatientRepository.get_all(db)
        print(f"\nCreated {len(patients)} patients:")
        for p in patients:
            conditions = len(p.conditions)
            medications = len(p.medications)
            allergies = len(p.allergies)
            print(
                f"  - {p.full_name} ({p.age}y {p.gender}): "
                f"{conditions} conditions, {medications} medications, {allergies} allergies"
            )
        print()


if __name__ == "__main__":
    seed_database()
