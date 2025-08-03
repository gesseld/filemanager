"""Document model definitions."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

class DocumentStatus(str, Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EXTRACTING_TEXT = "extracting_text"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
    FAILED_RETRYABLE = "failed_retryable"

class DocumentMetadata(BaseModel):
    """Metadata for a document."""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    author: Optional[str] = Field(None, max_length=100)
    created_at: Optional[datetime] = None
    pages: Optional[int] = None
    language: Optional[str] = Field(None, max_length=10)
    keywords: List[str] = Field(default_factory=list)
    custom_tags: List[str] = Field(default_factory=list)

class Document(BaseModel):
    """Core document model."""
    id: str
    user_id: str
    filename: str
    content_type: str
    size: int
    storage_path: Optional[str] = None
    status: DocumentStatus = DocumentStatus.UPLOADED
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processing_started_at: Optional[datetime] = None
    text_extracted_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    retry_count: int = 0
    ocr_text: Optional[str] = None
    vector_id: Optional[str] = None
    collection_id: Optional[str] = None
    parent_id: Optional[str] = None  # For folder hierarchy
    is_folder: bool = False  # Whether this is a folder vs file
    starred: bool = False  # Starred/flagged status
    last_accessed_at: Optional[datetime] = None  # Recent access tracking
    shared_with: List[str] = Field(default_factory=list)
    share_permissions: List[str] = Field(default_factory=list)  # e.g. ["view", "edit"]

    def update_status(self, status: DocumentStatus, reason: Optional[str] = None) -> None:
        """Update document status with detailed tracking."""
        self.status = status
        self.updated_at = datetime.utcnow()
        
        if status == DocumentStatus.PROCESSING:
            self.processing_started_at = datetime.utcnow()
        elif status == DocumentStatus.EXTRACTING_TEXT:
            self.text_extracted_at = datetime.utcnow()
        elif status == DocumentStatus.INDEXED:
            self.indexed_at = datetime.utcnow()
        elif status in (DocumentStatus.FAILED, DocumentStatus.FAILED_RETRYABLE):
            self.failed_at = datetime.utcnow()
            self.failure_reason = reason
            if status == DocumentStatus.FAILED_RETRYABLE:
                self.retry_count += 1

    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "user123",
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "size": 1024,
                "status": "uploaded",
                "collection_id": "folder123",
                "shared_with": ["user456"],
                "metadata": {
                    "title": "Sample Document",
                    "description": "Example document for testing",
                    "author": "John Doe",
                    "pages": 10,
                    "language": "en",
                    "keywords": ["sample", "test"],
                    "custom_tags": ["important", "review"]
                }
            }
        }