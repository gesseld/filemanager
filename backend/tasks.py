from celery import shared_task
from loguru import logger
from typing import Optional
import requests
from io import BytesIO
from PIL import Image
import pytesseract
import PyPDF2
import magic

@shared_task(bind=True, name='extract_text')
def extract_text(self, file_url: str, file_type: Optional[str] = None) -> str:
    """Extract text from various file types"""
    try:
        response = requests.get(file_url)
        response.raise_for_status()
        file_data = BytesIO(response.content)
        
        if not file_type:
            mime = magic.Magic(mime=True)
            file_type = mime.from_buffer(file_data.read(1024))
            file_data.seek(0)

        if file_type.startswith('image/'):
            image = Image.open(file_data)
            return pytesseract.image_to_string(image)
        elif file_type == 'application/pdf':
            reader = PyPDF2.PdfReader(file_data)
            return "\n".join(page.extract_text() for page in reader.pages)
        else:
            return file_data.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Text extraction failed: {str(e)}")
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, name='embed_document')
def embed_document(self, text: str) -> list[float]:
    """Generate embeddings for document text"""
    try:
        # TODO: Implement actual embedding logic
        # This is a placeholder - replace with your embedding service
        return [0.0] * 768  # Example 768-dim vector
    except Exception as e:
        logger.error(f"Embedding failed: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, name='cleanup_search_indexes')
def cleanup_search_indexes(self, file_id: int):
    """
    Clean up document from all search indexes (Qdrant + Meilisearch).
    
    Args:
        file_id: ID of the document to remove
        
    Raises:
        Exception: If cleanup fails (will trigger retry)
    """
    from loguru import logger
    from app.db.session import SessionLocal
    from app.models.document import Document
    
    try:
        db = SessionLocal()
        
        # Verify document was deleted from DB (shouldn't exist)
        doc = db.query(Document).filter(Document.id == file_id).first()
        if doc:
            logger.warning(f"Document {file_id} still exists in DB - skipping index cleanup")
            return
            
        # TODO: Implement Qdrant client
        # qdrant_client.delete(collection_name="documents", points=[file_id])
        logger.info(f"Removed document {file_id} from Qdrant")
        
        # TODO: Implement Meilisearch client
        # meilisearch_client.index('documents').delete_document(file_id)
        logger.info(f"Removed document {file_id} from Meilisearch")
        
    except Exception as e:
        logger.error(f"Failed to cleanup search indexes for document {file_id}: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, name='reindex_document')
def reindex_document(self, file_id: int):
    """
    Reindex a document in all search indexes (Qdrant + Meilisearch).
    
    Args:
        file_id: ID of the document to reindex
        
    Raises:
        Exception: If reindexing fails (will trigger retry)
    """
    from loguru import logger
    from app.db.session import SessionLocal
    from app.models.document import Document
    
    try:
        db = SessionLocal()
        doc = db.query(Document).filter(Document.id == file_id).first()
        
        if not doc:
            logger.error(f"Document {file_id} not found in DB")
            raise ValueError(f"Document {file_id} not found")
            
        # TODO: Implement text extraction if needed
        # text = extract_text(doc.file_path)
        
        # TODO: Implement Qdrant update
        # qdrant_client.upsert(
        #     collection_name="documents",
        #     points=[{
        #         "id": doc.id,
        #         "vector": embed_document(text),
        #         "payload": {
        #             "title": doc.title,
        #             "content": text
        #         }
        #     }]
        # )
        logger.info(f"Updated document {file_id} in Qdrant")
        
        # TODO: Implement Meilisearch update
        # meilisearch_client.index('documents').add_documents([{
        #     "id": doc.id,
        #     "title": doc.title,
        #     "content": text,
        #     "metadata": doc.metadata
        # }])
        logger.info(f"Updated document {file_id} in Meilisearch")
        
    except Exception as e:
        logger.error(f"Failed to reindex document {file_id}: {e}")
        raise self.retry(exc=e, countdown=60)