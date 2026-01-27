"""
Streamlit chat interface for Patient Digital Twin.

Provides:
- Secure authentication (login/logout)
- Patient selection
- Agent selection (Medical Assistant or Health Coach)
- Health profile sidebar
- Chat interface with selected agent
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
import streamlit_authenticator as stauth
import plotly.express as px
import plotly.graph_objects as go

from src.agents import HealthCoach, MedicalAssistant
from src.database import get_db
from src.database.repositories import (
    AuditLogRepository,
    ConversationRepository,
    ConversationSessionRepository,
    PatientMemberRepository,
    PatientRepository,
    UserRepository,
)
from src.schemas import UserRole
from src.logging_config import get_logger, setup_logging

# Initialize logging at app startup
setup_logging()
logger = get_logger("app.streamlit")


def get_authenticator():
    """Create and return the authenticator instance.

    Uses database credentials if available, falls back to secrets for backwards compatibility.
    """
    credentials = {"usernames": {}}

    # Try to load credentials from database first
    try:
        with get_db() as db:
            users = UserRepository.get_all(db, active_only=True)
            if users:
                for user in users:
                    credentials["usernames"][user.username] = {
                        "name": user.name,
                        "email": user.email,
                        "password": user.hashed_password,  # Already hashed
                    }
                logger.debug(f"Loaded {len(users)} users from database")
    except Exception as e:
        logger.warning(f"Could not load users from database: {e}")

    # Fall back to secrets if no database users
    if not credentials["usernames"]:
        if "credentials" in st.secrets and "usernames" in st.secrets["credentials"]:
            for username, user_data in st.secrets["credentials"]["usernames"].items():
                credentials["usernames"][username] = {
                    "name": user_data["name"],
                    "email": user_data["email"],
                    "password": user_data["password"],
                }
            logger.debug("Using credentials from secrets (fallback)")

    # Create authenticator
    authenticator = stauth.Authenticate(
        credentials,
        st.secrets["auth"]["cookie_name"],
        st.secrets["auth"]["cookie_key"],
        st.secrets["auth"]["cookie_expiry_days"],
    )

    return authenticator


def get_user_from_db(username: str) -> dict | None:
    """Get user info from database by username.

    Returns a dict with user data to avoid detached instance issues.
    """
    try:
        with get_db() as db:
            user = UserRepository.get_by_username(db, username)
            if user:
                return {
                    "id": str(user.id),
                    "username": user.username,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                    "is_active": user.is_active,
                }
            return None
    except Exception:
        return None


# Agent access based on user role
AGENT_ACCESS = {
    "admin": ["Medical Assistant", "Health Coach"],
    "doctor": ["Medical Assistant"],
    "patient": ["Medical Assistant", "Health Coach"],
    "caregiver": ["Medical Assistant"],
}


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


# Page configuration
st.set_page_config(
    page_title="Patient Digital Twin",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS enhancements (theme-agnostic, works with Streamlit's built-in light/dark) ---
CUSTOM_CSS = """
<style>
/* Chat messages */
div[data-testid="stChatMessage"] {
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
}

/* Chat input */
.stChatInput > div {
    border-radius: 12px !important;
}

/* Metric cards */
div[data-testid="stMetric"] {
    border-radius: 10px;
    padding: 1rem;
}

/* Buttons */
.stButton > button {
    border-radius: 8px;
    transition: all 0.2s ease;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    padding: 8px 16px;
}

/* Expanders */
.streamlit-expanderHeader {
    border-radius: 8px;
}

/* Selectbox and inputs */
.stSelectbox > div > div,
.stTextInput > div > div {
    border-radius: 8px;
}

/* Radio buttons */
.stRadio > div {
    border-radius: 8px;
    padding: 0.5rem;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 6px;
}
::-webkit-scrollbar-thumb {
    border-radius: 3px;
}

/* Alert boxes */
.stAlert {
    border-radius: 10px;
}
</style>
"""


def apply_theme():
    """Apply custom CSS enhancements."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "patient_id" not in st.session_state:
        st.session_state.patient_id = None
    if "patient_name" not in st.session_state:
        st.session_state.patient_name = None
    if "agent_type" not in st.session_state:
        st.session_state.agent_type = "Medical Assistant"
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "session_list_refresh" not in st.session_state:
        st.session_state.session_list_refresh = 0
    if "editing_session_id" not in st.session_state:
        st.session_state.editing_session_id = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = "patient"  # Default to patient role
    if "user_id" not in st.session_state:
        st.session_state.user_id = None  # Database user UUID
    if "llm_provider" not in st.session_state:
        st.session_state.llm_provider = "anthropic"  # Default to Claude
    if "llm_model" not in st.session_state:
        st.session_state.llm_model = "claude-sonnet-4-20250514"


