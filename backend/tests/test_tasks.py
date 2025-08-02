import pytest
from unittest.mock import patch, MagicMock
from filemanager.backend.tasks import extract_text, embed_document
from celery.exceptions import Retry

@pytest.fixture
def mock_requests():
    with patch('requests.get') as mock:
        yield mock

@pytest.fixture
def mock_magic():
    with patch('magic.Magic') as mock:
        yield mock

@pytest.fixture
def mock_pytesseract():
    with patch('pytesseract.image_to_string') as mock:
        yield mock

@pytest.fixture
def mock_pypdf2():
    with patch('PyPDF2.PdfReader') as mock:
        yield mock

class TestExtractTextTask:
    def test_extract_text_from_image(self, mock_requests, mock_magic, mock_pytesseract):
        mock_requests.return_value.content = b'image_data'
        mock_magic.return_value.from_buffer.return_value = 'image/png'
        mock_pytesseract.return_value = 'extracted text'
        
        result = extract_text('http://example.com/image.png')
        assert result == 'extracted text'

    def test_extract_text_from_pdf(self, mock_requests, mock_magic, mock_pypdf2):
        mock_requests.return_value.content = b'pdf_data'
        mock_magic.return_value.from_buffer.return_value = 'application/pdf'
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock(extract_text=lambda: 'page1'), MagicMock(extract_text=lambda: 'page2')]
        mock_pypdf2.return_value = mock_reader
        
        result = extract_text('http://example.com/doc.pdf')
        assert result == 'page1\npage2'

    def test_retry_on_failure(self, mock_requests):
        mock_requests.side_effect = Exception('Failed')
        task = extract_text.s('http://example.com/file.txt')
        with pytest.raises(Retry):
            task.apply()

class TestEmbedDocumentTask:
    @patch('filemanager.backend.tasks.logger')
    def test_embed_document(self, mock_logger):
        result = embed_document('sample text')
        assert len(result) == 768  # Mock embedding dimension
        
    @patch('filemanager.backend.tasks.logger')
    def test_retry_on_failure(self, mock_logger):
        with patch('filemanager.backend.tasks.SOME_EMBEDDING_FUNC', side_effect=Exception('Failed')):
            task = embed_document.s('sample text')
            with pytest.raises(Retry):
                task.apply()