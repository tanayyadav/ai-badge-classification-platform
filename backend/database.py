"""
SQLAlchemy engine, session factory, and table initialisation.

All other modules import get_db() for dependency injection.
create_tables() is called once from main.py lifespan handler.
"""

import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.governance_log import Base

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./badges.db")

# connect_args required for SQLite to allow multi-threaded access
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """Create all tables defined in Base metadata. Safe to call on every startup."""
    Base.metadata.create_all(bind=engine)


def migrate_tables() -> None:
    """
    Add new columns to existing tables without dropping data.

    Each ALTER TABLE is wrapped in try/except so it silently skips
    columns that already exist (SQLite raises OperationalError for
    duplicate column additions).
    """
    _new_columns = [
        ("submitter_email",              "TEXT"),
        ("reviewer_email",               "TEXT"),
        ("review_token",                 "TEXT"),
        ("review_token_expires_at",      "TEXT"),
        ("notification_sent_at",         "TEXT"),
        ("decision_notification_sent_at","TEXT"),
    ]
    with engine.connect() as conn:
        for col_name, col_type in _new_columns:
            try:
                conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE governance_logs ADD COLUMN {col_name} {col_type}"
                    )
                )
                conn.commit()
            except Exception:
                # Column already exists — safe to ignore
                pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency — yields a database session and guarantees cleanup.

    Usage in route:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager version for use outside of FastAPI dependency injection
    (e.g. scripts, tests).

    Usage:
        with get_db_context() as db:
            db.add(record)
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
