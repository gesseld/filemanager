"""File handling service."""
from .base import BaseService
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
import time
from typing import Callable


class FileService(BaseService):
    MAX_RETRIES = 3
    RETRY_DELAY = 0.1  # Initial delay in seconds
    """Service for handling file operations."""
    
    def __init__(self):
        super().__init__()
        self.storage_root = Path(settings.STORAGE_ROOT)
        self.temp_dir = self.storage_root / "temp"
        self.chunks_dir = self.storage_root / "chunks"
        self.ensure_directories_exist()
        
    def health_check(self) -> dict:
        """Check service health and storage availability."""
        try:
            test_file = self.temp_dir / "healthcheck.tmp"
            with open(test_file, "w") as f:
                f.write("healthcheck")
            os.remove(test_file)
            return {
                "status": "healthy",
                "storage_writable": True,
                "storage_path": str(self.storage_root)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "storage_writable": False
            }
    
    def ensure_directories_exist(self) -> None:
        """Ensure required directories exist."""
        os.makedirs(self.storage_root, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.chunks_dir, exist_ok=True)
    
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
        operation = lambda: self._save_file_operation(file)
        return await self._retry_operation(operation)
        
    def _save_file_operation(self, file: UploadFile) -> Tuple[str, str]:
        """Core file save operation with no retry logic."""
        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix.lower()
        filename = f"{file_id}{ext}"
        filepath = self.temp_dir / filename
        
        # Save file contents
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return str(filepath), file_id
    
    async def move_to_permanent_storage(
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
        operation = lambda: self._move_file_operation(temp_path, document)
        return await self._retry_operation(operation)
        
    def _move_file_operation(self, temp_path: str, document: Document) -> str:
        """Core file move operation with no retry logic."""
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
    
    async def delete_file(self, filepath: str) -> None:
        """Delete a file from storage.
        
        Args:
            filepath: Path to file to delete
        """
        operation = lambda: self._delete_file_operation(filepath)
        return await self._retry_operation(operation)
        
    def _delete_file_operation(self, filepath: str) -> None:
        """Core file delete operation with no retry logic."""
        path = Path(filepath)
        if path.exists():
            path.unlink()
    
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
        
    async def save_chunk(
        self,
        file: UploadFile,
        chunk_id: str,
        chunk_index: int,
        total_chunks: int,
        file_id: str
    ) -> dict:
        """Save an individual file chunk to temporary storage.
        
        Args:
            file: UploadFile chunk
            chunk_id: Unique identifier for this chunk
            chunk_index: Position of this chunk in sequence
            total_chunks: Total number of chunks expected
            file_id: Unique identifier for the complete file
            
        Returns:
            Dictionary with chunk metadata
        """
        operation = lambda: self._save_chunk_operation(
            file, chunk_id, chunk_index, total_chunks, file_id
        )
        return await self._retry_operation(operation)
        
    def _save_chunk_operation(
        self,
        file: UploadFile,
        chunk_id: str,
        chunk_index: int,
        total_chunks: int,
        file_id: str
    ) -> dict:
        """Core chunk save operation with no retry logic."""
        # Validate chunk parameters
        if chunk_index < 0 or chunk_index >= total_chunks:
            raise FileStorageError("Invalid chunk index")
            
        # Create chunk directory if needed
        chunk_dir = self.chunks_dir / file_id
        os.makedirs(chunk_dir, exist_ok=True)
        
        # Save chunk with sequential naming
        chunk_path = chunk_dir / f"{chunk_index:05d}.part"
        with open(chunk_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "chunk_id": chunk_id,
            "file_id": file_id,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "size": os.path.getsize(chunk_path)
        }
            
    async def assemble_chunks(
        self,
        file_id: str,
        filename: str,
        content_type: str
    ) -> Tuple[str, str]:
        """Combine saved chunks into a complete file.
        
        Args:
            file_id: Unique identifier for the complete file
            filename: Original filename
            content_type: File content type
            
        Returns:
            Tuple of (file_path, file_id)
        """
        operation = lambda: self._assemble_chunks_operation(
            file_id, filename, content_type
        )
        return await self._retry_operation(operation)
        
    def _assemble_chunks_operation(
        self,
        file_id: str,
        filename: str,
        content_type: str
    ) -> Tuple[str, str]:
        """Core chunk assembly operation with no retry logic."""
        chunk_dir = self.chunks_dir / file_id
        if not chunk_dir.exists():
            raise FileStorageError("No chunks found for this file")
            
        # Get all chunks in order
        chunks = sorted(chunk_dir.glob("*.part"))
        if not chunks:
            raise FileStorageError("No valid chunks found")
            
        # Create temporary file
        ext = Path(filename).suffix.lower()
        temp_filename = f"{file_id}{ext}"
        temp_path = self.temp_dir / temp_filename
        
        # Combine chunks
        with open(temp_path, "wb") as outfile:
            for chunk in chunks:
                with open(chunk, "rb") as infile:
                    shutil.copyfileobj(infile, outfile)
        
        # Clean up chunks
        shutil.rmtree(chunk_dir)
        
        return str(temp_path), file_id
            
    def cleanup_old_chunks(self, older_than_hours: int = 24) -> int:
        """Remove chunk directories older than specified time.
        
        Args:
            older_than_hours: Minimum age in hours to consider for cleanup
            
        Returns:
            Number of chunk directories removed
        """
        count = 0
        cutoff = datetime.now().timestamp() - (older_than_hours * 3600)
        
        for chunk_dir in self.chunks_dir.iterdir():
            if chunk_dir.is_dir():
                dir_time = os.path.getmtime(chunk_dir)
                if dir_time < cutoff:
                    try:
                        shutil.rmtree(chunk_dir)
                        count += 1
                    except Exception:
                        continue
                        
        return count
        
    async def _retry_operation(
        self,
        operation: Callable,
        max_retries: int = MAX_RETRIES,
        initial_delay: float = RETRY_DELAY
    ):
        """Execute an operation with retry logic.
        
        Args:
            operation: Callable to execute
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            
        Returns:
            Result of the operation if successful
            
        Raises:
            FileStorageError: If all retries fail
        """
        last_error = None
        delay = initial_delay
        
        for attempt in range(max_retries + 1):
            try:
                return operation()
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
                raise FileStorageError(
                    f"Operation failed after {max_retries} retries: {str(e)}"
                ) from e
