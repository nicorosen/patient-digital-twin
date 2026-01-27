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
    ConversationSession,
    FamilyHistory,
    LabResult,
    Medication,
    Patient,
    PatientMember,
    SocialHistory,
    User,
    VitalSigns,
)
from src.schemas import (
    AllergyCreate,
    AllergyUpdate,
    ConditionCreate,
    ConditionUpdate,
    ConversationSessionCreate,
    ConversationSessionSummary,
    ConversationSessionUpdate,
    FamilyHistoryCreate,
    FamilyHistoryUpdate,
    LabResultCreate,
    LabResultUpdate,
    MedicationCreate,
    MedicationUpdate,
    PatientCreate,
    PatientMemberCreate,
    PatientProfile,
    PatientSchema,
    PatientUpdate,
    SocialHistoryCreate,
    SocialHistoryUpdate,
    UserCreate,
    VitalSignsCreate,
    VitalSignsUpdate,
)
from src.auth.password import hash_password, verify_password


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
            vital_signs=[v for v in patient.vital_signs],
            lab_results=[l for l in patient.lab_results],
            family_history=[f for f in patient.family_history],
            social_history=[s for s in patient.social_history],
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


class ConversationSessionRepository:
    """Repository for conversation session operations."""

    @staticmethod
    def create(
        db: Session,
        patient_id: UUID,
        mode: str,
        title: Optional[str] = None,
    ) -> ConversationSession:
        """Create a new conversation session."""
        session = ConversationSession(
            patient_id=patient_id,
            mode=mode,
            title=title,
            is_active=True,
        )
        db.add(session)
        db.flush()
        return session

    @staticmethod
    def get_by_id(db: Session, session_id: UUID) -> Optional[ConversationSession]:
        """Get a session by ID."""
        return (
            db.query(ConversationSession)
            .filter(ConversationSession.id == session_id)
            .first()
        )

    @staticmethod
    def get_by_patient(
        db: Session,
        patient_id: UUID,
        mode: Optional[str] = None,
        limit: int = 20,
    ) -> List[ConversationSession]:
        """Get sessions for a patient, optionally filtered by mode."""
        query = db.query(ConversationSession).filter(
            ConversationSession.patient_id == patient_id
        )
        if mode:
            query = query.filter(ConversationSession.mode == mode)
        return query.order_by(ConversationSession.updated_at.desc()).limit(limit).all()

    @staticmethod
    def get_active_session(
        db: Session, patient_id: UUID, mode: str
    ) -> Optional[ConversationSession]:
        """Get the active session for a patient and mode."""
        return (
            db.query(ConversationSession)
            .filter(
                ConversationSession.patient_id == patient_id,
                ConversationSession.mode == mode,
                ConversationSession.is_active == True,
            )
            .order_by(ConversationSession.updated_at.desc())
            .first()
        )

    @staticmethod
    def get_session_summaries(
        db: Session,
        patient_id: UUID,
        mode: Optional[str] = None,
        limit: int = 20,
    ) -> List[ConversationSessionSummary]:
        """Get session summaries with message count and preview."""
        from sqlalchemy import func

        query = (
            db.query(
                ConversationSession,
                func.count(ConversationMessage.id).label("message_count"),
            )
            .outerjoin(
                ConversationMessage,
                ConversationSession.id == ConversationMessage.session_id,
            )
            .filter(ConversationSession.patient_id == patient_id)
            .group_by(ConversationSession.id)
        )

        if mode:
            query = query.filter(ConversationSession.mode == mode)

        results = (
            query.order_by(ConversationSession.updated_at.desc()).limit(limit).all()
        )

        summaries = []
        for session, message_count in results:
            # Get preview from first user message
            first_user_msg = (
                db.query(ConversationMessage)
                .filter(
                    ConversationMessage.session_id == session.id,
                    ConversationMessage.role == "user",
                )
                .order_by(ConversationMessage.created_at.asc())
                .first()
            )
            preview = None
            if first_user_msg:
                preview = (
                    first_user_msg.content[:100] + "..."
                    if len(first_user_msg.content) > 100
                    else first_user_msg.content
                )

            summaries.append(
                ConversationSessionSummary(
                    id=session.id,
                    mode=session.mode,
                    title=session.title,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    message_count=message_count,
                    preview=preview,
                )
            )

        return summaries

    @staticmethod
    def update_title(
        db: Session, session_id: UUID, title: str
    ) -> Optional[ConversationSession]:
        """Update session title."""
        session = ConversationSessionRepository.get_by_id(db, session_id)
        if not session:
            return None
        session.title = title
        db.flush()
        return session

    @staticmethod
    def update_timestamp(db: Session, session_id: UUID) -> Optional[ConversationSession]:
        """Update session's updated_at timestamp."""
        from datetime import datetime

        session = ConversationSessionRepository.get_by_id(db, session_id)
        if not session:
            return None
        session.updated_at = datetime.utcnow()
        db.flush()
        return session

    @staticmethod
    def deactivate_session(db: Session, session_id: UUID) -> Optional[ConversationSession]:
        """Mark a session as inactive."""
        session = ConversationSessionRepository.get_by_id(db, session_id)
        if not session:
            return None
        session.is_active = False
        db.flush()
        return session

    @staticmethod
    def delete(db: Session, session_id: UUID) -> bool:
        """Delete a session and all its messages."""
        session = ConversationSessionRepository.get_by_id(db, session_id)
        if not session:
            return False
        db.delete(session)
        db.flush()
        return True


