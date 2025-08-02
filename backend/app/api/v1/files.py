"""File upload API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.file import FileUploadResponse, FileUploadError
from app.services.file_service import file_service
from app.core.config import settings

# For now, we'll use a mock user since authentication isn't implemented yet
# In production, this would be replaced with proper authentication
def get_current_user(db: Session = Depends(get_db)) -> User:
    """Get current user - temporary mock implementation."""
    # TODO: Replace with proper authentication
    user = db.query(User).first()
    if not user:
        # Create a mock user if none exists
        user = User(
            email="admin@example.com",
            username="admin",
            full_name="Admin User",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


router = APIRouter(prefix="/files", tags=["files"])


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": FileUploadError, "description": "Bad Request"},
        413: {"model": FileUploadError, "description": "File Too Large"},
        415: {"model": FileUploadError, "description": "Unsupported Media Type"},
        422: {"model": FileUploadError, "description": "Unprocessable Entity"},
        500: {"model": FileUploadError, "description": "Internal Server Error"},
    }
)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    title: Optional[str] = Form(None, description="Document title"),
    description: Optional[str] = Form(None, description="Document description"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a file and create a document record.
    
    - Validates file type using python-magic
    - Stores file in storage/uploads/{uuid} directory
    - Creates Document record with status="pending"
    
    Args:
        file: The file to upload
        title: Optional document title (defaults to filename)
        description: Optional document description
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        FileUploadResponse: Details of the uploaded file
        
    Raises:
        HTTPException: If validation or upload fails
    """
    try:
        # Validate file
        mime_type, file_size = await file_service.validate_file(file)
        
        # Save file to storage
        storage_full_path, relative_path, checksum, file_size = await file_service.save_file(
            file, mime_type
        )
        
        # Check for duplicate files using checksum
        existing_doc = db.query(Document).filter(Document.checksum == checksum).first()
        if existing_doc:
            # Clean up the newly saved file since it's a duplicate
            file_service.delete_file(relative_path)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File already exists with ID: {existing_doc.id}"
            )
        
        # Create document record
        document = Document(
            title=title or file.filename,
            description=description,
            filename=file.filename,
            file_path=relative_path,
            file_size=file_size,
            mime_type=mime_type,
            checksum=checksum,
            status="pending",  # Set status to pending for processing
            owner_id=current_user.id
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return FileUploadResponse(
            id=document.id,
            title=document.title,
            filename=document.filename,
            file_path=document.file_path,
            file_size=document.file_size,
            mime_type=document.mime_type,
            status=document.status,
            created_at=document.created_at
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        from loguru import logger
        logger.error(f"Unexpected error during file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during file upload"
        )


@router.get("/upload")
async def get_upload_info():
    """Get information about supported file types and upload limits."""
    from app.schemas.file import FileValidationConfig
    
    return {
        "max_file_size": FileValidationConfig.MAX_FILE_SIZE,
        "supported_mime_types": list(FileValidationConfig.ALLOWED_MIME_TYPES),
        "max_file_size_mb": FileValidationConfig.MAX_FILE_SIZE / (1024 * 1024)
    }


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    }
)
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a file and all associated data.
    
    - Removes file from storage
    - Deletes database record
    - Triggers async cleanup of search indexes (Qdrant/Meilisearch)
    
    Args:
        file_id: ID of the file to delete
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        HTTP 204 No Content on success
        
    Raises:
        HTTPException: If file not found or deletion fails
    """
    try:
        # Get document record
        document = db.query(Document).filter(
            Document.id == file_id,
            Document.owner_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Delete file from storage
        file_service.delete_file(document.file_path)
        
        # Delete database record
        db.delete(document)
        db.commit()
        
        # Trigger async cleanup of search indexes
        from tasks import cleanup_search_indexes
        cleanup_search_indexes.delay(file_id)
        
    except HTTPException:
        raise
    except Exception as e:
        from loguru import logger
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )


@router.post(
    "/{file_id}/reindex",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    }
)
async def reindex_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger reindexing of a file's content in search indexes.
    
    - Verifies document exists and belongs to user
    - Triggers async reindexing task
    - Returns immediately with 202 Accepted
    
    Args:
        file_id: ID of the file to reindex
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        HTTP 202 Accepted on success
        
    Raises:
        HTTPException: If file not found or reindex fails
    """
    try:
        # Get document record
        document = db.query(Document).filter(
            Document.id == file_id,
            Document.owner_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Trigger async reindexing
        from tasks import reindex_document
        reindex_document.delay(file_id)
        
    except HTTPException:
        raise
    except Exception as e:
        from loguru import logger
        logger.error(f"Error triggering reindex for file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger reindex"
        )