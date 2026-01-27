"""
Seed database with synthetic patient data.

Creates 3 test patients with realistic clinical data:
1. Maria Garcia (45F) - Type 2 Diabetes, Hypertension
2. James Thompson (62M) - CAD, Hyperlipidemia, Penicillin allergy
3. Sarah Chen (28F) - Asthma, Anxiety, Shellfish allergy

Usage:
    python -m src.database.seed
"""

from datetime import date, datetime, timedelta

from src.database.connection import create_tables, get_db
from src.database.repositories import (
    AllergyRepository,
    ConditionRepository,
    FamilyHistoryRepository,
    LabResultRepository,
    MedicationRepository,
    PatientMemberRepository,
    PatientRepository,
    SocialHistoryRepository,
    UserRepository,
    VitalSignsRepository,
)
from src.schemas import (
    AllergyCategory,
    AllergyCriticality,
    AllergyCreate,
    ClinicalStatus,
    ConditionCreate,
    FamilyHistoryCreate,
    FamilyRelationship,
    Gender,
    LabInterpretation,
    LabResultCreate,
    MedicationCreate,
    MedicationStatus,
    MemberRole,
    PatientCreate,
    PatientMemberCreate,
    Severity,
    SocialHistoryCategory,
    SocialHistoryCreate,
    SocialHistoryStatus,
    UserCreate,
    VitalSignsCreate,
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

    # Add vital signs
    VitalSignsRepository.create(
        db,
        VitalSignsCreate(
            patient_id=patient_id,
            recorded_at=datetime.now() - timedelta(days=7),
            systolic_bp=128,
            diastolic_bp=82,
            heart_rate=76,
            temperature=36.8,
            weight_kg=68.5,
            height_cm=162,
            oxygen_saturation=98,
            notes="Routine check-up",
        ),
    )
    VitalSignsRepository.create(
        db,
        VitalSignsCreate(
            patient_id=patient_id,
            recorded_at=datetime.now() - timedelta(days=90),
            systolic_bp=135,
            diastolic_bp=88,
            heart_rate=80,
            weight_kg=70.2,
            height_cm=162,
            oxygen_saturation=97,
        ),
    )

    # Add lab results
    LabResultRepository.create(
        db,
        LabResultCreate(
            patient_id=patient_id,
            test_name="HbA1c",
            test_code="4548-4",
            value="6.8",
            value_numeric=6.8,
            unit="%",
            reference_range_low=4.0,
            reference_range_high=5.6,
            interpretation=LabInterpretation.ABNORMAL,
            result_date=datetime.now() - timedelta(days=30),
            notes="Slightly elevated, continue current management",
        ),
    )
    LabResultRepository.create(
        db,
        LabResultCreate(
            patient_id=patient_id,
            test_name="Fasting Blood Glucose",
            test_code="1558-6",
            value="118",
            value_numeric=118,
            unit="mg/dL",
            reference_range_low=70,
            reference_range_high=100,
            interpretation=LabInterpretation.ABNORMAL,
            result_date=datetime.now() - timedelta(days=30),
        ),
    )
    LabResultRepository.create(
        db,
        LabResultCreate(
            patient_id=patient_id,
            test_name="Total Cholesterol",
            test_code="2093-3",
            value="195",
            value_numeric=195,
            unit="mg/dL",
            reference_range_low=0,
            reference_range_high=200,
            interpretation=LabInterpretation.NORMAL,
            result_date=datetime.now() - timedelta(days=30),
        ),
    )

    # Add family history
    FamilyHistoryRepository.create(
        db,
        FamilyHistoryCreate(
            patient_id=patient_id,
            relation=FamilyRelationship.FATHER,
            condition_name="Type 2 Diabetes",
            onset_age=55,
            notes="Managed with diet and oral medications",
        ),
    )
    FamilyHistoryRepository.create(
        db,
        FamilyHistoryCreate(
            patient_id=patient_id,
            relation=FamilyRelationship.MOTHER,
            condition_name="Hypertension",
            onset_age=50,
        ),
    )

    # Add social history
    SocialHistoryRepository.create(
        db,
        SocialHistoryCreate(
            patient_id=patient_id,
            category=SocialHistoryCategory.SMOKING,
            status=SocialHistoryStatus.NEVER,
            description="Never smoked",
        ),
    )
    SocialHistoryRepository.create(
        db,
        SocialHistoryCreate(
            patient_id=patient_id,
            category=SocialHistoryCategory.ALCOHOL,
            status=SocialHistoryStatus.OCCASIONAL,
            description="Social drinker, 1-2 glasses of wine per week",
        ),
    )
    SocialHistoryRepository.create(
        db,
        SocialHistoryCreate(
            patient_id=patient_id,
            category=SocialHistoryCategory.EXERCISE,
            status=SocialHistoryStatus.CURRENT,
            description="Walks 30 minutes daily, yoga twice weekly",
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

    # Add vital signs
    VitalSignsRepository.create(
        db,
        VitalSignsCreate(
            patient_id=patient_id,
            recorded_at=datetime.now() - timedelta(days=14),
            systolic_bp=142,
            diastolic_bp=88,
            heart_rate=68,
            temperature=36.6,
            weight_kg=82.3,
            height_cm=178,
            oxygen_saturation=96,
            notes="Follow-up for cardiac monitoring",
        ),
    )

    # Add lab results
    LabResultRepository.create(
        db,
        LabResultCreate(
            patient_id=patient_id,
            test_name="LDL Cholesterol",
            test_code="2089-1",
            value="78",
            value_numeric=78,
            unit="mg/dL",
            reference_range_low=0,
            reference_range_high=100,
            interpretation=LabInterpretation.NORMAL,
            result_date=datetime.now() - timedelta(days=60),
            notes="Well controlled on statin therapy",
        ),
    )
    LabResultRepository.create(
        db,
        LabResultCreate(
            patient_id=patient_id,
            test_name="HDL Cholesterol",
            test_code="2085-9",
            value="52",
            value_numeric=52,
            unit="mg/dL",
            reference_range_low=40,
            reference_range_high=60,
            interpretation=LabInterpretation.NORMAL,
            result_date=datetime.now() - timedelta(days=60),
        ),
    )
    LabResultRepository.create(
        db,
        LabResultCreate(
            patient_id=patient_id,
            test_name="Triglycerides",
            test_code="2571-8",
            value="145",
            value_numeric=145,
            unit="mg/dL",
            reference_range_low=0,
            reference_range_high=150,
            interpretation=LabInterpretation.NORMAL,
            result_date=datetime.now() - timedelta(days=60),
        ),
    )

    # Add family history
    FamilyHistoryRepository.create(
        db,
        FamilyHistoryCreate(
            patient_id=patient_id,
            relation=FamilyRelationship.FATHER,
            condition_name="Myocardial Infarction",
            onset_age=58,
            notes="Fatal heart attack",
        ),
    )
    FamilyHistoryRepository.create(
        db,
        FamilyHistoryCreate(
            patient_id=patient_id,
            relation=FamilyRelationship.SIBLING,
            condition_name="Coronary Artery Disease",
            onset_age=55,
            notes="Brother had bypass surgery",
        ),
    )

    # Add social history
    SocialHistoryRepository.create(
        db,
        SocialHistoryCreate(
            patient_id=patient_id,
            category=SocialHistoryCategory.SMOKING,
            status=SocialHistoryStatus.FORMER,
            description="Quit 15 years ago, previously 1 pack/day for 20 years",
        ),
    )
    SocialHistoryRepository.create(
        db,
        SocialHistoryCreate(
            patient_id=patient_id,
            category=SocialHistoryCategory.ALCOHOL,
            status=SocialHistoryStatus.NEVER,
            description="Non-drinker",
        ),
    )
    SocialHistoryRepository.create(
        db,
        SocialHistoryCreate(
            patient_id=patient_id,
            category=SocialHistoryCategory.EXERCISE,
            status=SocialHistoryStatus.CURRENT,
            description="Cardiac rehab program, walking 45 min 5x/week",
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

    # Add vital signs
    VitalSignsRepository.create(
        db,
        VitalSignsCreate(
            patient_id=patient_id,
            recorded_at=datetime.now() - timedelta(days=3),
            systolic_bp=112,
            diastolic_bp=72,
            heart_rate=74,
            temperature=36.5,
            weight_kg=58.2,
            height_cm=165,
            oxygen_saturation=99,
        ),
    )

    # Add lab results (anxiety-related)
    LabResultRepository.create(
        db,
        LabResultCreate(
            patient_id=patient_id,
            test_name="TSH",
            test_code="3016-3",
            value="2.1",
            value_numeric=2.1,
            unit="mIU/L",
            reference_range_low=0.4,
            reference_range_high=4.0,
            interpretation=LabInterpretation.NORMAL,
            result_date=datetime.now() - timedelta(days=45),
            notes="Thyroid function normal, not contributing to anxiety",
        ),
    )
    LabResultRepository.create(
        db,
        LabResultCreate(
            patient_id=patient_id,
            test_name="Vitamin D",
            test_code="1989-3",
            value="28",
            value_numeric=28,
            unit="ng/mL",
            reference_range_low=30,
            reference_range_high=100,
            interpretation=LabInterpretation.ABNORMAL,
            result_date=datetime.now() - timedelta(days=45),
            notes="Slightly low, recommend supplementation",
        ),
    )

    # Add family history
    FamilyHistoryRepository.create(
        db,
        FamilyHistoryCreate(
            patient_id=patient_id,
            relation=FamilyRelationship.MOTHER,
            condition_name="Generalized Anxiety Disorder",
            onset_age=35,
        ),
    )
    FamilyHistoryRepository.create(
        db,
        FamilyHistoryCreate(
            patient_id=patient_id,
            relation=FamilyRelationship.MATERNAL_GRANDMOTHER,
            condition_name="Asthma",
            onset_age=40,
        ),
    )

    # Add social history
    SocialHistoryRepository.create(
        db,
        SocialHistoryCreate(
            patient_id=patient_id,
            category=SocialHistoryCategory.SMOKING,
            status=SocialHistoryStatus.NEVER,
        ),
    )
    SocialHistoryRepository.create(
        db,
        SocialHistoryCreate(
            patient_id=patient_id,
            category=SocialHistoryCategory.ALCOHOL,
            status=SocialHistoryStatus.OCCASIONAL,
            description="Occasional social drinking",
        ),
    )
    SocialHistoryRepository.create(
        db,
        SocialHistoryCreate(
            patient_id=patient_id,
            category=SocialHistoryCategory.EXERCISE,
            status=SocialHistoryStatus.CURRENT,
            description="Running 3x/week, yoga for anxiety management",
        ),
    )
    SocialHistoryRepository.create(
        db,
        SocialHistoryCreate(
            patient_id=patient_id,
            category=SocialHistoryCategory.STRESS,
            status=SocialHistoryStatus.CURRENT,
            description="High-stress job in tech industry",
            notes="Working on stress management techniques with therapist",
        ),
    )

    print(f"  Created patient: {patient.full_name} (ID: {patient.id})")


def seed_users(db) -> dict:
    """Create demo users matching current authentication credentials.

    Returns:
        dict: Mapping of username to user object
    """
    print("Creating demo users...")

    users = {}

    # Admin user (doctor role)
    admin = UserRepository.create(
        db,
        UserCreate(
            username="admin",
            email="admin@example.com",
            password="admin123",
            name="Admin User",
        ),
    )
    users["admin"] = admin
    print(f"  Created user: {admin.username} (ID: {admin.id})")

    # Doctor user
    doctor = UserRepository.create(
        db,
        UserCreate(
            username="doctor",
            email="doctor@example.com",
            password="doctor123",
            name="Dr. Smith",
        ),
    )
    users["doctor"] = doctor
    print(f"  Created user: {doctor.username} (ID: {doctor.id})")

    # Patient user
    patient_user = UserRepository.create(
        db,
        UserCreate(
            username="patient",
            email="patient@example.com",
            password="patient123",
            name="John Patient",
        ),
    )
    users["patient"] = patient_user
    print(f"  Created user: {patient_user.username} (ID: {patient_user.id})")

    return users


def seed_patient_memberships(db, users: dict, patients: list) -> None:
    """Create patient memberships linking users to patients.

    Args:
        db: Database session
        users: Dict mapping username to User object
        patients: List of Patient objects
    """
    print("\nCreating patient memberships...")

    # Admin and doctor get access to all patients as doctor role
    for patient in patients:
        PatientMemberRepository.add_member(
            db,
            PatientMemberCreate(
                user_id=users["admin"].id,
                patient_id=patient.id,
                role=MemberRole.DOCTOR,
            ),
        )
        PatientMemberRepository.add_member(
            db,
            PatientMemberCreate(
                user_id=users["doctor"].id,
                patient_id=patient.id,
                role=MemberRole.DOCTOR,
            ),
        )
        print(f"  Added admin and doctor to patient: {patient.full_name}")

    # Patient user gets access to first patient (Maria Garcia) as patient role
    if patients:
        PatientMemberRepository.add_member(
            db,
            PatientMemberCreate(
                user_id=users["patient"].id,
                patient_id=patients[0].id,
                role=MemberRole.PATIENT,
            ),
        )
        print(f"  Added patient user to: {patients[0].full_name}")


def seed_database() -> None:
    """Seed the database with all synthetic patients."""
    print("\n" + "=" * 60)
    print("Seeding Patient Digital Twin Database")
    print("=" * 60 + "\n")

    # Create tables
    print("Creating database tables...")
    create_tables()
    print("Tables created.\n")

    # Seed data
    with get_db() as db:
        # Check if data already exists
        existing_patients = PatientRepository.get_all(db)
        existing_users = UserRepository.get_all(db, active_only=False)

        if existing_patients and existing_users:
            print(f"Database already has {len(existing_patients)} patients and {len(existing_users)} users.")
            print("To reset, run: python -m src.database.reset\n")
            return

        # Seed users first (if not already seeded)
        if not existing_users:
            users = seed_users(db)
        else:
            print(f"Users already exist ({len(existing_users)}), skipping user creation.")
            # Build users dict from existing
            users = {u.username: u for u in existing_users}

        # Seed patients (if not already seeded)
        if not existing_patients:
            seed_maria_garcia(db)
            seed_james_thompson(db)
            seed_sarah_chen(db)
        else:
            print(f"Patients already exist ({len(existing_patients)}), skipping patient creation.")

        # Get all patients for membership creation and indexing
        patients = PatientRepository.get_all(db)

        # Create patient memberships (if users were just created)
        if not existing_users and patients:
            seed_patient_memberships(db, users, patients)

        # Auto-index all patients for RAG search
        print("\nIndexing patients for RAG search...")
        from src.rag import get_retriever

        retriever = get_retriever()
        total_docs = 0
        for patient in patients:
            count = retriever.index_patient(db, patient.id)
            total_docs += count
        print(f"Indexed {total_docs} documents for {len(patients)} patients.")

        print("\n" + "-" * 60)
        print("Database seeded and indexed successfully!")
        print("-" * 60)

        # Print summary
        print(f"\nCreated {len(users)} users:")
        for username, user in users.items():
            print(f"  - {user.name} ({username})")

        print(f"\nCreated {len(patients)} patients:")
        for p in patients:
            conditions = len(p.conditions)
            medications = len(p.medications)
            allergies = len(p.allergies)
            vital_signs = len(p.vital_signs)
            lab_results = len(p.lab_results)
            family_history = len(p.family_history)
            social_history = len(p.social_history)
            members = len(p.members)
            print(
                f"  - {p.full_name} ({p.age}y {p.gender}): "
                f"{conditions} conditions, {medications} meds, {allergies} allergies, "
                f"{vital_signs} vitals, {lab_results} labs, "
                f"{family_history} family hx, {social_history} social hx, "
                f"{members} members"
            )
        print()


if __name__ == "__main__":
    seed_database()
