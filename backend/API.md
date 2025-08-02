# File Upload API Documentation

## POST /api/v1/files/upload

Upload a file with MIME type validation and store it in the system.

### Request

**Content-Type:** `multipart/form-data`

**Parameters:**
- `file` (required): The file to upload
- `title` (optional): Document title (defaults to filename if not provided)
- `description` (optional): Document description

### Response

**Success (201 Created):**
```json
{
  "id": 1,
  "title": "My Document",
  "filename": "document.pdf",
  "file_path": "2025/08/02/550e8400-e29b-41d4-a716-446655440000.pdf",
  "file_size": 1024000,
  "mime_type": "application/pdf",
  "status": "pending",
  "created_at": "2025-08-02T02:53:31.714Z"
}
```

**Error Responses:**

- **400 Bad Request**: No file provided
- **413 File Too Large**: File exceeds maximum size (100MB)
- **415 Unsupported Media Type**: File type not supported
- **409 Conflict**: File already exists (duplicate checksum)
- **422 Unprocessable Entity**: Unable to determine file type
- **500 Internal Server Error**: Server error during upload

### Supported File Types

**Documents:**
- PDF (application/pdf)
- Word Documents (.doc, .docx)
- Excel Spreadsheets (.xls, .xlsx)
- PowerPoint Presentations (.ppt, .pptx)
- Plain Text (.txt)
- CSV (.csv)
- Markdown (.md)

**Images:**
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)
- SVG (.svg)

**Archives:**
- ZIP (.zip)
- TAR (.tar)
- 7-Zip (.7z)
- RAR (.rar)

### Storage Structure

Files are stored in `storage/uploads/` with a date-based directory structure:
```
storage/uploads/
├── 2025/
│   └── 08/
│       └── 02/
│           ├── 550e8400-e29b-41d4-a716-446655440000.pdf
│           └── 6ba7b810-9dad-11d1-80b4-00c04fd430c8.docx
```

### File Validation

- **Maximum file size**: 100MB
- **MIME type detection**: Uses python-magic for accurate file type detection
- **Duplicate detection**: SHA-256 checksum comparison
- **Security**: Files are stored with UUID-based filenames to prevent path traversal attacks

### Example Usage

**cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@document.pdf" \
  -F "title=My Important Document" \
  -F "description=This is a test document"
```

**Python (requests):**
```python
import requests

url = "http://localhost:8000/api/v1/files/upload"
files = {"file": ("document.pdf", open("document.pdf", "rb"), "application/pdf")}
data = {"title": "My Document", "description": "Test upload"}

response = requests.post(url, files=files, data=data)
print(response.json())
```

### GET /api/v1/files/upload

Get information about supported file types and upload limits.

**Response:**
```json
{
  "max_file_size": 104857600,
  "supported_mime_types": ["application/pdf", "image/jpeg", ...],
  "max_file_size_mb": 100.0
}