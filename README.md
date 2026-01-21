# Patient Digital Twin

An AI-powered comprehensive Electronic Health Record (EHR) system that demonstrates **agent-to-agent consultation**, **role-based access control**, and **conversational health data management**.

## Overview

Patient Digital Twin is a proof-of-concept application showcasing:

- **Comprehensive EHR Data Model**: 7 clinical data types with full CRUD operations
- **Dual AI Agents**: Medical Assistant (clinical) and Health Coach (education/motivation)
- **Role-Based Access**: Doctor mode (full CRUD) vs Patient mode (read-only)
- **Conversation Persistence**: Sessions are saved and can be continued later
- **Agent-to-Agent Consultation**: Medical Assistant consults specialists with de-identified data
- **Clinical Translation**: Complex medical responses translated to 6th-grade reading level
- **Semantic Search (RAG)**: Natural language queries over patient health data
- **Interactive Visualizations**: Health metrics dashboard, medication timeline, severity charts

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              STREAMLIT UI                                        │
│  ┌──────────────────┐  ┌─────────────────────────────────────────────────────┐  │
│  │  Patient Select  │  │             Main Content Area                        │  │
│  │  Role Toggle     │  │  ┌───────────────────────────────────────────────┐  │  │
│  │  🩺 Doctor Mode  │  │  │         Health Metrics Dashboard              │  │  │
│  │  👤 Patient Mode │  │  │ [Conditions] [Medications] [Allergies] [Labs] │  │  │
│  │                  │  │  └───────────────────────────────────────────────┘  │  │
│  │  Conversations   │  │  ┌─────────────┬────────────────────────────────┐  │  │
│  │  [+ New Chat]    │  │  │ 💬 Chat Tab │ 📊 Visualizations Tab          │  │  │
│  │  • Session 1     │  │  └─────────────┴────────────────────────────────┘  │  │
│  │  • Session 2     │  │                                                     │  │
│  │                  │  │  Agent: 🩺 Clinical Mode / 💪 Coaching Mode        │  │
│  │  Audit Log       │  │                                                     │  │
│  └──────────────────┘  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
              ┌──────────────────────────┴──────────────────────────┐
              ▼                                                      ▼
┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐
│     MEDICAL ASSISTANT AGENT          │    │       HEALTH COACH AGENT             │
│  ┌────────────────────────────────┐  │    │  ┌────────────────────────────────┐  │
│  │ Full CRUD Tools (30 total):   │  │    │  │ Read-Only Tools:               │  │
│  │                                │  │    │  │ • get_patient_profile          │  │
│  │ GET: 8 tools (profile, 7 types)│  │    │  │ • get_* (7 data types)        │  │
│  │ ADD: 7 tools (one per type)   │  │    │  │ • search_patient_data          │  │
│  │ UPDATE: 7 tools               │  │    │  │ • search_clinical_history      │  │
│  │ DELETE: 7 tools               │  │    │  │                                │  │
│  │ SEARCH: 2 tools               │  │    │  │ Purpose:                       │  │
│  │ CONSULT: 1 tool               │  │    │  │ • Health education             │  │
│  └────────────────────────────────┘  │    │  │ • Lifestyle guidance           │  │
└──────────────────────────────────────┘    │  │ • Motivation support           │  │
          │                   │              │  └────────────────────────────────┘  │
          ▼                   ▼              └──────────────────────────────────────┘
┌──────────────────┐  ┌──────────────────┐
│  PRIMARY CARE    │  │  TRANSLATION     │
│  SPECIALIST      │  │  LAYER           │
│                  │  │                  │
│ De-identified    │  │ Clinical → Plain │
│ context only     │  │ language (6th    │
│                  │  │ grade reading)   │
└──────────────────┘  └──────────────────┘
              │                   │
              └─────────┬─────────┘
                        ▼
         ┌──────────────────────────────┐
         │  DATA LAYER                  │
         │  ┌────────────┐ ┌─────────┐  │
         │  │ PostgreSQL │ │ Chroma  │  │
         │  │ (Records)  │ │ (RAG)   │  │
         │  └────────────┘ └─────────┘  │
         └──────────────────────────────┘
```

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

### Conversation System

| Model | Description |
| ----- | ----------- |
| `ConversationSession` | Persistent chat sessions with title, mode (clinical/coach), active status |
| `ConversationMessage` | Individual messages with role, content, metadata, session linkage |
| `ConsultationAuditLog` | Audit trail for specialist consultations |

### Entity Relationship

```text
Patient (1) ──────┬────── (N) Condition
                  ├────── (N) Medication
                  ├────── (N) Allergy
                  ├────── (N) VitalSigns
                  ├────── (N) LabResult
                  ├────── (N) FamilyHistory
                  ├────── (N) SocialHistory
                  └────── (N) ConversationSession ──── (N) ConversationMessage
