"""
AI agents for patient health management.

Contains:
- Medical Assistant: Patient-facing agent for data gathering and queries
- Primary Care Specialist: Clinical consultation agent
- Agent tools for data access and specialist consultation
- Translation layer for clinical to patient-friendly language
"""

from src.agents.medical_assistant import MedicalAssistant
from src.agents.primary_care import (
    PrimaryCareSpecialist,
    SpecialistResponse,
    get_primary_care_specialist,
)
from src.agents.tools import (
    ALL_TOOLS,
    CONSULTATION_TOOLS,
    PATIENT_DATA_TOOLS,
    add_allergy,
    add_condition,
    add_medication,
    consult_primary_care,
    get_patient_profile,
    search_patient_data,
)
from src.agents.translation import (
    atranslate_specialist_response,
    translate_specialist_response,
)

__all__ = [
    # Agents
    "MedicalAssistant",
    "PrimaryCareSpecialist",
    "get_primary_care_specialist",
    "SpecialistResponse",
    # Translation
    "translate_specialist_response",
    "atranslate_specialist_response",
    # Tools
    "ALL_TOOLS",
    "PATIENT_DATA_TOOLS",
    "CONSULTATION_TOOLS",
    "get_patient_profile",
    "search_patient_data",
    "add_condition",
    "add_medication",
    "add_allergy",
    "consult_primary_care",
]
