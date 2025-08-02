"""Indexing service for text extraction using Apache Tika."""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import requests
from loguru import logger

from app.core.config import settings


class IndexingService:
    """Service for extracting text and metadata from documents using Apache Tika."""
    
    def __init__(self):
        """Initialize indexing service with Tika configuration."""
        self.tika_url = settings.tika_url
        self.timeout = 300  # 5 minutes timeout for large files
        
    async def extract_text(self, file_path: str, mime_type: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text and metadata from a document using Apache Tika.
        
        Args:
            file_path: Path to the file to extract text from
            mime_type: MIME type of the file
            
        Returns:
            Tuple of (extracted_text, metadata_dict)
            
        Raises:
            Exception: If text extraction fails
        """
        try:
            # Check if Tika server is available
            if not self._check_tika_health():
                raise Exception("Tika server is not available")
            
            # Prepare file for Tika
            with open(file_path, 'rb') as file:
                files = {'file': file}
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': mime_type
                }
                
                # Call Tika for text extraction
                response = requests.post(
                    f"{self.tika_url}/tika",
                    files=files,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    raise Exception(f"Tika extraction failed: {response.status_code}")
                
                extracted_text = response.text.strip()
                
                # Get metadata
                metadata = await self._extract_metadata(file_path, mime_type)
                
                logger.info(
                    f"Successfully extracted text from {file_path} "
                    f"(length: {len(extracted_text)} chars)"
                )
                
                return extracted_text, metadata
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            raise
    
    async def _extract_metadata(self, file_path: str, mime_type: str) -> Dict[str, Any]:
        """
        Extract metadata from a document using Apache Tika.
        
        Args:
            file_path: Path to the file
            mime_type: MIME type of the file
            
        Returns:
            Dictionary containing metadata
        """
        try:
            with open(file_path, 'rb') as file:
                files = {'file': file}
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': mime_type
                }
                
                response = requests.put(
                    f"{self.tika_url}/meta",
                    files=files,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    metadata = response.json()
                    # Clean up metadata - remove empty values and binary data
                    cleaned_metadata = {}
                    for key, value in metadata.items():
                        if value and not key.startswith('X-TIKA'):
                            if isinstance(value, (str, int, float, bool)):
                                cleaned_metadata[key] = value
                            elif isinstance(value, list) and value:
                                cleaned_metadata[key] = value
                    
                    return cleaned_metadata
                else:
                    logger.warning(f"Failed to extract metadata: {response.status_code}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {}
    
    def _check_tika_health(self) -> bool:
        """Check if Tika server is healthy and available."""
        try:
            response = requests.get(
                f"{self.tika_url}/tika",
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def is_supported_type(self, mime_type: str) -> bool:
        """Check if the MIME type is supported by Tika."""
        supported_types = {
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
            'application/zip',
            'application/x-tar',
            'application/gzip',
            'application/x-bzip2',
            'application/x-7z-compressed',
            'application/x-rar-compressed',
        }
        
        # Add image types that Tika can extract text from
        supported_types.update({
            'image/jpeg',
            'image/png',
            'image/tiff',
            'image/bmp',
            'image/gif',
            'image/webp',
        })
        
        return mime_type in supported_types


# Document model import
from backend.app.models.document import Document

# Global indexing service instance

# Qdrant client setup
from qdrant_client import QdrantClient
from qdrant_client.http import models

qdrant_client = QdrantClient(
    host=settings.qdrant_host,
    port=settings.qdrant_port,
    api_key=settings.qdrant_api_key,
    timeout=settings.qdrant_timeout
)

# Meilisearch client setup
from meilisearch import Client as MeilisearchClient

meilisearch_client = MeilisearchClient(
    f"http://{settings.meilisearch_host}:{settings.meilisearch_port}",
    settings.meilisearch_api_key
)

class SearchService:
    """Service for managing document search indexes."""
    
    def __init__(self):
        """Initialize search service clients."""
        self.qdrant = qdrant_client
        self.meilisearch = meilisearch_client
        
    async def index_document(self, document: Document, text: str):
        """Index document in both Qdrant and Meilisearch."""
        from loguru import logger
        
        try:
            # Qdrant vector index
            vector = await self._get_document_embedding(text)
            self.qdrant.upsert(
                collection_name="documents",
                points=[
                    models.PointStruct(
                        id=document.id,
                        vector=vector,
                        payload={
                            "title": document.title,
                            "content": text,
                            "metadata": document.metadata
                        }
                    )
                ]
            )
            
            # Meilisearch full-text index
            self.meilisearch.index("documents").add_documents([{
                "id": document.id,
                "title": document.title,
                "content": text,
                "metadata": document.metadata
            }])
            
            logger.info(f"Successfully indexed document {document.id}")
            
        except Exception as e:
            logger.error(f"Failed to index document {document.id}: {e}")
            raise
            
    async def delete_document(self, document_id: int):
        """Remove document from both indexes."""
        from loguru import logger
        
        try:
            # Qdrant
            self.qdrant.delete(
                collection_name="documents",
                points=[document_id]
            )
            
            # Meilisearch
            self.meilisearch.index("documents").delete_document(document_id)
            
            logger.info(f"Successfully deleted document {document_id} from indexes")
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id} from indexes: {e}")
            raise
            
    async def _get_document_embedding(self, text: str) -> list[float]:
        """Generate document embedding vector."""
        # TODO: Implement actual embedding generation
        # Placeholder - replace with your embedding model
        return [0.0] * 768


search_service = SearchService()
indexing_service = IndexingService()