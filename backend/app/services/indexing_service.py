"""Document indexing service."""

import logging
from typing import Optional, List, Dict
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from ..config import settings
from ..models.document import Document
from ..exceptions import IndexingError

logger = logging.getLogger(__name__)

class IndexingService:
    """Service for document indexing operations."""
    
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=settings.QDRANT_TIMEOUT
        )
        self.collection_name = settings.QDRANT_COLLECTION
        self.vector_size = settings.EMBEDDING_SIZE
        
    def ensure_collection_exists(self) -> None:
        """Ensure the Qdrant collection exists."""
        try:
            collections = self.client.get_collections()
            existing = any(
                c.name == self.collection_name 
                for c in collections.collections
            )
            
            if not existing:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created collection {self.collection_name}")
                
        except UnexpectedResponse as e:
            raise IndexingError(f"Qdrant connection error: {str(e)}")
    
    def index_document(
        self,
        document: Document,
        vector: List[float],
        metadata: Dict
    ) -> str:
        """Index a document in Qdrant.
        
        Args:
            document: Document to index
            vector: Document embedding vector
            metadata: Additional metadata
            
        Returns:
            The Qdrant point ID
        """
        try:
            self.ensure_collection_exists()
            
            point_id = str(document.id)
            payload = {
                "document_id": document.id,
                "user_id": document.user_id,
                "text": document.ocr_text or "",
                **metadata
            }
            
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            
            logger.debug(
                f"Indexed document {document.id} - {operation_info}"
            )
            return point_id
            
        except Exception as e:
            raise IndexingError(f"Indexing failed: {str(e)}")
    
    def search_documents(
        self,
        query_vector: List[float],
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Search documents by similarity.
        
        Args:
            query_vector: Search query embedding
            user_id: Filter by user ID
            limit: Maximum results to return
            
        Returns:
            List of matching documents with scores
        """
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id",
                            match=models.MatchValue(value=user_id)
                        ]
                    ),
                limit=limit
            )
            
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results
            ]
            
        except Exception as e:
            raise IndexingError(f"Search failed: {str(e)}")
    
    def delete_document(self, document_id: str) -> None:
        """Delete a document from the index.
        
        Args:
            document_id: ID of document to remove
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[document_id]
                )
            )
        except Exception as e:
            raise IndexingError(f"Deletion failed: {str(e)}")