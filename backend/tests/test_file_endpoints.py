"""Tests for file management API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from backend.app.main import app
from backend.app.db.session import get_db
from backend.app.models.document import Document
from backend.app.models.user import User
from backend.app.tests.conftest import override_get_db
from backend.app.services.navigation_state import NavigationStateService

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture
def test_user(test_db: Session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashedpass",
        preferences=json.dumps({
            "view_mode": "list",
            "sort_by": "name",
            "sort_order": "asc"
        })
    )
    test_db.add(user)
    test_db.commit()
    return user

@pytest.fixture
def test_documents(test_db: Session, test_user: User):
    """Create test documents for navigation."""
    docs = []
    for i in range(1, 21):
        doc = Document(
            title=f"Test Doc {i}",
            filename=f"test_{i}.txt",
            file_path=f"/test/test_{i}.txt",
            file_size=100 * i,
            mime_type="text/plain",
            checksum=f"abc{i}",
            status="processed",
            owner_id=test_user.id,
            updated_at=datetime.utcnow() - timedelta(hours=i),
            last_accessed_at=datetime.utcnow() - timedelta(hours=i)
        )
        if i % 5 == 0:
            doc.starred = True
        if i % 3 == 0:
            doc.shared_with = ["user2"]
        test_db.add(doc)
        docs.append(doc)
    test_db.commit()
    return docs

def test_browse_files_basic(test_db: Session, test_user: User, test_documents):
    """Test basic folder browsing."""
    response = client.get(
        "/api/v1/files/browse",
        headers={"Authorization": f"Bearer {test_user.id}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 20
    assert data["has_more"] is False

def test_browse_files_pagination(test_db: Session, test_user: User, test_documents):
    """Test cursor-based pagination."""
    # First page
    response = client.get(
        "/api/v1/files/browse?per_page=5",
        headers={"Authorization": f"Bearer {test_user.id}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5
    assert data["has_more"] is True
    assert "next_cursor" in data

    # Second page
    response = client.get(
        f"/api/v1/files/browse?per_page=5&cursor={data['next_cursor']}",
        headers={"Authorization": f"Bearer {test_user.id}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5
    assert data["has_more"] is True

def test_browse_files_sorting(test_db: Session, test_user: User, test_documents):
    """Test different sorting options."""
    # Sort by size descending
    response = client.get(
        "/api/v1/files/browse?sort_by=size&sort_order=desc",
        headers={"Authorization": f"Bearer {test_user.id}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["size"] > data["items"][1]["size"]

    # Sort by date ascending
    response = client.get(
        "/api/v1/files/browse?sort_by=date&sort_order=asc",
        headers={"Authorization": f"Bearer {test_user.id}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["updated_at"] < data["items"][1]["updated_at"]

def test_browse_files_view_modes(test_db: Session, test_user: User, test_documents):
    """Test different view modes."""
    response = client.get(
        "/api/v1/files/browse?view_mode=grid",
        headers={"Authorization": f"Bearer {test_user.id}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["view_mode"] == "grid"

def test_breadcrumbs(test_db: Session, test_user: User):
    """Test breadcrumb generation."""
    response = client.get(
        "/api/v1/files/breadcrumbs?path=/test/path",
        headers={"Authorization": f"Bearer {test_user.id}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_recent_files(test_db: Session, test_user: User, test_documents):
    """Test recent files collection."""
    response = client.get(
        "/api/v1/files/collections/recent",
        headers={"Authorization": f"Bearer {test_user.id}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["has_more"] is True

def test_starred_files(test_db: Session, test_user: User, test_documents):
    """Test starred files collection."""
    response = client.get(
        "/api/v1/files/collections/starred",
        headers={"Authorization": f"Bearer {test_user.id}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 4  # 20/5 = 4 starred docs
    assert all(doc["starred"] for doc in data["items"])

def test_shared_files(test_db: Session, test_user: User, test_documents):
    """Test shared files collection."""
    response = client.get(
        "/api/v1/files/collections/shared",
        headers={"Authorization": f"Bearer {test_user.id}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 6  # 20/3 ≈ 6 shared docs
    assert test_user.id in data["items"][0]["shared_with"]

def test_navigation_state_persistence(test_db: Session, test_user: User):
    """Test navigation state persistence."""
    mock_service = MagicMock(spec=NavigationStateService)
    app.dependency_overrides[NavigationStateService] = lambda: mock_service

    response = client.get(
        "/api/v1/files/browse",
        headers={"Authorization": f"Bearer {test_user.id}"}
    )
    assert response.status_code == 200
    mock_service.save_state.assert_called_once()

    app.dependency_overrides.pop(NavigationStateService)

def test_browse_files_unauthorized():
    """Test unauthorized access to browse endpoint."""
    response = client.get("/api/v1/files/browse")
    assert response.status_code == 401