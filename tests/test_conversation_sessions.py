"""
Tests for conversation session management.

Tests:
- ConversationSession model
- ConversationSessionRepository CRUD operations
- Session summaries with message counts
- Session-based message retrieval
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.models.conversation import ConversationSession, ConversationMessage
from src.database.repositories import (
    ConversationRepository,
    ConversationSessionRepository,
)


# =============================================================================
# CONVERSATION SESSION MODEL TESTS
# =============================================================================


class TestConversationSessionModel:
    """Tests for ConversationSession model."""

    def test_create_session(self, db_session, sample_patient):
        """Test creating a conversation session."""
        session = ConversationSession(
            patient_id=sample_patient.id,
            mode="clinical",
            title="Test Session",
            is_active=True,
        )
        db_session.add(session)
        db_session.flush()

        assert session.id is not None
        assert session.patient_id == sample_patient.id
        assert session.mode == "clinical"
        assert session.title == "Test Session"
        assert session.is_active is True

    def test_session_modes(self, db_session, sample_patient):
        """Test different session modes."""
        clinical_session = ConversationSession(
            patient_id=sample_patient.id,
            mode="clinical",
        )
        coach_session = ConversationSession(
            patient_id=sample_patient.id,
            mode="coach",
        )
        db_session.add_all([clinical_session, coach_session])
        db_session.flush()

        assert clinical_session.mode == "clinical"
        assert coach_session.mode == "coach"

    def test_session_repr(self, db_session, sample_patient):
        """Test session __repr__."""
        session = ConversationSession(
            patient_id=sample_patient.id,
            mode="clinical",
            title="My test session title",
        )
        db_session.add(session)
        db_session.flush()

        repr_str = repr(session)
        assert "clinical" in repr_str
        assert "My test session title" in repr_str


# =============================================================================
# CONVERSATION SESSION REPOSITORY TESTS
# =============================================================================


class TestConversationSessionRepository:
    """Tests for ConversationSessionRepository."""

    def test_create_session(self, db_session, sample_patient):
        """Test creating a session via repository."""
        session = ConversationSessionRepository.create(
            db_session,
            patient_id=sample_patient.id,
            mode="clinical",
            title="Test Session",
        )

        assert session.id is not None
        assert session.patient_id == sample_patient.id
        assert session.mode == "clinical"
        assert session.title == "Test Session"
        assert session.is_active is True

    def test_get_by_id(self, db_session, sample_patient):
        """Test getting a session by ID."""
        session = ConversationSessionRepository.create(
            db_session,
            patient_id=sample_patient.id,
            mode="clinical",
        )

        found = ConversationSessionRepository.get_by_id(db_session, session.id)
        assert found is not None
        assert found.id == session.id

    def test_get_by_id_not_found(self, db_session):
        """Test getting non-existent session."""
        found = ConversationSessionRepository.get_by_id(db_session, uuid4())
        assert found is None

    def test_get_by_patient(self, db_session, sample_patient):
        """Test getting sessions by patient."""
        # Create multiple sessions
        ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )
        ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="coach"
        )
        ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )

        sessions = ConversationSessionRepository.get_by_patient(
            db_session, patient_id=sample_patient.id
        )
        assert len(sessions) == 3

    def test_get_by_patient_filtered_by_mode(self, db_session, sample_patient):
        """Test filtering sessions by mode."""
        ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )
        ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="coach"
        )
        ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )

        clinical = ConversationSessionRepository.get_by_patient(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )
        coach = ConversationSessionRepository.get_by_patient(
            db_session, patient_id=sample_patient.id, mode="coach"
        )

        assert len(clinical) == 2
        assert len(coach) == 1

    def test_get_active_session(self, db_session, sample_patient):
        """Test getting active session for patient and mode."""
        session = ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )

        active = ConversationSessionRepository.get_active_session(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )

        assert active is not None
        assert active.id == session.id

    def test_update_title(self, db_session, sample_patient):
        """Test updating session title."""
        session = ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )
        assert session.title is None

        updated = ConversationSessionRepository.update_title(
            db_session, session.id, "New Title"
        )
        assert updated.title == "New Title"

    def test_deactivate_session(self, db_session, sample_patient):
        """Test deactivating a session."""
        session = ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )
        assert session.is_active is True

        deactivated = ConversationSessionRepository.deactivate_session(
            db_session, session.id
        )
        assert deactivated.is_active is False

    def test_delete_session(self, db_session, sample_patient):
        """Test deleting a session."""
        session = ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )

        result = ConversationSessionRepository.delete(db_session, session.id)
        assert result is True

        # Verify deletion
        found = ConversationSessionRepository.get_by_id(db_session, session.id)
        assert found is None

    def test_delete_session_not_found(self, db_session):
        """Test deleting non-existent session."""
        result = ConversationSessionRepository.delete(db_session, uuid4())
        assert result is False


# =============================================================================
# SESSION SUMMARIES TESTS
# =============================================================================


class TestSessionSummaries:
    """Tests for session summaries with message counts."""

    def test_get_session_summaries(self, db_session, sample_patient):
        """Test getting session summaries."""
        session = ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical", title="Test"
        )

        # Add messages
        ConversationRepository.add_message(
            db_session,
            patient_id=sample_patient.id,
            role="user",
            content="Hello",
            session_id=session.id,
        )
        ConversationRepository.add_message(
            db_session,
            patient_id=sample_patient.id,
            role="assistant",
            content="Hi there!",
            session_id=session.id,
        )

        summaries = ConversationSessionRepository.get_session_summaries(
            db_session, patient_id=sample_patient.id
        )

        assert len(summaries) == 1
        assert summaries[0].message_count == 2
        assert summaries[0].title == "Test"
        assert summaries[0].preview == "Hello"

    def test_summary_preview_truncation(self, db_session, sample_patient):
        """Test that long messages are truncated in preview."""
        session = ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )

        long_message = "A" * 150
        ConversationRepository.add_message(
            db_session,
            patient_id=sample_patient.id,
            role="user",
            content=long_message,
            session_id=session.id,
        )

        summaries = ConversationSessionRepository.get_session_summaries(
            db_session, patient_id=sample_patient.id
        )

        assert len(summaries[0].preview) <= 103  # 100 + "..."


# =============================================================================
# SESSION-BASED MESSAGE TESTS
# =============================================================================


class TestSessionMessages:
    """Tests for session-based message operations."""

    def test_add_message_to_session(self, db_session, sample_patient):
        """Test adding a message to a session."""
        session = ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )

        message = ConversationRepository.add_message(
            db_session,
            patient_id=sample_patient.id,
            role="user",
            content="Test message",
            session_id=session.id,
        )

        assert message.session_id == session.id

    def test_get_messages_by_session(self, db_session, sample_patient):
        """Test getting messages for a specific session."""
        session1 = ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )
        session2 = ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="coach"
        )

        # Add messages to both sessions
        ConversationRepository.add_message(
            db_session,
            patient_id=sample_patient.id,
            role="user",
            content="Clinical message",
            session_id=session1.id,
        )
        ConversationRepository.add_message(
            db_session,
            patient_id=sample_patient.id,
            role="user",
            content="Coach message",
            session_id=session2.id,
        )

        messages1 = ConversationRepository.get_messages_by_session(
            db_session, session1.id
        )
        messages2 = ConversationRepository.get_messages_by_session(
            db_session, session2.id
        )

        assert len(messages1) == 1
        assert len(messages2) == 1
        assert messages1[0].content == "Clinical message"
        assert messages2[0].content == "Coach message"

    def test_clear_session_messages(self, db_session, sample_patient):
        """Test clearing messages from a session."""
        session = ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )

        # Add messages
        for i in range(5):
            ConversationRepository.add_message(
                db_session,
                patient_id=sample_patient.id,
                role="user",
                content=f"Message {i}",
                session_id=session.id,
            )

        count = ConversationRepository.clear_session_messages(db_session, session.id)
        assert count == 5

        # Verify messages are gone
        messages = ConversationRepository.get_messages_by_session(
            db_session, session.id
        )
        assert len(messages) == 0

    def test_session_cascade_delete(self, db_session, sample_patient):
        """Test that deleting a session deletes its messages."""
        session = ConversationSessionRepository.create(
            db_session, patient_id=sample_patient.id, mode="clinical"
        )

        # Add messages
        ConversationRepository.add_message(
            db_session,
            patient_id=sample_patient.id,
            role="user",
            content="Test",
            session_id=session.id,
        )

        # Delete session
        ConversationSessionRepository.delete(db_session, session.id)

        # Messages should be gone (cascade delete)
        messages = ConversationRepository.get_messages_by_session(
            db_session, session.id
        )
        assert len(messages) == 0
