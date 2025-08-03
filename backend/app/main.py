"""FastAPI application with lifespan events."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette_context.middleware import RawContextMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, request_id_middleware
from app.core.exceptions import register_exception_handlers
from app.db.base import init_db, check_db_connection
from app.db.session import get_db
from loguru import logger

# Import API routers
from app.api.v1.files import router as files_router
from app.api.v1.errors import router as errors_router

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info("Starting File Manager API...")
    
    # Setup logging
    setup_logging()
    logger.info("Logging configured successfully")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
        
        # Check database connection
        db = next(get_db())
        if check_db_connection(db):
            logger.info("Database connection healthy")
        else:
            logger.warning("Database connection check failed")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    logger.info("File Manager API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down File Manager API...")
    
    # Cleanup resources
    logger.info("Cleaning up resources...")
    
    logger.info("File Manager API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add request ID middleware
app.add_middleware(RawContextMiddleware)
app.middleware("http")(request_id_middleware)

# Register exception handlers
register_exception_handlers(app)

# Include API routers
app.include_router(files_router, prefix="/api/v1")
app.include_router(errors_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "File Manager API is running",
        "version": settings.api_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.db.session import get_db
    
    db_status = "healthy"
    try:
        db = next(get_db())
        if not check_db_connection(db):
            db_status = "unhealthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "version": settings.api_version
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    from app.db.session import get_db
    
    checks = {
        "database": False,
        "logging": True  # Always true if we can log
    }
    
    try:
        db = next(get_db())
        checks["database"] = check_db_connection(db)
    except Exception:
        checks["database"] = False
    
    all_ready = all(checks.values())
    
    return {
        "ready": all_ready,
        "checks": checks
    }