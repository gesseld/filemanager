"""Application configuration using Pydantic-settings."""

from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    api_title: str = Field(default="File Manager API", description="API title")
    api_description: str = Field(
        default="A modern file management API with AI-powered search",
        description="API description"
    )
    api_version: str = Field(default="0.1.0", description="API version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # Frontend Settings
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="Frontend application URL"
    )
    
    # CORS Settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="CORS allowed origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials")
    cors_allow_methods: List[str] = Field(default=["*"], description="Allowed methods")
    cors_allow_headers: List[str] = Field(default=["*"], description="Allowed headers")
    
    # Database Settings
    database_url: str = Field(
        default="sqlite:///./filemanager.db",
        description="Database connection URL"
    )
    database_echo: bool = Field(default=False, description="SQLAlchemy echo SQL")
    
    # Security Settings
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for JWT"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Token expiry")
    
    # Terms of Service Settings
    tos_version: str = Field(default="1.0.0", description="Current Terms of Service version")
    tos_required: bool = Field(default=True, description="Require ToS acceptance")
    tos_update_url: str = Field(
        default="https://example.com/terms",
        description="URL to latest Terms of Service"
    )
    
    # Redis Settings
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    
    # Qdrant Settings
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant port")
    qdrant_api_key: str = Field(default="", description="Qdrant API key")
    qdrant_timeout: int = Field(default=30, description="Qdrant connection timeout in seconds")
    
    # Meilisearch Settings
    meilisearch_host: str = Field(default="localhost", description="Meilisearch host")
    meilisearch_port: int = Field(default=7700, description="Meilisearch port")
    meilisearch_api_key: str = Field(default="", description="Meilisearch API key")
    meilisearch_url: str = Field(
        default="http://localhost:7700",
        description="Meilisearch URL"
    )
    
    # Logging Settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="json",
        description="Log format (json or standard)"
    )
    log_file: Optional[str] = Field(
        default=None,
        description="Log file path (None for stdout)"
    )
    log_rotation: str = Field(
        default="1 day",
        description="Log rotation interval"
    )
    log_retention: str = Field(
        default="30 days",
        description="Log retention period"
    )
    
    # Tika Settings
    tika_url: str = Field(
        default="http://localhost:9998",
        description="Apache Tika server URL"
    )
    
    # Tesseract Settings
    tesseract_url: str = Field(
        default="http://localhost:8080",
        description="Tesseract OCR server URL"
    )
    
    # Mistral OCR Settings
    mistral_api_key: str = Field(
        default="IYMIT4sLUvxOzIHXUxR63yDalnaDPZy3",
        description="Mistral OCR API key"
    )
    mistral_api_url: str = Field(
        default="https://api.mistral.ai/v1/ocr",
        description="Mistral OCR API URL"
    )
    
    class Config:
        """Pydantic settings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()