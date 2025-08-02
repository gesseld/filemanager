"""Unit tests for metadata service."""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime


class TestMetadataService:
    """Test cases for metadata extraction service."""
    
    def test_format_file_size(self):
        """Test file size formatting."""
        from app.services.metadata_service import MetadataService
        
        service = MetadataService()
        
        assert service._format_file_size(0) == "0.0 B"
        assert service._format_file_size(500) == "500.0 B"
        assert service._format_file_size(1024) == "1.0 KB"
        assert service._format_file_size(1536) == "1.5 KB"
        assert service._format_file_size(1048576) == "1.0 MB"
        assert service._format_file_size(1073741824) == "1.0 GB"
    
    def test_calculate_checksum(self):
        """Test checksum calculation."""
        from app.services.metadata_service import MetadataService
        
        service = MetadataService()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            checksum = service._calculate_checksum(temp_path)
            assert len(checksum) == 64  # SHA-256 produces 64 hex chars
            assert checksum.isalnum()  # Should be hexadecimal
            
            # Test same content produces same checksum
            checksum2 = service._calculate_checksum(temp_path)
            assert checksum == checksum2
            
        finally:
            os.unlink(temp_path)
    
    def test_extract_text_metadata(self):
        """Test text file metadata extraction."""
        from app.services.metadata_service import MetadataService
        
        service = MetadataService()
        
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3")
            temp_path = f.name
        
        try:
            metadata = service._extract_text_metadata(temp_path)
            
            assert "text_lines" in metadata
            assert "text_words" in metadata
            assert "text_characters" in metadata
            
            assert metadata["text_lines"] == 3
            assert metadata["text_words"] >= 6  # "Line", "1", "Line", "2", "Line", "3"
            assert metadata["text_characters"] > 0
            
        finally:
            os.unlink(temp_path)
    
    def test_validate_file_exists(self):
        """Test file existence validation."""
        from app.services.metadata_service import MetadataService
        
        service = MetadataService()
        
        # Create a temporary file in the upload directory structure
        temp_dir = Path("storage/uploads/test")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_file = temp_dir / "test.txt"
        temp_file.write_text("test")
        
        try:
            # Test relative path
            relative_path = str(temp_file.relative_to("storage/uploads"))
            assert service.validate_file_exists(relative_path) is True
            
            # Test non-existent file
            assert service.validate_file_exists("nonexistent.txt") is False
            
        finally:
            if temp_file.exists():
                temp_file.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()
    
    def test_get_mime_type_fallback(self):
        """Test MIME type detection with fallback."""
        from app.services.metadata_service import MetadataService
        
        service = MetadataService()
        
        # Test with extension-based fallback
        mime_type = service._get_mime_type("test.txt")
        assert mime_type == "text/plain" or mime_type == "application/octet-stream"
        
        mime_type = service._get_mime_type("test.pdf")
        assert mime_type == "application/pdf" or mime_type == "application/octet-stream"
    
    def test_extract_system_metadata(self):
        """Test system metadata extraction."""
        from app.services.metadata_service import MetadataService
        import stat
        
        service = MetadataService()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        try:
            stat_info = Path(temp_path).stat()
            metadata = service._extract_system_metadata(temp_path, stat_info)
            
            # Check that basic system metadata is present
            assert isinstance(metadata, dict)
            
            # Unix metadata should be present (even on Windows)
            assert "unix_uid" in metadata
            assert "unix_gid" in metadata
            assert "unix_device" in metadata
            assert "unix_inode" in metadata
            assert "unix_nlink" in metadata
            
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])