# Available models per provider
LLM_PROVIDER_MODELS = {
    "anthropic": [
        ("claude-sonnet-4-20250514", "Claude Sonnet 4"),
        ("claude-opus-4-20250514", "Claude Opus 4"),
    ],
    "google": [
        ("gemini-2.5-pro", "Gemini 2.5 Pro"),
        ("gemini-2.0-flash", "Gemini 2.0 Flash"),
        ("gemini-1.5-pro", "Gemini 1.5 Pro"),
    ],
    "openai": [
        ("gpt-4o", "GPT-4o"),
        ("gpt-4-turbo", "GPT-4 Turbo"),
        ("gpt-4o-mini", "GPT-4o Mini"),
    ],
}


def get_conversation_mode():
    """Get conversation mode from agent type."""
    if st.session_state.agent_type == "Health Coach":
        return "coach"
    return "clinical"


def generate_session_title(first_message: str) -> str:
    """Generate a session title from the first user message."""
    # Truncate and clean the message for title
    title = first_message.strip()
    if len(title) > 50:
        title = title[:47] + "..."
    return title


def load_session(session_id):
    """Load a session's messages into session state."""
    from uuid import UUID

    with get_db() as db:
        session = ConversationSessionRepository.get_by_id(db, UUID(session_id))
        if not session:
            logger.warning(f"Session {session_id} not found")
            return

        messages = ConversationRepository.get_messages_by_session(db, UUID(session_id))
        st.session_state.messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]
        st.session_state.current_session_id = session_id
        logger.info(f"Loaded session {session_id} with {len(messages)} messages")


def create_new_session():
    """Create a new conversation session."""
    from uuid import UUID

    if not st.session_state.patient_id:
        return None

    mode = get_conversation_mode()
    with get_db() as db:
        session = ConversationSessionRepository.create(
            db,
            patient_id=UUID(st.session_state.patient_id),
            mode=mode,
        )
        db.commit()
        st.session_state.current_session_id = str(session.id)
        logger.info(f"Created new session {session.id} for mode {mode}")
        return str(session.id)


def save_message_to_db(role: str, content: str):
    """Save a message to the database."""
    from uuid import UUID

    if not st.session_state.patient_id:
        return

    # Create session if needed
    if not st.session_state.current_session_id:
        session_id = create_new_session()
        if not session_id:
            return

        # Set title from first user message
        if role == "user":
            with get_db() as db:
                ConversationSessionRepository.update_title(
                    db, UUID(session_id), generate_session_title(content)
                )
                db.commit()

    with get_db() as db:
        message = ConversationRepository.add_message(
            db,
            patient_id=UUID(st.session_state.patient_id),
            role=role,
            content=content,
            session_id=UUID(st.session_state.current_session_id) if st.session_state.current_session_id else None,
        )
        db.commit()

        # Index clinical assistant messages for Health Coach RAG access
        mode = get_conversation_mode()
        if mode == "clinical" and role == "assistant":
            from src.rag import get_retriever
            retriever = get_retriever()
            retriever.index_conversation_message(
                patient_id=UUID(st.session_state.patient_id),
                message_id=message.id,
                content=content,
                mode=mode,
                role=role,
            )
            logger.debug(f"Indexed clinical message {message.id} for RAG")


def start_new_chat():
    """Start a new chat session."""
    st.session_state.messages = []
    st.session_state.current_session_id = None
    st.session_state.session_list_refresh += 1


def delete_session(session_id: str):
    """Delete a conversation session."""
    from uuid import UUID

    with get_db() as db:
        ConversationSessionRepository.delete(db, UUID(session_id))
        db.commit()
        logger.info(f"Deleted session {session_id}")

    # If we deleted the current session, clear the chat
    if st.session_state.current_session_id == session_id:
        st.session_state.messages = []
        st.session_state.current_session_id = None

    st.session_state.session_list_refresh += 1


def rename_session(session_id: str, new_title: str):
    """Rename a conversation session."""
    from uuid import UUID

    if not new_title.strip():
        return

    with get_db() as db:
        ConversationSessionRepository.update_title(db, UUID(session_id), new_title.strip())
        db.commit()
        logger.info(f"Renamed session {session_id} to '{new_title}'")

    st.session_state.editing_session_id = None
    st.session_state.session_list_refresh += 1


