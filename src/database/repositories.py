"""
Repository pattern for data access.

Provides clean CRUD interfaces for all database models,
abstracting SQLAlchemy operations from business logic.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models import (
    Allergy,
    Condition,
    ConsultationAuditLog,
    ConversationMessage,
    Medication,
    Patient,
)
from src.schemas import (
    AllergyCreate,
    AllergyUpdate,
    ConditionCreate,
    ConditionUpdate,
    MedicationCreate,
    MedicationUpdate,
    PatientCreate,
    PatientProfile,
    PatientSchema,
    PatientUpdate,
)


class PatientRepository:
    """Repository for Patient CRUD operations."""

    @staticmethod
    def get_all(db: Session) -> List[Patient]:
        """Get all patients."""
        return db.query(Patient).order_by(Patient.last_name, Patient.first_name).all()

    @staticmethod
    def get_by_id(db: Session, patient_id: UUID) -> Optional[Patient]:
        """Get a patient by ID."""
        return db.query(Patient).filter(Patient.id == patient_id).first()

    @staticmethod
    def create(db: Session, patient_data: PatientCreate) -> Patient:
        """Create a new patient."""
        patient = Patient(
            first_name=patient_data.first_name,
            last_name=patient_data.last_name,
            date_of_birth=patient_data.date_of_birth,
            gender=patient_data.gender.value,
        )
        db.add(patient)
        db.flush()
        return patient

    @staticmethod
    def update(
        db: Session, patient_id: UUID, patient_data: PatientUpdate
    ) -> Optional[Patient]:
        """Update a patient."""
        patient = PatientRepository.get_by_id(db, patient_id)
        if not patient:
            return None

        update_data = patient_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field == "gender":
                    value = value.value
                setattr(patient, field, value)

        db.flush()
        return patient

    @staticmethod
    def delete(db: Session, patient_id: UUID) -> bool:
        """Delete a patient."""
        patient = PatientRepository.get_by_id(db, patient_id)
        if not patient:
            return False

        db.delete(patient)
        db.flush()
        return True

    @staticmethod
    def get_profile(db: Session, patient_id: UUID) -> Optional[PatientProfile]:
        """Get complete patient profile with all clinical data."""
        patient = PatientRepository.get_by_id(db, patient_id)
        if not patient:
            return None

        return PatientProfile(
            patient=PatientSchema.model_validate(patient),
            conditions=[c for c in patient.conditions],
            medications=[m for m in patient.medications],
            allergies=[a for a in patient.allergies],
        )


class ConditionRepository:
    """Repository for Condition CRUD operations."""

    @staticmethod
    def get_by_patient(
        db: Session, patient_id: UUID, active_only: bool = False
    ) -> List[Condition]:
        """Get all conditions for a patient."""
        query = db.query(Condition).filter(Condition.patient_id == patient_id)
        if active_only:
            query = query.filter(Condition.clinical_status == "active")
        return query.order_by(Condition.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, condition_id: UUID) -> Optional[Condition]:
        """Get a condition by ID."""
        return db.query(Condition).filter(Condition.id == condition_id).first()

    @staticmethod
    def create(db: Session, condition_data: ConditionCreate) -> Condition:
        """Create a new condition."""
        condition = Condition(
            patient_id=condition_data.patient_id,
            code=condition_data.code,
            display_name=condition_data.display_name,
            clinical_status=condition_data.clinical_status.value,
            onset_date=condition_data.onset_date,
            severity=condition_data.severity.value if condition_data.severity else None,
            notes=condition_data.notes,
        )
        db.add(condition)
        db.flush()
        return condition

    @staticmethod
    def update(
        db: Session, condition_id: UUID, condition_data: ConditionUpdate
    ) -> Optional[Condition]:
        """Update a condition."""
        condition = ConditionRepository.get_by_id(db, condition_id)
        if not condition:
            return None

        update_data = condition_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field in ("clinical_status", "severity"):
                    value = value.value
                setattr(condition, field, value)

        db.flush()
        return condition

    @staticmethod
    def delete(db: Session, condition_id: UUID) -> bool:
        """Delete a condition."""
        condition = ConditionRepository.get_by_id(db, condition_id)
        if not condition:
            return False

        db.delete(condition)
        db.flush()
        return True


class MedicationRepository:
    """Repository for Medication CRUD operations."""

    @staticmethod
    def get_by_patient(
        db: Session, patient_id: UUID, active_only: bool = False
    ) -> List[Medication]:
        """Get all medications for a patient."""
        query = db.query(Medication).filter(Medication.patient_id == patient_id)
        if active_only:
            query = query.filter(Medication.status == "active")
        return query.order_by(Medication.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, medication_id: UUID) -> Optional[Medication]:
        """Get a medication by ID."""
        return db.query(Medication).filter(Medication.id == medication_id).first()

    @staticmethod
    def create(db: Session, medication_data: MedicationCreate) -> Medication:
        """Create a new medication."""
        medication = Medication(
            patient_id=medication_data.patient_id,
            code=medication_data.code,
            display_name=medication_data.display_name,
            dosage=medication_data.dosage,
            frequency=medication_data.frequency,
            route=medication_data.route,
            status=medication_data.status.value,
            start_date=medication_data.start_date,
            end_date=medication_data.end_date,
            reason=medication_data.reason,
        )
        db.add(medication)
        db.flush()
        return medication

    @staticmethod
    def update(
        db: Session, medication_id: UUID, medication_data: MedicationUpdate
    ) -> Optional[Medication]:
        """Update a medication."""
        medication = MedicationRepository.get_by_id(db, medication_id)
        if not medication:
            return None

        update_data = medication_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field == "status":
                    value = value.value
                setattr(medication, field, value)

        db.flush()
        return medication

    @staticmethod
    def delete(db: Session, medication_id: UUID) -> bool:
        """Delete a medication."""
        medication = MedicationRepository.get_by_id(db, medication_id)
        if not medication:
            return False

        db.delete(medication)
        db.flush()
        return True


class AllergyRepository:
    """Repository for Allergy CRUD operations."""

    @staticmethod
    def get_by_patient(db: Session, patient_id: UUID) -> List[Allergy]:
        """Get all allergies for a patient."""
        return (
            db.query(Allergy)
            .filter(Allergy.patient_id == patient_id)
            .order_by(Allergy.created_at.desc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, allergy_id: UUID) -> Optional[Allergy]:
        """Get an allergy by ID."""
        return db.query(Allergy).filter(Allergy.id == allergy_id).first()

    @staticmethod
    def create(db: Session, allergy_data: AllergyCreate) -> Allergy:
        """Create a new allergy."""
        allergy = Allergy(
            patient_id=allergy_data.patient_id,
            code=allergy_data.code,
            substance=allergy_data.substance,
            category=allergy_data.category.value,
            criticality=(
                allergy_data.criticality.value if allergy_data.criticality else None
            ),
            reaction=allergy_data.reaction,
            onset_date=allergy_data.onset_date,
        )
        db.add(allergy)
        db.flush()
        return allergy

    @staticmethod
    def update(
        db: Session, allergy_id: UUID, allergy_data: AllergyUpdate
    ) -> Optional[Allergy]:
        """Update an allergy."""
        allergy = AllergyRepository.get_by_id(db, allergy_id)
        if not allergy:
            return None

        update_data = allergy_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field in ("category", "criticality"):
                    value = value.value
                setattr(allergy, field, value)

        db.flush()
        return allergy

    @staticmethod
    def delete(db: Session, allergy_id: UUID) -> bool:
        """Delete an allergy."""
        allergy = AllergyRepository.get_by_id(db, allergy_id)
        if not allergy:
            return False

        db.delete(allergy)
        db.flush()
        return True


class ConversationRepository:
    """Repository for conversation message operations."""

    @staticmethod
    def get_messages(
        db: Session, patient_id: UUID, limit: int = 100
    ) -> List[ConversationMessage]:
        """Get conversation messages for a patient."""
        return (
            db.query(ConversationMessage)
            .filter(ConversationMessage.patient_id == patient_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def add_message(
        db: Session,
        patient_id: UUID,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> ConversationMessage:
        """Add a message to the conversation."""
        message = ConversationMessage(
            patient_id=patient_id,
            role=role,
            content=content,
            metadata=metadata,
        )
        db.add(message)
        db.flush()
        return message

    @staticmethod
    def clear_messages(db: Session, patient_id: UUID) -> int:
        """Clear all messages for a patient. Returns count deleted."""
        count = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.patient_id == patient_id)
            .delete()
        )
        db.flush()
        return count


class AuditLogRepository:
    """Repository for consultation audit log operations."""

    @staticmethod
    def get_by_patient(
        db: Session, patient_id: UUID, limit: int = 50
    ) -> List[ConsultationAuditLog]:
        """Get audit logs for a patient."""
        return (
            db.query(ConsultationAuditLog)
            .filter(ConsultationAuditLog.patient_id == patient_id)
            .order_by(ConsultationAuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(
        db: Session,
        patient_id: UUID,
        specialist_type: str,
        clinical_question: str,
        data_shared: dict,
        specialist_response: dict,
    ) -> ConsultationAuditLog:
        """Create a new audit log entry."""
        log = ConsultationAuditLog(
            patient_id=patient_id,
            specialist_type=specialist_type,
            clinical_question=clinical_question,
            data_shared=data_shared,
            specialist_response=specialist_response,
        )
        db.add(log)
        db.flush()
        return log
