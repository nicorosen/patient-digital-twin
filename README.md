# Patient Digital Twin

An AI-powered healthcare assistant that demonstrates **agent-to-agent consultation** - where a patient's Medical Assistant agent consults with specialist AI agents, translating clinical insights back to accessible language.

## Overview

Patient Digital Twin is a proof-of-concept application that showcases:

- **Dual AI Agents**: Medical Assistant for clinical queries and Health Coach for education/motivation
- **Conversational Health Data Management**: Patients can describe their health information naturally, and the system extracts structured data
- **Agent-to-Agent Consultation**: The Medical Assistant can consult a Primary Care specialist on behalf of the patient
- **Privacy-Preserving Architecture**: Specialist consultations use de-identified data (no names, birthdates, or identifiers)
- **Clinical Translation**: Complex medical responses are translated to 6th-grade reading level
- **Interactive Visualizations**: Health metrics dashboard, medication timeline, and severity charts

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              STREAMLIT UI                                        │
│  ┌──────────────────┐  ┌─────────────────────────────────────────────────────┐  │
│  │  Patient Select  │  │             Main Content Area                        │  │
│  │  Agent Selector  │  │  ┌───────────────────────────────────────────────┐  │  │
│  │  Profile Sidebar │  │  │         Health Metrics Dashboard              │  │  │
│  │  Audit Log       │  │  │ [Conditions] [Medications] [Allergies] [Last] │  │  │
│  │                  │  │  └───────────────────────────────────────────────┘  │  │
│  │  🩺 Clinical Mode│  │  ┌─────────────┬────────────────────────────────┐  │  │
│  │  💪 Coaching Mode│  │  │ 💬 Chat Tab │ 📊 Visualizations Tab          │  │  │
│  └──────────────────┘  │  └─────────────┴────────────────────────────────┘  │  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
              ┌──────────────────────────┴──────────────────────────┐
              ▼                                                      ▼
┌──────────────────────────────────┐          ┌──────────────────────────────────┐
│     MEDICAL ASSISTANT AGENT      │          │       HEALTH COACH AGENT         │
│  ┌────────────────────────────┐  │          │  ┌────────────────────────────┐  │
│  │ Tools:                     │  │          │  │ Read-Only Tools:           │  │
│  │ • get_patient_profile      │  │          │  │ • get_patient_profile      │  │
│  │ • search_patient_data      │  │          │  │ • search_patient_data      │  │
│  │ • add_condition            │  │          │  │                            │  │
│  │ • add_medication           │  │          │  │ Purpose:                   │  │
│  │ • add_allergy              │  │          │  │ • Health education         │  │
│  │ • consult_primary_care     │  │          │  │ • Lifestyle guidance       │  │
│  └────────────────────────────┘  │          │  │ • Motivation support       │  │
└──────────────────────────────────┘          │  │ • Plain language           │  │
          │                   │               │  └────────────────────────────┘  │
          ▼                   ▼               └──────────────────────────────────┘
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

## Features

### 1. Dual AI Agents

**Medical Assistant** (🩺 Clinical Mode)

- Clinical questions and symptom assessment
- Add conditions, medications, and allergies to health record
- Consult with Primary Care specialist for complex questions

**Health Coach** (💪 Coaching Mode)

- Health education in plain language
- Lifestyle and wellness guidance
- Motivation and support for healthy behaviors
- Read-only access (no data modification)

### 2. Health Profile Management

- View patient demographics, conditions, medications, and allergies
- Add new health information through natural conversation
- Automatic extraction and confirmation of structured data

### 3. Semantic Search (RAG)

- Natural language queries over patient health data
- "What medications am I taking?" returns relevant medication information
- Powered by Chroma vector database and sentence-transformers

### 4. Specialist Consultation

- Medical Assistant can consult Primary Care specialist for clinical questions
- **Privacy-preserving**: Only de-identified data is shared (age, gender, conditions - no names or DOB)
- Full audit trail of what data was shared and specialist responses

### 5. Clinical Translation

- Specialist responses are translated to plain language
- Medical jargon replaced with simple terms
- Appropriate reading level for patient understanding

### 6. Interactive Dashboard & Visualizations

- **Health Metrics Dashboard**: Quick view of conditions, medications, allergies count
- **Medication Timeline**: Visual timeline of medication history (Plotly)
- **Condition Severity Chart**: Donut chart showing severity distribution
- **Consultation History**: Bar chart of consultations over time

## Technology Stack

| Component       | Technology                          | Purpose                |
| --------------- | ----------------------------------- | ---------------------- |
| LLM             | Claude / GPT-4 / Gemini (switchable)| Agent intelligence     |
| Agent Framework | LangChain                           | Tool orchestration     |
| Database        | PostgreSQL                          | Structured health data |
| Vector Store    | Chroma                              | Semantic search        |
| Embeddings      | sentence-transformers               | Document embeddings    |
| Frontend        | Streamlit                           | Chat interface         |
| Visualizations  | Plotly                              | Interactive charts     |
| Validation      | Pydantic                            | Schema validation      |

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Anthropic API key

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

   Edit `.env` and add your API key (Google Gemini is the default):

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

| Provider    | Default Model              | Other Models                         |
| ----------- | -------------------------- | ------------------------------------ |
| `google`    | `gemini-2.5-pro`           | `gemini-2.0-flash`, `gemini-1.5-pro` |
| `anthropic` | `claude-sonnet-4-20250514` | `claude-opus-4-20250514`             |
| `openai`    | `gpt-4o`                   | `gpt-4-turbo`, `gpt-4o-mini`         |

### Step-by-Step

1. **Seed the database** (creates 3 synthetic patients)

   ```bash
   python -m src.database.seed
   ```

