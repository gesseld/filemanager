"""Tests for text extraction services."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.services.indexing_service import IndexingService
from app.services.ocr_service import OCRService
from app.services.text_extraction_service import TextExtractionService


class TestIndexingService:
    """Tests for IndexingService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = IndexingService()
        self.service.tika_url = "http://localhost:9998"
    
    @pytest.mark.asyncio
    async def test_extract_text_success(self):
        """Test successful text extraction."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello, this is a test document.")
            temp_path = f.name
        
        try:
            with patch('requests.post') as mock_post, \
                 patch('requests.put') as mock_put:
                
                mock_post.return_value.status_code = 200
                mock_post.return_value.text = "Hello, this is a test document."
                
                mock_put.return_value.status_code = 200
                mock_put.return_value.json.return_value = {
                    'Content-Type': 'text/plain',
                    'Content-Length': '35'
                }
                
                text, metadata = await self.service.extract_text(temp_path, 'text/plain')
                
                assert text == "Hello, this is a test document."
                assert metadata['Content-Type'] == 'text/plain'
                
        finally:
            os.unlink(temp_path)
    
    def test_is_supported_type(self):
        """Test MIME type support checking."""
        assert self.service.is_supported_type('application/pdf') is True
        assert self.service.is_supported_type('image/jpeg') is True
        assert self.service.is_supported_type('application/unknown') is False


class TestOCRService:
    """Tests for OCRService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = OCRService()
        self.service.tesseract_url = "http://localhost:8080"
        self.service.mistral_api_key = "test-key"
    
    @pytest.mark.asyncio
    async def test_extract_image_text_tesseract_success(self):
        """Test successful OCR with Tesseract."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            with patch('requests.post') as mock_post, \
                 patch('requests.get') as mock_get:
                
                mock_get.return_value.status_code = 200
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {
                    'text': 'Extracted text from image'
                }
                
                text, metadata = await self.service.extract_image_text(temp_path)
                
                assert text == 'Extracted text from image'
                assert metadata['engine'] == 'tesseract'
                
        finally:
            os.unlink(temp_path)
    
    def test_is_supported_image(self):
        """Test image format support checking."""
        assert self.service.is_supported_image('image/jpeg') is True
        assert self.service.is_supported_image('image/png') is True
        assert self.service.is_supported_image('application/pdf') is False


class TestTextExtractionService:
    """Tests for TextExtractionService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = TextExtractionService()
    
    def test_is_text_extraction_needed(self):
        """Test text extraction need checking."""
        assert self.service.is_text_extraction_needed('application/pdf') is True
        assert self.service.is_text_extraction_needed('image/jpeg') is True
        assert self.service.is_text_extraction_needed('application/octet-stream') is False
    
    @pytest.mark.asyncio
    async def test_extract_text_from_document_pdf(self):
        """Test PDF document text extraction."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            temp_path = f.name
        
        try:
            with patch.object(self.service, '_extract_document_text') as mock_extract:
                mock_extract.return_value = {
                    'text_extraction_status': 'completed',
                    'extracted_text': 'PDF content',
                    'extracted_metadata': {'pages': 1},
                    'ocr_status': 'not_required'
                }
                
                # Mock document
                class MockDocument:
                    def __init__(self):
                        self.id = 1
                        self.file_path = temp_path
                        self.mime_type = 'application/pdf'
                
                document = MockDocument()
                results = await self.service.extract_text_from_document(document)
                
                assert results['text_extraction_status'] == 'completed'
                assert results['extracted_text'] == 'PDF content'
                
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_extract_text_from_document_image(self):
        """Test image document text extraction."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jpg', delete=False) as f:
            temp_path = f.name
        
        try:
            with patch.object(self.service, '_extract_image_text') as mock_extract:
                mock_extract.return_value = {
                    'text_extraction_status': 'not_required',
                    'extracted_text': None,
                    'extracted_metadata': {},
                    'ocr_status': 'completed',
                    'ocr_text': 'Image text',
                    'ocr_confidence': {'confidence': 0.95}
                }
                
                # Mock document
                class MockDocument:
                    def __init__(self):
                        self.id = 1
                        self.file_path = temp_path
                        self.mime_type = 'image/jpeg'
                
                document = MockDocument()
                results = await self.service.extract_text_from_document(document)
                
                assert results['ocr_status'] == 'completed'
                assert results['ocr_text'] == 'Image text'
                
        finally:
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_integration_flow():
    """Test complete integration flow."""
    service = TextExtractionService()
    
    # Test with a mock document
    class MockDocument:
        def __init__(self):
            self.id = 1
            self.file_path = "/tmp/test.pdf"
            self.mime_type = "application/pdf"
    
    document = MockDocument()
    
    with patch.object(service, '_extract_document_text') as mock_extract, \
         patch('os.path.exists') as mock_exists:
        
        mock_exists.return_value = True
        mock_extract.return_value = {
            'text_extraction_status': 'completed',
            'extracted_text': 'Test content',
            'extracted_metadata': {'pages': 1},
            'ocr_status': 'not_required'
        }
        
        results = await service.extract_text_from_document(document)
        
        assert results['text_extraction_status'] == 'completed'
        assert results['extracted_text'] == 'Test content'