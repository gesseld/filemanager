# Document Management System

A comprehensive document management system with OCR, search, and tagging capabilities.

## Features

- **Document Upload**: Supports PDF, JPG, PNG file formats
- **OCR Processing**: Automatic text extraction from images/PDFs
- **Search**: Semantic search across document contents
- **Tagging**: AI-powered automatic document tagging
- **User Management**: Multi-user support with access control

## Technologies

- **Backend**: Python/FastAPI
- **Frontend**: React/TypeScript
- **Database**: PostgreSQL
- **Vector Search**: Qdrant
- **OCR**: Tesseract (via WSL) + Mistral API
- **AI**: OpenAI embeddings for semantic search

## Setup

### Prerequisites

- Python 3.9+
- Node.js 16+
- Docker
- WSL (for OCR processing on Windows)

### Installation

1. Clone the repository
2. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```
4. Configure environment variables (copy `.env.example` to `.env`)

### Running

Start the development environment:

```bash
docker-compose up -d
cd backend && uvicorn app.main:app --reload
cd frontend && npm start
```

## API Documentation

API docs available at `/docs` when the backend is running.

## Testing

Run backend tests:
```bash
cd backend
pytest
```

Run frontend tests:
```bash
cd frontend
npm test
```

## Deployment

Production deployment uses Docker containers managed via Kubernetes. See `deploy/` for configuration files.

## License

MIT
