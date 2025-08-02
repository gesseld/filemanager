@echo off
REM Development setup script for File Manager (Windows)

echo 🚀 Setting up File Manager development environment...

REM Backend setup
echo 📦 Setting up backend...
cd backend

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install dependencies
echo Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM Initialize database
echo 🗄️ Initializing database...
alembic upgrade head

REM Return to root
cd ..

REM Frontend setup
echo 📦 Setting up frontend...
cd frontend

REM Install dependencies
echo Installing Node.js dependencies...
npm install

REM Return to root
cd ..

echo ✅ Development environment setup complete!
echo.
echo To start development:
echo 1. Backend: cd backend && venv\Scripts\activate && uvicorn app.main:app --reload
echo 2. Frontend: cd frontend && npm run dev
echo.
echo API Documentation: http://localhost:8000/docs
echo Frontend: http://localhost:5173

pause