```

## Agent Tools (32 Total)

### Getter Tools (10)

| Tool | Description | Returns |
| ---- | ----------- | ------- |
| `get_patient_profile` | Complete health profile | Demographics, all conditions, meds, allergies |
| `get_conditions` | All conditions with IDs | Condition list with UUIDs for update/delete |
| `get_medications` | All medications with IDs | Medication list with UUIDs |
| `get_allergies` | All allergies with IDs | Allergy list with UUIDs |
| `get_vital_signs` | Recent vitals with IDs | Vital signs with timestamps and UUIDs |
| `get_lab_results` | Lab results with IDs | Lab results with UUIDs |
| `get_family_history` | Family history with IDs | Family history entries with UUIDs |
| `get_social_history` | Social history with IDs | Lifestyle factors with UUIDs |
| `search_patient_data` | RAG semantic search | Relevant health data matching query |
| `search_clinical_history` | Search past conversations | Context from clinical sessions |

### Add Tools (7)

| Tool | Description | Key Parameters |
| ---- | ----------- | -------------- |
| `add_condition` | Add diagnosis | display_name, clinical_status, severity |
| `add_medication` | Add prescription | display_name, dosage, frequency, route |
| `add_allergy` | Add allergy | substance, category, criticality |
| `add_vital_signs` | Record vitals | systolic_bp, diastolic_bp, heart_rate |
| `add_lab_result` | Add lab result | test_name, value, unit, interpretation |
| `add_family_history` | Add family condition | relationship, condition_name |
| `add_social_history` | Add lifestyle factor | category, status, description |

### Update Tools (7)

| Tool | Description | Required |
| ---- | ----------- | -------- |
| `update_condition` | Modify condition | condition_id (from get_conditions) |
| `update_medication` | Modify medication | medication_id |
| `update_allergy` | Modify allergy | allergy_id |
| `update_vital_signs` | Modify vitals | vital_signs_id |
| `update_lab_result` | Modify lab result | lab_result_id |
| `update_family_history` | Modify family history | family_history_id |
| `update_social_history` | Modify social history | social_history_id |

### Delete Tools (7)

| Tool | Description | Required |
| ---- | ----------- | -------- |
| `delete_condition` | Remove condition | condition_id |
| `delete_medication` | Remove medication | medication_id |
| `delete_allergy` | Remove allergy | allergy_id |
| `delete_vital_signs` | Remove vitals | vital_signs_id |
| `delete_lab_result` | Remove lab result | lab_result_id |
| `delete_family_history` | Remove family history | family_history_id |
| `delete_social_history` | Remove social history | social_history_id |

### Consultation Tool (1)

| Tool | Description |
| ---- | ----------- |
| `consult_primary_care` | Consult specialist with de-identified patient context |

## Role-Based Access Control

### Doctor Mode (🩺)

- Full read/write access to all patient data
- Can add, update, and delete clinical records
- Access to specialist consultation tool
- Suitable for clinical documentation

### Patient Mode (👤)

- Read-only access to health data
- Cannot modify clinical records
- Can view all their health information
- Suitable for patient portal experience

| Capability | Doctor Mode | Patient Mode |
| ---------- | ----------- | ------------ |
| View data | Yes | Yes |
| Add records | Yes | No |
| Update records | Yes | No |
| Delete records | Yes | No |
| Consult specialist | Yes | No |

## Conversation Persistence

### Session Management

- **Auto-create**: New session created on first message
- **Auto-save**: Messages saved to database immediately
- **Title generation**: Auto-generated from first message
- **Mode separation**: Clinical and Coach conversations stored separately
- **Continue later**: Click session in sidebar to resume

### Session States

| State | Description |
| ----- | ----------- |
| `active` | Current conversation, shown in sidebar |
| `inactive` | Archived, can be reactivated |

## Semantic Search (RAG)

### How It Works

1. All patient data is indexed in Chroma vector store
2. Documents are embedded using `all-MiniLM-L6-v2` sentence transformer
3. Natural language queries find semantically similar content
4. Results are filtered by patient_id for privacy

### Indexed Document Types

- Patient demographics
- Conditions (with status, severity, notes)
- Medications (with dosage, frequency, reason)
- Allergies (with reactions, criticality)
- Vital signs (with measurements)
- Lab results (with interpretations)
- Family history
- Social history
- Clinical conversation summaries

## Privacy and De-identification

### Specialist Consultation Data Flow

```text
Patient Data → De-identification → Specialist → Translation → Patient Response
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

All consultations logged in `ConsultationAuditLog` for transparency.

## Technology Stack

