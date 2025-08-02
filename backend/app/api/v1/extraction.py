"""API endpoints for text extraction operations."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.models.document import Document
from app.services.text_extraction_service import text_extraction_service
from app.api.deps import get_current_user

router = APIRouter(prefix="/extraction", tags=["extraction"])


@router.post("/extract/{document_id}", response_model=dict)
async def extract_text_from_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Trigger text extraction for a specific document.
    
    Args:
        document_id: ID of document to process
        background_tasks: FastAPI background tasks handler
        db: Async database session
        current_user: Authenticated user via JWT
        
    Returns:
        dict: {
            "message": str,
            "document_id": int,
            "status": str
        }
        
    Raises:
        HTTPException: 404 if document not found
        HTTPException: 403 if unauthorized
        HTTPException: 500 for server errors
    """
    try:
        # Get document
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check ownership
        if document.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to extract text from this document"
            )
        
        # Trigger extraction in background
        background_tasks.add_task(
            text_extraction_service.extract_text_from_document,
            document
        )
        
        return {
            "message": "Text extraction started",
            "document_id": document_id,
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error triggering text extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/extract-pending", response_model=dict)
async def extract_pending_documents(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Trigger text extraction for all pending documents.
    
    Args:
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        
    Returns:
        Dictionary with processing status
    """
    try:
        # Process pending documents in background
        background_tasks.add_task(
            text_extraction_service.process_pending_documents
        )
        
        return {
            "message": "Processing pending documents started",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error processing pending documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/status/{document_id}", response_model=dict)
async def get_extraction_status(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get text extraction status for a document.
    
    Args:
        document_id: ID of the document
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dictionary with extraction status
    """
    try:
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check ownership
        if document.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this document"
            )
        
        return {
            "document_id": document_id,
            "text_extraction_status": document.text_extraction_status,
            "ocr_status": document.ocr_status,
            "has_extracted_text": bool(document.extracted_text),
            "has_ocr_text": bool(document.ocr_text),
            "extracted_metadata": document.extracted_metadata,
            "ocr_confidence": document.ocr_confidence
        }
        
    except Exception as e:
        logger.error(f"Error getting extraction status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/search-text", response_model=list)
async def search_extracted_text(
    query: str,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Search within extracted text content.
    
    Args:
        query: Search query
        limit: Maximum number of results
        offset: Pagination offset
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of documents with matching text
    """
    try:
        from sqlalchemy import or_, select
        
        # Search in extracted text and OCR text
        stmt = (
            select(Document)
            .where(
                Document.owner_id == current_user.id,
                or_(
                    Document.extracted_text.contains(query),
                    Document.ocr_text.contains(query)
                )
            )
            .limit(limit)
            .offset(offset)
        )
        
        result = await db.execute(stmt)
        documents = result.scalars().all()
        
        return [
            {
                "id": doc.id,
                "title": doc.title,
                "filename": doc.filename,
                "mime_type": doc.mime_type,
                "text_extraction_status": doc.text_extraction_status,
                "ocr_status": doc.ocr_status,
                "extracted_text_preview": doc.extracted_text[:200] if doc.extracted_text else None,
                "ocr_text_preview": doc.ocr_text[:200] if doc.ocr_text else None,
                "created_at": doc.created_at
            }
            for doc in documents
        ]
        
    except Exception as e:
        logger.error(f"Error searching extracted text: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
