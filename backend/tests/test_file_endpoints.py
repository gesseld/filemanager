import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.main import app
from backend.app.db.session import get_db
from backend.app.models.document import Document
from backend.app.tests.conftest import override_get_db

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_delete_file_success(test_db: Session):
    # Create test document
    doc = Document(
        title="Test Doc",
        filename="test.txt",
        file_path="/test/test.txt",
        file_size=100,
        mime_type="text/plain",
        checksum="abc123",
        status="processed",
        owner_id=1
    )
    test_db.add(doc)
    test_db.commit()

    # Test delete
    response = client.delete(f"/api/v1/files/{doc.id}")
    assert response.status_code == 204
    assert test_db.query(Document).filter(Document.id == doc.id).first() is None

def test_delete_file_not_found(test_db: Session):
    response = client.delete("/api/v1/files/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"

def test_reindex_file_success(test_db: Session):
    # Create test document
    doc = Document(
        title="Test Doc",
        filename="test.txt",
        file_path="/test/test.txt",
        file_size=100,
        mime_type="text/plain",
        checksum="abc123",
        status="processed",
        owner_id=1
    )
    test_db.add(doc)
    test_db.commit()

    # Test reindex
    response = client.post(f"/api/v1/files/{doc.id}/reindex")
    assert response.status_code == 202

def test_reindex_file_not_found(test_db: Session):
    response = client.post("/api/v1/files/9999/reindex")
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"

@pytest.mark.asyncio
async def test_cleanup_search_indexes_task(test_db: Session, mocker):
    from app.tasks import cleanup_search_indexes
    mock_qdrant = mocker.patch("app.services.indexing_service.qdrant_client")
    mock_meilisearch = mocker.patch("app.services.indexing_service.meilisearch_client")

    # Test task execution
    await cleanup_search_indexes(1)
    mock_qdrant.delete.assert_called_once()
    mock_meilisearch.index().delete_document.assert_called_once()

@pytest.mark.asyncio
async def test_reindex_document_task(test_db: Session, mocker):
    from app.tasks import reindex_document
    mock_qdrant = mocker.patch("app.services.indexing_service.qdrant_client")
    mock_meilisearch = mocker.patch("app.services.indexing_service.meilisearch_client")

    # Create test document
    doc = Document(
        title="Test Doc",
        filename="test.txt",
        file_path="/test/test.txt",
        file_size=100,
        mime_type="text/plain",
        checksum="abc123",
        status="processed",
        owner_id=1
    )
    test_db.add(doc)
    test_db.commit()

    # Test task execution
    await reindex_document(doc.id)
    mock_qdrant.upsert.assert_called_once()
    mock_meilisearch.index().add_documents.assert_called_once()