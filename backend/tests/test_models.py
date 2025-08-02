"""Test database models."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.models.document import Document
from app.models.search_history import SearchHistory


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_user_creation(db_session):
    """Test user model creation."""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=False
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.username == "testuser"


def test_document_creation(db_session):
    """Test document model creation."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    
    document = Document(
        title="Test Document",
        filename="test.pdf",
        file_path="/uploads/test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        checksum="abc123",
        owner_id=user.id
    )
    db_session.add(document)
    db_session.commit()
    
    assert document.id is not None
    assert document.title == "Test Document"
    assert document.owner_id == user.id


def test_search_history_creation(db_session):
    """Test search history model creation."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    
    search = SearchHistory(
        query="test search",
        search_type="general",
        results_count=10,
        user_id=user.id
    )
    db_session.add(search)
    db_session.commit()
    
    assert search.id is not None
    assert search.query == "test search"
    assert search.user_id == user.id