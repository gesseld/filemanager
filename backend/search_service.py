from app.services.base import BaseService
from meilisearch import Client as MeiliClient
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional, Union
from datetime import datetime
from app.models.search_history import SearchHistory
from app.db.session import SessionLocal
import re
from transformers import pipeline

class SearchService(BaseService):
    def __init__(self):
        super().__init__()
        # Initialize Meilisearch client
        self.meili_client = MeiliClient(
            self.config.MEILI_URL,
            self.config.MEILI_MASTER_KEY
        )
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            self.config.QDRANT_HOST,
            port=self.config.QDRANT_PORT,
            api_key=self.config.QDRANT_API_KEY
        )
        
        # Load embedding model
        self.embedding_model = SentenceTransformer(
            self.config.EMBEDDING_MODEL
        )
        
        # Initialize NLP components
        self.nlp = pipeline(
            "text2text-generation",
            model="tscholak/cxmefzzi",
            device="cpu"
        )
        
        # Initialize indexes/collections
        self._init_meilisearch()
        self._init_qdrant()
        
    def health_check(self) -> dict:
        """Check search service health."""
        status = {
            "service": "SearchService",
            "meilisearch_healthy": self._check_meilisearch(),
            "qdrant_healthy": self._check_qdrant(),
            "embedding_model_loaded": True,
            "status": "healthy"
        }
        
        if not status["meilisearch_healthy"]:
            status["status"] = "degraded"
            status["warning"] = "Meilisearch connection failed"
            
        if not status["qdrant_healthy"]:
            status["status"] = "degraded"
            status["warning"] = "Qdrant connection failed"
            
        return status
        
    def _check_meilisearch(self) -> bool:
        """Check Meilisearch connection."""
        try:
            self.meili_client.health()
            return True
        except Exception:
            return False
            
    def _check_qdrant(self) -> bool:
        """Check Qdrant connection."""
        try:
            self.qdrant_client.get_collections()
            return True
        except Exception:
            return False

    def _init_meilisearch(self):
        """Initialize Meilisearch index with ranking rules and settings."""
        """Initialize Meilisearch index with ranking rules"""
        try:
            self.meili_client.create_index('documents', {'primaryKey': 'id'})
            index = self.meili_client.index('documents')
            index.update_ranking_rules([
                'words', 
                'typo', 
                'proximity', 
                'attribute', 
                'sort', 
                'exactness'
            ])
            index.update_settings({
                'searchableAttributes': ['title', 'content', 'tags'],
                'filterableAttributes': [
                    'type', 'size', 'created_date', 
                    'owner', 'tags', 'extension', 'location'
                ],
                'sortableAttributes': ['created_date', 'size'],
                'typoTolerance': {
                    'enabled': True,
                    'minWordSizeForTypos': {
                        'oneTypo': 5,
                        'twoTypos': 9
                    }
                },
                'faceting': {
                    'maxValuesPerFacet': 100
                }
            })
        except Exception as e:
            print(f"Meilisearch index already exists: {e}")

    def _init_qdrant(self):
        """Initialize Qdrant collection for dense vectors"""
        try:
            self.qdrant_client.recreate_collection(
                collection_name="documents_dense",
                vectors_config={
                    "size": self.embedding_model.get_sentence_embedding_dimension(),
                    "distance": "Cosine"
                }
            )
        except Exception as e:
            print(f"Qdrant collection already exists: {e}")

    async def upsert_documents(self, documents: List[Dict]):
        """Upsert documents into both search systems"""
        # Add to Meilisearch
        meili_index = self.meili_client.index('documents')
        meili_index.add_documents(documents)
        
        # Generate embeddings and add to Qdrant
        texts = [doc['content'] for doc in documents]
        embeddings = self.embedding_model.encode(texts).tolist()
        
        points = []
        for idx, doc in enumerate(documents):
            points.append({
                "id": doc['id'],
                "vector": embeddings[idx],
                "payload": doc
            })
        
        self.qdrant_client.upsert(
            collection_name="documents_dense",
            points=points
        )

    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict] = None,
        facets: Optional[List[str]] = None
    ) -> List[Dict]:
        """Perform hybrid search with advanced capabilities.
        
        Args:
            query: Search query (supports advanced syntax)
            limit: Maximum results to return
            filters: Dictionary of filter conditions
            facets: List of fields to compute facets for
            
        Returns:
            Dictionary containing:
            - results: List of matching documents
            - facets: Facet counts if requested
            - suggestions: Autocomplete suggestions
        """
        # Build search parameters
        params = {
            'limit': limit,
            'attributesToHighlight': ['content'],
            'highlightPreTag': '<mark>',
            'highlightPostTag': '</mark>',
            'showMatchesPosition': True
        }
        
        # Add filters if provided
        if filters:
            filter_conditions = []
            for field, value in filters.items():
                if isinstance(value, list):
                    filter_conditions.append(f"{field} IN {value}")
                else:
                    filter_conditions.append(f"{field} = {value}")
            params['filter'] = ' AND '.join(filter_conditions)
        
        # Add facets if requested
        if facets:
            params['facets'] = facets
            
        # Keyword search with Meilisearch
        meili_results = self.meili_client.index('documents').search(query, params)
        
        # Vector search with Qdrant
        query_embedding = self.embedding_model.encode(query).tolist()
        qdrant_results = self.qdrant_client.search(
            collection_name="documents_dense",
            query_vector=query_embedding,
            limit=limit
        )
        
        # Combine and re-rank results
        combined = self._combine_results(meili_results['hits'], qdrant_results)
        # Log search history if user is authenticated
        if user_id:
            async with SessionLocal() as session:
                history = SearchHistory(
                    user_id=user_id,
                    query=query,
                    result_count=len(combined[:limit]),
                    timestamp=datetime.utcnow()
                )
                session.add(history)
                await session.commit()
        
        return {
            "hits": combined[:limit],
            "facets": meili_results.get('facets', {}),
            "query_suggestions": self._generate_suggestions(query)
        }

    def process_natural_language_query(self, query: str) -> str:
        """Convert natural language query to search syntax."""
        try:
            # Simple pattern matching for common queries
            if re.match(r"^(find|show|get) me", query, re.I):
                query = re.sub(r"^(find|show|get) me", "", query, flags=re.I).strip()
            
            # Use NLP model for complex queries
            if len(query.split()) > 4:  # Only use NLP for longer queries
                processed = self.nlp(
                    f"translate English to SQL: {query}",
                    max_length=128
                )
                query = processed[0]['generated_text']
                query = re.sub(r"SELECT .*? FROM", "", query, flags=re.I)
                query = re.sub(r"WHERE (.*?)(?:ORDER BY|GROUP BY|LIMIT|$).*", r"\1", query)
                query = query.strip()
            
            return query
        except Exception as e:
            self.logger.error(f"Failed to process natural language query: {e}")
            return query

    def _generate_suggestions(self, query: str) -> List[str]:
        """Generate autocomplete suggestions for a query."""
        if len(query) < 3:
            return []
            
        try:
            suggestions = self.meili_client.index('documents').search(query, {
                'limit': 5,
                'attributesToRetrieve': [],
                'showMatchesPosition': False,
                'attributesToHighlight': [],
                'attributesToCrop': [],
                'cropLength': 0,
                'matches': False
            })
            return [hit['_formatted']['title'] for hit in suggestions['hits']]
        except Exception as e:
            self.logger.error(f"Failed to generate suggestions: {e}")
            return []

    def _combine_results(self, keyword_results: List, vector_results: List) -> List[Dict]:
        """Combine and re-rank results from both search systems"""
        combined = []
        
        # Create a mapping of document IDs to scores
        scores = {}
        for idx, result in enumerate(keyword_results):
            scores[result['id']] = scores.get(result['id'], 0) + (1 - idx/len(keyword_results))
        
        for idx, result in enumerate(vector_results):
            doc_id = result.payload['id']
            scores[doc_id] = scores.get(doc_id, 0) + (1 - idx/len(vector_results))
        
        # Combine all unique documents
        all_docs = {doc['id']: doc for doc in keyword_results}
        for result in vector_results:
            doc = result.payload
            if doc['id'] not in all_docs:
                all_docs[doc['id']] = doc
        
        # Sort by combined score
        combined = sorted(
            all_docs.values(),
            key=lambda x: scores.get(x['id'], 0),
            reverse=True
        )
        
        return combined
