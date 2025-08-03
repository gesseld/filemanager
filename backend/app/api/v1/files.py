"""File upload and management API endpoints."""

import logging
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status, Form
from fastapi.responses import JSONResponse
from typing import List, Optional

from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.services.file_service import FileService
from app.services.ocr_wsl import OCRService
from app.services.indexing_service import IndexingService
from app.services.tagging import TaggingService
from app.services.navigation_state import NavigationStateService
from app.api.dependencies import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/files", tags=["files"])
logger = logging.getLogger(__name__)

@router.post("/temporary", status_code=status.HTTP_200_OK)
async def create_temporary_file(
    file: UploadFile = File(...),
    expires_in: int = Form(300),  # Default 5 minutes
    current_user: User = Depends(get_current_user)
):
    """Create a temporary file URL for external processing."""
    try:
        # Save file temporarily
        file_service = FileService()
        file_path, file_id = await file_service.save_uploaded_file(file, current_user)
        
        # Generate temporary URL
        temp_url = f"{settings.API_BASE_URL}/files/temporary/{file_id}"
        
        # Schedule cleanup
        background_tasks.add_task(
            file_service.delete_file_after_delay,
            file_path,
            delay=expires_in
        )
        
        return {
            "url": temp_url,
            "expires_in": expires_in,
            "file_id": file_id
        }
        
    except Exception as e:
        logger.error(f"Failed to create temporary file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create temporary file: {str(e)}"
        )

