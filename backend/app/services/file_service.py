"""File upload service with MIME type validation and storage management."""

import os
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import magic
from loguru import logger

from fastapi import UploadFile, HTTPException, status

from app.schemas.file import FileValidationConfig
from app.core.config import settings


class FileService:
    """Service for handling file uploads, validation, and storage."""
    
    def __init__(self):
        """Initialize file service."""
        self.upload_dir = Path("storage/uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
    async def validate_file(self, file: UploadFile) -> Tuple[str, int]:
        """
        Validate file type and size.
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            Tuple of (mime_type, file_size)
            
        Raises:
            HTTPException: If validation fails
        """
        # Check if file is provided
        if not file or not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
            
        # Read file content for validation
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        # Check file size
        file_size = len(content)
        if file_size > FileValidationConfig.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {FileValidationConfig.MAX_FILE_SIZE} bytes"
            )
            
        # Validate MIME type using python-magic
        try:
            mime_type = magic.from_buffer(content, mime=True)
        except Exception as e:
            logger.error(f"Error detecting MIME type: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unable to determine file type"
            )
            
        # Check if MIME type is allowed
        if mime_type not in FileValidationConfig.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File type {mime_type} is not supported"
            )
            
        return mime_type, file_size
        
    def generate_file_path(self, original_filename: str) -> Tuple[str, str]:
        """
        Generate unique file path for storage.
        
        Args:
            original_filename: Original filename
            
        Returns:
            Tuple of (storage_path, unique_filename)
        """
        # Generate unique filename
        file_extension = Path(original_filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Create date-based directory structure
        date_path = Path(datetime.now().strftime("%Y/%m/%d"))
        storage_dir = self.upload_dir / date_path
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Full storage path
        storage_path = storage_dir / unique_filename
        
        return str(storage_path), str(date_path / unique_filename)
        
    def calculate_checksum(self, content: bytes) -> str:
        """
        Calculate SHA-256 checksum of file content.
        
        Args:
            content: File content as bytes
            
        Returns:
            SHA-256 checksum as hex string
        """
        return hashlib.sha256(content).hexdigest()
        
    async def save_file(self, file: UploadFile, mime_type: str) -> Tuple[str, str, str, int]:
        """
        Save uploaded file to storage.
        
        Args:
            file: FastAPI UploadFile object
            mime_type: Validated MIME type
            
        Returns:
            Tuple of (storage_path, unique_filename, checksum, file_size)
        """
        # Read file content
        content = await file.read()
        
        # Calculate checksum
        checksum = self.calculate_checksum(content)
        
        # Generate storage path
        storage_full_path, relative_path = self.generate_file_path(file.filename)
        
        # Save file to disk
        try:
            with open(storage_full_path, 'wb') as f:
                f.write(content)
                
            logger.info(
                f"File saved successfully: {file.filename} -> {storage_full_path} "
                f"(size: {len(content)} bytes, type: {mime_type})"
            )
            
            return storage_full_path, relative_path, checksum, len(content)
            
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save file"
            )
            
    def delete_file(self, file_path: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            full_path = self.upload_dir / file_path
            if full_path.exists():
                full_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False


# Global file service instance
file_service = FileService()