def display_conversation_sidebar():
    """Display conversation session sidebar section."""
    from uuid import UUID

    if not st.session_state.patient_id:
        return

    st.subheader("💬 Conversations")

    # New Chat button
    if st.button("➕ New Chat", key="new_chat_btn", use_container_width=True):
        start_new_chat()
        st.rerun()

    mode = get_conversation_mode()
    mode_label = "Clinical" if mode == "clinical" else "Coach"

    with get_db() as db:
        summaries = ConversationSessionRepository.get_session_summaries(
            db,
            patient_id=UUID(st.session_state.patient_id),
            mode=mode,
            limit=10,
        )

    if not summaries:
        st.caption(f"No {mode_label} conversations yet")
        return

    st.caption(f"Recent {mode_label} conversations:")

    for summary in summaries:
        session_id_str = str(summary.id)
        is_current = session_id_str == st.session_state.current_session_id
        is_editing = st.session_state.editing_session_id == session_id_str

        # Build button label
        title = summary.title or summary.preview or "Untitled"
        full_title = title  # Keep full title for editing
        if len(title) > 25:
            title = title[:22] + "..."

        # Show date
        date_str = summary.created_at.strftime("%m/%d")

        # Check if we're editing this session
        if is_editing:
            # Show rename input
            col_input, col_btns = st.columns([3, 1])
            with col_input:
                new_title = st.text_input(
                    "Rename",
                    value=full_title,
                    key=f"rename_input_{session_id_str}",
                    label_visibility="collapsed",
                )
            with col_btns:
                if st.button("✓", key=f"save_rename_{session_id_str}", help="Save"):
                    rename_session(session_id_str, new_title)
                    st.rerun()
            # Cancel button
            if st.button("Cancel", key=f"cancel_rename_{session_id_str}", use_container_width=True):
                st.session_state.editing_session_id = None
                st.rerun()
        else:
            # Normal session display with action buttons
            col_btn, col_edit, col_del = st.columns([6, 1, 1])

            with col_btn:
                btn_label = f"{'▶ ' if is_current else ''}{title}"
                btn_help = f"{date_str} • {summary.message_count} messages"

                if st.button(
                    btn_label,
                    key=f"session_{session_id_str}",
                    use_container_width=True,
                    type="primary" if is_current else "secondary",
                    help=btn_help,
                ):
                    if not is_current:
                        load_session(session_id_str)
                        st.rerun()

            with col_edit:
                if st.button("✏️", key=f"edit_{session_id_str}", help="Rename"):
                    st.session_state.editing_session_id = session_id_str
                    st.rerun()

            with col_del:
                if st.button("🗑️", key=f"delete_{session_id_str}", help="Delete"):
                    delete_session(session_id_str)
                    st.rerun()


def display_patient_summary_card(patient_id):
    """Display compact patient summary card in sidebar."""
    with get_db() as db:
        profile = PatientRepository.get_profile(db, patient_id)
        if not profile:
            return

        patient = profile.patient
        active_conditions = [c for c in profile.conditions if c.clinical_status == "active"]
        active_meds = [m for m in profile.medications if m.status == "active"]

        st.markdown(
            f"**{patient.age}y** {patient.gender.value.capitalize()} · "
            f"{len(active_conditions)} conditions · "
            f"{len(active_meds)} meds · "
            f"{len(profile.allergies)} allergies"
        )


