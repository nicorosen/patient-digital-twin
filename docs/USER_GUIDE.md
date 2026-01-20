# User Guide

Welcome to Patient Digital Twin! This guide will help you use the application effectively.

## Getting Started

### Starting the Application

```bash
# Quick start with database seeding
python run.py --seed --index

# Or start without seeding (if database already has data)
streamlit run src/app/streamlit_app.py
```

The application will open in your browser at `http://localhost:8501`.

## Interface Overview

### Sidebar (Left Panel)

The sidebar contains:

1. **Patient Selector**: Choose which patient to work with
2. **Agent Selector**: Switch between Medical Assistant and Health Coach
3. **Agent Mode Badge**: Shows current mode (Clinical or Coaching)
4. **Patient Profile**: View demographics, conditions, medications, allergies
5. **Consultation Log**: View past specialist consultations

### Main Area (Center)

The main area shows:

1. **Health Metrics Dashboard**: Quick stats at the top
2. **Tabs**:
   - **Chat Tab**: Conversation with your selected agent
   - **Visualizations Tab**: Interactive health data charts

## Choosing an Agent

### Medical Assistant (Clinical Mode)

Use the Medical Assistant when you want to:

- Ask about symptoms or health concerns
- Add new conditions, medications, or allergies
- Get specialist consultation for clinical questions
- Make changes to your health record

**Example prompts:**

- "What conditions do I have?"
- "I was just diagnosed with high cholesterol"
- "I've been having dizziness when I stand up. Should I be worried?"
- "Add that I'm now taking aspirin 81mg daily"

### Health Coach (Coaching Mode)

Use the Health Coach when you want to:

- Understand your conditions in simple terms
- Get lifestyle and wellness tips
- Learn why you take your medications
- Get motivation and encouragement

**Example prompts:**

- "Can you explain what diabetes means and how it affects my body?"
- "What lifestyle changes can help with my conditions?"
- "I'm finding it hard to stick to my medication routine. Can you help?"
- "Why do I take my medications and how do they help me?"

**Note:** The Health Coach cannot add or modify your health data. If you ask to add information, they'll redirect you to the Medical Assistant.

## Using the Chat Interface

### Suggested Prompts

Click the suggested prompt buttons to quickly ask common questions. These change based on which agent you're using.

### Typing Your Own Questions

Type your question in the chat input at the bottom and press Enter.

### Conversation History

Your conversation history is preserved while you're on the same patient and agent. Switching patients or agents clears the history.

## Understanding Specialist Consultations

When you ask the Medical Assistant a clinical question (like about symptoms), they may consult a specialist:

1. **Consultation Initiated**: The assistant says they're consulting a specialist
2. **De-identification**: Your data is anonymized (age, gender, conditions - no name)
3. **Specialist Assessment**: The Primary Care specialist reviews and responds
4. **Translation**: Complex medical terms are translated to plain language
5. **Response Delivered**: You receive easy-to-understand advice

### Viewing the Audit Log

All consultations are logged for transparency. To view:

1. Open the sidebar
2. Click "Consultation Log" expander
3. See each consultation with:
   - Date and specialist type
   - The clinical question asked
   - Data that was shared (de-identified)
   - The specialist's response

## Using the Dashboard

### Health Metrics Cards

At the top of the main area, you'll see four metric cards:

| Metric | Description |
|--------|-------------|
| Conditions | Number of active conditions |
| Medications | Number of active medications |
| Allergies | Total allergy count |
| Last Consult | Date of most recent specialist consultation |

### Visualizations Tab

Click the "Visualizations" tab to see:

#### Condition Severity Chart

A donut chart showing the distribution of your conditions by severity:

- Green: Mild conditions
- Yellow: Moderate conditions
- Red: Severe conditions

#### Consultation History Chart

A bar chart showing how many specialist consultations you've had over time.

#### Medication Timeline

A timeline showing when each medication was started and if/when it was stopped.

## Managing Health Data

### Adding a Condition

With the Medical Assistant, say something like:

- "I was diagnosed with high blood pressure"
- "I have type 2 diabetes"
- "Add anxiety disorder to my conditions"

The assistant will:

1. Confirm what they understood
2. Ask for additional details if needed (severity, onset date)
3. Add it to your record
4. Confirm the addition

### Adding a Medication

Say something like:

- "I'm now taking metformin 500mg twice daily"
- "My doctor prescribed lisinopril 10mg"
- "Add aspirin 81mg daily for heart health"

### Adding an Allergy

Say something like:

- "I'm allergic to penicillin"
- "I have a shellfish allergy"
- "Add that I react to sulfa drugs"

## Tips for Best Results

### Be Specific

Instead of: "Tell me about my medications"
Try: "What is metformin for and when should I take it?"

### Ask Follow-up Questions

The agents remember your conversation. You can ask:

- "Tell me more about that"
- "What else should I know?"
- "Can you explain that in simpler terms?"

### Use the Right Agent

- Clinical questions symptom concerns: Medical Assistant
- Understanding and education: Health Coach

### Check Your Profile

Before chatting, review your profile in the sidebar to ensure your health information is accurate.

## Troubleshooting

### "No patients found"

Run the database seeding:

```bash
python -m src.database.seed
```

### Chat Not Responding

1. Check that your LLM API key is configured in `.env`
2. Check the terminal for error messages
3. Try refreshing the page

### Visualizations Not Loading

Ensure plotly is installed:

```bash
pip install plotly
```

### Agent Seems Confused

Try:

1. Clearing the conversation (switch agents and back)
2. Being more specific in your question
3. Providing context about what you're asking

## Privacy and Security

### What's Protected

- Your name and date of birth are never shared with specialists
- Specialist consultations use de-identified data only
- All consultations are logged for your review

### What's Shared in Consultations

When consulting a specialist, only this information is shared:

- Your age (calculated)
- Your gender
- Condition names
- Medication names and dosages
- Allergy substances

### Viewing Shared Data

Open the Consultation Log in the sidebar to see exactly what data was shared in each consultation.

## Getting Help

### In the Application

The agents can help explain:

- What conditions mean
- Why medications are prescribed
- How to manage your health

### Technical Issues

For technical problems with the application:

1. Check this User Guide
2. Review the README.md
3. Check the Architecture documentation

## Disclaimer

This application is a demonstration/proof-of-concept. It is NOT intended for actual medical decisions. Always consult with qualified healthcare professionals for medical advice.
