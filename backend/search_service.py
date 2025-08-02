from meilisearch import Client as MeiliClient
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import os

class SearchService:
    def __init__(self):
        # Initialize Meilisearch client
        self.meili_client = MeiliClient('http://localhost:7700', os.getenv('MEILI_MASTER_KEY', ''))
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient("localhost", port=6333)
        
        # Load embedding model
        self.embedding_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
        
        # Initialize indexes/collections
        self._init_meilisearch()
        self._init_qdrant()

    def _init_meilisearch(self):
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
            index.update_searchable_attributes(['title', 'content'])
            index.update_attributes_for_faceting(['tags'])
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

    async def hybrid_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Perform hybrid search combining keyword and vector results"""
        # Keyword search with Meilisearch
        meili_results = self.meili_client.index('documents').search(
            query,
            {
                'limit': limit,
                'attributesToHighlight': ['content'],
                'highlightPreTag': '<mark>',
                'highlightPostTag': '</mark>'
            }
        )
        
        # Vector search with Qdrant
        query_embedding = self.embedding_model.encode(query).tolist()
        qdrant_results = self.qdrant_client.search(
            collection_name="documents_dense",
            query_vector=query_embedding,
            limit=limit
        )
        
        # Combine and re-rank results
        combined = self._combine_results(meili_results['hits'], qdrant_results)
        return combined[:limit]

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