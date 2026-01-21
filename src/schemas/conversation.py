"""
Conversation Pydantic schemas for session and message management.

These schemas support:
- ConversationSession: Groups of messages for a patient in a specific mode
- ConversationMessage: Individual messages within a session
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# ENUMS
# =============================================================================


class ConversationMode(str, Enum):
    """Mode of conversation - determines which agent was active."""

    CLINICAL = "clinical"  # Medical Assistant
    COACH = "coach"  # Health Coach


# =============================================================================
# BASE SCHEMAS
# =============================================================================


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for created/updated timestamps."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# CONVERSATION SESSION SCHEMAS
# =============================================================================


class ConversationSessionBase(BaseSchema):
    """Base conversation session schema with common fields."""

    mode: ConversationMode = Field(
        default=ConversationMode.CLINICAL,
        description="Conversation mode (clinical or coach)",
    )
    title: Optional[str] = Field(
        None,
        max_length=255,
        description="Title of the conversation (auto-generated or custom)",
    )


class ConversationSessionCreate(ConversationSessionBase):
    """Schema for creating a new conversation session."""

    patient_id: UUID


class ConversationSessionUpdate(BaseSchema):
    """Schema for updating a conversation session."""

    title: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class ConversationSessionSchema(ConversationSessionBase, TimestampMixin):
    """Complete conversation session schema with ID and timestamps."""

    id: UUID
    patient_id: UUID
    is_active: bool = True


class ConversationSessionSummary(BaseSchema):
    """Lightweight session summary for sidebar listing."""

    id: UUID
    mode: ConversationMode
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    preview: Optional[str] = Field(
        None,
        description="Preview of first user message",
    )


# =============================================================================
# CONVERSATION MESSAGE SCHEMAS
# =============================================================================


class ConversationMessageBase(BaseSchema):
    """Base message schema with common fields."""

    role: str = Field(
        ...,
        description="Who sent the message ('user' or 'assistant')",
    )
    content: str = Field(
        ...,
        description="The message content",
    )


class ConversationMessageCreate(ConversationMessageBase):
    """Schema for creating a new message."""

    patient_id: UUID
    session_id: Optional[UUID] = None
    message_metadata: Optional[dict] = None


class ConversationMessageSchema(ConversationMessageBase, TimestampMixin):
    """Complete message schema with ID and timestamps."""

    id: UUID
    patient_id: UUID
    session_id: Optional[UUID]
    message_metadata: Optional[dict] = None


# =============================================================================
# COMPOSITE SCHEMAS
# =============================================================================


class ConversationSessionWithMessages(ConversationSessionSchema):
    """Session with all its messages loaded."""

    messages: List[ConversationMessageSchema] = []
