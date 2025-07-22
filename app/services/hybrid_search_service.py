"""
Hybrid search service combining vector similarity and text search.

This service provides sophisticated search capabilities by combining:
- Vector similarity search (semantic similarity)
- Text-based search (keyword/full-text matching)
- Configurable weighting and ranking strategies
- Result fusion and reranking
"""

import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import numpy as np

from app.config.logging import get_logger, LoggingMixin
from app.models.schemas import (
    SearchOptions, SearchResultItem, SearchResponse, SearchStats, VectorResponse
)
from app.services.deeplake_service import DeepLakeService
from app.services.embedding_service import get_embedding_service


class FusionMethod(Enum):
    """Methods for combining vector and text search results."""
    WEIGHTED_SUM = "weighted_sum"        # Simple weighted combination
    RRF = "reciprocal_rank_fusion"      # Reciprocal Rank Fusion
    CombSUM = "comb_sum"                # CombSUM algorithm
    CombMNZ = "comb_mnz"                # CombMNZ algorithm
    BORDA_COUNT = "borda_count"         # Borda count voting


@dataclass
class TextSearchResult:
    """Text search result."""
    vector_id: str
    score: float
    rank: int
    matched_fields: List[str]
    snippet: Optional[str] = None


@dataclass
class HybridSearchConfig:
    """Configuration for hybrid search."""
    vector_weight: float = 0.5
    text_weight: float = 0.5
    fusion_method: FusionMethod = FusionMethod.WEIGHTED_SUM
    min_vector_score: float = 0.0
    min_text_score: float = 0.0
    max_results: int = 100
    text_boost_factor: float = 1.0
    enable_reranking: bool = False
    snippet_length: int = 200


