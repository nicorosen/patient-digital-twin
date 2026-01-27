# Patient Digital Twin

An AI-powered comprehensive Electronic Health Record (EHR) system that demonstrates **multi-agent consultation**, **role-based access control**, and **conversational health data management**.

## Overview

Patient Digital Twin is a proof-of-concept application showcasing:

- **Comprehensive EHR Data Model**: 7 clinical data types with full CRUD operations
- **Dual AI Agents**: Medical Assistant (clinical) and Health Coach (education/motivation)
- **11 Specialist Agents**: Cardiology, Endocrinology, Neurology, Psychiatry, and more
- **4 User Roles**: Admin, Doctor, Patient, Caregiver with role-adaptive UI
- **Authentication System**: Database-backed user auth with cookie-based sessions
- **Conversation Persistence**: Sessions saved per mode (clinical/coach), resumable later
- **Agent-to-Agent Consultation**: Medical Assistant consults specialists with de-identified data
- **Clinical Translation**: Complex medical responses translated to 6th-grade reading level
- **Medical Web Search**: Real-time lookup of drug interactions, clinical guidelines, and medical literature via Tavily
- **Semantic Search (RAG)**: Natural language queries over patient health data via Chroma
- **Interactive Visualizations**: Health metrics dashboard, medication timeline, severity charts

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              STREAMLIT UI                                       │
│  ┌──────────────────┐  ┌─────────────────────────────────────────────────────┐  │
│  │  Sidebar          │  │             Main Content Area                       │  │
│  │  ─────────────── │  │  ┌─────────┬──────────┬─────────┬──────────┐       │  │
│  │  Patient Select   │  │  │💬 Chat  │📋 Health │📊 Viz   │📜 Audit  │       │  │
│  │  Agent Toggle     │  │  │         │  Record  │         │  Log*    │       │  │
│  │  Patient Summary  │  │  └─────────┴──────────┴─────────┴──────────┘       │  │
│  │  Conversations    │  │                                                     │  │
│  │  Access Mgmt*     │  │  Quick Actions (chips) → Chat Messages → Input     │  │
│  │  LLM Settings     │  │                                                     │  │
│  └──────────────────┘  └─────────────────────────────────────────────────────┘  │
│  * Role-dependent                                                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
              ┌──────────────────────────┴──────────────────────────┐
              ▼                                                      ▼
┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐
│     MEDICAL ASSISTANT AGENT          │    │       HEALTH COACH AGENT             │
│  ┌────────────────────────────────┐  │    │  ┌────────────────────────────────┐  │
│  │ Full CRUD Tools:              │  │    │  │ Read-Only Tools:               │  │
│  │ GET: 8 tools (profile + 7)   │  │    │  │ • get_patient_profile          │  │
│  │ ADD: 7 tools (one per type)  │  │    │  │ • get_* (7 data types)        │  │
│  │ UPDATE: 7 tools              │  │    │  │ • search_patient_data          │  │
│  │ DELETE: 7 tools              │  │    │  │ • search_clinical_history      │  │
│  │ SEARCH: 2 tools              │  │    │  │                                │  │
│  │ CONSULT: 11 specialists      │  │    │  │ Purpose:                       │  │
│  │ WEB: 1 tool (Tavily search) │  │    │  │ • Health education             │  │
│  └────────────────────────────────┘  │    │  │ • Lifestyle guidance           │  │
└──────────────────────────────────────┘    │  │ • Motivation support           │  │
          ▼                                 │  └────────────────────────────────┘  │
┌──────────────────────────────────┐       └──────────────────────────────────────┘
│  SPECIALIST AGENTS (11)          │
│  Cardiology, Endocrinology,      │
│  Pulmonology, Neurology,         │
│  Gastroenterology, Oncology,     │
│  Psychiatry, Orthopedics,        │
│  Nephrology, Dermatology,        │
│  Primary Care                    │
│                                  │
│  + Medical Board (multi-consult) │
│  De-identified context only      │
│  Structured responses with       │
│  assessment, recommendations,    │
│  red flags, guidelines           │
└──────────────────────────────────┘
              │
              ▼