2. **Index patient data for RAG** (optional, improves search)

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
│   │
│   ├── schemas/                  # Pydantic data models
│   │   ├── __init__.py
│   │   └── fhir.py              # FHIR-inspired schemas
│   │
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py              # Base model with UUID, timestamps
│   │   ├── patient.py           # Patient model
│   │   ├── clinical.py          # Condition, Medication, Allergy
│   │   └── conversation.py      # Chat history, audit logs
│   │
│   ├── database/                 # Data access layer
│   │   ├── __init__.py
│   │   ├── connection.py        # PostgreSQL connection
│   │   ├── repositories.py      # CRUD operations
│   │   └── seed.py              # Synthetic patient data
│   │
│   ├── rag/                      # RAG system
│   │   ├── __init__.py
│   │   ├── embeddings.py        # Sentence-transformer embeddings
│   │   ├── vectorstore.py       # Chroma vector store
│   │   └── retriever.py         # Search and indexing
│   │
│   ├── agents/                   # AI agents
│   │   ├── __init__.py
│   │   ├── medical_assistant.py # Clinical agent (full tools)
│   │   ├── health_coach.py      # Education agent (read-only)
│   │   ├── primary_care.py      # Specialist agent
│   │   ├── translation.py       # Clinical to plain language
│   │   └── tools/               # Agent tools
│   │       ├── __init__.py
│   │       ├── patient_data.py  # Profile, search, add data
│   │       └── consultation.py  # Specialist consultation
│   │
│   └── app/                      # Streamlit application
│       ├── __init__.py
│       └── streamlit_app.py     # Main chat interface
│
├── tests/                        # Test suite
├── data/
│   ├── synthetic/               # Synthetic data files
│   └── embeddings/              # Chroma persistence
│
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
├── run.py                        # Convenience runner
└── README.md                     # This file
```

## Synthetic Patients

The seed script creates 3 test patients with realistic clinical data:

| Patient            | Demographics | Conditions                    | Medications                                   | Allergies         |
| ------------------ | ------------ | ----------------------------- | --------------------------------------------- | ----------------- |
| **Maria Garcia**   | 45F          | Type 2 Diabetes, Hypertension | Metformin 500mg BID, Lisinopril 10mg daily    | None              |
| **James Thompson** | 62M          | CAD, Hyperlipidemia           | Aspirin 81mg daily, Atorvastatin 40mg daily   | Penicillin (HIGH) |
| **Sarah Chen**     | 28F          | Asthma, Anxiety               | Albuterol PRN, Sertraline 50mg daily          | Shellfish (LOW)   |

## Agent Tools

### Patient Data Tools

| Tool                  | Description                                                                  |
| --------------------- | ---------------------------------------------------------------------------- |
| `get_patient_profile` | Retrieve complete health profile (demographics, conditions, meds, allergies) |
| `search_patient_data` | RAG-powered semantic search over patient records                             |
| `add_condition`       | Add a new condition to the patient's problem list                            |
| `add_medication`      | Add a new medication to the patient's medication list                        |
| `add_allergy`         | Add a new allergy to the patient's allergy list                              |

### Consultation Tools

| Tool                   | Description                                                   |
| ---------------------- | ------------------------------------------------------------- |
| `consult_primary_care` | Consult with Primary Care specialist using de-identified data |

## Privacy and De-identification

When consulting specialists, the following data transformation occurs:

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
- Specific dates

All consultations are logged in `ConsultationAuditLog` for transparency.

## Example Interactions

### Asking about medications

```text
Patient: "What medications am I taking?"

Assistant: "You are currently taking:
1. **Metformin 500mg** twice daily - For managing your diabetes
2. **Lisinopril 10mg** once daily - For blood pressure control

Would you like more details about any of these medications?"
```

### Adding new information

```text
Patient: "I was just diagnosed with high cholesterol last month"

Assistant: "Let me confirm what I heard:
- New condition: High cholesterol (Hyperlipidemia)
- Diagnosis: Last month
- Status: Active

Is this correct?"

Patient: "Yes, that's right"

Assistant: "I've added high cholesterol to your health record."
```

### Specialist consultation

```text
Patient: "I've been having dizziness when I stand up. Should I be worried?"

Assistant: "I'll consult with a Primary Care specialist about your symptoms...

[Consulting specialist with de-identified data...]

Based on the specialist's assessment:

**Main Finding:** Dizziness when standing (orthostatic hypotension) can be
a side effect of Lisinopril, your blood pressure medication.

**Recommendations:**
- Rise slowly from sitting or lying positions
- Stay well hydrated
- Mention this to your doctor at your next visit

**Warning Signs:** Seek immediate care if you experience fainting
or severe dizziness.

This is for informational purposes. Please discuss with your healthcare
provider for personalized medical advice."
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
# Format with black
black src/ tests/

# Lint with flake8
flake8 src/ tests/
```

### Reset Database

```bash
# Drop and recreate tables
python -c "from src.database import drop_tables, create_tables; drop_tables(); create_tables()"

# Re-seed
python -m src.database.seed
```

## Troubleshooting

### Database connection errors

Ensure PostgreSQL is running and the database exists:

```bash
# Check PostgreSQL status
pg_isready

# Create database if missing
createdb patient_twin
```

### Missing API key

Ensure your `.env` file contains a valid Anthropic API key:

```bash
echo $ANTHROPIC_API_KEY  # Should show your key
```

### Embedding model download

The embedding model downloads automatically on first use. If you encounter issues:

```bash
# Pre-download the model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

## License

This project is for demonstration purposes.

## Disclaimer

This is a proof-of-concept application and should NOT be used for actual medical decisions.
Always consult with qualified healthcare professionals for medical advice.
