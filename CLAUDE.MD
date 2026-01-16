# CLAUDE.MD

This file provides context and guidance for AI assistants working on this project.

## Project Overview

**Project Name:** Patient Digital Twin
**Type:** Python Application
**Purpose:** [To be defined - appears to be a healthcare/medical digital twin system]

## Project Structure

This is a new project. Structure to be established.

## Technology Stack

- **Language:** Python
- **Version Control:** Git

## Development Guidelines

### Code Style
- Follow PEP 8 Python style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes

### Testing
- Write unit tests for new features
- Maintain test coverage
- Run tests before committing

### Security & Privacy
- This project likely involves sensitive healthcare data
- Follow HIPAA compliance guidelines if applicable
- Never commit sensitive patient data or credentials
- Use environment variables for configuration secrets

## Key Concepts

### Digital Twin
A digital twin is a virtual representation of a physical entity (in this case, a patient) that:
- Models patient health data and characteristics
- Can simulate patient responses to treatments
- Provides predictive insights for healthcare decisions

## Common Tasks

### Setup Development Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies (once requirements.txt exists)
pip install -r requirements.txt
```

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
# Using black
black .

# Using flake8 for linting
flake8 .
```

## Important Notes for AI Assistants

1. **Healthcare Context:** This project deals with patient data - prioritize privacy and security
2. **Data Sensitivity:** Never generate or use real patient data in examples
3. **Compliance:** Consider healthcare regulations (HIPAA, GDPR) in all implementations
4. **Documentation:** Maintain clear documentation for medical algorithms and models
5. **Testing:** Thorough testing is critical for healthcare applications

## Project Status

- [ ] Initial project structure
- [ ] Core data models
- [ ] Patient twin simulation engine
- [ ] API/Interface layer
- [ ] Testing framework
- [ ] Documentation

## Resources

- Project Repository: /Users/nicorosen/code_projects/python/patient-digital-twin
- Documentation: [To be added]
- Issue Tracker: [To be added]

## Contact & Contribution

[To be defined]

---

**Last Updated:** 2026-01-16
**Maintained By:** Project Team
