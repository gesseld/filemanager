# File Manager

A modern file management application with AI-powered search and organization capabilities.

## Architecture

- **Backend**: FastAPI with Python 3.11
- **Frontend**: React with TypeScript and Vite
- **Database**: SQLite (development) → PostgreSQL (production)
- **Vector Search**: Qdrant
- **Full-text Search**: Meilisearch
- **Cache**: Redis
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for local development)

### Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd filemanager
```

2. Start all services with Docker Compose:
```bash
docker-compose up -d
```

3. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Qdrant Dashboard: http://localhost:6333
- Meilisearch: http://localhost:7700

### Local Development

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Database setup
alembic upgrade head  # Apply migrations
# or
python -c "from app.db.base import init_db; init_db()"  # Initialize database

uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Development Workflow

### Pre-commit Hooks
Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

### Database Migration

#### SQLite Development Setup
The application uses SQLite for development with Alembic for migrations:

```bash
# Initialize database with migrations
cd backend
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "Description of changes"

# Apply specific migration
alembic upgrade 20250802_0001

# Downgrade migration
alembic downgrade -1

# Check current migration
alembic current

# View migration history
alembic history --verbose
```

#### Migration Path to PostgreSQL
For production deployment, migrate from SQLite to PostgreSQL:

1. **Update configuration**:
   ```bash
   # Set PostgreSQL connection string in .env
   DATABASE_URL=postgresql://user:password@localhost/filemanager
   ```

2. **Generate PostgreSQL migration**:
   ```bash
   alembic revision --autogenerate -m "PostgreSQL migration"
   ```

3. **Data migration** (if needed):
   ```bash
   # Export SQLite data
   sqlite3 filemanager.db .dump > backup.sql
   
   # Import to PostgreSQL
   psql -d filemanager -f backup.sql
   ```

4. **Update environment variables**:
   ```bash
   # Production .env
   DATABASE_URL=postgresql://user:password@postgres:5432/filemanager
   ```

### Testing
```bash
# Backend tests
pytest tests/

# Frontend tests
cd frontend && npm test
```

### Code Quality
```bash
# Backend
black backend/
flake8 backend/
mypy backend/

# Frontend
cd frontend && npm run lint
cd frontend && npm run format
```

## Project Structure

```
filemanager/
├── backend/              # FastAPI backend
│   ├── app/             # Application code
│   ├── requirements.txt # Python dependencies
│   └── Dockerfile       # Backend container
├── frontend/            # React frontend
│   ├── src/            # Source code
│   ├── package.json    # Node.js dependencies
│   └── Dockerfile      # Frontend container
├── tests/              # Test files
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── docker-compose.yml  # Development services
└── .github/            # GitHub workflows
```

## Security

- Dependency scanning with Snyk
- Automated security updates with Dependabot
- Pre-commit hooks for code quality
- Container security scanning

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details