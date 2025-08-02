"""Text extraction service that integrates Tika and OCR services."""
from .base import BaseService
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from sqlalchemy import select
from app.models.document import Document
from app.services.indexing_service import indexing_service
from app.services.ocr_service import ocr_service
from app.db.session import SessionLocal


class TextExtractionService(BaseService):
    """Service for orchestrating text extraction from documents."""
    
    def __init__(self):
        """Initialize text extraction service."""
        super().__init__()
        self.supported_image_types = {
            'image/jpeg',
            'image/png',
            'image/tiff',
            'image/bmp',
            'image/gif',
            'image/webp'
        }
        
        self.supported_document_types = {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain',
            'text/html',
            'text/xml',
            'text/csv',
            'application/json',
            'application/xml',
            'application/rtf',
            'application/epub+zip',
        }
    
    async def extract_text_from_document(self, document: Document) -> Dict[str, Any]:
        """
        Extract text from a document based on its type.
        
        Args:
            document: Document model instance
            
        Returns:
            Dictionary with extraction results
        """
        try:
            file_path = document.file_path
            mime_type = document.mime_type
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            results = {
                'text_extraction_status': 'failed',
                'ocr_status': 'failed',
                'extracted_text': None,
                'ocr_text': None,
                'extracted_metadata': {},
                'ocr_confidence': {}
            }
            
            # Extract text based on file type
            if mime_type in self.supported_document_types:
                results.update(await self._extract_document_text(file_path, mime_type))
            elif mime_type in self.supported_image_types:
                results.update(await self._extract_image_text(file_path))
            else:
                self.logger.warning(f"Unsupported file type: {mime_type}")
                results['text_extraction_status'] = 'unsupported'
                results['ocr_status'] = 'unsupported'
            
            # Update document in database
            await self._update_document_with_results(document.id, results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error extracting text from document {document.id}: {e}")
            await self._update_document_status(document.id, 'failed', str(e))
            raise
    
    async def _extract_document_text(self, file_path: str, mime_type: str) -> Dict[str, Any]:
        """Extract text from document files using Tika."""
        try:
            extracted_text, metadata = await indexing_service.extract_text(file_path, mime_type)
            
            return {
                'text_extraction_status': 'completed',
                'extracted_text': extracted_text,
                'extracted_metadata': metadata,
                'ocr_status': 'not_required'  # Documents don't need OCR
            }
            
        except Exception as e:
            self.logger.error(f"Document text extraction failed: {e}")
            return {
                'text_extraction_status': 'failed',
                'extracted_text': None,
                'extracted_metadata': {},
                'ocr_status': 'not_required'
            }
    
    async def _extract_image_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text from image files using OCR."""
        try:
            ocr_text, ocr_metadata = await ocr_service.extract_image_text(file_path)
            
            return {
                'text_extraction_status': 'not_required',  # Images use OCR
                'extracted_text': None,
                'extracted_metadata': {},
                'ocr_status': 'completed',
                'ocr_text': ocr_text,
                'ocr_confidence': ocr_metadata
            }
            
        except Exception as e:
            self.logger.error(f"Image text extraction failed: {e}")
            return {
                'text_extraction_status': 'not_required',
                'extracted_text': None,
                'extracted_metadata': {},
                'ocr_status': 'failed'
            }
    
    async def _update_document_with_results(self, document_id: int, results: Dict[str, Any]) -> None:
        """Update document with extraction results."""
        async with SessionLocal() as session:
            document = await session.get(Document, document_id)
            if document:
                document.text_extraction_status = results['text_extraction_status']
                document.ocr_status = results['ocr_status']
                document.extracted_text = results['extracted_text']
                document.ocr_text = results['ocr_text']
                document.extracted_metadata = results['extracted_metadata']
                document.ocr_confidence = results['ocr_confidence']
                
                await session.commit()
                self.logger.info(f"Updated document {document_id} with extraction results")
    
    async def _update_document_status(self, document_id: int, status: str, error: str = None) -> None:
        """Update document status with error information."""
        async with SessionLocal() as session:
            document = await session.get(Document, document_id)
            if document:
                document.text_extraction_status = status
                document.ocr_status = status
                if error:
                    document.metadata = {**document.metadata, 'extraction_error': error}
                await session.commit()
    
    async def process_pending_documents(self) -> int:
        """
        Process all documents with pending text extraction.
        
        Returns:
            Number of documents processed
        """
        try:
            async with SessionLocal() as session:
                # Get documents with pending extraction
                pending_docs = await session.execute(
                    select(Document).where(
                        (Document.text_extraction_status == 'pending') |
                        (Document.ocr_status == 'pending')
                    )
                )
                documents = pending_docs.scalars().all()
                
                processed_count = 0
                for document in documents:
                    try:
                        await self.extract_text_from_document(document)
                        processed_count += 1
                        
                        # Add small delay to avoid overwhelming services
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to process document {document.id}: {e}")
                
                return processed_count
                
        except Exception as e:
            self.logger.error(f"Error processing pending documents: {e}")
            return 0
    
    def is_text_extraction_needed(self, mime_type: str) -> bool:
        """Check if text extraction is needed for the given MIME type."""
        return (
            mime_type in self.supported_document_types or
            mime_type in self.supported_image_types
        )


# Global text extraction service instance
text_extraction_service = TextExtractionService()
