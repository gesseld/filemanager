"""API v1 routes."""

from fastapi import APIRouter

from .files import router as files_router
from .extraction import router as extraction_router
from .metadata import router as metadata_router

router = APIRouter(prefix="/v1")

router.include_router(files_router)
router.include_router(extraction_router)
router.include_router(metadata_router)