┌──────────────────────────────┐
│  DATA LAYER                  │
│  ┌────────────┐ ┌─────────┐ │
│  │ PostgreSQL │ │ Chroma  │ │
│  │ (Records)  │ │ (RAG)   │ │
│  └────────────┘ └─────────┘ │
└──────────────────────────────┘
```

## User Roles & Permissions

The system supports 4 user roles with role-adaptive UI:

| Capability | Admin | Doctor | Patient | Caregiver |
| ---------- | ----- | ------ | ------- | --------- |
| View patients | All | Assigned | Own only | Assigned |
| Patient selector | Shown | Shown | Hidden (single) | Shown |
| Add/edit records | Yes | Yes | Yes | No |
| Delete records | Yes | Yes | No | No |
| Agent selector | Both agents | Medical only | Both agents | Medical only |
| Access management | Yes | Yes | No | Yes |
| Audit Log tab | Yes | Yes | No | No |
| Health Record tab | Yes | Yes | Yes (read-only) | Yes (read-only) |

### Demo Credentials

| User | Password | Role |
| ---- | -------- | ---- |
| `admin` | `admin123` | Admin |
| `drsmith` | `doctor123` | Doctor |
| `maria` | `patient123` | Patient |
| `jamescaregiver` | `caregiver123` | Caregiver |

## UI Layout

### Sidebar (compact, role-filtered)

- **Header**: User name, role badge, logout
- **Patient selector**: Dropdown (hidden when single patient)
- **Agent toggle**: Horizontal radio (hidden when role has one agent)
- **Patient summary**: Compact card (age, gender, condition/med/allergy counts)
- **Conversations**: Session list with new/rename/delete
- **Access Management**: Expander (admin/doctor/caregiver only)
- **LLM Settings**: Collapsed expander (provider + model selection)

### Main Area (tabbed)

- **Chat** (default): Quick action chips (shown when no messages) + chat messages + input
- **Health Record**: Full patient profile — demographics, conditions, medications, allergies, vital signs, lab results, family history, social history
- **Visualizations**: Metrics dashboard, severity chart, consultation history, medication timeline
- **Audit Log** (admin/doctor only): Specialist consultation history with expandable details

## Data Model

### Clinical Data Types (7 Types)

| Data Type | Model | Description | Key Fields |
| --------- | ----- | ----------- | ---------- |
| **Conditions** | `Condition` | Diagnoses/problems | display_name, clinical_status, severity, onset_date |
| **Medications** | `Medication` | Prescriptions | display_name, dosage, frequency, status, route |
| **Allergies** | `Allergy` | Allergies/sensitivities | substance, category, criticality, reaction |
| **Vital Signs** | `VitalSigns` | BP, HR, temp, weight | systolic_bp, diastolic_bp, heart_rate, temperature |
| **Lab Results** | `LabResult` | Blood tests, labs | test_name, value, unit, reference_range, interpretation |
| **Family History** | `FamilyHistory` | Genetic risk factors | relation, condition_name, onset_age |
| **Social History** | `SocialHistory` | Lifestyle factors | category, status, description |

### System Models

| Model | Description |
| ----- | ----------- |
| `User` | Authenticated users with role (admin/doctor/patient/caregiver) |
| `Patient` | Patient demographics (name, DOB, gender) |
| `PatientMember` | User-to-patient access mapping (composite key) |
| `ConversationSession` | Persistent chat sessions with title, mode (clinical/coach) |
| `ConversationMessage` | Individual messages with role, content, session linkage |
| `ConsultationAuditLog` | Audit trail for specialist consultations |

### Entity Relationship

```text
User (1) ──────────── (N) PatientMember (N) ──────────── (1) Patient
                                                              │
Patient (1) ──────┬────── (N) Condition
                  ├────── (N) Medication
                  ├────── (N) Allergy
                  ├────── (N) VitalSigns
                  ├────── (N) LabResult
                  ├────── (N) FamilyHistory
                  ├────── (N) SocialHistory
                  ├────── (N) ConversationSession ──── (N) ConversationMessage
                  └────── (N) ConsultationAuditLog
