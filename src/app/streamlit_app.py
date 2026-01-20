"""
Streamlit chat interface for Patient Digital Twin.

Provides:
- Patient selection
- Health profile sidebar
- Chat interface with Medical Assistant
- Consultation audit log viewer
"""

import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env file BEFORE setting up logging so LOG_LEVEL is available
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

import streamlit as st

from src.agents import MedicalAssistant
from src.database import get_db
from src.database.repositories import AuditLogRepository, PatientRepository
from src.logging_config import get_logger, setup_logging

# Initialize logging at app startup
setup_logging()
logger = get_logger("app.streamlit")


def ensure_patients_indexed():
    """Ensure all patients are indexed in the vector store for RAG search."""
    from src.rag import get_retriever
    from src.rag.vectorstore import get_vectorstore

    retriever = get_retriever()
    vectorstore = get_vectorstore()

    with get_db() as db:
        patients = PatientRepository.get_all(db)
        indexed_count = 0
        for patient in patients:
            doc_count = vectorstore.get_document_count(patient.id)
            if doc_count == 0:
                logger.info(f"Auto-indexing patient {patient.id} (no documents in vector store)")
                retriever.index_patient(db, patient.id)
                indexed_count += 1
        if indexed_count > 0:
            logger.info(f"Auto-indexed {indexed_count} patients for RAG search")


# Auto-index patients on startup if needed
ensure_patients_indexed()

# Page configuration
st.set_page_config(
    page_title="Patient Digital Twin",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "patient_id" not in st.session_state:
        st.session_state.patient_id = None
    if "patient_name" not in st.session_state:
        st.session_state.patient_name = None


def display_patient_profile(patient_id):
    """Display patient profile in sidebar."""
    with get_db() as db:
        profile = PatientRepository.get_profile(db, patient_id)
        if not profile:
            st.warning("Patient not found")
            return

        patient = profile.patient

        # Demographics
        st.subheader("📋 Demographics")
        st.write(f"**Age:** {patient.age} years old")
        st.write(f"**Gender:** {patient.gender.value.capitalize()}")

        # Active Conditions
        st.subheader("🩺 Conditions")
        active_conditions = [c for c in profile.conditions if c.clinical_status == "active"]
        if active_conditions:
            for condition in active_conditions:
                severity_emoji = {
                    "mild": "🟢",
                    "moderate": "🟡",
                    "severe": "🔴",
                }.get(condition.severity, "⚪")
                st.write(f"{severity_emoji} **{condition.display_name}**")
                if condition.notes:
                    st.caption(condition.notes)
        else:
            st.write("No active conditions")

        # Medications
        st.subheader("💊 Medications")
        active_meds = [m for m in profile.medications if m.status == "active"]
        if active_meds:
            for med in active_meds:
                dosage = f" {med.dosage}" if med.dosage else ""
                freq = f" ({med.frequency})" if med.frequency else ""
                st.write(f"**{med.display_name}**{dosage}{freq}")
                if med.reason:
                    st.caption(f"For: {med.reason}")
        else:
            st.write("No active medications")

        # Allergies
        st.subheader("⚠️ Allergies")
        if profile.allergies:
            for allergy in profile.allergies:
                crit_emoji = {"high": "🔴", "low": "🟡"}.get(allergy.criticality, "⚪")
                st.write(f"{crit_emoji} **{allergy.substance}**")
                if allergy.reaction:
                    st.caption(allergy.reaction)
        else:
            st.write("No known allergies")


def display_audit_log(patient_id):
    """Display consultation audit log."""
    with get_db() as db:
        logs = AuditLogRepository.get_by_patient(db, patient_id, limit=10)

        if not logs:
            st.info("No consultations yet")
            return

        for log in logs:
            with st.expander(
                f"📋 {log.specialist_type.replace('_', ' ').title()} - {log.timestamp.strftime('%Y-%m-%d %H:%M')}"
            ):
                st.write("**Question:**")
                st.write(log.clinical_question)

                st.write("**Data Shared (De-identified):**")
                st.json(log.data_shared)

                st.write("**Specialist Response:**")
                if isinstance(log.specialist_response, dict):
                    st.write(f"*Assessment:* {log.specialist_response.get('assessment', 'N/A')}")
                    if log.specialist_response.get("recommendations"):
                        st.write("*Recommendations:*")
                        for rec in log.specialist_response["recommendations"]:
                            st.write(f"- [{rec.get('priority', 'N/A').upper()}] {rec.get('action', 'N/A')}")


def get_suggested_prompts():
    """Return suggested prompts for the user."""
    return [
        ("📋 My conditions", "What conditions do I have?"),
        ("💊 My medications", "What medications am I taking?"),
        ("🩺 Symptom question", "I've been having some dizziness when I stand up. Should I be worried?"),
        ("➕ Add information", "I was just diagnosed with high cholesterol last month"),
    ]


def main():
    """Main application entry point."""
    logger.debug("Starting main application")
    init_session_state()

    # Sidebar
    with st.sidebar:
        st.title("🏥 Patient Digital Twin")
        st.markdown("---")

        # Patient Selection
        st.subheader("Select Patient")
        with get_db() as db:
            patients = PatientRepository.get_all(db)
            patient_options = {f"{p.first_name} {p.last_name}": str(p.id) for p in patients}

        if not patient_options:
            logger.warning("No patients found in database")
            st.warning("No patients found. Please seed the database first.")
            st.code("python -m src.database.seed")
            return

        selected_name = st.selectbox(
            "Patient",
            options=list(patient_options.keys()),
            key="patient_selector",
        )

        if selected_name:
            new_patient_id = patient_options[selected_name]
            if new_patient_id != st.session_state.patient_id:
                logger.info(f"Patient changed: {selected_name} (id={new_patient_id})")
                st.session_state.patient_id = new_patient_id
                st.session_state.patient_name = selected_name
                st.session_state.messages = []
                st.rerun()

        st.markdown("---")

        # Profile display
        if st.session_state.patient_id:
            display_patient_profile(st.session_state.patient_id)

            st.markdown("---")

            # Audit log
            with st.expander("📜 Consultation Log"):
                display_audit_log(st.session_state.patient_id)

    # Main content area
    if not st.session_state.patient_id:
        st.info("👈 Please select a patient from the sidebar to begin.")
        return

    st.title(f"Chat with {st.session_state.patient_name}'s Medical Assistant")

    # Suggested prompts
    st.caption("Try asking:")
    cols = st.columns(4)
    for i, (label, prompt) in enumerate(get_suggested_prompts()):
        with cols[i]:
            if st.button(label, key=f"prompt_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.rerun()

    st.markdown("---")

    # Display message history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Check if we need to generate a response (last message is from user without response)
    needs_response = (
        st.session_state.messages
        and st.session_state.messages[-1]["role"] == "user"
    )

    # Chat input
    if prompt := st.chat_input("How can I help you today?"):
        # Add user message
        logger.info(f"User submitted chat message: length={len(prompt)}")
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        needs_response = True
        user_prompt = prompt
    elif needs_response:
        user_prompt = st.session_state.messages[-1]["content"]
    else:
        user_prompt = None

    # Get agent response if needed
    if needs_response and user_prompt:
        logger.debug(f"Generating response for patient={st.session_state.patient_id}")
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    from uuid import UUID

                    agent = MedicalAssistant(UUID(st.session_state.patient_id))
                    response = agent.chat(user_prompt, st.session_state.messages[:-1])
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    logger.info(f"Agent response generated: length={len(response)}")
                except Exception as e:
                    logger.error(f"Error generating response: {e}", exc_info=True)
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


if __name__ == "__main__":
    main()
