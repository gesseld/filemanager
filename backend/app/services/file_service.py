"""File handling service."""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile
from datetime import datetime

from ..config import settings
from ..models.document import Document
from ..models.user import User
from ..exceptions import FileStorageError


class FileService:
    """Service for handling file operations."""
    
    def __init__(self):
        self.storage_root = Path(settings.STORAGE_ROOT)
        self.temp_dir = self.storage_root / "temp"
        self.ensure_directories_exist()
    
    def ensure_directories_exist(self) -> None:
        """Ensure required directories exist."""
        os.makedirs(self.storage_root, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def save_uploaded_file(
        self, 
        file: UploadFile,
        user: User
    ) -> Tuple[str, str]:
        """Save an uploaded file to temporary storage.
        
        Args:
            file: FastAPI UploadFile object
            user: User who uploaded the file
            
        Returns:
            Tuple of (file_path, file_id)
        """
        try:
            file_id = str(uuid.uuid4())
            ext = Path(file.filename).suffix.lower()
            filename = f"{file_id}{ext}"
            filepath = self.temp_dir / filename
            
            # Save file contents
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            return str(filepath), file_id
            
        except Exception as e:
            raise FileStorageError(f"Failed to save file: {str(e)}")
    
    def move_to_permanent_storage(
        self,
        temp_path: str,
        document: Document
    ) -> str:
        """Move file from temp to permanent storage.
        
        Args:
            temp_path: Path to temporary file
            document: Document metadata
            
        Returns:
            Final storage path
        """
        try:
            path = Path(temp_path)
            if not path.exists():
                raise FileStorageError("Source file does not exist")
                
            # Create user directory if needed
            user_dir = self.storage_root / str(document.user_id)
            os.makedirs(user_dir, exist_ok=True)
            
            # Create dated subdirectory
            date_str = datetime.now().strftime("%Y/%m/%d")
            dated_dir = user_dir / date_str
            os.makedirs(dated_dir, exist_ok=True)
            
            # Move file
            dest_path = dated_dir / path.name
            shutil.move(str(path), str(dest_path))
            
            return str(dest_path)
            
        except Exception as e:
            raise FileStorageError(f"Failed to move file: {str(e)}")
    
    def delete_file(self, filepath: str) -> None:
        """Delete a file from storage.
        
        Args:
            filepath: Path to file to delete
        """
        try:
            path = Path(filepath)
            if path.exists():
                path.unlink()
        except Exception as e:
            raise FileStorageError(f"Failed to delete file: {str(e)}")
    
    def get_file_path(self, document: Document) -> Optional[str]:
        """Get full filesystem path for a document.
        
        Args:
            document: Document model
            
        Returns:
            Full filesystem path if exists, else None
        """
        if not document.storage_path:
            return None
            
        path = Path(document.storage_path)
        if not path.exists():
            return None
            
        return str(path)
