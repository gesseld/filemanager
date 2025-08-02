#!/usr/bin/env python3
"""Test script for file metadata extraction service."""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.metadata_service import metadata_service


def create_test_file():
    """Create a test file for metadata extraction."""
    test_dir = Path("storage/uploads/test")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    test_file = test_dir / "test_metadata.txt"
    test_content = "This is a test file for metadata extraction.\nIt contains multiple lines.\nUsed for testing purposes."
    
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    return str(test_file.relative_to("storage/uploads"))


def test_metadata_extraction():
    """Test the metadata extraction service."""
    print("Testing file metadata extraction...")
    
    # Create test file
    test_file_path = create_test_file()
    print(f"Created test file: {test_file_path}")
    
    try:
        # Extract metadata
        metadata = metadata_service.extract_file_metadata(test_file_path)
        
        print("\n=== Extracted Metadata ===")
        print(f"Filename: {metadata['filename']}")
        print(f"Size: {metadata['size']} bytes ({metadata['size_human']})")
        print(f"Created: {metadata['created_date']}")
        print(f"Modified: {metadata['modified_date']}")
        print(f"Accessed: {metadata['accessed_date']}")
        print(f"MIME Type: {metadata['mime_type']}")
        print(f"Extension: {metadata['extension']}")
        print(f"Checksum: {metadata['checksum']}")
        print(f"Permissions: {metadata['permissions']}")
        print(f"Hidden: {metadata['is_hidden']}")
        
        # Text-specific metadata
        if 'text_lines' in metadata:
            print(f"Lines: {metadata['text_lines']}")
            print(f"Words: {metadata['text_words']}")
            print(f"Characters: {metadata['text_characters']}")
        
        print("\n=== Full Metadata ===")
        for key, value in metadata.items():
            print(f"{key}: {value}")
            
        return True
        
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        return False


def test_batch_extraction():
    """Test batch metadata extraction."""
    print("\nTesting batch metadata extraction...")
    
    # Create multiple test files
    test_files = []
    test_dir = Path("storage/uploads/test")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create different types of test files
    files_to_create = [
        ("test1.txt", "Text file 1 content"),
        ("test2.txt", "Text file 2 content with more text"),
        ("test3.md", "# Markdown Test\nThis is a markdown file."),
    ]
    
    for filename, content in files_to_create:
        test_file = test_dir / filename
        with open(test_file, 'w') as f:
            f.write(content)
        test_files.append(str(test_file.relative_to("storage/uploads")))
    
    try:
        # Batch extract metadata
        batch_results = metadata_service.get_file_info_batch(test_files)
        
        print("\n=== Batch Results ===")
        for file_path, result in batch_results.items():
            if "error" in result:
                print(f"{file_path}: ERROR - {result['error']}")
            else:
                print(f"{file_path}: {result['size_human']} - {result['mime_type']}")
        
        return True
        
    except Exception as e:
        print(f"Error in batch extraction: {e}")
        return False


if __name__ == "__main__":
    print("File Metadata Extraction Test")
    print("=" * 40)
    
    success1 = test_metadata_extraction()
    success2 = test_batch_extraction()
    
    if success1 and success2:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)