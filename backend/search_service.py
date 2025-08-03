from app.services.base import BaseService
from meilisearch import Client as MeiliClient
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional, Union, Tuple
from datetime import datetime
from app.models.search_history import SearchHistory
from app.db.session import SessionLocal
import re
from transformers import pipeline
from collections import defaultdict
from sqlalchemy import select
from enum import Enum, auto


class QueryOperator(Enum):
    AND = auto()
    OR = auto()
    NOT = auto()


class QueryParser:
    """Parses advanced search queries with AND/OR/NOT operators."""
    
    def __init__(self):
        self.operator_map = {
            'AND': QueryOperator.AND,
            'OR': QueryOperator.OR,
            'NOT': QueryOperator.NOT
        }
    
    def parse(self, query: str) -> Tuple[str, bool]:
        """Parse query and convert to Meilisearch compatible syntax.
        
        Args:
            query: User search query with optional AND/OR/NOT operators
            
        Returns:
            Tuple of (parsed_query, is_advanced) where:
            - parsed_query: Query in Meilisearch syntax
            - is_advanced: True if query contains operators
        """
        if not any(op in query.upper() for op in self.operator_map):
            return query, False
            
        try:
            # Tokenize query while preserving quoted phrases
            tokens = []
            current_token = []
            in_quotes = False
            
            for char in query:
                if char == '"':
                    if in_quotes:
                        tokens.append(''.join(current_token))
                        current_token = []
                    in_quotes = not in_quotes
                elif char.isspace() and not in_quotes:
                    if current_token:
                        tokens.append(''.join(current_token))
                        current_token = []
                else:
                    current_token.append(char)
            
            if current_token:
                tokens.append(''.join(current_token))
            
            # Process tokens into Meilisearch syntax
            parsed = []
            i = 0
            while i < len(tokens):
                token = tokens[i]
                upper_token = token.upper()
                
                if upper_token in self.operator_map:
                    operator = self.operator_map[upper_token]
                    if operator == QueryOperator.NOT:
                        parsed.append(f'NOT {tokens[i+1]}')
                        i += 2
                    else:
                        left = parsed.pop() if parsed else tokens[i-1]
                        right = tokens[i+1]
                        parsed.append(f'({left} {operator.name} {right})')
                        i += 2
                else:
                    parsed.append(token)
                    i += 1
            
            return ' '.join(parsed), True
        except Exception as e:
            raise ValueError(f"Invalid query syntax: {str(e)}")

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
        
        # Initialize suggestion systems
        self.suggestion_cache = defaultdict(list)
        self.popular_terms = defaultdict(int)
        
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
        facets: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        use_nlp: bool = True
    ) -> List[Dict]:
        """Perform hybrid search with advanced capabilities and NLP support.
        
        Args:
            query: Search query (supports AND/OR/NOT operators and natural language)
            limit: Maximum results to return
            filters: Dictionary of filter conditions
            facets: List of fields to compute facets for
            user_id: Optional user ID for personalization
            use_nlp: Whether to attempt NLP processing (default: True)
            
        Returns:
            Dictionary containing:
            - results: List of matching documents
            - facets: Facet counts if requested
            - suggestions: Autocomplete suggestions
            - nlp_processed: Boolean indicating if NLP was used
            
        Raises:
            ValueError: If query syntax is invalid
        """
        original_query = query
        nlp_processed = False
        
        # Try NLP processing if enabled
        if use_nlp:
            try:
                processed_query = self.process_natural_language_query(query)
                if processed_query != query:
                    query = processed_query
                    nlp_processed = True
                    self.logger.info(f"NLP processed query: {original_query} -> {query}")
            except Exception as e:
                self.logger.warning(f"NLP processing failed, using original query: {e}")
        
        # Parse and validate query
        parser = QueryParser()
        try:
            parsed_query, is_advanced = parser.parse(query)
            query = parsed_query
        except ValueError as e:
            if nlp_processed:
                # If NLP processing caused the error, fall back to original query
                self.logger.warning(f"Parsing NLP-processed query failed, falling back: {e}")
                query = original_query
                try:
                    parsed_query, is_advanced = parser.parse(query)
                    query = parsed_query
                except ValueError:
                    raise ValueError(f"Invalid search query: {str(e)}")
            else:
                raise ValueError(f"Invalid search query: {str(e)}")
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
            "query_suggestions": await self._generate_suggestions(query, user_id),
            "nlp_processed": nlp_processed,
            "original_query": original_query if nlp_processed else None
        }

    def process_natural_language_query(self, query: str) -> str:
        """Convert natural language query to search syntax with intent recognition.
        
        Args:
            query: Natural language search query
            
        Returns:
            Processed query in search syntax or original query if processing fails
            
        Behavior:
            - Recognizes common search intents (find, filter, compare)
            - Transforms natural language to structured query
            - Falls back to original query if processing fails
            - Logs processing failures for improvement
        """
        original_query = query
        try:
            # Common query patterns
            patterns = {
                r"^(find|show|get|search for) me? (.*)": r"\2",  # Remove command words
                r"(.*) (from|in) (.*)": r"\1",  # Remove location references
                r"(.*) (created|modified) (before|after|on) (.*)": r"\1",  # Remove date references
                r"compare (.*) and (.*)": r"\1 OR \2",  # Comparison queries
                r"what is (.*)": r"\1",  # Definition queries
            }
            
            # Apply pattern transformations
            for pattern, replacement in patterns.items():
                if re.match(pattern, query, re.I):
                    query = re.sub(pattern, replacement, query, flags=re.I).strip()
            
            # Intent classification
            intent = "general"
            if re.search(r"\b(compare|difference|similar)\b", query, re.I):
                intent = "comparison"
            elif re.search(r"\b(filter|only|just)\b", query, re.I):
                intent = "filter"
            elif re.search(r"\b(what|how|why)\b", query, re.I):
                intent = "informational"
            
            # Use NLP model for complex queries
            if len(query.split()) > 3:  # Use NLP for queries with 4+ words
                try:
                    processed = self.nlp(
                        f"convert to search query: {query}",
                        max_length=128
                    )
                    query = processed[0]['generated_text']
                    
                    # Fallback if NLP output is invalid
                    if not query or len(query) > 500:
                        query = original_query
                except Exception as e:
                    self.logger.warning(f"NLP processing failed, using original query: {e}")
                    query = original_query
            
            # Add intent-specific processing
            if intent == "comparison":
                query = f"({query})"
            elif intent == "filter":
                query = f"+{query}"
            
            return query
            
        except Exception as e:
            self.logger.error(f"Natural language processing failed: {e}")
            return original_query

    async def _generate_suggestions(self, query: str, user_id: Optional[int] = None) -> List[str]:
        """Enhanced autocomplete suggestions with context and popularity weighting."""
        if len(query) < 2:
            return []

        # Get cached suggestions if available
        cache_key = f"{user_id or 'global'}:{query.lower()}"
        if hasattr(self, 'suggestion_cache') and cache_key in self.suggestion_cache:
            return self.suggestion_cache[cache_key][:8]  # Return top 8

        try:
            # Get prefix matches from Meilisearch
            meili_suggestions = self.meili_client.index('documents').search(query, {
                'limit': 10,
                'attributesToRetrieve': ['title'],
                'showMatchesPosition': False,
                'matches': False
            })['hits']

            # Get popular terms from search history
            history_terms = []
            if user_id:
                async with SessionLocal() as session:
                    history = await session.execute(
                        select(SearchHistory.query)
                        .filter(SearchHistory.user_id == user_id)
                        .order_by(SearchHistory.created_at.desc())
                        .limit(100)
                    )
                    history_terms = [h[0] for h in history.all()]

            # Combine and rank suggestions
            suggestions = self._rank_suggestions(
                meili_suggestions,
                history_terms,
                query
            )

            # Cache results
            if not hasattr(self, 'suggestion_cache'):
                self.suggestion_cache = defaultdict(list)
            self.suggestion_cache[cache_key] = suggestions
            return suggestions[:8]

        except Exception as e:
            self.logger.error(f"Failed to generate suggestions: {e}")
            return []

    def _rank_suggestions(self, meili_results: List, history_terms: List[str], query: str) -> List[str]:
        """Rank suggestions using multiple factors."""
        suggestions = set()
        
        # Add Meilisearch title suggestions
        for hit in meili_results:
            title = hit.get('title', '')
            if title.lower().startswith(query.lower()):
                suggestions.add(title)
        
        # Add popular terms from history
        for term in history_terms:
            if term.lower().startswith(query.lower()):
                suggestions.add(term)
        
        # Score and sort suggestions
        scored_suggestions = []
        for suggestion in suggestions:
            score = 0
            # Boost exact prefix matches
            if suggestion.lower().startswith(query.lower()):
                score += 2
            
            # Boost popularity (if we have history)
            if hasattr(self, 'popular_terms'):
                score += self.popular_terms.get(suggestion.lower(), 0) * 0.1
            
            # Boost shorter suggestions (more likely completions)
            score += max(0, 10 - len(suggestion)) * 0.05
            
            scored_suggestions.append((score, suggestion))
        
        # Sort by score and return just the terms
        return [s[1] for s in sorted(scored_suggestions, key=lambda x: -x[0])]

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
