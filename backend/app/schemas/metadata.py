"""File metadata schemas."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class FileMetadataResponse(BaseModel):
    """Response schema for file metadata."""
    
    file_path: str = Field(..., description="Relative file path")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    size_human: str = Field(..., description="Human-readable file size")
    created_date: str = Field(..., description="File creation date (ISO format)")
    modified_date: str = Field(..., description="Last modification date (ISO format)")
    accessed_date: str = Field(..., description="Last access date (ISO format)")
    mime_type: str = Field(..., description="MIME type")
    extension: str = Field(..., description="File extension")
    checksum: str = Field(..., description="SHA-256 checksum")
    permissions: str = Field(..., description="File permissions (octal)")
    is_hidden: bool = Field(..., description="Whether file is hidden")
    absolute_path: str = Field(..., description="Absolute file path")
    directory: str = Field(..., description="Directory path")
    stem: str = Field(..., description="Filename without extension")
    
    # Type-specific metadata
    image_width: Optional[int] = Field(None, description="Image width in pixels")
    image_height: Optional[int] = Field(None, description="Image height in pixels")
    image_mode: Optional[str] = Field(None, description="Image color mode")
    image_format: Optional[str] = Field(None, description="Image format")
    image_has_transparency: Optional[bool] = Field(None, description="Whether image has transparency")
    
    # PDF metadata
    pdf_title: Optional[str] = Field(None, description="PDF title")
    pdf_author: Optional[str] = Field(None, description="PDF author")
    pdf_subject: Optional[str] = Field(None, description="PDF subject")
    pdf_creator: Optional[str] = Field(None, description="PDF creator")
    pdf_producer: Optional[str] = Field(None, description="PDF producer")
    pdf_creation_date: Optional[str] = Field(None, description="PDF creation date")
    pdf_modification_date: Optional[str] = Field(None, description="PDF modification date")
    pdf_pages: Optional[int] = Field(None, description="Number of PDF pages")
    pdf_encrypted: Optional[bool] = Field(None, description="Whether PDF is encrypted")
    
    # Text metadata
    text_lines: Optional[int] = Field(None, description="Number of text lines")
    text_characters: Optional[int] = Field(None, description="Number of characters")
    text_words: Optional[int] = Field(None, description="Number of words")
    text_encoding: Optional[str] = Field(None, description="Text encoding")
    
    # System metadata
    unix_uid: Optional[int] = Field(None, description="Unix user ID")
    unix_gid: Optional[int] = Field(None, description="Unix group ID")
    unix_device: Optional[int] = Field(None, description="Unix device ID")
    unix_inode: Optional[int] = Field(None, description="Unix inode number")
    unix_nlink: Optional[int] = Field(None, description="Unix hard link count")
    
    # Windows metadata
    windows_attributes: Optional[int] = Field(None, description="Windows file attributes")
    is_readonly: Optional[bool] = Field(None, description="Whether file is read-only")
    is_system: Optional[bool] = Field(None, description="Whether file is system file")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class MetadataBatchResponse(BaseModel):
    """Response schema for batch metadata extraction."""
    
    files: Dict[str, Any] = Field(..., description="Dictionary mapping file paths to metadata")
    total_files: int = Field(..., description="Total number of files processed")
    successful: int = Field(..., description="Number of successful extractions")
    failed: int = Field(..., description="Number of failed extractions")


class MetadataErrorResponse(BaseModel):
    """Error response schema for metadata extraction."""
    
    error: str = Field(..., description="Error message")
    file_path: str = Field(..., description="File path that caused the error")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class FileInfoRequest(BaseModel):
    """Request schema for file metadata extraction."""
    
    file_path: str = Field(..., description="Relative file path from upload directory")


class BatchMetadataRequest(BaseModel):
    """Request schema for batch metadata extraction."""
    
    file_paths: list[str] = Field(..., description="List of relative file paths")