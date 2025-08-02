# Text Extraction & OCR Integration Guide

This document provides a comprehensive guide for the newly integrated text extraction and OCR capabilities in the File Manager application.

## Overview

The system now supports automatic text extraction from documents and images using:
- **Apache Tika** for document text extraction (PDF, DOCX, etc.)
- **Tesseract OCR** for image text extraction (JPG, PNG, etc.)
- **Mistral OCR API** as fallback when Tesseract fails

## Architecture

### Services
- **IndexingService** (`app/services/indexing_service.py`): Apache Tika integration
- **OCRService** (`app/services/ocr_service.py`): Tesseract + Mistral OCR
- **TextExtractionService** (`app/services/text_extraction_service.py`): Orchestrates extraction

### Database Schema
New fields added to the `documents` table:
- `extracted_text`: Full text content from documents
- `extracted_text_path`: Path to extracted text file (optional)
- `ocr_text`: Text extracted via OCR
- `ocr_confidence`: OCR confidence scores and metadata
- `extracted_metadata`: Document metadata from Tika
- `text_extraction_status`: Status of text extraction
- `ocr_status`: Status of OCR processing

## Docker Services

### Apache Tika
- **Image**: `apache/tika:latest`
- **Port**: `9998`
- **URL**: `http://localhost:9998`

### Tesseract OCR
- **Image**: `tesseractshadow/tesseract4re:latest`
- **Port**: `8080`
- **Languages**: English, Spanish, French, German

## API Endpoints

### Text Extraction
- `POST /api/v1/extraction/extract/{document_id}` - Trigger extraction for specific document
- `POST /api/v1/extraction/extract-pending` - Process all pending documents
- `GET /api/v1/extraction/status/{document_id}` - Get extraction status
- `GET /api/v1/extraction/search-text?query=search_term` - Search within extracted text

## Configuration

### Environment Variables
```bash
# Tika Configuration
TIKA_URL=http://localhost:9998

# Tesseract Configuration
TESSERACT_URL=http://localhost:8080

# Mistral OCR Configuration
MISTRAL_API_KEY=your_api_key_here
MISTRAL_API_URL=https://api.mistral.ai/v1/ocr
```

### Supported File Types

#### Documents (Tika)
- PDF, DOCX, XLSX, PPTX
- TXT, HTML, XML, CSV, JSON
- RTF, EPUB
- Archive formats (ZIP, TAR, etc.)

#### Images (OCR)
- JPEG, PNG, TIFF, BMP, GIF, WebP

## Usage Examples

### 1. Automatic Text Extraction
Text extraction is automatically triggered after file upload for supported file types.

### 2. Manual Extraction Trigger
```bash
# Trigger extraction for specific document
curl -X POST http://localhost:8000/api/v1/extraction/extract/123 \
  -H "Authorization: Bearer your_token"

# Process all pending documents
curl -X POST http://localhost:8000/api/v1/extraction/extract-pending \
  -H "Authorization: Bearer your_token"
```

### 3. Check Extraction Status
```bash
curl http://localhost:8000/api/v1/extraction/status/123 \
  -H "Authorization: Bearer your_token"
```

### 4. Search Extracted Text
```bash
curl "http://localhost:8000/api/v1/extraction/search-text?query=important" \
  -H "Authorization: Bearer your_token"
```

## Integration with File Upload

The text extraction is integrated into the file upload process:

1. File is uploaded and saved
2. MIME type is validated
3. Text extraction is triggered asynchronously
4. Results are stored in the database
5. Status is updated for tracking

## Error Handling

### Retry Mechanisms
- Automatic retry on service unavailability
- Fallback from Tesseract to Mistral OCR
- Graceful handling of extraction failures

### Status Codes
- `pending`: Extraction queued
- `processing`: Extraction in progress
- `completed`: Successfully extracted
- `failed`: Extraction failed
- `unsupported`: File type not supported

## Testing

Run the text extraction tests:
```bash
cd backend
pytest tests/test_text_extraction.py -v
```

## Migration

Apply the database migration:
```bash
cd backend
alembic upgrade head
```

## Monitoring

### Health Checks
- Tika server: `GET http://localhost:9998/tika`
- Tesseract: `GET http://localhost:8080/health`

### Logs
Text extraction activities are logged with the following levels:
- INFO: Successful extractions
- WARNING: Fallback activations
- ERROR: Failed extractions

## Performance Considerations

- Large files are processed asynchronously
- Background tasks prevent blocking the API
- Resource limits are configured in docker-compose.yml
- Processing status can be monitored via API endpoints

## Security

- All extraction endpoints require authentication
- File access is restricted to document owners
- API keys are stored securely in environment variables

## Troubleshooting

### Common Issues

1. **Tika server not responding**
   - Check if container is running: `docker ps`
   - Verify port 9998 is accessible

2. **OCR extraction failing**
   - Check Tesseract container logs
   - Verify image quality and format
   - Check Mistral API key validity

3. **Database migration issues**
   - Ensure Alembic is properly configured
   - Check database connectivity

### Debug Mode
Enable debug logging by setting:
```bash
LOG_LEVEL=DEBUG
```

## Future Enhancements

- Support for additional languages
- Batch processing capabilities
- Advanced OCR preprocessing
- Integration with search indexing
- Real-time extraction progress