def display_health_record_tab(patient_id):
    """Display full health record in main content area."""
    with get_db() as db:
        profile = PatientRepository.get_profile(db, patient_id)
        if not profile:
            st.warning("Patient not found")
            return

        patient = profile.patient

        # Demographics
        st.subheader("📋 Demographics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Age", f"{patient.age} years")
        col2.metric("Gender", patient.gender.value.capitalize())
        col3.metric("Name", f"{patient.first_name} {patient.last_name}")

        # Two-column layout for conditions and medications
        col_left, col_right = st.columns(2)

        with col_left:
            # Conditions
            st.subheader("🩺 Conditions")
            active_conditions = [c for c in profile.conditions if c.clinical_status == "active"]
            if active_conditions:
                for condition in active_conditions:
                    severity_emoji = {
                        "mild": "🟢", "moderate": "🟡", "severe": "🔴",
                    }.get(condition.severity, "⚪")
                    st.write(f"{severity_emoji} **{condition.display_name}**")
                    if condition.notes:
                        st.caption(condition.notes)
            else:
                st.write("No active conditions")

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

        with col_right:
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

            # Family History
            st.subheader("👨‍👩‍👧 Family History")
            if profile.family_history:
                for fh in profile.family_history:
                    onset = f" (age {fh.onset_age})" if fh.onset_age else ""
                    st.write(f"**{fh.relation.replace('_', ' ').title()}**: {fh.condition_name}{onset}")
                    if fh.notes:
                        st.caption(fh.notes)
            else:
                st.write("No family history recorded")

        # Vital Signs (full width)
        st.subheader("❤️ Vital Signs")
        if profile.vital_signs:
            latest = profile.vital_signs[0] if profile.vital_signs else None
            if latest:
                vs_cols = st.columns(5)
                if latest.systolic_bp and latest.diastolic_bp:
                    vs_cols[0].metric("Blood Pressure", f"{latest.systolic_bp}/{latest.diastolic_bp}")
                if latest.heart_rate:
                    vs_cols[1].metric("Heart Rate", f"{latest.heart_rate} bpm")
                if latest.temperature:
                    vs_cols[2].metric("Temperature", f"{latest.temperature}°C")
                if latest.oxygen_saturation:
                    vs_cols[3].metric("SpO2", f"{latest.oxygen_saturation}%")
                if latest.weight_kg:
                    vs_cols[4].metric("Weight", f"{latest.weight_kg} kg")
                if latest.recorded_at:
                    st.caption(f"Recorded: {latest.recorded_at.strftime('%Y-%m-%d %H:%M')}")
        else:
            st.write("No vital signs recorded")

        # Lab Results (full width)
        st.subheader("🧪 Lab Results")
        if profile.lab_results:
            for lab in profile.lab_results[:10]:
                interp_emoji = {
                    "normal": "🟢", "abnormal": "🟡", "critical": "🔴",
                }.get(lab.interpretation, "⚪")
                value_str = f"{lab.value}"
                if lab.unit:
                    value_str += f" {lab.unit}"
                ref_str = ""
                if lab.reference_range_low is not None and lab.reference_range_high is not None:
                    ref_str = f" (ref: {lab.reference_range_low}-{lab.reference_range_high})"
                date_str = f" — {lab.result_date.strftime('%Y-%m-%d')}" if lab.result_date else ""
                st.write(f"{interp_emoji} **{lab.test_name}**: {value_str}{ref_str}{date_str}")
        else:
            st.write("No lab results recorded")

        # Social History (full width)
        st.subheader("🏠 Social History")
        if profile.social_history:
            for sh in profile.social_history:
                status_emoji = {
                    "current": "🔵", "former": "🟡", "never": "🟢", "daily": "🔴",
                }.get(sh.status, "⚪")
                cat = sh.category.replace("_", " ").title()
                st.write(f"{status_emoji} **{cat}**: {sh.status.capitalize()}")
                if sh.description:
                    st.caption(sh.description)
        else:
            st.write("No social history recorded")


def display_member_management(patient_id):
    """Display access management section."""
    from uuid import UUID

    user_role = st.session_state.get("user_role", "patient")
    can_manage = user_role in ("admin", "doctor", "caregiver")

    with st.expander("👥 Manage Access", expanded=False):
        with get_db() as db:
            members = PatientMemberRepository.get_members_by_patient(db, UUID(patient_id))

            if not members:
                st.info("No users assigned to this patient")
            else:
                st.caption("Current access:")
                for member in members:
                    col_name, col_role, col_del = st.columns([3, 1, 1])

                    with col_name:
                        st.write(f"**{member.user.name}**")
                        st.caption(f"@{member.user.username}")

                    with col_role:
                        role_emoji = {
                            "admin": "🔑",
                            "doctor": "👨‍⚕️",
                            "patient": "🧑",
                            "caregiver": "👥",
                        }.get(member.user.role, "👤")
                        st.write(f"{role_emoji} {member.user.role.capitalize()}")

                    with col_del:
                        # Remove button (managers only, can't remove self)
                        if can_manage and str(member.user_id) != st.session_state.user_id:
                            if st.button(
                                "✕",
                                key=f"remove_{member.user_id}_{patient_id}",
                                help=f"Remove {member.user.name}",
                            ):
                                PatientMemberRepository.remove_member(
                                    db, member.user_id, UUID(patient_id)
                                )
                                db.commit()
                                st.success(f"Removed {member.user.name}")
                                st.rerun()

                    st.markdown("---")

            # Add user section (admin, doctor, caregiver)
            if can_manage:
                st.subheader("Add User")
                all_users = UserRepository.get_all(db)
                member_user_ids = {str(m.user_id) for m in members}
                # Exclude admins (they see all automatically) and existing members
                available_users = [
                    u for u in all_users
                    if str(u.id) not in member_user_ids and u.role != "admin"
                ]

                if available_users:
                    user_options = {
                        f"{u.name} (@{u.username}) - {u.role}": str(u.id)
                        for u in available_users
                    }
                    selected_user = st.selectbox(
                        "Select User",
                        options=list(user_options.keys()),
                        key="add_member_user",
                    )

                    if st.button("Add User", type="primary", use_container_width=True):
                        from src.schemas import PatientMemberCreate
                        PatientMemberRepository.add_member(
                            db,
                            PatientMemberCreate(
                                user_id=UUID(user_options[selected_user]),
                                patient_id=UUID(patient_id),
                            ),
                        )
                        db.commit()
                        st.success(f"Added {selected_user}")
                        st.rerun()
                else:
                    st.info("All eligible users are already assigned")