@router.get("/temporary/{file_id}")
async def serve_temporary_file(
    file_id: str,
    file_service: FileService = Depends(FileService)
):
    """Serve a temporary file."""
    try:
        file_path = file_service.get_temp_file_path(file_id)
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or expired"
            )
            
        return FileResponse(
            file_path,
            media_type="application/octet-stream",
            filename=os.path.basename(file_path)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload and process multiple files (non-chunked)."""
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

@router.post("/chunked/start", status_code=status.HTTP_201_CREATED)
async def start_chunked_upload(
    filename: str,
    content_type: str,
    total_size: int,
    current_user: User = Depends(get_current_user)
):
    """Initialize a chunked file upload."""
    try:
        file_service = FileService()
        file_id = str(uuid.uuid4())
        
        # Create initial document record
        document = Document(
            id=file_id,
            user_id=current_user.id,
            filename=filename,
            content_type=content_type,
            size=total_size,
            status=DocumentStatus.UPLOADING
        )
        await document.save()
        
        return {
            "file_id": file_id,
            "chunk_size": settings.CHUNK_SIZE,
            "status": "uploading"
        }
        
    except Exception as e:
        logger.error(f"Failed to start chunked upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start chunked upload: {str(e)}"
        )

@router.post("/chunked/upload/{file_id}", status_code=status.HTTP_200_OK)
async def upload_chunk(
    file_id: str,
    chunk: UploadFile = File(...),
    chunk_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    current_user: User = Depends(get_current_user)
):
    """Upload a file chunk."""
    try:
        file_service = FileService()
        
        # Verify document exists and belongs to user
        document = await Document.get(file_id)
        if not document or document.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
            
        # Save the chunk
        result = await file_service.save_chunk(
            chunk,
            chunk_id,
            chunk_index,
            total_chunks,
            file_id
        )
        
        # Update document status
        document.status = DocumentStatus.PROCESSING
        await document.save()
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to upload chunk {chunk_index} for {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload chunk: {str(e)}"
        )

@router.post("/chunked/complete/{file_id}", status_code=status.HTTP_200_OK)
async def complete_chunked_upload(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """Complete a chunked upload by assembling all chunks."""
    try:
        file_service = FileService()
        ocr_service = OCRService()
        indexing_service = IndexingService()
        tagging_service = TaggingService()
        
        # Verify document exists and belongs to user
        document = await Document.get(file_id)
        if not document or document.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
            
        # Assemble chunks into complete file
        file_path, _ = await file_service.assemble_chunks(
            file_id,
            document.filename,
            document.content_type
        )
        
        # Process file (OCR, indexing, tagging)
        if document.content_type.startswith(('image/', 'application/pdf')):
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
                    "original_filename": document.filename,
                    "content_type": document.content_type
                })

            except Exception as e:
                logger.error(f"Processing failed for {document.filename}: {str(e)}")
                document.status = DocumentStatus.FAILED
                document.error_message = str(e)
                await document.save()
                raise

        # Move to permanent storage
        document.storage_path = file_service.move_to_permanent_storage(file_path, document)
        document.status = DocumentStatus.INDEXED
        await document.save()
        
        return {
            "file_id": file_id,
            "status": "completed",
            "storage_path": document.storage_path
        }
        
    except Exception as e:
        logger.error(f"Failed to complete chunked upload for {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete upload: {str(e)}"
        )

@router.get("/chunked/{file_id}/progress")
async def get_upload_progress(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get upload progress for a chunked upload."""
    try:
        file_service = FileService()
        document = await Document.get(file_id)
        
        if not document or document.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
            
        progress = await file_service.get_upload_progress(file_id)
        
        return {
            "file_id": file_id,
            "status": document.status.value,
            "progress": progress,
            "uploaded_chunks": progress.get("uploaded_chunks", 0),
            "total_chunks": progress.get("total_chunks", 0)
        }
        
    except Exception as e:
        logger.error(f"Failed to get upload progress for {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get upload progress: {str(e)}"
        )

@router.get("/{file_id}/status")
async def get_file_status(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed status information for a file."""
    try:
        document = await Document.get(file_id)
        
        if not document or (document.user_id != current_user.id and current_user.id not in document.shared_with):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
            
        return {
            "file_id": document.id,
            "status": document.status.value,
            "error_message": document.error_message,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
            "processing_stats": {
                "ocr_completed": bool(document.ocr_text),
                "indexed": document.status == DocumentStatus.INDEXED,
                "tags_generated": bool(document.metadata.keywords)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get status for {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file status: {str(e)}"
        )

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
        )@router.post("/download", response_class=StreamingResponse)
async def download_files_as_zip(
    file_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download multiple files as a ZIP archive."""
    try:
        # Verify access and collect file paths
        file_paths = []
        for file_id in file_ids:
            document = await db.get(Document, file_id)
            if not document or document.owner_id != current_user.id:
                continue
            if Path(document.storage_path).exists():
                file_paths.append(document.storage_path)

        if not file_paths:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No accessible files found"
            )

        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for file_path in file_paths:
                zip_file.write(file_path, Path(file_path).name)

        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=download.zip",
                "Content-Length": str(zip_buffer.getbuffer().nbytes)
            }
        )

    except Exception as e:
        logger.error(f"Failed to create ZIP download: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
@router.post("/{file_id}/copy", response_model=FileOperationResponse)
async def copy_file(
    file_id: str,
    target_path: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Copy a file to a new location."""
    document = await db.get(Document, file_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        new_path = file_service.copy_file(document.storage_path, target_path)
        return {
            "success": True,
            "message": "File copied successfully",
            "details": {"new_path": new_path}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{file_id}/move", response_model=FileOperationResponse)
async def move_file(
    file_id: str,
    target_path: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Move a file to a new location."""
    document = await db.get(Document, file_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        new_path = file_service.move_file(document.storage_path, target_path)
        return {
            "success": True,
            "message": "File moved successfully",
            "details": {"new_path": new_path}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{file_id}/rename", response_model=FileOperationResponse)
async def rename_file(
    file_id: str,
    new_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rename a file."""
    document = await db.get(Document, file_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        new_path = file_service.rename_file(
            document.storage_path,
            new_name
        )
        return {
            "success": True,
            "message": "File renamed successfully",
            "details": {"new_path": new_path}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/browse")
async def browse_files(
    current_user: User = Depends(get_current_user),
    path: Optional[str] = None,
    view_mode: str = "list",  # list/grid/gallery
    sort_by: str = "name",  # name/size/date
    sort_order: str = "asc",  # asc/desc
    cursor: Optional[str] = None,
    per_page: int = 20,
    nav_state: NavigationStateService = Depends(NavigationStateService)
):
    """Browse files with folder navigation and multiple view modes."""
    try:
        # Get files/folders in current path with optimized query
        base_query = Document.filter(
            user_id=current_user.id,
            parent_id=path
        ).with_hint("USE INDEX (idx_user_parent)")

        # Apply cursor-based pagination
        if cursor:
            last_item = await Document.get(cursor)
            if sort_by == "name":
                if sort_order == "asc":
                    base_query = base_query.filter(Document.filename > last_item.filename)
                else:
                    base_query = base_query.filter(Document.filename < last_item.filename)
            elif sort_by == "size":
                if sort_order == "asc":
                    base_query = base_query.filter(Document.size > last_item.size)
                else:
                    base_query = base_query.filter(Document.size < last_item.size)
            else:  # date
                if sort_order == "asc":
                    base_query = base_query.filter(Document.updated_at > last_item.updated_at)
                else:
                    base_query = base_query.filter(Document.updated_at < last_item.updated_at)

        # Apply sorting
        if sort_by == "name":
            base_query = base_query.order_by(Document.filename.asc() if sort_order == "asc" else Document.filename.desc())
        elif sort_by == "size":
            base_query = base_query.order_by(Document.size.asc() if sort_order == "asc" else Document.size.desc())
        else:  # date
            base_query = base_query.order_by(Document.updated_at.asc() if sort_order == "asc" else Document.updated_at.desc())

        # Execute optimized query
        items = await base_query.limit(per_page + 1).all()  # Fetch one extra to check for more items
        has_more = len(items) > per_page
        if has_more:
            items = items[:-1]  # Remove the extra item

        # Persist navigation state
        await nav_state.save_state(
            user_id=current_user.id,
            path=path,
            view_mode=view_mode,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        response = {
            "items": items,
            "per_page": per_page,
            "view_mode": view_mode,
            "has_more": has_more
        }
        
        if has_more:
            last_item = items[-1]
            if sort_by == "name":
                response["next_cursor"] = last_item.filename
            elif sort_by == "size":
                response["next_cursor"] = str(last_item.size)
            else:  # date
                response["next_cursor"] = last_item.updated_at.isoformat()
                
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Browse failed: {str(e)}"
        )

@router.get("/breadcrumbs")
async def get_breadcrumbs(
    path: str,
    current_user: User = Depends(get_current_user),
    nav_state: NavigationStateService = Depends(NavigationStateService)
):
    """Get breadcrumb trail for current path."""
    try:
        breadcrumbs = []
        current = path
        
        while current:
            folder = await Document.get(current)
            if not folder or folder.user_id != current_user.id:
                break
            breadcrumbs.insert(0, {
                "id": folder.id,
                "name": folder.filename
            })
            current = folder.parent_id

        # Persist current path in navigation state
        await nav_state.save_state(
            user_id=current_user.id,
            path=path
        )
            
        return breadcrumbs
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Breadcrumbs failed: {str(e)}"
        )

@router.get("/collections/recent")
async def get_recent_files(
    current_user: User = Depends(get_current_user),
    cursor: Optional[str] = None,
    limit: int = 10,
    nav_state: NavigationStateService = Depends(NavigationStateService)
):
    """Get recently accessed files."""
    try:
        base_query = Document.filter(
            user_id=current_user.id,
            is_folder=False
        ).with_hint("USE INDEX (idx_user_last_accessed)")

        if cursor:
            last_date = datetime.fromisoformat(cursor)
            base_query = base_query.filter(Document.last_accessed_at < last_date)

        items = await base_query.order_by(
            Document.last_accessed_at.desc()
        ).limit(limit + 1).all()  # Fetch one extra to check for more items

        has_more = len(items) > limit
        if has_more:
            items = items[:-1]  # Remove the extra item

        # Persist collection view state
        await nav_state.save_state(
            user_id=current_user.id,
            collection="recent",
            limit=limit
        )

        response = {
            "items": items,
            "limit": limit,
            "has_more": has_more
        }

        if has_more:
            response["next_cursor"] = items[-1].last_accessed_at.isoformat()

        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recent files failed: {str(e)}"
        )

@router.get("/collections/starred")
async def get_starred_files(
    current_user: User = Depends(get_current_user),
    cursor: Optional[str] = None,
    limit: int = 20,
    nav_state: NavigationStateService = Depends(NavigationStateService)
):
    """Get starred/flagged files."""
    try:
        base_query = Document.filter(
            user_id=current_user.id,
            starred=True
        ).with_hint("USE INDEX (idx_user_starred)")

        if cursor:
            last_date = datetime.fromisoformat(cursor)
            base_query = base_query.filter(Document.updated_at < last_date)

        items = await base_query.order_by(
            Document.updated_at.desc()
        ).limit(limit + 1).all()  # Fetch one extra to check for more items

        has_more = len(items) > limit
        if has_more:
            items = items[:-1]  # Remove the extra item

        # Persist collection view state
        await nav_state.save_state(
            user_id=current_user.id,
            collection="starred",
            limit=limit
        )

        response = {
            "items": items,
            "limit": limit,
            "has_more": has_more
        }

        if has_more:
            response["next_cursor"] = items[-1].updated_at.isoformat()

        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Starred files failed: {str(e)}"
        )

@router.get("/collections/shared")
async def get_shared_files(
    current_user: User = Depends(get_current_user),
    cursor: Optional[str] = None,
    limit: int = 20,
    nav_state: NavigationStateService = Depends(NavigationStateService)
):
    """Get files shared with current user."""
    try:
        base_query = Document.filter(
            shared_with__contains=[current_user.id]
        ).with_hint("USE INDEX (idx_shared_with)")

        if cursor:
            last_date = datetime.fromisoformat(cursor)
            base_query = base_query.filter(Document.updated_at < last_date)

        items = await base_query.order_by(
            Document.updated_at.desc()
        ).limit(limit + 1).all()  # Fetch one extra to check for more items

        has_more = len(items) > limit
        if has_more:
            items = items[:-1]  # Remove the extra item

        # Persist collection view state
        await nav_state.save_state(
            user_id=current_user.id,
            collection="shared",
            limit=limit
        )

        response = {
            "items": items,
            "limit": limit,
            "has_more": has_more
        }

        if has_more:
            response["next_cursor"] = items[-1].updated_at.isoformat()

        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Shared files failed: {str(e)}"
        )
@router.post("/{file_id}/resolve-conflict", response_model=FileConflictResolution)
async def resolve_file_conflict(
    file_id: str,
    strategy: FileConflictStrategy,
    backup: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resolve a file version conflict."""
    document = await db.get(Document, file_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        result = version_service.resolve_conflict(
            document.storage_path,
            strategy,
            create_backup=backup
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