class ConversationRepository:
    """Repository for conversation message operations."""

    @staticmethod
    def get_messages(
        db: Session, patient_id: UUID, limit: int = 100
    ) -> List[ConversationMessage]:
        """Get conversation messages for a patient (legacy - all messages)."""
        return (
            db.query(ConversationMessage)
            .filter(ConversationMessage.patient_id == patient_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_messages_by_session(
        db: Session, session_id: UUID, limit: int = 100
    ) -> List[ConversationMessage]:
        """Get conversation messages for a specific session."""
        return (
            db.query(ConversationMessage)
            .filter(ConversationMessage.session_id == session_id)
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
        session_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> ConversationMessage:
        """Add a message to the conversation."""
        message = ConversationMessage(
            patient_id=patient_id,
            session_id=session_id,
            role=role,
            content=content,
            message_metadata=metadata,
        )
        db.add(message)
        db.flush()

        # Update session timestamp if session provided
        if session_id:
            ConversationSessionRepository.update_timestamp(db, session_id)

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

    @staticmethod
    def clear_session_messages(db: Session, session_id: UUID) -> int:
        """Clear all messages for a specific session. Returns count deleted."""
        count = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.session_id == session_id)
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


class VitalSignsRepository:
    """Repository for VitalSigns CRUD operations."""

    @staticmethod
    def get_by_patient(
        db: Session, patient_id: UUID, limit: int = 10
    ) -> List[VitalSigns]:
        """Get vital signs for a patient, ordered by most recent first."""
        return (
            db.query(VitalSigns)
            .filter(VitalSigns.patient_id == patient_id)
            .order_by(VitalSigns.recorded_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, vital_signs_id: UUID) -> Optional[VitalSigns]:
        """Get vital signs by ID."""
        return db.query(VitalSigns).filter(VitalSigns.id == vital_signs_id).first()

    @staticmethod
    def create(db: Session, vital_signs_data: VitalSignsCreate) -> VitalSigns:
        """Create new vital signs record."""
        vital_signs = VitalSigns(
            patient_id=vital_signs_data.patient_id,
            recorded_at=vital_signs_data.recorded_at,
            systolic_bp=vital_signs_data.systolic_bp,
            diastolic_bp=vital_signs_data.diastolic_bp,
            heart_rate=vital_signs_data.heart_rate,
            temperature=vital_signs_data.temperature,
            weight_kg=vital_signs_data.weight_kg,
            height_cm=vital_signs_data.height_cm,
            oxygen_saturation=vital_signs_data.oxygen_saturation,
            notes=vital_signs_data.notes,
        )
        db.add(vital_signs)
        db.flush()
        return vital_signs

    @staticmethod
    def update(
        db: Session, vital_signs_id: UUID, vital_signs_data: VitalSignsUpdate
    ) -> Optional[VitalSigns]:
        """Update vital signs."""
        vital_signs = VitalSignsRepository.get_by_id(db, vital_signs_id)
        if not vital_signs:
            return None

        update_data = vital_signs_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(vital_signs, field, value)

        db.flush()
        return vital_signs

    @staticmethod
    def delete(db: Session, vital_signs_id: UUID) -> bool:
        """Delete vital signs."""
        vital_signs = VitalSignsRepository.get_by_id(db, vital_signs_id)
        if not vital_signs:
            return False

        db.delete(vital_signs)
        db.flush()
        return True


class LabResultRepository:
    """Repository for LabResult CRUD operations."""

    @staticmethod
    def get_by_patient(
        db: Session, patient_id: UUID, test_name: Optional[str] = None, limit: int = 50
    ) -> List[LabResult]:
        """Get lab results for a patient, optionally filtered by test name."""
        query = db.query(LabResult).filter(LabResult.patient_id == patient_id)
        if test_name:
            query = query.filter(LabResult.test_name.ilike(f"%{test_name}%"))
        return query.order_by(LabResult.result_date.desc()).limit(limit).all()

    @staticmethod
    def get_by_id(db: Session, lab_result_id: UUID) -> Optional[LabResult]:
        """Get a lab result by ID."""
        return db.query(LabResult).filter(LabResult.id == lab_result_id).first()

    @staticmethod
    def create(db: Session, lab_result_data: LabResultCreate) -> LabResult:
        """Create a new lab result."""
        lab_result = LabResult(
            patient_id=lab_result_data.patient_id,
            test_name=lab_result_data.test_name,
            test_code=lab_result_data.test_code,
            value=lab_result_data.value,
            value_numeric=lab_result_data.value_numeric,
            unit=lab_result_data.unit,
            reference_range_low=lab_result_data.reference_range_low,
            reference_range_high=lab_result_data.reference_range_high,
            interpretation=(
                lab_result_data.interpretation.value
                if lab_result_data.interpretation
                else None
            ),
            result_date=lab_result_data.result_date,
            notes=lab_result_data.notes,
        )
        db.add(lab_result)
        db.flush()
        return lab_result

    @staticmethod
    def update(
        db: Session, lab_result_id: UUID, lab_result_data: LabResultUpdate
    ) -> Optional[LabResult]:
        """Update a lab result."""
        lab_result = LabResultRepository.get_by_id(db, lab_result_id)
        if not lab_result:
            return None

        update_data = lab_result_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field == "interpretation":
                    value = value.value
                setattr(lab_result, field, value)

        db.flush()
        return lab_result

    @staticmethod
    def delete(db: Session, lab_result_id: UUID) -> bool:
        """Delete a lab result."""
        lab_result = LabResultRepository.get_by_id(db, lab_result_id)
        if not lab_result:
            return False

        db.delete(lab_result)
        db.flush()
        return True


class FamilyHistoryRepository:
    """Repository for FamilyHistory CRUD operations."""

    @staticmethod
    def get_by_patient(db: Session, patient_id: UUID) -> List[FamilyHistory]:
        """Get all family history entries for a patient."""
        return (
            db.query(FamilyHistory)
            .filter(FamilyHistory.patient_id == patient_id)
            .order_by(FamilyHistory.created_at.desc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, family_history_id: UUID) -> Optional[FamilyHistory]:
        """Get a family history entry by ID."""
        return (
            db.query(FamilyHistory).filter(FamilyHistory.id == family_history_id).first()
        )

    @staticmethod
    def create(db: Session, family_history_data: FamilyHistoryCreate) -> FamilyHistory:
        """Create a new family history entry."""
        family_history = FamilyHistory(
            patient_id=family_history_data.patient_id,
            relation=family_history_data.relation.value,
            condition_name=family_history_data.condition_name,
            onset_age=family_history_data.onset_age,
            notes=family_history_data.notes,
        )
        db.add(family_history)
        db.flush()
        return family_history

    @staticmethod
    def update(
        db: Session, family_history_id: UUID, family_history_data: FamilyHistoryUpdate
    ) -> Optional[FamilyHistory]:
        """Update a family history entry."""
        family_history = FamilyHistoryRepository.get_by_id(db, family_history_id)
        if not family_history:
            return None

        update_data = family_history_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field == "relation":
                    value = value.value
                setattr(family_history, field, value)

        db.flush()
        return family_history

    @staticmethod
    def delete(db: Session, family_history_id: UUID) -> bool:
        """Delete a family history entry."""
        family_history = FamilyHistoryRepository.get_by_id(db, family_history_id)
        if not family_history:
            return False

        db.delete(family_history)
        db.flush()
        return True


class SocialHistoryRepository:
    """Repository for SocialHistory CRUD operations."""

    @staticmethod
    def get_by_patient(db: Session, patient_id: UUID) -> List[SocialHistory]:
        """Get all social history entries for a patient."""
        return (
            db.query(SocialHistory)
            .filter(SocialHistory.patient_id == patient_id)
            .order_by(SocialHistory.category)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, social_history_id: UUID) -> Optional[SocialHistory]:
        """Get a social history entry by ID."""
        return (
            db.query(SocialHistory).filter(SocialHistory.id == social_history_id).first()
        )

    @staticmethod
    def get_by_category(
        db: Session, patient_id: UUID, category: str
    ) -> Optional[SocialHistory]:
        """Get social history entry by category for a patient."""
        return (
            db.query(SocialHistory)
            .filter(
                SocialHistory.patient_id == patient_id,
                SocialHistory.category == category,
            )
            .first()
        )

    @staticmethod
    def create(db: Session, social_history_data: SocialHistoryCreate) -> SocialHistory:
        """Create a new social history entry."""
        social_history = SocialHistory(
            patient_id=social_history_data.patient_id,
            category=social_history_data.category.value,
            status=social_history_data.status.value,
            description=social_history_data.description,
            notes=social_history_data.notes,
        )
        db.add(social_history)
        db.flush()
        return social_history

    @staticmethod
    def update(
        db: Session, social_history_id: UUID, social_history_data: SocialHistoryUpdate
    ) -> Optional[SocialHistory]:
        """Update a social history entry."""
        social_history = SocialHistoryRepository.get_by_id(db, social_history_id)
        if not social_history:
            return None

        update_data = social_history_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field in ("category", "status"):
                    value = value.value
                setattr(social_history, field, value)

        db.flush()
        return social_history

    @staticmethod
    def delete(db: Session, social_history_id: UUID) -> bool:
        """Delete a social history entry."""
        social_history = SocialHistoryRepository.get_by_id(db, social_history_id)
        if not social_history:
            return False

        db.delete(social_history)
        db.flush()
        return True


class UserRepository:
    """Repository for User CRUD operations."""

    @staticmethod
    def get_by_id(db: Session, user_id: UUID) -> Optional[User]:
        """Get a user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """Get a user by username."""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Get a user by email."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_all(db: Session, active_only: bool = True) -> List[User]:
        """Get all users, optionally filtering to active only."""
        query = db.query(User)
        if active_only:
            query = query.filter(User.is_active == True)
        return query.order_by(User.name).all()

    @staticmethod
    def create(db: Session, user_data: UserCreate) -> User:
        """Create a new user."""
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            name=user_data.name,
            is_active=True,
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def authenticate(db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username and password."""
        user = UserRepository.get_by_username(db, username)
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def update_password(db: Session, user_id: UUID, new_password: str) -> Optional[User]:
        """Update a user's password."""
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return None
        user.hashed_password = hash_password(new_password)
        db.flush()
        return user

    @staticmethod
    def deactivate(db: Session, user_id: UUID) -> Optional[User]:
        """Deactivate a user account."""
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return None
        user.is_active = False
        db.flush()
        return user


class PatientMemberRepository:
    """Repository for PatientMember CRUD operations."""

    @staticmethod
    def get_members_by_patient(db: Session, patient_id: UUID) -> List[PatientMember]:
        """Get all members for a patient."""
        return (
            db.query(PatientMember)
            .filter(PatientMember.patient_id == patient_id)
            .order_by(PatientMember.role)
            .all()
        )

    @staticmethod
    def get_patients_for_user(db: Session, user_id: UUID) -> List[Patient]:
        """Get all patients a user is a member of."""
        return (
            db.query(Patient)
            .join(PatientMember, Patient.id == PatientMember.patient_id)
            .filter(PatientMember.user_id == user_id)
            .order_by(Patient.last_name, Patient.first_name)
            .all()
        )

    @staticmethod
    def get_membership(
        db: Session, user_id: UUID, patient_id: UUID
    ) -> Optional[PatientMember]:
        """Get a specific membership."""
        return (
            db.query(PatientMember)
            .filter(
                PatientMember.user_id == user_id,
                PatientMember.patient_id == patient_id,
            )
            .first()
        )

    @staticmethod
    def add_member(db: Session, member_data: PatientMemberCreate) -> PatientMember:
        """Add a member to a patient."""
        member = PatientMember(
            user_id=member_data.user_id,
            patient_id=member_data.patient_id,
            role=member_data.role.value,
        )
        db.add(member)
        db.flush()
        return member

    @staticmethod
    def update_role(
        db: Session, user_id: UUID, patient_id: UUID, new_role: str
    ) -> Optional[PatientMember]:
        """Update a member's role."""
        member = PatientMemberRepository.get_membership(db, user_id, patient_id)
        if not member:
            return None
        member.role = new_role
        db.flush()
        return member

    @staticmethod
    def remove_member(db: Session, user_id: UUID, patient_id: UUID) -> bool:
        """Remove a member from a patient."""
        member = PatientMemberRepository.get_membership(db, user_id, patient_id)
        if not member:
            return False
        db.delete(member)
        db.flush()
        return True

    @staticmethod
    def is_member(db: Session, user_id: UUID, patient_id: UUID) -> bool:
        """Check if a user is a member of a patient."""
        return PatientMemberRepository.get_membership(db, user_id, patient_id) is not None

    @staticmethod
    def get_user_role(db: Session, user_id: UUID, patient_id: UUID) -> Optional[str]:
        """Get a user's role for a patient, or None if not a member."""
        member = PatientMemberRepository.get_membership(db, user_id, patient_id)
        return member.role if member else None
