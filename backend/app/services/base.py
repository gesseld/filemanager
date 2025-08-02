"""Base service class with common functionality."""
from typing import Any, Dict
from loguru import logger
from app.core.config import settings

class BaseService:
    """Base service providing common functionality to all services."""
    
    def __init__(self):
        self.logger = logger.bind(service=self.__class__.__name__)
        self.config = settings
        
    def service_status(self) -> Dict[str, Any]:
        """Return basic service status information."""
        return {
            "service": self.__class__.__name__,
            "status": "active",
            "config": {
                "env": self.config.ENVIRONMENT,
                "debug": self.config.DEBUG
            }
        }
