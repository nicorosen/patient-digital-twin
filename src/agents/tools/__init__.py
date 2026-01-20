"""
Tools available to AI agents.

Includes:
- Patient data tools (get profile, add condition/medication/allergy)
- Consultation tools (consult specialist via MCP)
- RAG search tools
"""

from src.agents.tools.consultation import CONSULTATION_TOOLS, consult_primary_care
from src.agents.tools.patient_data import (
    PATIENT_DATA_TOOLS,
    add_allergy,
    add_condition,
    add_medication,
    get_patient_profile,
    search_patient_data,
)

# All tools available to the Medical Assistant
ALL_TOOLS = PATIENT_DATA_TOOLS + CONSULTATION_TOOLS

# Read-only tools for Health Coach (no data modification, no specialist consultation)
HEALTH_COACH_TOOLS = [get_patient_profile, search_patient_data]

__all__ = [
    # Patient data tools
    "get_patient_profile",
    "search_patient_data",
    "add_condition",
    "add_medication",
    "add_allergy",
    "PATIENT_DATA_TOOLS",
    # Consultation tools
    "consult_primary_care",
    "CONSULTATION_TOOLS",
    # Combined
    "ALL_TOOLS",
    # Health Coach tools (read-only)
    "HEALTH_COACH_TOOLS",
]
