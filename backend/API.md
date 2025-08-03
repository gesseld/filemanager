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

## Search API

### GET /api/v1/search/facets

Get available facet fields and their types. Useful for building filter UIs.

**Response:**
```json
[
  {"field": "type", "type": "string"},
  {"field": "size", "type": "numeric"},
  {"field": "created_date", "type": "date"},
  {"field": "owner", "type": "string"},
  {"field": "tags", "type": "string"},
  {"field": "extension", "type": "string"},
  {"field": "location", "type": "string"}
]
```

### POST /api/v1/search

Perform a search across documents with advanced query syntax.

**Request:**
```json
{
  "query": "search terms",
  "filters": [
    {
      "field": "type",
      "values": ["pdf", "docx"]
    }
  ],
  "limit": 20,
  "offset": 0
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "doc123",
      "title": "Document Title",
      "content": "Matching content...",
      "type": "pdf",
      "tags": ["research", "important"]
    }
  ],
  "facets": {
    "type": {
      "pdf": 5,
      "docx": 3
    }
  },
  "total": 8,
  "query_suggestions": ["related term 1", "related term 2"]
}
```

**Error Responses:**
- **400 Bad Request**: Invalid filter field specified
- **500 Internal Server Error**: Search service unavailable

### Advanced Search Syntax

Supports the following operators:
- `AND`: Requires both terms (default if no operator specified)
  - Example: `apple AND orange`
- `OR`: Matches either term
  - Example: `apple OR orange`
- `NOT`: Excludes documents matching term
  - Example: `apple NOT orange`
- Quotes for exact phrases: `"exact phrase match"`
- Parentheses for grouping: `(apple AND orange) OR banana`

### Filterable Fields
- type, size, created_date, owner, tags, extension, location

### Examples
1. Simple search: `annual report`
2. Advanced search: `(financial AND report) NOT draft`
3. Phrase search: `"quarterly earnings report"`

## Search Export API

**Common Error Responses:**
- **400 Bad Request**: Invalid export fields specified
- **413 Payload Too Large**: Export exceeds system limits
- **500 Internal Server Error**: Export generation failed

### Export Field Specifications

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | string | Unique document identifier | "doc123" |
| title | string | Document title | "Annual Report 2024" |
| type | string | Document type | "pdf", "docx" |
| created_date | ISO8601 | Document creation timestamp | "2024-01-15T09:30:00Z" |
| size | integer | File size in bytes | 1048576 |
| tags | string[] | Array of document tags | ["finance", "confidential"] |
| owner | string | Document owner username | "jdoe" |
| extension | string | File extension | ".pdf" |
| location | string | Storage path | "/corporate/reports" |

### POST /api/v1/search/export/csv

Exports search results as CSV with the following format:
- First row contains headers matching field names
- Subsequent rows contain data values
- Strings are quoted if they contain commas
- Arrays are serialized as comma-separated values
- Dates are in ISO8601 format

**Example Output:**
```csv
id,title,type,created_date,size,tags
"doc123","Annual Report","pdf","2024-01-15T09:30:00Z",1048576,"finance,report"
"doc456","Q1 Financials","xlsx","2024-04-01T14:15:00Z",524288,"finance,quarterly"
```

Export search results as CSV with streaming support for large datasets.

**Request:**
```json
{
  "query": "search terms",
  "filters": [
    {
      "field": "type",
      "values": ["pdf", "docx"]
    }
  ],
  "limit": 1000,
  "offset": 0
}
```

**Query Parameters:**
- `fields`: Comma-separated list of fields to include (default: id,title,type,created_date)

**Response Headers:**
- `Content-Type`: text/csv
- `Content-Disposition`: attachment; filename=export.csv
- `X-Total-Count`: Total number of results

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/v1/search/export/csv?fields=id,title,type" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "annual report"}'
```

### POST /api/v1/search/export/json

Export search results as JSON with streaming support for large datasets. The output is a JSON array where each element represents one document.

**Request:** Same as CSV export endpoint

**Response Format:**
- Array of document objects
- Each object contains requested fields
- Dates formatted as ISO8601 strings
- Arrays preserved as JSON arrays

**Example Output:**
```json
[
  {
    "id": "doc123",
    "title": "Annual Report",
    "type": "pdf",
    "created_date": "2024-01-15T09:30:00Z",
    "size": 1048576,
    "tags": ["finance", "report"]
  },
  {
    "id": "doc456",
    "title": "Q1 Financials",
    "type": "xlsx",
    "created_date": "2024-04-01T14:15:00Z",
    "size": 524288,
    "tags": ["finance", "quarterly"]
  }
]
```

**Query Parameters:**
- `fields`: Comma-separated list of fields to include (default: id,title,type,created_date)

**Response Headers:**
- `Content-Type`: application/json
- `Content-Disposition`: attachment; filename=export.json
- `X-Total-Count`: Total number of results

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/v1/search/export/json?fields=id,title" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "financial report"}'
```

## Natural Language Search API

**Error Responses:**
- **400 Bad Request**: Invalid confidence threshold
- **422 Unprocessable Entity**: NLP processing failed
- **500 Internal Server Error**: NLP service unavailable

### POST /api/v1/search/nlp

## Real-World Examples

### 1. Business Report Search
**Scenario:** Find quarterly financial reports from last year excluding drafts.