def display_audit_log(patient_id):
    """Display consultation audit log with visual cards."""
    with get_db() as db:
        logs = AuditLogRepository.get_by_patient(db, patient_id, limit=10)

        if not logs:
            st.info("No consultations yet")
            return

        for log in logs:
            with st.expander(
                f"📋 {log.specialist_type.replace('_', ' ').title()} - {log.timestamp.strftime('%Y-%m-%d %H:%M')}"
            ):
                st.markdown(f"**Question:** {log.clinical_question}")

                # Data shared as compact metrics
                st.markdown("**Data Shared:**")
                data = log.data_shared
                cols = st.columns(4)
                cols[0].metric("Age", data.get("age", "N/A"))
                cols[1].metric("Gender", str(data.get("gender", "N/A")).capitalize())
                cols[2].metric("Conditions", len(data.get("conditions", [])))
                cols[3].metric("Medications", len(data.get("medications", [])))

                # Specialist response
                st.markdown("---")
                if isinstance(log.specialist_response, dict):
                    st.markdown(f"**Assessment:** {log.specialist_response.get('assessment', 'N/A')}")
                    if log.specialist_response.get("recommendations"):
                        st.markdown("**Recommendations:**")
                        for rec in log.specialist_response["recommendations"]:
                            priority = rec.get("priority", "routine")
                            priority_emoji = {"urgent": "🔴", "high": "🟠", "routine": "🟡", "low": "🟢"}.get(priority, "⚪")
                            st.markdown(f"{priority_emoji} **[{priority.upper()}]** {rec.get('action', 'N/A')}")


def display_health_metrics(patient_id):
    """Display health metrics dashboard at top of main area."""
    with get_db() as db:
        profile = PatientRepository.get_profile(db, patient_id)
        if not profile:
            return

        # Get counts
        active_conditions = [c for c in profile.conditions if c.clinical_status == "active"]
        active_meds = [m for m in profile.medications if m.status == "active"]
        allergies = profile.allergies

        # Get last consultation
        logs = AuditLogRepository.get_by_patient(db, patient_id, limit=1)
        last_consult = logs[0].timestamp.strftime("%m/%d") if logs else "None"

        # Display metric cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🩺 Conditions", len(active_conditions))
        with col2:
            st.metric("💊 Medications", len(active_meds))
        with col3:
            st.metric("⚠️ Allergies", len(allergies))
        with col4:
            st.metric("📋 Last Consult", last_consult)


def display_medication_timeline(patient_id):
    """Display medication timeline chart."""
    with get_db() as db:
        profile = PatientRepository.get_profile(db, patient_id)
        if not profile or not profile.medications:
            return

        # Filter medications with start dates
        meds_with_dates = [m for m in profile.medications if m.start_date]
        if not meds_with_dates:
            st.info("No medication timeline data available")
            return

        # Prepare data for timeline
        data = []
        for med in meds_with_dates:
            end_date = med.end_date if med.end_date else "2026-12-31"
            data.append({
                "Medication": med.display_name,
                "Start": med.start_date.isoformat() if hasattr(med.start_date, 'isoformat') else str(med.start_date),
                "End": end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date),
                "Status": med.status.capitalize() if med.status else "Active",
            })

        if data:
            fig = px.timeline(
                data,
                x_start="Start",
                x_end="End",
                y="Medication",
                color="Status",
                title="Medication Timeline",
                color_discrete_map={"Active": "#4CAF50", "Completed": "#9E9E9E", "Stopped": "#F44336"},
            )
            fig.update_layout(height=max(200, len(data) * 40))
            st.plotly_chart(fig, use_container_width=True)


