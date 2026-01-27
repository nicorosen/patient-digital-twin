"""
Database connection and session management.

Provides:
- Engine creation and configuration
- Session factory with proper lifecycle management
- Context managers for database sessions
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.models import Base

# Get settings
settings = get_settings()

# Fix Supabase/Heroku-style postgres:// URLs (SQLAlchemy requires postgresql://)
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Create engine
engine = create_engine(
    db_url,
    echo=False,  # Disable SQL logging to reduce terminal noise
    pool_pre_ping=True,  # Check connection health
    pool_size=5,
    max_overflow=10,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def create_tables() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """Drop all database tables. Use with caution!"""
    Base.metadata.drop_all(bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get a database session with automatic cleanup.

    Usage:
        with get_db() as db:
            patients = db.query(Patient).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a raw database session.

    Note: Caller is responsible for closing the session.
    Prefer using get_db() context manager instead.
    """
    return SessionLocal()
