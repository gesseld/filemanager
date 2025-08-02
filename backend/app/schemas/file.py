"""File upload schemas and validation models."""

from typing import Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime


class FileUploadResponse(BaseModel):
    """Response schema for file upload."""
    
    id: int = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Storage path")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    status: str = Field(default="pending", description="Processing status")
    created_at: datetime = Field(..., description="Upload timestamp")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class FileUploadError(BaseModel):
    """Error response schema for file upload."""
    
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    filename: Optional[str] = Field(None, description="Filename that caused error")


class FileValidationConfig:
    """Configuration for file validation."""
    
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_MIME_TYPES = {
        # Documents
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
        'text/csv',
        'text/markdown',
        
        # Images
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/svg+xml',
        
        # Archives
        'application/zip',
        'application/x-tar',
        'application/x-7z-compressed',
        'application/x-rar-compressed',
    }