| Component | Technology | Purpose |
| --------- | ---------- | ------- |
| LLM | Claude / GPT-4 / Gemini | Agent intelligence |
| Agent Framework | LangChain | Tool orchestration |
| Database | PostgreSQL | Structured health data |
| Vector Store | Chroma | Semantic search |
| Embeddings | sentence-transformers | Document embeddings |
| Frontend | Streamlit | Chat interface |
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
   GOOGLE_API_KEY=AIza...        # For Google Gemini (default)
   # ANTHROPIC_API_KEY=sk-ant-... # For Anthropic Claude
   # OPENAI_API_KEY=sk-...        # For OpenAI GPT-4
   ```

5. **Create PostgreSQL database**

   ```bash
   createdb patient_twin
   ```

## Running the Application

### Quick Start

```bash
# Seed database and start with Google Gemini (default)
python run.py --seed --index

# Or use a different LLM provider
python run.py --llm anthropic                    # Use Claude
python run.py --llm openai --model gpt-4o        # Use GPT-4o
python run.py --llm google --model gemini-2.0-flash  # Use Gemini Flash
```

### LLM Providers

| Provider | Default Model | Other Models |
| -------- | ------------- | ------------ |
| `google` | `gemini-2.5-pro` | `gemini-2.0-flash`, `gemini-1.5-pro` |
| `anthropic` | `claude-sonnet-4-20250514` | `claude-opus-4-20250514` |
| `openai` | `gpt-4o` | `gpt-4-turbo`, `gpt-4o-mini` |

### Step-by-Step

1. **Seed the database** (creates 3 synthetic patients)

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
│   │   └── conversation.py      # Session and message schemas
│   │
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py              # Base model with UUID, timestamps
│   │   ├── patient.py           # Patient model
│   │   ├── clinical.py          # Condition, Medication, Allergy
│   │   ├── clinical_extended.py # VitalSigns, LabResult, Family/Social
│   │   └── conversation.py      # Session, Message, AuditLog
│   │
│   ├── database/                 # Data access layer
│   │   ├── __init__.py
│   │   ├── connection.py        # PostgreSQL connection
│   │   ├── repositories.py      # CRUD operations (all 7 types)
│   │   └── seed.py              # Synthetic patient data
│   │
│   ├── rag/                      # RAG system
│   │   ├── __init__.py
│   │   ├── embeddings.py        # Sentence-transformer embeddings
│   │   ├── vectorstore.py       # Chroma vector store
│   │   └── retriever.py         # Search, indexing, delete
│   │
│   ├── agents/                   # AI agents
│   │   ├── __init__.py
│   │   ├── medical_assistant.py # Clinical agent (full CRUD)
│   │   ├── health_coach.py      # Education agent (read-only)
│   │   ├── primary_care.py      # Specialist agent
│   │   ├── translation.py       # Clinical to plain language
│   │   └── tools/               # Agent tools (32 total)
│   │       ├── __init__.py
│   │       ├── patient_data.py  # All CRUD tools
│   │       └── consultation.py  # Specialist consultation
│   │
│   └── app/                      # Streamlit application
│       ├── __init__.py
│       └── streamlit_app.py     # Main UI with role toggle
│
├── tests/                        # Test suite (197 tests)
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

### Doctor Mode - Adding Data

```text
Doctor: "Add a new condition: hypothyroidism, diagnosed today"
Assistant: "Added hypothyroidism [active] to the patient record."
```

### Doctor Mode - Updating Data

```text
Doctor: "Show conditions"
Assistant: "## Patient Conditions (3 total)
- High Cholesterol [active]
  ID: e567962c-d584-4048-b6d5-1628f803a429
..."

Doctor: "Mark the high cholesterol condition as resolved"
Assistant: "Updated condition e567962c... to resolved status."
```

### Doctor Mode - Deleting Data

```text
Doctor: "Delete the high cholesterol condition"
Assistant: "Deleted condition: High Cholesterol"
```

### Patient Mode - Asking Questions

```text
Patient: "What medications am I taking?"
Assistant: "You are currently taking:
1. Metformin 500mg twice daily - For managing your diabetes
2. Lisinopril 10mg once daily - For blood pressure control"
```

### Specialist Consultation

```text
Patient: "I have been having dizziness when I stand up. Should I be worried?"
Assistant: "I will consult with a Primary Care specialist...

[Consulting specialist with de-identified data...]

Based on the specialist assessment:

**Main Finding:** Dizziness when standing (orthostatic hypotension) can be
a side effect of Lisinopril, your blood pressure medication.

**Recommendations:**
- Rise slowly from sitting or lying positions
- Stay well hydrated
- Mention this to your doctor at your next visit"
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

All 197 tests should pass.

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
echo $GOOGLE_API_KEY  # or ANTHROPIC_API_KEY, OPENAI_API_KEY
```

### Embedding model download

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

## License

This project is for demonstration purposes.

## Disclaimer

This is a proof-of-concept application and should NOT be used for actual medical decisions.
Always consult with qualified healthcare professionals for medical advice.
