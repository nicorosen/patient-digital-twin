"""
Database connection and data access layer.

Provides:
- PostgreSQL connection management
- Repository pattern for CRUD operations
- Transaction handling
- Database seeding utilities
"""

from src.database.connection import (
    SessionLocal,
    create_tables,
    drop_tables,
    engine,
    get_db,
    get_db_session,
)
from src.database.repositories import (
    AllergyRepository,
    AuditLogRepository,
    ConditionRepository,
    ConversationRepository,
    MedicationRepository,
    PatientRepository,
)
from src.database.seed import seed_database

__all__ = [
    # Connection
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_session",
    "create_tables",
    "drop_tables",
    # Repositories
    "PatientRepository",
    "ConditionRepository",
    "MedicationRepository",
    "AllergyRepository",
    "ConversationRepository",
    "AuditLogRepository",
    # Seeding
    "seed_database",
]