```

## Agent Tools

### Medical Assistant Tools

| Category | Count | Description |
| -------- | ----- | ----------- |
| Getter | 10 | Profile, 7 data types, 2 search tools |
| Add | 7 | One per clinical data type |
| Update | 7 | One per clinical data type (doctor role) |
| Delete | 7 | One per clinical data type (doctor role) |
| Consultation | 12 | 11 specialists + medical board (multi-consult) |
| Web Search | 1 | Medical web search via Tavily (drug interactions, guidelines, literature) |

### Health Coach Tools (read-only)

| Tool | Description |
| ---- | ----------- |
| `get_patient_profile` | Complete health profile |
| `get_*` (7 tools) | Each clinical data type |
| `search_patient_data` | RAG semantic search |
| `search_clinical_history` | Search past clinical conversations |

### Specialist Agents (11)

| Specialist | Focus Areas |
| ---------- | ----------- |
| Primary Care | General medicine, preventive care, chronic disease |
| Cardiology | Chest pain, heart failure, arrhythmias, hypertension |
| Endocrinology | Diabetes, thyroid, hormonal disorders |
| Pulmonology | Asthma, COPD, shortness of breath, sleep apnea |
| Neurology | Headaches, seizures, dizziness, memory concerns |
| Gastroenterology | Acid reflux, IBS, IBD, liver disease |
| Oncology | Cancer screening, suspicious symptoms |
| Psychiatry | Depression, anxiety, mood changes, sleep |
| Orthopedics | Joint pain, arthritis, back pain, fractures |
| Nephrology | Kidney disease, electrolyte imbalances |
| Dermatology | Rashes, eczema, psoriasis, skin lesions |

All specialists return structured responses with: assessment, recommendations (with priority), red flags, guidelines referenced, and confidence level.

## Semantic Search (RAG)

### How It Works

1. All patient data is indexed in Chroma vector store
2. Documents are embedded using Anthropic embeddings
3. Natural language queries find semantically similar content
4. Results are filtered by patient_id for privacy
5. Clinical conversation messages are indexed for Health Coach cross-mode access

### Indexed Document Types

- Patient demographics
- Conditions (with status, severity, notes)
- Medications (with dosage, frequency, reason)
- Allergies (with reactions, criticality)
- Vital signs (with measurements)
- Lab results (with interpretations)
- Family history
- Social history
- Clinical conversation summaries (assistant responses)

## Privacy and De-identification

### Specialist Consultation Data Flow

```text
Patient Data → De-identification → Specialist → Structured Response → Translation → Patient
```

**Included (De-identified):**

- Age (calculated from DOB)
- Gender
- Condition names
- Medication names with dosages
- Allergy substances

**Excluded (Identifying):**

- Patient name
- Date of birth
- Addresses
- Contact information
- Specific dates (converted to relative timeframes)

All consultations logged in `ConsultationAuditLog` for transparency and compliance.

## Technology Stack

| Component | Technology | Purpose |
| --------- | ---------- | ------- |
| LLM | Gemini 2.5 Pro / Claude Opus 4.5 / OpenAI o3 | Agent intelligence |
| Agent Framework | LangChain | Tool orchestration |
| Database | PostgreSQL | Structured health data |
| Vector Store | Chroma | Semantic search |
| Embeddings | Anthropic API | Document embeddings |
| Frontend | Streamlit | Chat interface |
| Authentication | streamlit-authenticator + bcrypt | User auth |
| Visualizations | Plotly | Interactive charts |
| Validation | Pydantic | Schema validation |
| ORM | SQLAlchemy | Database models |

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- API key for at least one LLM provider

### Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd patient-digital-twin
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API key:

   ```env
   # Only the key for your provider is required
   GOOGLE_API_KEY=AIza...          # For Google Gemini (default)
   # ANTHROPIC_API_KEY=sk-ant-...  # For Anthropic Claude
   # OPENAI_API_KEY=sk-...         # For OpenAI

   # Optional: Web search for medical information
   # TAVILY_API_KEY=tvly-...       # Get one at https://tavily.com
   ```

5. **Create PostgreSQL database**

   ```bash
   createdb patient_twin
   ```

## Running the Application

### Quick Start

```bash
# Seed database and start with Anthropic Claude (default)
python run.py --seed --index

