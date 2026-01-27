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
from src.schemas import MemberRole
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


def get_user_from_db(username: str):
    """Get user object from database by username."""
    try:
        with get_db() as db:
            return UserRepository.get_by_username(db, username)
    except Exception:
        return None


def get_user_role_for_patient(user_id, patient_id) -> str:
    """Get the user's role for a specific patient."""
    if not user_id or not patient_id:
        return "patient"  # Default fallback
    try:
        from uuid import UUID
        with get_db() as db:
            role = PatientMemberRepository.get_user_role(
                db,
                UUID(str(user_id)),
                UUID(str(patient_id))
            )
            return role if role else "patient"
    except Exception as e:
        logger.warning(f"Could not get user role for patient: {e}")
        return "patient"


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
    return "coach" if st.session_state.agent_type == "Health Coach" else "clinical"


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


def display_member_management(patient_id):
    """Display member management section for doctors."""
    from uuid import UUID

    user_role = st.session_state.get("user_role", "patient")

    with st.expander("👥 Manage Members", expanded=False):
        with get_db() as db:
            members = PatientMemberRepository.get_members_by_patient(db, UUID(patient_id))

            if not members:
                st.info("No members assigned to this patient")
            else:
                st.caption("Current members:")
                for member in members:
                    col_name, col_role, col_actions = st.columns([2, 1, 1])

                    with col_name:
                        st.write(f"**{member.user.name}**")
                        st.caption(f"@{member.user.username}")

                    with col_role:
                        role_emoji = {
                            "doctor": "👨‍⚕️",
                            "patient": "🧑",
                            "caregiver": "👥",
                        }.get(member.role, "👤")
                        st.write(f"{role_emoji} {member.role.capitalize()}")

                    with col_actions:
                        if user_role == "doctor":
                            # Change role dropdown
                            member_key = f"role_{member.user_id}_{patient_id}"
                            new_role = st.selectbox(
                                "Role",
                                options=["doctor", "patient", "caregiver"],
                                index=["doctor", "patient", "caregiver"].index(member.role),
                                key=member_key,
                                label_visibility="collapsed",
                            )
                            if new_role != member.role:
                                PatientMemberRepository.update_role(
                                    db, member.user_id, UUID(patient_id), new_role
                                )
                                db.commit()
                                st.rerun()

                    # Remove button (only for doctors, can't remove self)
                    if user_role == "doctor" and str(member.user_id) != st.session_state.user_id:
                        if st.button(
                            "Remove",
                            key=f"remove_{member.user_id}_{patient_id}",
                            type="secondary",
                        ):
                            PatientMemberRepository.remove_member(
                                db, member.user_id, UUID(patient_id)
                            )
                            db.commit()
                            st.success(f"Removed {member.user.name}")
                            st.rerun()

                    st.markdown("---")

            # Add member section (doctors only)
            if user_role == "doctor":
                st.subheader("Add Member")
                # Get users not already members
                all_users = UserRepository.get_all(db)
                member_user_ids = {str(m.user_id) for m in members}
                available_users = [u for u in all_users if str(u.id) not in member_user_ids]

                if available_users:
                    user_options = {f"{u.name} (@{u.username})": str(u.id) for u in available_users}
                    selected_user = st.selectbox(
                        "Select User",
                        options=list(user_options.keys()),
                        key="add_member_user",
                    )
                    selected_role = st.selectbox(
                        "Role",
                        options=["doctor", "patient", "caregiver"],
                        index=2,  # Default to caregiver
                        key="add_member_role",
                    )

                    if st.button("Add Member", type="primary", use_container_width=True):
                        from src.schemas import PatientMemberCreate
                        PatientMemberRepository.add_member(
                            db,
                            PatientMemberCreate(
                                user_id=UUID(user_options[selected_user]),
                                patient_id=UUID(patient_id),
                                role=MemberRole(selected_role),
                            ),
                        )
                        db.commit()
                        st.success(f"Added {selected_user}")
                        st.rerun()
                else:
                    st.info("All users are already members")


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
        st.info("**Demo Credentials:**\n- Username: `admin`, `doctor`, or `patient`\n- Password: `admin123`, `doctor123`, or `patient123`")
        return
    elif st.session_state.get("authentication_status") is False:
        st.error("Username/password is incorrect")
        return

    # User is authenticated - proceed with app
    logger.info(f"User logged in: {st.session_state.get('username')}")
    init_session_state()

    # Get user from database and store user_id
    db_user = get_user_from_db(st.session_state.get("username", ""))
    if db_user:
        st.session_state.user_id = str(db_user.id)
    else:
        st.session_state.user_id = None

    # Auto-index patients on startup if needed (only once per session)
    if "patients_indexed" not in st.session_state:
        try:
            ensure_patients_indexed()
            st.session_state.patients_indexed = True
        except Exception as e:
            logger.error(f"Failed to index patients: {e}")
            st.error(f"Database connection error: {e}\n\nPlease ensure DATABASE_URL is configured in your Streamlit secrets.")
            return

    # Sidebar
    with st.sidebar:
        # User info and logout at top
        st.markdown(f"### Welcome, {st.session_state.get('name', 'User')}!")
        authenticator.logout("Logout", "sidebar")
        st.markdown("---")

        st.title("🏥 Patient Digital Twin")
        st.markdown("---")

        # Patient Selection - filter by user's membership
        st.subheader("Select Patient")
        with get_db() as db:
            from uuid import UUID
            if st.session_state.user_id:
                # Show only patients the user is a member of
                patients = PatientMemberRepository.get_patients_for_user(
                    db, UUID(st.session_state.user_id)
                )
            else:
                # Fallback to all patients if no database user
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
                st.session_state.current_session_id = None
                # Update user role for the new patient
                st.session_state.user_role = get_user_role_for_patient(
                    st.session_state.user_id, new_patient_id
                )
                st.rerun()

        # Set user role for current patient if not already set
        if st.session_state.patient_id and st.session_state.user_id:
            current_role = get_user_role_for_patient(
                st.session_state.user_id, st.session_state.patient_id
            )
            st.session_state.user_role = current_role
            st.caption(f"Your role: **{current_role.capitalize()}**")

        st.markdown("---")

        # Agent Selection
        st.subheader("Select Agent")
        agent_options = ["Medical Assistant", "Health Coach"]
        selected_agent = st.radio(
            "Agent",
            options=agent_options,
            index=agent_options.index(st.session_state.agent_type),
            key="agent_selector",
            help="**Medical Assistant**: Clinical questions, add health info, consult specialists\n\n"
                 "**Health Coach**: Health education, lifestyle tips, motivation",
        )

        if selected_agent != st.session_state.agent_type:
            logger.info(f"Agent changed: {selected_agent}")
            st.session_state.agent_type = selected_agent
            st.session_state.messages = []
            st.session_state.current_session_id = None
            st.rerun()

        # Agent personality badge
        if st.session_state.agent_type == "Medical Assistant":
            st.info("🩺 **Clinical Mode**\n\nAsk symptoms, add health info, consult specialists")
        else:
            st.success("💪 **Coaching Mode**\n\nHealth education, lifestyle tips, motivation")

        st.markdown("---")

        # User Role Display (based on patient membership)
        st.subheader("👤 Your Permissions")
        user_role = st.session_state.user_role
        if user_role == "doctor":
            st.success("👨‍⚕️ **Doctor Access**\n\n✓ View records\n✓ Add records\n✓ Update records\n✓ Delete records\n✓ Manage members")
        elif user_role == "patient":
            st.info("🧑 **Patient Access**\n\n✓ View records\n✓ Add records\n✗ Update records\n✗ Delete records\n✗ Manage members")
        else:  # caregiver
            st.warning("👥 **Caregiver Access**\n\n✓ View records\n✗ Add records\n✗ Update records\n✗ Delete records\n✗ Manage members")

        st.markdown("---")

        # LLM Provider/Model Selection
        st.subheader("🤖 LLM Settings")

        provider_options = list(LLM_PROVIDER_MODELS.keys())
        provider_labels = {"anthropic": "Anthropic (Claude)", "google": "Google (Gemini)", "openai": "OpenAI (GPT)"}

        selected_provider = st.selectbox(
            "Provider",
            options=provider_options,
            format_func=lambda x: provider_labels.get(x, x),
            index=provider_options.index(st.session_state.llm_provider),
            key="provider_selector",
        )

        if selected_provider != st.session_state.llm_provider:
            logger.info(f"Provider changed: {selected_provider}")
            st.session_state.llm_provider = selected_provider
            # Reset to first model for new provider
            st.session_state.llm_model = LLM_PROVIDER_MODELS[selected_provider][0][0]
            st.rerun()

        # Model selection based on provider
        model_options = LLM_PROVIDER_MODELS[st.session_state.llm_provider]
        model_ids = [m[0] for m in model_options]
        model_labels = {m[0]: m[1] for m in model_options}

        # Ensure current model is valid for selected provider
        if st.session_state.llm_model not in model_ids:
            st.session_state.llm_model = model_ids[0]

        selected_model = st.selectbox(
            "Model",
            options=model_ids,
            format_func=lambda x: model_labels.get(x, x),
            index=model_ids.index(st.session_state.llm_model),
            key="model_selector",
        )

        if selected_model != st.session_state.llm_model:
            logger.info(f"Model changed: {selected_model}")
            st.session_state.llm_model = selected_model
            st.rerun()

        # Show current selection
        st.caption(f"Using: {model_labels.get(st.session_state.llm_model, st.session_state.llm_model)}")

        st.markdown("---")

        # Conversation history sidebar
        display_conversation_sidebar()

        st.markdown("---")

        # Profile display
        if st.session_state.patient_id:
            display_patient_profile(st.session_state.patient_id)

            st.markdown("---")

            # Member management (shown to all, editable by doctors)
            display_member_management(st.session_state.patient_id)

            st.markdown("---")

            # Audit log
            with st.expander("📜 Consultation Log"):
                display_audit_log(st.session_state.patient_id)

        st.markdown("---")

        # Database tools
        st.subheader("🗄️ Database")
        if st.button("Open DBeaver", use_container_width=True, help="Open database in DBeaver"):
            import subprocess
            subprocess.Popen(["open", "-a", "DBeaver"])
            st.toast("Opening DBeaver...", icon="🗄️")

    # Main content area
    if not st.session_state.patient_id:
        st.info("👈 Please select a patient from the sidebar to begin.")
        return

    # Title based on selected agent
    agent_emoji = "🩺" if st.session_state.agent_type == "Medical Assistant" else "💪"
    st.title(f"{agent_emoji} Chat with {st.session_state.patient_name}'s {st.session_state.agent_type}")

    # Health metrics dashboard
    display_health_metrics(st.session_state.patient_id)

    st.markdown("---")

    # Create tabs for Chat and Visualizations
    tab_chat, tab_viz = st.tabs(["💬 Chat", "📊 Visualizations"])

    with tab_viz:
        st.subheader("Health Data Visualizations")
        viz_col1, viz_col2 = st.columns(2)
        with viz_col1:
            display_severity_chart(st.session_state.patient_id)
        with viz_col2:
            display_consultation_history_chart(st.session_state.patient_id)

        display_medication_timeline(st.session_state.patient_id)

    with tab_chat:
        # Quick action prompts by category - send directly when clicked
        st.caption("Quick actions (click to send):")
        prompt_categories = get_suggested_prompts()

        # Display categories in columns
        cols = st.columns(len(prompt_categories))
        for col_idx, (category, prompts) in enumerate(prompt_categories.items()):
            with cols[col_idx]:
                st.markdown(f"**{category}**")
                for prompt_idx, prompt in enumerate(prompts):
                    # Show truncated prompt as button text
                    display_text = prompt if len(prompt) <= 50 else prompt[:47] + "..."
                    if st.button(
                        display_text,
                        key=f"prompt_{col_idx}_{prompt_idx}",
                        use_container_width=True,
                        help=prompt,  # Full text on hover
                    ):
                        logger.info(f"Quick action clicked: {prompt[:50]}")
                        st.session_state.messages.append({"role": "user", "content": prompt})
                        save_message_to_db("user", prompt)
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
        # Regular chat input (no pending prompt)
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

    # Get agent response if needed
    if needs_response and user_prompt:
        logger.debug(f"Generating response for patient={st.session_state.patient_id}, agent={st.session_state.agent_type}")
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    from uuid import UUID

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
