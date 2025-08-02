"""Structured JSON logging configuration with rotation."""

import json
import logging
import sys
from typing import Any, Dict
from pathlib import Path

from loguru import logger
from starlette_context import context

from .config import settings


class InterceptHandler(logging.Handler):
    """Custom logging handler to intercept standard logging to loguru."""
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record."""
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def serialize(record: Dict[str, Any]) -> str:
    """Serialize log record to JSON."""
    subset = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }
    
    # Add extra fields
    if "request_id" in context.data:
        subset["request_id"] = context.data["request_id"]
    
    if record.get("extra"):
        subset.update(record["extra"])
    
    return json.dumps(subset)


def patching(record: Dict[str, Any]) -> None:
    """Patch record for JSON serialization."""
    record["extra"]["serialized"] = serialize(record)


def setup_logging() -> None:
    """Configure structured logging with rotation."""
    
    # Remove default handler
    logger.remove()
    
    # Configure log format based on settings
    if settings.log_format == "json":
        # JSON format with rotation
        log_config = {
            "sink": settings.log_file or sys.stdout,
            "format": "{extra[serialized]}",
            "level": settings.log_level.upper(),
            "serialize": False,
            "filter": patching,
        }
        
        if settings.log_file:
            log_config.update({
                "rotation": settings.log_rotation,
                "retention": settings.log_retention,
                "compression": "zip",
            })
        
        logger.add(**log_config)
    else:
        # Standard format
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "{message}"
        )
        
        log_config = {
            "sink": settings.log_file or sys.stderr,
            "format": log_format,
            "level": settings.log_level.upper(),
            "colorize": True,
        }
        
        if settings.log_file:
            log_config.update({
                "rotation": settings.log_rotation,
                "retention": settings.log_retention,
                "compression": "zip",
            })
        
        logger.add(**log_config)
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Configure uvicorn access logging
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers = [InterceptHandler()]
    
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers = [InterceptHandler()]


# Request ID middleware for logging
async def request_id_middleware(request, call_next):
    """Add request ID to logging context."""
    from uuid import uuid4
    
    request_id = str(uuid4())
    context.data["request_id"] = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response