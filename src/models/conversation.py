"""
Conversation and audit log models.

Stores:
- Conversation history between patients and the Medical Assistant
- Audit logs of specialist consultations for transparency
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.patient import Patient


class ConversationMessage(Base, UUIDMixin, TimestampMixin):
    """
    Individual message in a conversation.

    Attributes:
        id: Unique identifier (UUID)
        patient_id: Reference to the patient this conversation is with
        role: Who sent the message ('user' or 'assistant')
        content: The message content
        message_metadata: Optional metadata (tool calls, etc.)
    """

    __tablename__ = "conversation_messages"

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(role='{self.role}', content='{preview}')>"


class ConsultationAuditLog(Base, UUIDMixin):
    """
    Audit log for specialist consultations.

    Records what de-identified data was shared with specialist agents
    for transparency and compliance.

    Attributes:
        id: Unique identifier (UUID)
        patient_id: Reference to the patient (internal tracking only)
        timestamp: When the consultation occurred
        specialist_type: Type of specialist consulted (e.g., 'primary_care')
        clinical_question: The question asked of the specialist
        data_shared: De-identified patient context that was shared
        specialist_response: The specialist's response
    """

    __tablename__ = "consultation_audit_logs"

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    specialist_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="primary_care",
    )
    clinical_question: Mapped[str] = mapped_column(Text, nullable=False)
    data_shared: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="De-identified patient context shared with specialist",
    )
    specialist_response: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="Structured response from specialist",
    )

    def __repr__(self) -> str:
        return f"<ConsultationAuditLog(id={self.id}, specialist='{self.specialist_type}', timestamp={self.timestamp})>"

    def get_shared_fields(self) -> list[str]:
        """Get list of field names that were shared with specialist."""
        return list(self.data_shared.keys()) if self.data_shared else []
