"""File metadata API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.metadata import (
    FileMetadataResponse,
    MetadataBatchResponse,
    MetadataErrorResponse,
    FileInfoRequest,
    BatchMetadataRequest
)
from app.services.metadata_service import metadata_service

# For now, we'll use a mock user since authentication isn't implemented yet
def get_current_user(db: Session = Depends(get_db)) -> User:
    """Get current user - temporary mock implementation."""
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


router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get(
    "/{document_id}",
    response_model=FileMetadataResponse,
    responses={
        404: {"model": MetadataErrorResponse, "description": "File not found"},
        500: {"model": MetadataErrorResponse, "description": "Internal server error"},
    }
)
async def get_file_metadata(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive metadata for a specific file.
    
    Args:
        document_id: Document ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        FileMetadataResponse: Comprehensive file metadata
        
    Raises:
        HTTPException: If file not found or access denied
    """
    try:
        # Get document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )
        
        # Extract metadata
        metadata = metadata_service.extract_file_metadata(document.file_path)
        
        return FileMetadataResponse(**metadata)
        
    except HTTPException:
        raise
    except Exception as e:
        from loguru import logger
        logger.error(f"Error extracting metadata for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting file metadata: {str(e)}"
        )


@router.post(
    "/batch",
    response_model=MetadataBatchResponse,
    responses={
        400: {"model": MetadataErrorResponse, "description": "Bad request"},
        500: {"model": MetadataErrorResponse, "description": "Internal server error"},
    }
)
async def get_batch_metadata(
    request: BatchMetadataRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get metadata for multiple files in batch.
    
    Args:
        request: Batch metadata request containing file paths
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        MetadataBatchResponse: Batch metadata results
    """
    try:
        # Get documents for the current user
        documents = db.query(Document).filter(
            Document.owner_id == current_user.id,
            Document.file_path.in_(request.file_paths)
        ).all()
        
        # Create mapping of file paths to document IDs
        document_map = {doc.file_path: doc.id for doc in documents}
        
        # Extract metadata for each file
        results = {}
        successful = 0
        failed = 0
        
        for file_path in request.file_paths:
            if file_path not in document_map:
                results[file_path] = {"error": "File not found or access denied"}
                failed += 1
                continue
                
            try:
                metadata = metadata_service.extract_file_metadata(file_path)
                results[file_path] = metadata
                successful += 1
            except Exception as e:
                results[file_path] = {"error": str(e)}
                failed += 1
        
        return MetadataBatchResponse(
            files=results,
            total_files=len(request.file_paths),
            successful=successful,
            failed=failed
        )
        
    except Exception as e:
        from loguru import logger
        logger.error(f"Error in batch metadata extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing batch metadata: {str(e)}"
        )


@router.get(
    "/document/{document_id}/exists",
    response_model=dict
)
async def check_file_exists(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if a file exists in storage.
    
    Args:
        document_id: Document ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dictionary with file existence status
    """
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )
        
        exists = metadata_service.validate_file_exists(document.file_path)
        
        return {
            "document_id": document_id,
            "file_path": document.file_path,
            "exists": exists,
            "filename": document.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        from loguru import logger
        logger.error(f"Error checking file existence for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking file existence: {str(e)}"
        )


@router.get(
    "/user/all",
    response_model=List[FileMetadataResponse]
)
async def get_all_user_metadata(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get metadata for all files owned by the current user.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of file metadata for all user files
    """
    try:
        # Get all documents for the current user
        documents = db.query(Document).filter(
            Document.owner_id == current_user.id
        ).all()
        
        metadata_list = []
        
        for document in documents:
            try:
                metadata = metadata_service.extract_file_metadata(document.file_path)
                metadata_list.append(FileMetadataResponse(**metadata))
            except Exception as e:
                # Log error but continue processing other files
                from loguru import logger
                logger.warning(f"Error extracting metadata for document {document.id}: {e}")
        
        return metadata_list
        
    except Exception as e:
        from loguru import logger
        logger.error(f"Error getting all user metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user metadata: {str(e)}"
        )