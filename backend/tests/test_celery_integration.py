import pytest
from unittest.mock import patch, MagicMock
from filemanager.backend.main import app
from filemanager.backend.celery import app as celery_app
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_celery():
    with patch('filemanager.backend.main.celery_app') as mock:
        mock.control.inspect.return_value.ping.return_value = {'worker1': {}}
        mock.control.inspect.return_value.active.return_value = {'worker1': [{'id': 'task1'}]}
        yield mock

class TestCeleryIntegration:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "celery_workers": 1,
            "celery_tasks": 1
        }

    @patch('filemanager.backend.tasks.extract_text.delay')
    def test_file_processing_flow(self, mock_extract, client):
        mock_extract.return_value = MagicMock(id='task123')
        
        # Simulate file upload and processing
        response = client.post("/api/v1/upload", files={"file": ("test.pdf", b"content")})
        assert response.status_code == 202
        assert response.json() == {"task_id": "task123"}

    @patch('filemanager.backend.tasks.embed_document.delay')
    def test_embedding_flow(self, mock_embed, client):
        mock_embed.return_value = MagicMock(id='task456')
        
        response = client.post("/api/v1/embed", json={"text": "sample"})
        assert response.status_code == 202
        assert response.json() == {"task_id": "task456"}

@pytest.fixture
def mock_qdrant():
    with patch('qdrant_client.QdrantClient') as mock:
        instance = mock.return_value
        instance.search.return_value = [{'id': 1, 'score': 0.9}]
        yield mock

@pytest.fixture
def mock_tika():
    with patch('tika.parser.from_buffer') as mock:
        mock.return_value = {'content': 'parsed text'}
        yield mock

def test_search_integration(client, mock_qdrant):
    response = client.get("/api/v1/search?query=test")
    assert response.status_code == 200
    assert 'results' in response.json()

def test_text_extraction_integration(mock_tika):
    from filemanager.backend.tasks import extract_text
    result = extract_text('http://test.com/file', 'application/pdf')
    assert result == 'parsed text'