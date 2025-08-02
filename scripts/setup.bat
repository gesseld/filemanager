@echo off
echo 🚀 Setting up File Manager development environment...

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker first.
    pause
    exit /b 1
)

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

REM Create .env file from example if it doesn't exist
if not exist .env (
    echo 📋 Creating .env file from example...
    copy .env.example .env
    echo ⚠️  Please edit .env file with your actual configuration values
)

REM Build and start services
echo 🏗️  Building and starting services...
docker-compose up --build -d

REM Wait for services to be ready
echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Check service health
echo 🔍 Checking service health...
docker-compose ps

echo.
echo ✅ Setup complete!
echo.
echo 🌐 Services are now running:
echo    Frontend: http://localhost:3000
echo    Backend API: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo    Qdrant: http://localhost:6333
echo    Meilisearch: http://localhost:7700
echo.
echo 📖 Next steps:
echo    1. Edit .env file with your configuration
echo    2. Install pre-commit hooks: pip install pre-commit && pre-commit install
echo    3. Start developing!
pause