**Request:**
```json
{
  "query": "(Q1 OR Q2 OR Q3 OR Q4) AND financial AND report",
  "filters": [
    {"field": "created_date", "values": ["2024-01-01 TO 2024-12-31"]},
    {"field": "type", "values": ["pdf", "docx"]}
  ],
  "limit": 20
}
```

**Response Highlights:**
```json
{
  "results": [
    {
      "id": "rep-2024-q1",
      "title": "Q1 2024 Financial Report",
      "type": "pdf",
      "created_date": "2024-04-15T00:00:00Z",
      "tags": ["financial", "quarterly", "approved"]
    }
  ],
  "facets": {
    "type": {"pdf": 3, "docx": 1},
    "tags": {"financial": 4, "quarterly": 4}
  }
}
```

### 2. Legal Document Discovery
**Scenario:** Find contracts signed in 2024 containing "NDA" clauses.

**NLP Query:**
```json
{
  "query": "Show me contracts signed in 2024 that include NDA clauses",
  "limit": 10,
  "fallback_to_keyword": true
}
```

**NLP Processing:**
```json
{
  "processed_query": "contract AND NDA",
  "filters": {"created_date": ["2024-01-01 TO 2024-12-31"]}
}
```

### 3. Technical Documentation Search
**Scenario:** Find API documentation about authentication.

**Request:**
```json
{
  "query": "API authentication",
  "filters": [
    {"field": "tags", "values": ["documentation"]},
    {"field": "type", "values": ["md", "html"]}
  ]
}
```

### 4. Export Workflow
**Scenario:** Export customer contracts for audit.

**Request:**
```bash
curl -X POST "http://api.example.com/search/export/csv?fields=id,title,created_date,owner" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "customer contract",
    "filters": [{"field": "created_date", "values": ["2023-01-01 TO 2023-12-31"]}],
    "limit": 1000
  }'
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Slow Search Performance
**Symptoms:**
- Queries taking longer than 2 seconds
- Timeout errors

**Possible Causes:**
- Complex query with many filters
- Large result set being processed
- System resource constraints

**Solutions:**
- Simplify query by reducing filters
- Add pagination (limit/offset)
- Check system health endpoints

#### 2. Query Syntax Errors
**Symptoms:**
- 400 Bad Request responses
- Unexpected empty results

**Common Mistakes:**
- Unbalanced parentheses
- Incorrect operator usage (AND/OR/NOT)
- Unescaped special characters

**Solutions:**
- Review query syntax documentation
- Use query validation tools
- Start with simple queries and build up

#### 3. NLP Processing Failures
**Symptoms:**
- 422 Unprocessable Entity responses
- Queries returning keyword results instead of NLP

**Solutions:**
- Check for ambiguous phrases
- Try simpler sentence structures
- Set fallback_to_keyword=true

#### 4. Export Limitations
**Symptoms:**
- Incomplete export files
- 413 Payload Too Large errors

**Limitations:**
- Max 10,000 records per export
- 100MB file size limit
- 60 second timeout

**Solutions:**
- Use smaller batches with limit/offset
- Filter results before exporting
- Use streaming APIs for large exports

#### 5. Authentication Issues
**Symptoms:**
- 401 Unauthorized responses
- Missing facets or results

**Solutions:**
- Verify API token is valid
- Check token expiration
- Confirm required permissions

Perform a search using natural language queries with NLP processing.

**Request:**
```json
{
  "query": "find documents about quarterly financial reports from last year",
  "limit": 20,
  "offset": 0,
  "fallback_to_keyword": true
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "doc456",
      "title": "Q4 2024 Financial Report",
      "content": "Quarterly earnings report showing...",
      "type": "pdf",
      "tags": ["financial", "quarterly"],
      "score": 0.92,
      "nlp_metadata": {
        "detected_intent": "find financial reports",
        "time_period": "last year",
        "processed_query": "quarterly financial reports 2024"
      }
    }
  ],
  "total": 5,
  "search_type": "hybrid",
  "query_analysis": {
    "original_query": "find documents about quarterly financial reports from last year",
    "processed_query": "quarterly financial reports 2024",
    "intent": "find financial reports",
    "entities": [
      {"type": "time_period", "value": "last year", "normalized": "2024"},
      {"type": "document_type", "value": "reports"}
    ]
  }
}
```

### Features

1. **Natural Language Processing**:
   - Understands queries like "show me contracts signed last month"
   - Extracts entities (dates, document types, people)
   - Detects search intent

2. **Hybrid Search**:
   - Combines NLP understanding with traditional keyword search
   - Uses vector embeddings for semantic similarity

3. **Graceful Degradation**:
   - When `fallback_to_keyword=true`, falls back to keyword search if NLP fails
   - Returns `search_type: "keyword"` in response when fallback occurs

4. **Query Analysis**:
   - Returns detailed analysis of how the query was interpreted
   - Includes extracted entities and normalized values

### Examples

1. Simple natural language query:
   ```json
   {"query": "find my tax documents from 2023"}
   ```

2. Complex query with filters:
   ```json
   {
     "query": "show me presentations about AI from the last quarter",
     "filters": [{"field": "type", "values": ["pptx"]}]
   }
   ```

3. Fallback example (when NLP fails):
   ```json
   {
     "query": "technical spec for project xyz",
     "fallback_to_keyword": true
   }
   ```