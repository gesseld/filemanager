"""File upload and management API endpoints."""

import logging
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List

from app.models.user import User
from app.services.file_service import FileService
from app.services.ocr_wsl import OCRService
from app.services.indexing_service import IndexingService
from app.services.tagging import TaggingService
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/files", tags=["files"])
logger = logging.getLogger(__name__)

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload and process multiple files."""
    file_service = FileService()
    ocr_service = OCRService()
    indexing_service = IndexingService()
    tagging_service = TaggingService()

    results = []
    for file in files:
        try:
            # Save file temporarily
            file_path, file_id = await file_service.save_uploaded_file(file, current_user)

            # Create document record
            document = Document(
                id=file_id,
                user_id=current_user.id,
                filename=file.filename,
                content_type=file.content_type,
                size=file.size
            )

            # Process file (OCR, indexing, tagging)
            if file.content_type.startswith(('image/', 'application/pdf')):
                try:
                    # Extract text
                    text, metadata = await ocr_service.extract_image_text(file_path)
                    document.ocr_text = text

                    # Generate tags
                    tags = tagging_service.tag_document(document)
                    document.metadata.keywords = tags

                    # Index document
                    vector = await generate_embedding(text)
                    indexing_service.index_document(document, vector, {
                        "original_filename": file.filename,
                        "content_type": file.content_type
                    })

                except Exception as e:
                    logger.error(f"Processing failed for {file.filename}: {str(e)}")
                    document.status = DocumentStatus.FAILED

            # Move to permanent storage
            document.storage_path = file_service.move_to_permanent_storage(file_path, document)
            document.status = DocumentStatus.INDEXED
            await document.save()

            results.append({
                "id": file_id,
                "filename": file.filename,
                "status": "success"
            })

        except Exception as e:
            logger.error(f"Upload failed for {file.filename}: {str(e)}")
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e)
            })

    return JSONResponse(content={"files": results})

@router.get("/{file_id}")
async def get_file_info(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get information about a specific file."""
    file_service = FileService()
    document = await Document.get(file_id)

    if not document or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return {
        "id": document.id,
        "filename": document.filename,
        "size": document.size,
        "status": document.status,
        "created_at": document.created_at,
        "metadata": document.metadata.dict()
    }

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a file and its metadata."""
    file_service = FileService()
    document = await Document.get(file_id)

    if not document or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    try:
        # Delete from storage
        if document.storage_path:
            file_service.delete_file(document.storage_path)

        # Delete from index
        indexing_service = IndexingService()
        indexing_service.delete_document(document.id)

        # Delete document record
        await document.delete()

        return {"status": "success"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}"
        )

@router.put("/{file_id}/metadata")
async def update_file_metadata(
    file_id: str,
    metadata_update: dict,
    current_user: User = Depends(get_current_user)
):
    """Update document metadata (title, description, custom tags)."""
    document = await Document.get(file_id)
    
    if not document or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    try:
        # Update editable fields
        if 'title' in metadata_update:
            document.metadata.title = metadata_update['title']
        if 'description' in metadata_update:
            document.metadata.description = metadata_update['description']
        if 'custom_tags' in metadata_update:
            document.metadata.custom_tags = metadata_update['custom_tags']
        
        document.updated_at = datetime.utcnow()
        await document.save()
        
        return {"status": "success", "updated_fields": list(metadata_update.keys())}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Metadata update failed: {str(e)}"
        )

@router.put("/{file_id}/collection")
async def update_file_collection(
    file_id: str,
    collection_id: str,
    current_user: User = Depends(get_current_user)
):
    """Move document to a collection/folder."""
    document = await Document.get(file_id)
    
    if not document or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    try:
        document.collection_id = collection_id
        document.updated_at = datetime.utcnow()
        await document.save()
        
        return {"status": "success", "collection_id": collection_id}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Collection update failed: {str(e)}"
        )

@router.post("/{file_id}/share")
async def share_file(
    file_id: str,
    user_ids: List[str],
    current_user: User = Depends(get_current_user)
):
    """Share document with other users."""
    document = await Document.get(file_id)
    
    if not document or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    try:
        # Add new users to shared_with list
        document.shared_with = list(set(document.shared_with + user_ids))
        document.updated_at = datetime.utcnow()
        await document.save()
        
        return {"status": "success", "shared_with": document.shared_with}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sharing failed: {str(e)}"
        )