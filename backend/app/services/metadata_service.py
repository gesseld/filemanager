"""Enhanced file metadata extraction service."""

import os
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import magic
from loguru import logger
import hashlib


class MetadataService:
    """Service for extracting comprehensive file metadata."""
    
    def __init__(self):
        """Initialize metadata service."""
        self.upload_dir = Path("storage/uploads")
        
    def extract_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from a file.
        
        Args:
            file_path: Path to the file (relative to upload_dir)
            
        Returns:
            Dictionary containing file metadata including:
            - size: File size in bytes
            - created_date: File creation date
            - modified_date: Last modification date
            - accessed_date: Last access date
            - mime_type: MIME type
            - extension: File extension
            - checksum: SHA-256 checksum
            - permissions: File permissions
            - is_hidden: Whether file is hidden
            - additional metadata based on file type
        """
        try:
            full_path = self.upload_dir / file_path
            
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Basic file stats
            stat_info = full_path.stat()
            
            # Extract MIME type
            mime_type = self._get_mime_type(str(full_path))
            
            # Calculate checksum
            checksum = self._calculate_checksum(str(full_path))
            
            # Build metadata dictionary
            metadata = {
                "file_path": file_path,
                "full_path": str(full_path),
                "filename": full_path.name,
                "size": stat_info.st_size,
                "size_human": self._format_file_size(stat_info.st_size),
                "created_date": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "modified_date": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "accessed_date": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                "mime_type": mime_type,
                "extension": full_path.suffix.lower(),
                "checksum": checksum,
                "permissions": oct(stat_info.st_mode)[-3:],
                "is_hidden": full_path.name.startswith('.'),
                "absolute_path": str(full_path.resolve()),
                "directory": str(full_path.parent),
                "stem": full_path.stem,
            }
            
            # Add type-specific metadata
            metadata.update(self._extract_type_specific_metadata(str(full_path), mime_type))
            
            # Add system-specific metadata
            metadata.update(self._extract_system_metadata(str(full_path), stat_info))
            
            logger.info(f"Extracted metadata for {file_path}: {metadata['size_human']}, {mime_type}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata for {file_path}: {e}")
            raise
    
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type using python-magic."""
        try:
            mime_type = magic.from_file(file_path, mime=True)
            return mime_type or "application/octet-stream"
        except Exception:
            # Fallback to mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)
            return mime_type or "application/octet-stream"
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of file."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating checksum: {e}")
            return ""
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _extract_type_specific_metadata(self, file_path: str, mime_type: str) -> Dict[str, Any]:
        """Extract metadata specific to file type."""
        metadata = {}
        
        if mime_type.startswith('image/'):
            metadata.update(self._extract_image_metadata(file_path))
        elif mime_type.startswith('video/'):
            metadata.update(self._extract_video_metadata(file_path))
        elif mime_type.startswith('audio/'):
            metadata.update(self._extract_audio_metadata(file_path))
        elif mime_type == 'application/pdf':
            metadata.update(self._extract_pdf_metadata(file_path))
        elif mime_type.startswith('text/'):
            metadata.update(self._extract_text_metadata(file_path))
        
        return metadata
    
    def _extract_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract image-specific metadata."""
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                return {
                    "image_width": img.width,
                    "image_height": img.height,
                    "image_mode": img.mode,
                    "image_format": img.format,
                    "image_has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
        except Exception as e:
            logger.warning(f"Could not extract image metadata: {e}")
            return {}
    
    def _extract_video_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract video-specific metadata."""
        # Placeholder for video metadata extraction
        # Could use ffmpeg-python or similar
        return {"video_metadata": "not_implemented"}
    
    def _extract_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract audio-specific metadata."""
        # Placeholder for audio metadata extraction
        # Could use mutagen or similar
        return {"audio_metadata": "not_implemented"}
    
    def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract PDF-specific metadata."""
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata = reader.metadata
                return {
                    "pdf_title": metadata.get('/Title', ''),
                    "pdf_author": metadata.get('/Author', ''),
                    "pdf_subject": metadata.get('/Subject', ''),
                    "pdf_creator": metadata.get('/Creator', ''),
                    "pdf_producer": metadata.get('/Producer', ''),
                    "pdf_creation_date": str(metadata.get('/CreationDate', '')),
                    "pdf_modification_date": str(metadata.get('/ModDate', '')),
                    "pdf_pages": len(reader.pages),
                    "pdf_encrypted": reader.is_encrypted
                }
        except Exception as e:
            logger.warning(f"Could not extract PDF metadata: {e}")
            return {}
    
    def _extract_text_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract text-specific metadata."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return {
                    "text_lines": len(content.splitlines()),
                    "text_characters": len(content),
                    "text_words": len(content.split()),
                    "text_encoding": 'utf-8'
                }
        except Exception as e:
            logger.warning(f"Could not extract text metadata: {e}")
            return {}
    
    def _extract_system_metadata(self, file_path: str, stat_info) -> Dict[str, Any]:
        """Extract system-specific metadata."""
        metadata = {}
        
        try:
            # Unix-style metadata
            metadata.update({
                "unix_uid": getattr(stat_info, 'st_uid', None),
                "unix_gid": getattr(stat_info, 'st_gid', None),
                "unix_device": getattr(stat_info, 'st_dev', None),
                "unix_inode": getattr(stat_info, 'st_ino', None),
                "unix_nlink": getattr(stat_info, 'st_nlink', None),
            })
            
            # Windows-specific metadata
            if hasattr(stat_info, 'st_file_attributes'):
                metadata.update({
                    "windows_attributes": stat_info.st_file_attributes,
                    "is_readonly": bool(stat_info.st_file_attributes & 0x1),
                    "is_hidden": bool(stat_info.st_file_attributes & 0x2),
                    "is_system": bool(stat_info.st_file_attributes & 0x4),
                })
                
        except Exception as e:
            logger.debug(f"Could not extract system metadata: {e}")
        
        return metadata
    
    def get_file_info_batch(self, file_paths: list) -> Dict[str, Any]:
        """
        Extract metadata for multiple files.
        
        Args:
            file_paths: List of file paths relative to upload_dir
            
        Returns:
            Dictionary with file paths as keys and metadata as values
        """
        results = {}
        
        for file_path in file_paths:
            try:
                results[file_path] = self.extract_file_metadata(file_path)
            except Exception as e:
                results[file_path] = {"error": str(e)}
        
        return results
    
    def validate_file_exists(self, file_path: str) -> bool:
        """Check if file exists in storage."""
        full_path = self.upload_dir / file_path
        return full_path.exists() and full_path.is_file()


# Global metadata service instance
metadata_service = MetadataService()