def display_severity_chart(patient_id):
    """Display condition severity distribution donut chart."""
    with get_db() as db:
        profile = PatientRepository.get_profile(db, patient_id)
        if not profile or not profile.conditions:
            return

        active_conditions = [c for c in profile.conditions if c.clinical_status == "active"]
        if not active_conditions:
            return

        # Count severities
        severity_counts = {"Mild": 0, "Moderate": 0, "Severe": 0, "Unknown": 0}
        for c in active_conditions:
            severity = (c.severity or "unknown").capitalize()
            if severity in severity_counts:
                severity_counts[severity] += 1
            else:
                severity_counts["Unknown"] += 1

        # Remove zeros
        severity_counts = {k: v for k, v in severity_counts.items() if v > 0}

        if severity_counts:
            fig = go.Figure(data=[go.Pie(
                labels=list(severity_counts.keys()),
                values=list(severity_counts.values()),
                hole=0.4,
                marker_colors=["#90EE90", "#FFD700", "#FF6B6B", "#CCCCCC"],
            )])
            fig.update_layout(
                title="Condition Severity",
                height=300,
                showlegend=True,
            )
            st.plotly_chart(fig, use_container_width=True)


def display_consultation_history_chart(patient_id):
    """Display consultation history bar chart."""
    with get_db() as db:
        logs = AuditLogRepository.get_by_patient(db, patient_id, limit=50)

        if not logs:
            st.info("No consultation history to display")
            return

        # Group by month
        monthly = {}
        for log in logs:
            month = log.timestamp.strftime("%Y-%m")
            monthly[month] = monthly.get(month, 0) + 1

        if monthly:
            fig = px.bar(
                x=list(monthly.keys()),
                y=list(monthly.values()),
                title="Consultations Over Time",
                labels={"x": "Month", "y": "Consultations"},
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)


def get_medical_assistant_prompts():
    """Return categorized prompts for Medical Assistant."""
    return {
        "📋 My Health Records": [
            "What conditions do I have?",
            "What medications am I taking?",
            "What are my allergies?",
        ],
        "🩺 Symptoms & Concerns": [
            "I've been having dizziness when I stand up. Should I be worried?",
            "I'm experiencing chest tightness after exercise. What should I do?",
            "I've noticed increased fatigue lately. Could it be related to my conditions?",
        ],
        "➕ Add Information": [
            "I was just diagnosed with high cholesterol last month",
            "I started taking a new vitamin D supplement",
            "I developed a rash after eating shellfish",
        ],
    }


def get_health_coach_prompts():
    """Return categorized prompts for Health Coach."""
    return {
        "🌿 Understand My Health": [
            "Can you explain what my conditions mean in simple terms?",
            "How do my medications work and why are they important?",
            "What should I know about managing my health day-to-day?",
        ],
        "🥗 Lifestyle & Wellness": [
            "What diet changes would help with my conditions?",
            "What exercises are safe and beneficial for me?",
            "How can I improve my sleep and manage stress?",
        ],
        "💪 Stay Motivated": [
            "I'm struggling to stick to my medication routine. Any tips?",
            "How can I stay motivated with my health goals?",
            "What small changes can make a big difference?",
        ],
    }


def get_suggested_prompts():
    """Return suggested prompts based on selected agent type."""
    if st.session_state.agent_type == "Health Coach":
        return get_health_coach_prompts()
    return get_medical_assistant_prompts()


