"""
Tools available to AI agents.

Includes:
- Patient data tools (get profile, add condition/medication/allergy/procedure)
- Consultation tools (consult specialist via MCP)
- RAG search tools
"""

from src.agents.tools.web_search import (
    WEB_SEARCH_TOOLS,
    search_medical_web,
)
from src.agents.tools.consultation import (
    CONSULTATION_TOOLS,
    consult_primary_care,
    consult_cardiology,
    consult_endocrinology,
    consult_pulmonology,
    consult_neurology,
    consult_gastroenterology,
    consult_oncology,
    consult_psychiatry,
    consult_orthopedics,
    consult_nephrology,
    consult_dermatology,
    consult_medical_board,
)
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
    get_procedures,
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
    add_procedure,
    # Update tools
    update_condition,
    update_medication,
    update_allergy,
    update_vital_signs,
    update_lab_result,
    update_family_history,
    update_social_history,
    update_procedure,
    # Delete tools
    delete_condition,
    delete_medication,
    delete_allergy,
    delete_vital_signs,
    delete_lab_result,
    delete_family_history,
    delete_social_history,
    delete_procedure,
)

# All tools available to the Medical Assistant
ALL_TOOLS = PATIENT_DATA_TOOLS + CONSULTATION_TOOLS + WEB_SEARCH_TOOLS

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
    "get_procedures",
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
    "add_procedure",
    # Patient data tools - update
    "update_condition",
    "update_medication",
    "update_allergy",
    "update_vital_signs",
    "update_lab_result",
    "update_family_history",
    "update_social_history",
    "update_procedure",
    # Patient data tools - delete
    "delete_condition",
    "delete_medication",
    "delete_allergy",
    "delete_vital_signs",
    "delete_lab_result",
    "delete_family_history",
    "delete_social_history",
    "delete_procedure",
    "PATIENT_DATA_TOOLS",
    # Consultation tools
    "consult_primary_care",
    "consult_cardiology",
    "consult_endocrinology",
    "consult_pulmonology",
    "consult_neurology",
    "consult_gastroenterology",
    "consult_oncology",
    "consult_psychiatry",
    "consult_orthopedics",
    "consult_nephrology",
    "consult_dermatology",
    "consult_medical_board",
    "CONSULTATION_TOOLS",
    # Web search tools
    "search_medical_web",
    "WEB_SEARCH_TOOLS",
    # Combined
    "ALL_TOOLS",
    # Health Coach tools (read-only with clinical history access)
    "HEALTH_COACH_TOOLS",
]