# Or use a different LLM provider
python run.py --llm google --model gemini-2.5-pro              # Use Gemini (default)
python run.py --llm anthropic --model claude-opus-4-5-20251101 # Use Claude Opus 4.5
python run.py --llm openai --model o3                          # Use OpenAI o3
```

### LLM Providers

Only high-reasoning models are supported. Flash and lightweight models have been removed.

| Provider | Default Model | Other Models |
| -------- | ------------- | ------------ |
| `google` | `gemini-2.5-pro` | — |
| `anthropic` | `claude-opus-4-5-20251101` | `claude-sonnet-4-20250514` |
| `openai` | `o3` | `gpt-4.1` |

### Step-by-Step

1. **Seed the database** (creates demo users + 3 synthetic patients)

   ```bash
   python -m src.database.seed
   ```

2. **Index patient data for RAG**

   ```bash
   python -c "from src.rag import get_retriever; print(f'Indexed {get_retriever().index_all_patients()} documents')"
   ```

3. **Run the Streamlit app**

   ```bash
   streamlit run src/app/streamlit_app.py
   ```

4. **Open in browser**

   Navigate to `http://localhost:8501`

5. **Login** with one of the demo credentials (see table above)

## Project Structure

```text
patient-digital-twin/
├── src/
│   ├── __init__.py
│   ├── config.py                 # Environment configuration
│   ├── logging_config.py         # Logging setup
│   │
│   ├── schemas/                  # Pydantic data models
│   │   ├── __init__.py
│   │   ├── fhir.py              # Core FHIR-inspired schemas
│   │   ├── clinical_extended.py # VitalSigns, LabResult, Family/Social history
│   │   ├── user.py              # User and PatientMember schemas
│   │   ├── patient_member.py    # Patient-user association schemas
│   │   └── conversation.py      # Session and message schemas
│   │
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py              # Base model with UUID, timestamps
│   │   ├── patient.py           # Patient model
│   │   ├── user.py              # User model with roles
│   │   ├── patient_member.py    # User-patient access mapping
│   │   ├── clinical.py          # Condition, Medication, Allergy
│   │   ├── clinical_extended.py # VitalSigns, LabResult, Family/Social
│   │   └── conversation.py      # Session, Message, AuditLog
│   │
│   ├── database/                 # Data access layer
│   │   ├── __init__.py
│   │   ├── connection.py        # PostgreSQL connection
│   │   ├── repositories.py      # CRUD operations (all types + users)
│   │   └── seed.py              # Synthetic patient + user data
│   │
│   ├── rag/                      # RAG system
│   │   ├── __init__.py
│   │   ├── embeddings.py        # Anthropic embeddings
│   │   ├── vectorstore.py       # Chroma vector store
│   │   └── retriever.py         # Search, indexing, delete
│   │
│   ├── agents/                   # AI agents
│   │   ├── __init__.py
│   │   ├── medical_assistant.py # Clinical agent (full CRUD + consult)
│   │   ├── health_coach.py      # Education agent (read-only + RAG)
│   │   ├── translation.py       # Clinical to plain language
│   │   ├── specialists/         # 11 specialist agents
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # BaseSpecialist with structured output
│   │   │   ├── cardiology.py
│   │   │   ├── endocrinology.py
│   │   │   ├── pulmonology.py
│   │   │   ├── neurology.py
│   │   │   ├── gastroenterology.py
│   │   │   ├── oncology.py
│   │   │   ├── psychiatry.py
│   │   │   ├── orthopedics.py
│   │   │   ├── nephrology.py
│   │   │   └── dermatology.py
│   │   └── tools/               # Agent tools
│   │       ├── __init__.py
│   │       ├── patient_data.py  # All CRUD tools
│   │       ├── consultation.py  # Specialist consultation tools (12)
│   │       └── web_search.py   # Medical web search via Tavily
│   │
│   └── app/                      # Streamlit application
│       ├── __init__.py
│       └── streamlit_app.py     # Main UI with role-adaptive layout
│
├── tests/                        # Test suite
│   ├── conftest.py              # Test fixtures
│   ├── test_models.py           # Model tests
│   ├── test_repositories.py     # Repository tests
│   ├── test_tools.py            # Tool tests
│   ├── test_clinical_extended.py # Extended model tests
│   ├── test_conversation_sessions.py # Session tests
│   ├── test_health_coach.py     # Health Coach tests
│   ├── test_consultation.py     # Consultation tests
│   └── test_llm_factory.py      # LLM factory tests
│
├── data/
│   ├── synthetic/               # Synthetic data files
│   └── embeddings/              # Chroma persistence
│
├── .streamlit/
│   ├── config.toml              # Streamlit theme and server config
│   └── secrets.toml             # Auth cookies and credentials
│
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
├── run.py                        # Convenience runner
├── CLAUDE.md                     # AI assistant instructions
└── README.md                     # This file
```

