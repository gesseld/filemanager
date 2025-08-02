# File Metadata Extraction Feature

This document describes the file metadata extraction functionality added to the filemanager application.

## Overview

The metadata extraction service provides comprehensive file metadata extraction capabilities, including file size, dates, MIME type detection, and type-specific metadata.

## Features

### Core Metadata
- **File size** in bytes and human-readable format
- **Creation date** (ISO format)
- **Last modified date** (ISO format)
- **Last accessed date** (ISO format)
- **MIME type** detection using python-magic
- **File extension** and basic file info
- **SHA-256 checksum** for integrity verification
- **File permissions** (Unix-style octal)
- **Hidden file detection**

### Type-Specific Metadata
- **Images**: width, height, color mode, format, transparency info
- **PDFs**: title, author, subject, pages, encryption status
- **Text files**: line count, word count, character count, encoding
- **Videos**: placeholder for video metadata (extensible)
- **Audio**: placeholder for audio metadata (extensible)

### API Endpoints

#### Single File Metadata
```
GET /api/v1/metadata/{document_id}
```
Returns comprehensive metadata for a specific file.

#### Batch Metadata
```
POST /api/v1/metadata/batch
```
Accepts a list of file paths and returns metadata for all files.

#### File Existence Check
```
GET /api/v1/metadata/document/{document_id}/exists
```
Checks if a file exists in storage.

#### All User Files
```
GET /api/v1/metadata/user/all
```
Returns metadata for all files owned by the current user.

## Usage Examples

### Python Usage
```python
from app.services.metadata_service import metadata_service

# Extract metadata for a single file
metadata = metadata_service.extract_file_metadata("2024/08/01/document.pdf")

# Batch extraction
results = metadata_service.get_file_info_batch([
    "2024/08/01/file1.pdf",
    "2024/08/01/file2.jpg"
])
```

### API Usage
```bash
# Get metadata for document ID 1
curl http://localhost:8000/api/v1/metadata/1

# Batch metadata extraction
curl -X POST http://localhost:8000/api/v1/metadata/batch \
  -H "Content-Type: application/json" \
  -d '{"file_paths": ["2024/08/01/file1.pdf", "2024/08/01/file2.jpg"]}'

# Check file existence
curl http://localhost:8000/api/v1/metadata/document/1/exists

# Get all user metadata
curl http://localhost:8000/api/v1/metadata/user/all
```

## Response Format

### Single File Response
```json
{
  "file_path": "2024/08/01/document.pdf",
  "filename": "document.pdf",
  "size": 1024576,
  "size_human": "1.0 MB",
  "created_date": "2024-08-01T15:30:00",
  "modified_date": "2024-08-01T15:30:00",
  "accessed_date": "2024-08-01T15:30:00",
  "mime_type": "application/pdf",
  "extension": ".pdf",
  "checksum": "a1b2c3d4e5f6...",
  "permissions": "644",
  "is_hidden": false,
  "absolute_path": "/app/storage/uploads/2024/08/01/document.pdf",
  "directory": "2024/08/01",
  "stem": "document",
  "pdf_title": "Sample Document",
  "pdf_author": "John Doe",
  "pdf_pages": 42,
  "pdf_encrypted": false
}
```

### Batch Response
```json
{
  "files": {
    "2024/08/01/file1.pdf": {
      "file_path": "2024/08/01/file1.pdf",
      "size": 1024576,
      "mime_type": "application/pdf",
      ...
    },
    "2024/08/01/file2.jpg": {
      "file_path": "2024/08/01/file2.jpg",
      "size": 204800,
      "mime_type": "image/jpeg",
      ...
    }
  },
  "total_files": 2,
  "successful": 2,
  "failed": 0
}
```

## Installation

### Dependencies
The following additional packages are required:

```bash
pip install pypdf2
```

### Windows-Specific Setup
For Windows users, you may need to install `libmagic`:

```bash
# Using chocolatey
choco install file

# Or download from https://gnuwin32.sourceforge.net/packages/file.htm
```

### Linux/Mac Setup
```bash
# Ubuntu/Debian
sudo apt-get install libmagic1

# macOS
brew install libmagic
```

## Error Handling

The service includes comprehensive error handling:
- **FileNotFoundError**: When file doesn't exist
- **PermissionError**: When file access is denied
- **TypeError**: When file type is unsupported
- **General exceptions**: With detailed error messages

## Security Considerations

- All file paths are validated to prevent directory traversal
- File access is restricted to the upload directory
- User authentication is required for API endpoints
- File existence checks prevent information leakage

## Extensibility

The service is designed to be extensible:
- Add new file type handlers in `_extract_type_specific_metadata`
- Add new system metadata in `_extract_system_metadata`
- Add new API endpoints as needed

## Testing

Run the test script:
```bash
python backend/test_metadata.py
```

## Integration with Existing System

The metadata service integrates seamlessly with:
- **File upload service**: Provides metadata after upload
- **Document model**: Stores extracted metadata in the database
- **Text extraction**: Can be extended to include extracted text metadata
- **Search functionality**: Metadata can be used for enhanced search

## Future Enhancements

- Video/audio metadata extraction using ffmpeg
- EXIF data extraction for images
- Office document metadata extraction
- Archive file metadata (zip, tar, etc.)
- Performance optimization for large files
- Caching layer for frequently accessed metadata