class HybridSearchService(LoggingMixin):
    """Service for hybrid vector + text search."""
    
    def __init__(self, deeplake_service: DeepLakeService):
        super().__init__()
        self.deeplake_service = deeplake_service
        self.embedding_service = get_embedding_service()
        
        # Text search index cache (in production, use proper text search engine)
        self._text_indexes: Dict[str, Dict[str, Any]] = {}
    
    async def hybrid_search(
        self,
        dataset_id: str,
        query_text: str,
        query_vector: Optional[List[float]] = None,
        options: Optional[SearchOptions] = None,
        vector_weight: float = 0.5,
        text_weight: float = 0.5,
        fusion_method: FusionMethod = FusionMethod.WEIGHTED_SUM,
        tenant_id: Optional[str] = None
    ) -> SearchResponse:
        """
        Perform hybrid search combining vector and text search.
        
        Args:
            dataset_id: Dataset to search in
            query_text: Text query for both vector embedding and text search
            query_vector: Optional pre-computed query vector
            options: Search options
            vector_weight: Weight for vector search results (0.0-1.0)
            text_weight: Weight for text search results (0.0-1.0)
            fusion_method: Method for combining results
            tenant_id: Tenant ID for multi-tenancy
        
        Returns:
            Combined search results
        """
        start_time = datetime.now()
        
        # Validate weights
        if abs(vector_weight + text_weight - 1.0) > 0.01:
            vector_weight = vector_weight / (vector_weight + text_weight)
            text_weight = 1.0 - vector_weight
        
        # Setup search options
        if options is None:
            options = SearchOptions()
        
        # Create hybrid search config
        config = HybridSearchConfig(
            vector_weight=vector_weight,
            text_weight=text_weight,
            fusion_method=fusion_method,
            max_results=options.top_k,
            enable_reranking=options.rerank
        )
        
        try:
            # Perform vector search and text search in parallel
            vector_results, text_results = await asyncio.gather(
                self._vector_search(dataset_id, query_text, query_vector, options, tenant_id),
                self._text_search(dataset_id, query_text, options, tenant_id),
                return_exceptions=True
            )
            
            # Handle potential exceptions
            if isinstance(vector_results, Exception):
                self.logger.error(f"Vector search failed: {vector_results}")
                vector_results = []
            
            if isinstance(text_results, Exception):
                self.logger.error(f"Text search failed: {text_results}")
                text_results = []
            
            # Combine results using specified fusion method
            combined_results = await self._fuse_results(
                vector_results, text_results, config
            )
            
            # Apply final filtering and ranking
            final_results = await self._post_process_results(
                combined_results, query_text, config, options
            )
            
            # Calculate timing
            end_time = datetime.now()
            query_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Create search stats
            stats = SearchStats(
                vectors_scanned=len(vector_results) + len(text_results),
                index_hits=len(vector_results),
                filtered_results=len(final_results),
                database_time_ms=query_time_ms * 0.7,  # Estimated
                post_processing_time_ms=query_time_ms * 0.3
            )
            
            return SearchResponse(
                results=final_results[:options.top_k],
                total_found=len(final_results),
                has_more=len(final_results) > options.top_k,
                query_time_ms=query_time_ms,
                stats=stats
            )
            
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            raise
    
    async def _vector_search(
        self,
        dataset_id: str,
        query_text: str,
        query_vector: Optional[List[float]],
        options: SearchOptions,
        tenant_id: Optional[str]
    ) -> List[SearchResultItem]:
        """Perform vector similarity search."""
        try:
            # Generate vector if not provided
            if query_vector is None:
                query_vector = await self.embedding_service.text_to_vector(query_text)
            
            # Perform vector search
            from app.models.schemas import SearchRequest
            search_request = SearchRequest(
                query_vector=query_vector,
                options=options
            )
            
            results = await self.deeplake_service.search_vectors(
                dataset_id=dataset_id,
                search_request=search_request,
                tenant_id=tenant_id
            )
            
            return results.results
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return []
    
    async def _text_search(
        self,
        dataset_id: str,
        query_text: str,
        options: SearchOptions,
        tenant_id: Optional[str]
    ) -> List[TextSearchResult]:
        """Perform text-based search."""
        try:
            # Build or get text index for dataset
            index_key = f"{tenant_id}:{dataset_id}" if tenant_id else dataset_id
            
            if index_key not in self._text_indexes:
                await self._build_text_index(dataset_id, tenant_id)
            
            text_index = self._text_indexes.get(index_key, {})
            
            # Perform text search
            results = await self._search_text_index(text_index, query_text, options)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Text search failed: {e}")
            return []
    
    async def _build_text_index(
        self,
        dataset_id: str,
        tenant_id: Optional[str]
    ) -> None:
        """Build text search index for a dataset."""
        try:
            index_key = f"{tenant_id}:{dataset_id}" if tenant_id else dataset_id
            
            # Get all vectors from dataset
            vectors = await self.deeplake_service.list_vectors(
                dataset_id=dataset_id,
                tenant_id=tenant_id,
                limit=10000  # In production, implement pagination
            )
            
            # Build inverted index
            inverted_index = {}
            document_index = {}
            
            for vector in vectors:
                doc_id = vector.id
                
                # Index content
                if vector.content:
                    tokens = self._tokenize_text(vector.content)
                    for token in tokens:
                        if token not in inverted_index:
                            inverted_index[token] = set()
                        inverted_index[token].add(doc_id)
                
                # Store document info
                document_index[doc_id] = {
                    'content': vector.content or '',
                    'metadata': vector.metadata,
                    'chunk_id': vector.chunk_id,
                    'document_id': vector.document_id
                }
            
            # Store index
            self._text_indexes[index_key] = {
                'inverted_index': inverted_index,
                'document_index': document_index,
                'created_at': datetime.now()
            }
            
            self.logger.info(f"Built text index for {dataset_id}: {len(document_index)} documents, {len(inverted_index)} terms")
            
        except Exception as e:
            self.logger.error(f"Failed to build text index: {e}")
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Simple text tokenization."""
        # Convert to lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        
        # Filter out very short tokens
        tokens = [t for t in tokens if len(t) >= 2]
        
        return tokens
    
    async def _search_text_index(
        self,
        text_index: Dict[str, Any],
        query_text: str,
        options: SearchOptions
    ) -> List[TextSearchResult]:
        """Search the text index."""
        if not text_index:
            return []
        
        inverted_index = text_index.get('inverted_index', {})
        document_index = text_index.get('document_index', {})
        
        # Tokenize query
        query_tokens = self._tokenize_text(query_text)
        if not query_tokens:
            return []
        
        # Find matching documents
        doc_scores = {}
        doc_matches = {}
        
        for token in query_tokens:
            if token in inverted_index:
                matching_docs = inverted_index[token]
                for doc_id in matching_docs:
                    if doc_id not in doc_scores:
                        doc_scores[doc_id] = 0
                        doc_matches[doc_id] = []
                    
                    # Simple TF-IDF style scoring
                    tf = self._calculate_term_frequency(
                        token, document_index.get(doc_id, {}).get('content', '')
                    )
                    idf = np.log(len(document_index) / len(matching_docs))
                    score = tf * idf
                    
                    doc_scores[doc_id] += score
                    doc_matches[doc_id].append(token)
        
        # Convert to results and sort by score
        results = []
        for doc_id, score in doc_scores.items():
            if score > 0:
                snippet = self._generate_snippet(
                    document_index.get(doc_id, {}).get('content', ''),
                    query_tokens
                )
                
                results.append(TextSearchResult(
                    vector_id=doc_id,
                    score=score,
                    rank=0,  # Will be set later
                    matched_fields=['content'],
                    snippet=snippet
                ))
        
        # Sort by score and assign ranks
        results.sort(key=lambda x: x.score, reverse=True)
        for i, result in enumerate(results):
            result.rank = i + 1
        
        return results[:options.top_k * 2]  # Get more for fusion
    
    def _calculate_term_frequency(self, term: str, text: str) -> float:
        """Calculate term frequency in text."""
        tokens = self._tokenize_text(text)
        if not tokens:
            return 0.0
        
        count = tokens.count(term)
        return count / len(tokens)
    
    def _generate_snippet(self, text: str, query_tokens: List[str], max_length: int = 200) -> str:
        """Generate a snippet around query terms."""
        if not text or not query_tokens:
            return text[:max_length] + "..." if len(text) > max_length else text
        
        # Find first occurrence of any query token
        text_lower = text.lower()
        best_pos = len(text)
        
        for token in query_tokens:
            pos = text_lower.find(token.lower())
            if pos != -1 and pos < best_pos:
                best_pos = pos
        
        if best_pos == len(text):
            # No tokens found, return beginning
            return text[:max_length] + "..." if len(text) > max_length else text
        
        # Center snippet around found position
        start = max(0, best_pos - max_length // 2)
        end = min(len(text), start + max_length)
        
        snippet = text[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    async def _fuse_results(
        self,
        vector_results: List[SearchResultItem],
        text_results: List[TextSearchResult],
        config: HybridSearchConfig
    ) -> List[SearchResultItem]:
        """Fuse vector and text search results."""
        if config.fusion_method == FusionMethod.WEIGHTED_SUM:
            return await self._weighted_sum_fusion(vector_results, text_results, config)
        elif config.fusion_method == FusionMethod.RRF:
            return await self._rrf_fusion(vector_results, text_results, config)
        elif config.fusion_method == FusionMethod.CombSUM:
            return await self._combsum_fusion(vector_results, text_results, config)
        elif config.fusion_method == FusionMethod.CombMNZ:
            return await self._combmnz_fusion(vector_results, text_results, config)
        elif config.fusion_method == FusionMethod.BORDA_COUNT:
            return await self._borda_count_fusion(vector_results, text_results, config)
        else:
            # Default to weighted sum
            return await self._weighted_sum_fusion(vector_results, text_results, config)
    
    async def _weighted_sum_fusion(
        self,
        vector_results: List[SearchResultItem],
        text_results: List[TextSearchResult],
        config: HybridSearchConfig
    ) -> List[SearchResultItem]:
        """Combine results using weighted sum."""
        combined_scores = {}
        result_map = {}
        
        # Normalize vector scores (0-1)
        vector_scores = [r.score for r in vector_results]
        if vector_scores:
            max_vector_score = max(vector_scores)
            min_vector_score = min(vector_scores)
            score_range = max_vector_score - min_vector_score
            
            for result in vector_results:
                vector_id = result.vector.id
                normalized_score = ((result.score - min_vector_score) / score_range) if score_range > 0 else 1.0
                
                combined_scores[vector_id] = config.vector_weight * normalized_score
                result_map[vector_id] = result
        
        # Normalize text scores (0-1)
        text_scores = [r.score for r in text_results]
        if text_scores:
            max_text_score = max(text_scores)
            min_text_score = min(text_scores)
            score_range = max_text_score - min_text_score
            
            for result in text_results:
                vector_id = result.vector_id
                normalized_score = ((result.score - min_text_score) / score_range) if score_range > 0 else 1.0
                
                if vector_id in combined_scores:
                    combined_scores[vector_id] += config.text_weight * normalized_score
                else:
                    combined_scores[vector_id] = config.text_weight * normalized_score
                    # Need to get vector info for text-only results
                    # In production, cache this or get in batch
        
        # Sort by combined score
        sorted_items = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Create final results
        final_results = []
        for i, (vector_id, score) in enumerate(sorted_items):
            if vector_id in result_map:
                result = result_map[vector_id]
                # Update score and rank
                result.score = score
                result.rank = i + 1
                final_results.append(result)
        
        return final_results
    
    async def _rrf_fusion(
        self,
        vector_results: List[SearchResultItem],
        text_results: List[TextSearchResult],
        config: HybridSearchConfig
    ) -> List[SearchResultItem]:
        """Reciprocal Rank Fusion (RRF)."""
        k = 60  # RRF parameter
        rrf_scores = {}
        result_map = {}
        
        # Calculate RRF scores from vector results
        for i, result in enumerate(vector_results):
            vector_id = result.vector.id
            rrf_scores[vector_id] = config.vector_weight / (k + i + 1)
            result_map[vector_id] = result
        
        # Add RRF scores from text results
        for i, result in enumerate(text_results):
            vector_id = result.vector_id
            if vector_id in rrf_scores:
                rrf_scores[vector_id] += config.text_weight / (k + i + 1)
            else:
                rrf_scores[vector_id] = config.text_weight / (k + i + 1)
        
        # Sort by RRF score
        sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Create final results
        final_results = []
        for i, (vector_id, score) in enumerate(sorted_items):
            if vector_id in result_map:
                result = result_map[vector_id]
                result.score = score
                result.rank = i + 1
                final_results.append(result)
        
        return final_results
    
    async def _combsum_fusion(
        self,
        vector_results: List[SearchResultItem],
        text_results: List[TextSearchResult],
        config: HybridSearchConfig
    ) -> List[SearchResultItem]:
        """CombSUM fusion algorithm."""
        # Similar to weighted sum but without normalization
        combined_scores = {}
        result_map = {}
        
        for result in vector_results:
            vector_id = result.vector.id
            combined_scores[vector_id] = config.vector_weight * result.score
            result_map[vector_id] = result
        
        for result in text_results:
            vector_id = result.vector_id
            if vector_id in combined_scores:
                combined_scores[vector_id] += config.text_weight * result.score
            else:
                combined_scores[vector_id] = config.text_weight * result.score
        
        # Sort and return
        sorted_items = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        final_results = []
        for i, (vector_id, score) in enumerate(sorted_items):
            if vector_id in result_map:
                result = result_map[vector_id]
                result.score = score
                result.rank = i + 1
                final_results.append(result)
        
        return final_results
    
    async def _combmnz_fusion(
        self,
        vector_results: List[SearchResultItem],
        text_results: List[TextSearchResult],
        config: HybridSearchConfig
    ) -> List[SearchResultItem]:
        """CombMNZ fusion algorithm."""
        # CombSUM multiplied by number of non-zero scores
        combined_scores = {}
        result_map = {}
        non_zero_counts = {}
        
        for result in vector_results:
            vector_id = result.vector.id
            if result.score > 0:
                combined_scores[vector_id] = config.vector_weight * result.score
                non_zero_counts[vector_id] = 1
                result_map[vector_id] = result
        
        for result in text_results:
            vector_id = result.vector_id
            if result.score > 0:
                if vector_id in combined_scores:
                    combined_scores[vector_id] += config.text_weight * result.score
                    non_zero_counts[vector_id] += 1
                else:
                    combined_scores[vector_id] = config.text_weight * result.score
                    non_zero_counts[vector_id] = 1
        
        # Multiply by number of non-zero scores
        for vector_id in combined_scores:
            combined_scores[vector_id] *= non_zero_counts[vector_id]
        
        # Sort and return
        sorted_items = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        final_results = []
        for i, (vector_id, score) in enumerate(sorted_items):
            if vector_id in result_map:
                result = result_map[vector_id]
                result.score = score
                result.rank = i + 1
                final_results.append(result)
        
        return final_results
    
    async def _borda_count_fusion(
        self,
        vector_results: List[SearchResultItem],
        text_results: List[TextSearchResult],
        config: HybridSearchConfig
    ) -> List[SearchResultItem]:
        """Borda count voting fusion."""
        borda_scores = {}
        result_map = {}
        
        # Assign Borda points from vector results
        for i, result in enumerate(vector_results):
            vector_id = result.vector.id
            points = len(vector_results) - i
            borda_scores[vector_id] = config.vector_weight * points
            result_map[vector_id] = result
        
        # Add Borda points from text results
        for i, result in enumerate(text_results):
            vector_id = result.vector_id
            points = len(text_results) - i
            if vector_id in borda_scores:
                borda_scores[vector_id] += config.text_weight * points
            else:
                borda_scores[vector_id] = config.text_weight * points
        
        # Sort by Borda score
        sorted_items = sorted(borda_scores.items(), key=lambda x: x[1], reverse=True)
        
        final_results = []
        for i, (vector_id, score) in enumerate(sorted_items):
            if vector_id in result_map:
                result = result_map[vector_id]
                result.score = score
                result.rank = i + 1
                final_results.append(result)
        
        return final_results
    
    async def _post_process_results(
        self,
        results: List[SearchResultItem],
        query_text: str,
        config: HybridSearchConfig,
        options: SearchOptions
    ) -> List[SearchResultItem]:
        """Post-process and rerank results."""
        if not results:
            return results
        
        # Apply filters
        if options.filters:
            # Import here to avoid circular imports
            from app.services.metadata_filter import metadata_filter_service
            
            try:
                filter_expr = metadata_filter_service.parse_filter_expression(options.filters)
                filtered_results = []
                
                for result in results:
                    if metadata_filter_service.apply_filter(result.vector.metadata, filter_expr):
                        filtered_results.append(result)
                
                results = filtered_results
            except Exception as e:
                self.logger.error(f"Error applying filters: {e}")
        
        # Apply reranking if enabled
        if config.enable_reranking and len(results) > 1:
            results = await self._rerank_results(results, query_text)
        
        # Apply thresholds
        if options.threshold:
            results = [r for r in results if r.score >= options.threshold]
        
        # Limit results
        return results[:config.max_results]
    
    async def _rerank_results(
        self,
        results: List[SearchResultItem],
        query_text: str
    ) -> List[SearchResultItem]:
        """Rerank results using additional signals."""
        # Simple reranking based on content relevance
        # In production, could use a dedicated reranking model
        
        query_tokens = set(self._tokenize_text(query_text))
        
        for result in results:
            content = result.vector.content or ""
            content_tokens = set(self._tokenize_text(content))
            
            # Calculate token overlap
            overlap = len(query_tokens.intersection(content_tokens))
            overlap_ratio = overlap / len(query_tokens) if query_tokens else 0
            
            # Boost score based on token overlap
            boost = 1.0 + (overlap_ratio * 0.1)  # Small boost for token overlap
            result.score *= boost
        
        # Re-sort by adjusted scores
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Update ranks
        for i, result in enumerate(results):
            result.rank = i + 1
        
        return results