## Synthetic Patients

The seed script creates 3 test patients with realistic clinical data:

| Patient | Demographics | Conditions | Medications | Allergies |
| ------- | ------------ | ---------- | ----------- | --------- |
| **Maria Garcia** | 45F | Type 2 Diabetes, Hypertension | Metformin 500mg BID, Lisinopril 10mg daily | None |
| **James Thompson** | 62M | CAD, Hyperlipidemia | Aspirin 81mg daily, Atorvastatin 40mg daily | Penicillin (HIGH) |
| **Sarah Chen** | 28F | Asthma, Anxiety, High Cholesterol | Albuterol PRN, Sertraline 50mg daily | Shellfish (LOW) |

Each patient also has:

- Sample vital signs records
- Lab results (HbA1c, cholesterol panels, etc.)
- Family history entries
- Social history (smoking, alcohol, exercise status)

## Example Interactions

### Medical Assistant - Adding Data (Doctor/Admin)

```text
Doctor: "Add a new condition: hypothyroidism, diagnosed today"
Assistant: "Added hypothyroidism [active] to the patient record."
```

### Medical Assistant - Specialist Consultation

```text
Patient: "I have been having dizziness when I stand up. Should I be worried?"
Assistant: "I'll consult with a specialist about your symptoms...

[Consulting Cardiology with de-identified data...]

Based on the specialist assessment:

**Assessment:** Dizziness when standing (orthostatic hypotension) can be
a side effect of Lisinopril, your blood pressure medication.

**Recommendations:**
🟡 [ROUTINE] Rise slowly from sitting or lying positions
🟡 [ROUTINE] Stay well hydrated
🟠 [HIGH] Mention this to your doctor at your next visit"
```

### Health Coach - Lifestyle Guidance

```text
Patient: "What diet changes would help with my conditions?"
Coach: "Great question! With your Type 2 Diabetes and Hypertension,
here are some dietary changes that can make a real difference..."
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black src/ tests/
flake8 src/ tests/
```

### Reset Database

```bash
python -c "from src.database import drop_tables, create_tables; drop_tables(); create_tables()"
python -m src.database.seed
```

## Enums Reference

### Clinical Status (Conditions)

- `active` - Currently affecting patient
- `inactive` - Not currently active
- `resolved` - No longer present
- `remission` - In remission

### Medication Status

- `active` - Currently taking
- `on-hold` - Temporarily paused
- `discontinued` - No longer taking

### Allergy Category

- `food` - Food allergy
- `medication` - Drug allergy
- `environment` - Environmental allergen
- `biologic` - Biological allergen

### Allergy Criticality

- `low` - Low risk
- `high` - High risk / life-threatening

### Lab Interpretation

- `normal` - Within reference range
- `abnormal` - Outside reference range
- `critical` - Critically abnormal

### Family Relation

- `mother`, `father`, `sister`, `brother`
- `maternal_grandmother`, `maternal_grandfather`
- `paternal_grandmother`, `paternal_grandfather`
- `aunt`, `uncle`, `cousin`

### Social History Category

- `smoking`, `alcohol`, `drugs`
- `exercise`, `diet`
- `occupation`, `living_situation`
- `stress`, `sleep`, `other`

### Social History Status

- `current` - Currently active
- `former` - Previously active
- `never` - Never engaged
- `occasional` - Sometimes
- `daily` - Every day
- `unknown` - Not specified

## Troubleshooting

### Database connection errors

```bash
pg_isready
createdb patient_twin
```

### Missing API key

```bash
echo $ANTHROPIC_API_KEY  # or GOOGLE_API_KEY, OPENAI_API_KEY
```

### Embedding issues

Ensure your Anthropic API key is set — embeddings use the Anthropic API.

## License

This project is for demonstration purposes.

## Disclaimer

This is a proof-of-concept application and should NOT be used for actual medical decisions.
Always consult with qualified healthcare professionals for medical advice.
