"""Database initialization utilities."""

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .session import engine
from app.models.base import Base


def init_db() -> None:
    """Initialize database by creating all tables."""
    Base.metadata.create_all(bind=engine)


def check_db_connection(db: Session) -> bool:
    """Check if database connection is healthy."""
    try:
        # Try to execute a simple query
        db.execute("SELECT 1")
        return True
    except Exception:
        return False


def get_table_names() -> list[str]:
    """Get list of all table names in the database."""
    inspector = inspect(engine)
    return inspector.get_table_names()