def main():
    """Main application entry point."""
    logger.debug("Starting main application")

    # Apply theme CSS
    apply_theme()

    # Initialize authenticator
    authenticator = get_authenticator()

    # Show login form
    try:
        authenticator.login(location="main")
    except Exception as e:
        st.error(f"Authentication error: {e}")
        logger.error(f"Authentication error: {e}")
        return

    # Check authentication status
    if st.session_state.get("authentication_status") is None:
        st.warning("Please enter your username and password")
        st.info("**Demo Credentials:**\n- `admin` / `admin123` (Admin)\n- `drsmith` / `doctor123` (Doctor)\n- `maria` / `patient123` (Patient)\n- `jamescaregiver` / `caregiver123` (Caregiver)")
        return
    elif st.session_state.get("authentication_status") is False:
        st.error("Username/password is incorrect")
        return

    # User is authenticated - proceed with app
    logger.info(f"User logged in: {st.session_state.get('username')}")
    init_session_state()

    # Get user from database and store user_id and role
    db_user = get_user_from_db(st.session_state.get("username", ""))
    if db_user:
        st.session_state.user_id = db_user["id"]
        st.session_state.user_role = db_user["role"]
    else:
        st.session_state.user_id = None
        st.session_state.user_role = "patient"

    # Auto-index patients on startup if needed (only once per session)
    if "patients_indexed" not in st.session_state:
        try:
            ensure_patients_indexed()
            st.session_state.patients_indexed = True
        except Exception as e:
            logger.error(f"Failed to index patients: {e}")
            st.error(f"Database connection error: {e}\n\nPlease ensure DATABASE_URL is configured in your Streamlit secrets.")
            return

    # Sidebar — compact context panel
    with st.sidebar:
        from uuid import UUID

        # Header: welcome + logout
        st.markdown(f"### 🏥 {st.session_state.get('name', 'User')}")
        st.caption(f"{st.session_state.user_role.capitalize()}")
        authenticator.logout("Logout", "sidebar")
        st.markdown("---")

        # Patient Selection
        with get_db() as db:
            if st.session_state.user_role == "admin":
                patients = PatientRepository.get_all(db)
            elif st.session_state.user_id:
                patients = PatientMemberRepository.get_patients_for_user(
                    db, UUID(st.session_state.user_id)
                )
            else:
                patients = PatientRepository.get_all(db)
            patient_options = {f"{p.first_name} {p.last_name}": str(p.id) for p in patients}

        if not patient_options:
            logger.warning("No patients found in database")
            st.warning("No patients found. Please seed the database first.")
            st.code("python -m src.database.seed")
            return

        # Only show selector if multiple patients
        if len(patient_options) > 1:
            selected_name = st.selectbox(
                "Patient",
                options=list(patient_options.keys()),
                key="patient_selector",
            )
        else:
            selected_name = list(patient_options.keys())[0]

        if selected_name:
            new_patient_id = patient_options[selected_name]
            if new_patient_id != st.session_state.patient_id:
                logger.info(f"Patient changed: {selected_name} (id={new_patient_id})")
                st.session_state.patient_id = new_patient_id
                st.session_state.patient_name = selected_name
                st.session_state.messages = []
                st.session_state.current_session_id = None
                st.rerun()

        # Agent Selection — only show if role has multiple agents
        agent_options = AGENT_ACCESS.get(st.session_state.user_role, ["Medical Assistant"])
        if st.session_state.agent_type not in agent_options:
            st.session_state.agent_type = agent_options[0]

        if len(agent_options) > 1:
            selected_agent = st.radio(
                "Agent",
                options=agent_options,
                index=agent_options.index(st.session_state.agent_type),
                key="agent_selector",
                horizontal=True,
                help="**Medical Assistant**: Clinical questions, specialist consultations\n\n"
                     "**Health Coach**: Health education, lifestyle tips",
            )
            if selected_agent != st.session_state.agent_type:
                logger.info(f"Agent changed: {selected_agent}")
                st.session_state.agent_type = selected_agent
                st.session_state.messages = []
                st.session_state.current_session_id = None
                st.rerun()

        # Compact mode badge
        if st.session_state.agent_type == "Medical Assistant":
            st.caption("🩺 Clinical Mode")
        else:
            st.caption("💪 Coaching Mode")

        st.markdown("---")

        # Patient summary card
        if st.session_state.patient_id:
            display_patient_summary_card(st.session_state.patient_id)
            st.markdown("---")

        # Conversations
        display_conversation_sidebar()

        st.markdown("---")

        # Access Management — admin/doctor/caregiver only
        if st.session_state.patient_id and st.session_state.user_role in ("admin", "doctor", "caregiver"):
            display_member_management(st.session_state.patient_id)
            st.markdown("---")

        # LLM Settings — collapsed expander
        with st.expander("🤖 LLM Settings", expanded=False):
            provider_options = list(LLM_PROVIDER_MODELS.keys())
            provider_labels = {"anthropic": "Anthropic (Claude)", "google": "Google (Gemini)", "openai": "OpenAI (GPT)"}

            def on_provider_change():
                new_provider = st.session_state.provider_selector
                logger.info(f"Provider changed: {new_provider}")
                st.session_state.llm_provider = new_provider
                first_model = LLM_PROVIDER_MODELS[new_provider][0][0]
                st.session_state.llm_model = first_model
                st.session_state.model_selector = first_model

            st.selectbox(
                "Provider",
                options=provider_options,
                format_func=lambda x: provider_labels.get(x, x),
                index=provider_options.index(st.session_state.llm_provider),
                key="provider_selector",
                on_change=on_provider_change,
            )

            model_options = LLM_PROVIDER_MODELS[st.session_state.llm_provider]
            model_ids = [m[0] for m in model_options]
            model_labels = {m[0]: m[1] for m in model_options}

            if st.session_state.llm_model not in model_ids:
                st.session_state.llm_model = model_ids[0]

            def on_model_change():
                new_model = st.session_state.model_selector
                logger.info(f"Model changed: {new_model}")
                st.session_state.llm_model = new_model

            st.selectbox(
                "Model",
                options=model_ids,
                format_func=lambda x: model_labels.get(x, x),
                index=model_ids.index(st.session_state.llm_model),
                key="model_selector",
                on_change=on_model_change,
            )

            st.caption(f"Using: {model_labels.get(st.session_state.llm_model, st.session_state.llm_model)}")

    # ── Main content area ──
    if not st.session_state.patient_id:
        st.info("Please select a patient from the sidebar to begin.")
        return

    # Title
    agent_emoji = "🩺" if st.session_state.agent_type == "Medical Assistant" else "💪"
    st.title(f"{agent_emoji} {st.session_state.patient_name}'s {st.session_state.agent_type}")

    # Build tabs based on role
    show_audit = st.session_state.user_role in ("admin", "doctor")
    tab_labels = ["💬 Chat", "📋 Health Record", "📊 Visualizations"]
    if show_audit:
        tab_labels.append("📜 Audit Log")

    tabs = st.tabs(tab_labels)

    # ── Tab: Chat ──
    with tabs[0]:
        # Quick actions as compact chips
        if not st.session_state.messages:
            prompt_categories = get_suggested_prompts()
            for category, prompts in prompt_categories.items():
                st.caption(category)
                chip_cols = st.columns(len(prompts))
                for idx, prompt in enumerate(prompts):
                    display_text = prompt if len(prompt) <= 45 else prompt[:42] + "..."
                    with chip_cols[idx]:
                        if st.button(display_text, key=f"chip_{category}_{idx}", use_container_width=True, help=prompt):
                            logger.info(f"Quick action clicked: {prompt[:50]}")
                            st.session_state.messages.append({"role": "user", "content": prompt})
                            save_message_to_db("user", prompt)
                            st.rerun()

    # ── Tab: Health Record ──
    with tabs[1]:
        display_health_record_tab(st.session_state.patient_id)

    # ── Tab: Visualizations ──
    with tabs[2]:
        display_health_metrics(st.session_state.patient_id)
        st.markdown("---")
        viz_col1, viz_col2 = st.columns(2)
        with viz_col1:
            display_severity_chart(st.session_state.patient_id)
        with viz_col2:
            display_consultation_history_chart(st.session_state.patient_id)
        display_medication_timeline(st.session_state.patient_id)

    # ── Tab: Audit Log (admin/doctor only) ──
    if show_audit:
        with tabs[3]:
            st.subheader("Specialist Consultation History")
            display_audit_log(st.session_state.patient_id)

    # ── Chat messages and input (always visible below tabs) ──
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    needs_response = (
        st.session_state.messages
        and st.session_state.messages[-1]["role"] == "user"
    )

    if prompt := st.chat_input("How can I help you today?"):
        logger.info(f"User submitted chat message: length={len(prompt)}")
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_message_to_db("user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)
        needs_response = True
        user_prompt = prompt
    elif needs_response:
        user_prompt = st.session_state.messages[-1]["content"]
    else:
        user_prompt = None

    if needs_response and user_prompt:
        logger.debug(f"Generating response for patient={st.session_state.patient_id}, agent={st.session_state.agent_type}")
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    patient_uuid = UUID(st.session_state.patient_id)
                    if st.session_state.agent_type == "Health Coach":
                        agent = HealthCoach(
                            patient_uuid,
                            provider=st.session_state.llm_provider,
                            model=st.session_state.llm_model,
                        )
                    else:
                        agent = MedicalAssistant(
                            patient_uuid,
                            user_role=st.session_state.user_role,
                            provider=st.session_state.llm_provider,
                            model=st.session_state.llm_model,
                        )

                    response = agent.chat(user_prompt, st.session_state.messages[:-1])
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    save_message_to_db("assistant", response)
                    logger.info(f"Agent response generated: agent={st.session_state.agent_type}, length={len(response)}")
                except Exception as e:
                    logger.error(f"Error generating response: {e}", exc_info=True)
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    save_message_to_db("assistant", error_msg)


if __name__ == "__main__":
    main()
