"""Service layer initialization."""
from .base import BaseService
from .file_service import FileService, file_service
from .indexing_service import IndexingService, indexing_service
from .metadata_service import MetadataService, metadata_service
from .ocr_service import OCRService, ocr_service
from .search_service import SearchService, search_service
from .tagging_service import TaggingService, tagging_service
from .text_extraction_service import TextExtractionService, text_extraction_service

__all__ = [
    'BaseService',
    'FileService',
    'file_service',
    'IndexingService',
    'indexing_service',
    'MetadataService',
    'metadata_service',
    'OCRService',
    'ocr_service',
    'SearchService',
    'search_service',
    'TaggingService',
    'tagging_service',
    'TextExtractionService',
    'text_extraction_service'
]
