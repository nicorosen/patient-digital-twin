"""
Tools available to AI agents.

Includes:
- Patient data tools (get profile, add condition/medication/allergy)
- Consultation tools (consult specialist via MCP)
- RAG search tools
"""

from src.agents.tools.consultation import CONSULTATION_TOOLS, consult_primary_care
from src.agents.tools.patient_data import (
    HEALTH_COACH_TOOLS,
    PATIENT_DATA_TOOLS,
    # Getter tools
    get_patient_profile,
    get_conditions,
    get_medications,
    get_allergies,
    get_vital_signs,
    get_lab_results,
    get_family_history,
    get_social_history,
    search_patient_data,
    search_clinical_history,
    # Add tools
    add_condition,
    add_medication,
    add_allergy,
    add_vital_signs,
    add_lab_result,
    add_family_history,
    add_social_history,
    # Update tools
    update_condition,
    update_medication,
    update_allergy,
    update_vital_signs,
    update_lab_result,
    update_family_history,
    update_social_history,
    # Delete tools
    delete_condition,
    delete_medication,
    delete_allergy,
    delete_vital_signs,
    delete_lab_result,
    delete_family_history,
    delete_social_history,
)

# All tools available to the Medical Assistant
ALL_TOOLS = PATIENT_DATA_TOOLS + CONSULTATION_TOOLS

__all__ = [
    # Patient data tools - getters
    "get_patient_profile",
    "get_conditions",
    "get_medications",
    "get_allergies",
    "get_vital_signs",
    "get_lab_results",
    "get_family_history",
    "get_social_history",
    "search_patient_data",
    "search_clinical_history",
    # Patient data tools - add
    "add_condition",
    "add_medication",
    "add_allergy",
    "add_vital_signs",
    "add_lab_result",
    "add_family_history",
    "add_social_history",
    # Patient data tools - update
    "update_condition",
    "update_medication",
    "update_allergy",
    "update_vital_signs",
    "update_lab_result",
    "update_family_history",
    "update_social_history",
    # Patient data tools - delete
    "delete_condition",
    "delete_medication",
    "delete_allergy",
    "delete_vital_signs",
    "delete_lab_result",
    "delete_family_history",
    "delete_social_history",
    "PATIENT_DATA_TOOLS",
    # Consultation tools
    "consult_primary_care",
    "CONSULTATION_TOOLS",
    # Combined
    "ALL_TOOLS",
    # Health Coach tools (read-only with clinical history access)
    "HEALTH_COACH_TOOLS",
]
