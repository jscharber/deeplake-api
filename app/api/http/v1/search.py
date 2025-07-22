"""Vector search endpoints."""

import hashlib
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Path
import structlog

logger = structlog.get_logger(__name__)

from app.api.http.dependencies import (
    get_deeplake_service, get_current_tenant, authorize_operation,
    validate_dataset_access, get_cache_manager, get_metrics_service,
    get_embedding_service_dep
)
from app.services.deeplake_service import DeepLakeService
from app.services.cache_service import CacheManager
from app.services.metrics_service import MetricsService
from app.services.embedding_service import EmbeddingService
from app.models.schemas import (
    SearchRequest, TextSearchRequest, HybridSearchRequest, SearchResponse, SearchOptions
)
from app.config.settings import settings
from app.services.hybrid_search_service import HybridSearchService, FusionMethod
from app.models.exceptions import (
    DatasetNotFoundException, InvalidVectorDimensionsException,
    InvalidSearchParametersException, DeepLakeServiceException
)


router = APIRouter(tags=["search"])


def _hash_query(data: str) -> str:
    """Create a hash for caching query results."""
    return hashlib.sha256(data.encode()).hexdigest()[:16]


@router.post("/datasets/{dataset_id}/search", response_model=SearchResponse)
async def search_vectors(
    search_request: SearchRequest,
    dataset_id: str = Path(..., description="Dataset ID"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("search_vectors"))
) -> SearchResponse:
    """Search for similar vectors using vector similarity."""
    
    start_time = time.time()
    
    try:
        # Validate dataset exists and tenant has access
        await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # Create cache keys
        query_hash = _hash_query(str(search_request.query_vector))
        options_hash = _hash_query(search_request.options.model_dump_json() if search_request.options else "{}")
        
        # Try to get cached results
        cached_results = await cache_manager.get_search_results(
            dataset_id, query_hash, options_hash, tenant_id
        )
        
        if cached_results:
            metrics_service.record_cache_operation("get", "hit")
            metrics_service.record_search_query(
                dataset_id, "vector", time.time() - start_time, 
                len(cached_results), 0, tenant_id
            )
            return SearchResponse.model_validate(cached_results)
        
        metrics_service.record_cache_operation("get", "miss")
        
        # Perform search
        search_response = await deeplake_service.search_vectors(
            dataset_id=dataset_id,
            query_vector=search_request.query_vector,
            options=search_request.options or SearchOptions(),  # type: ignore[call-arg]
            tenant_id=tenant_id
        )
        
        # Cache the results
        await cache_manager.cache_search_results(
            dataset_id, query_hash, options_hash, 
            [search_response.model_dump()], tenant_id
        )
        
        # Update metrics
        query_time = time.time() - start_time
        metrics_service.record_search_query(
            dataset_id, "vector", query_time,
            len(search_response.results),
            search_response.stats.vectors_scanned,
            tenant_id
        )
        
        return search_response
        
    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "search_vectors", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidVectorDimensionsException as e:
        metrics_service.record_error("invalid_dimensions", "search_vectors", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except InvalidSearchParametersException as e:
        metrics_service.record_error("invalid_search_params", "search_vectors", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DeepLakeServiceException as e:
        metrics_service.record_error(e.error_code or "unknown", "search_vectors", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_error("internal_error", "search_vectors", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/datasets/{dataset_id}/search/text", response_model=SearchResponse)
async def search_by_text(
    search_request: TextSearchRequest,
    dataset_id: str = Path(..., description="Dataset ID"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service_dep),
    auth_info: dict = Depends(authorize_operation("search_vectors"))
) -> SearchResponse:
    """Search for similar vectors using text query (converts text to embeddings)."""
    
    start_time = time.time()
    
    try:
        # Get dataset information and validate access
        dataset = await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # Check if embedding service is compatible with dataset dimensions
        if not await embedding_service.validate_compatibility(dataset.dimensions):
            embedding_dims = embedding_service.get_embedding_dimensions()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Embedding dimensions ({embedding_dims}) don't match dataset dimensions ({dataset.dimensions})"
            )
        
        # Convert text to embedding vector
        try:
            query_vector = await embedding_service.text_to_vector(search_request.query_text)
        except Exception as e:
            metrics_service.record_error("embedding_failed", "search_by_text", tenant_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to generate embedding: {e}"
            )
        
        # Create cache keys for text search
        text_hash = _hash_query(search_request.query_text)
        options_hash = _hash_query(search_request.options.model_dump_json() if search_request.options else "{}")
        
        # Try to get cached results
        cached_results = await cache_manager.get_search_results(
            dataset_id, text_hash, options_hash, tenant_id
        )
        
        if cached_results:
            metrics_service.record_cache_operation("get", "hit")
            metrics_service.record_search_query(
                dataset_id, "text", time.time() - start_time, 
                len(cached_results), 0, tenant_id
            )
            return SearchResponse.model_validate(cached_results)
        
        metrics_service.record_cache_operation("get", "miss")
        
        # Perform vector search with the generated embedding
        search_response = await deeplake_service.search_vectors(
            dataset_id=dataset_id,
            query_vector=query_vector,
            options=search_request.options or SearchOptions(),  # type: ignore[call-arg]
            tenant_id=tenant_id
        )
        
        # Cache the results
        await cache_manager.cache_search_results(
            dataset_id, text_hash, options_hash, 
            [search_response.model_dump()], tenant_id
        )
        
        # Update metrics
        query_time = time.time() - start_time
        metrics_service.record_search_query(
            dataset_id, "text", query_time,
            len(search_response.results),
            search_response.stats.vectors_scanned,
            tenant_id
        )
        
        return search_response
        
    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "search_by_text", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidVectorDimensionsException as e:
        metrics_service.record_error("invalid_dimensions", "search_by_text", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except InvalidSearchParametersException as e:
        metrics_service.record_error("invalid_search_params", "search_by_text", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DeepLakeServiceException as e:
        metrics_service.record_error(e.error_code or "unknown", "search_by_text", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        metrics_service.record_error("internal_error", "search_by_text", tenant_id)
        # Log the full error for debugging
        import traceback
        logger.error(
            "Text search failed with internal error",
            error=str(e),
            traceback=traceback.format_exc(),
            dataset_id=dataset_id,
            query_text=search_request.query_text[:100]
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text search failed: {str(e)}"
        )


@router.post("/datasets/{dataset_id}/search/hybrid", response_model=SearchResponse)
async def hybrid_search(
    search_request: HybridSearchRequest,
    dataset_id: str = Path(..., description="Dataset ID"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service_dep),
    auth_info: dict = Depends(authorize_operation("search_vectors"))
) -> SearchResponse:
    """Perform hybrid search combining vector and text search."""
    
    start_time = time.time()
    
    try:
        # Validate dataset exists and tenant has access
        await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # Validate that at least one search method is provided
        if not search_request.query_vector and not search_request.query_text:
            raise InvalidSearchParametersException(
                "Either query_vector or query_text must be provided",
                {"query_vector": search_request.query_vector, "query_text": search_request.query_text}
            )
        
        # Note: This is a simplified implementation
        # In a full implementation, you would:
        # 1. Perform vector search if query_vector is provided
        # 2. Perform text search if query_text is provided (after embedding)
        # 3. Combine results using the specified weights
        # 4. Re-rank and return merged results
        
        # Handle text-only search
        if search_request.query_text and not search_request.query_vector:
            from app.models.schemas import TextSearchRequest
            text_search = TextSearchRequest(
                query_text=search_request.query_text,
                options=search_request.options
            )
            result: SearchResponse = await search_by_text(text_search, dataset_id, tenant_id, deeplake_service, cache_manager, metrics_service, embedding_service, auth_info)
            return result
        
        # Handle vector-only search
        if search_request.query_vector and not search_request.query_text:
            from app.models.schemas import SearchRequest
            vector_search = SearchRequest(
                query_vector=search_request.query_vector,
                options=search_request.options
            )
            result: SearchResponse = await search_vectors(vector_search, dataset_id, tenant_id, deeplake_service, cache_manager, metrics_service, auth_info)
            return result
        
        # Handle true hybrid search (both vector and text)
        if search_request.query_vector and search_request.query_text:
            # Get dataset information to check dimensions
            dataset = await deeplake_service.get_dataset(dataset_id, tenant_id)
            
            # Validate text embedding compatibility
            if not await embedding_service.validate_compatibility(dataset.dimensions):
                embedding_dims = embedding_service.get_embedding_dimensions()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Embedding dimensions ({embedding_dims}) don't match dataset dimensions ({dataset.dimensions})"
                )
            
            # Convert text to embedding for hybrid search
            try:
                text_vector = await embedding_service.text_to_vector(search_request.query_text)
            except Exception as e:
                metrics_service.record_error("embedding_failed", "hybrid_search", tenant_id)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to generate text embedding: {e}"
                )
            
            # Combine vectors using weighted average
            combined_vector = []
            for i in range(len(search_request.query_vector)):
                combined_value = (
                    search_request.vector_weight * search_request.query_vector[i] +
                    search_request.text_weight * text_vector[i]
                )
                combined_vector.append(combined_value)
            
            # Perform search with combined vector
            search_response = await deeplake_service.search_vectors(
                dataset_id=dataset_id,
                query_vector=combined_vector,
                options=search_request.options or SearchOptions(),  # type: ignore[call-arg]
                tenant_id=tenant_id
            )
            
            # Update metrics
            query_time = time.time() - start_time
            metrics_service.record_search_query(
                dataset_id, "hybrid", query_time,
                len(search_response.results),
                search_response.stats.vectors_scanned,
                tenant_id
            )
            
            return search_response
        
        # This should not happen due to validation, but just in case
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either query_vector or query_text must be provided"
        )
        
    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "hybrid_search", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidSearchParametersException as e:
        metrics_service.record_error("invalid_search_params", "hybrid_search", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_error("internal_error", "hybrid_search", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/search/multi-dataset", response_model=SearchResponse)
async def multi_dataset_search(
    search_request: SearchRequest,
    dataset_ids: List[str],
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("search_vectors"))
) -> SearchResponse:
    """Search across multiple datasets and merge results."""
    
    start_time = time.time()
    
    try:
        # Validate access to all datasets
        for dataset_id in dataset_ids:
            await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # Note: This is a simplified implementation
        # In a full implementation, you would:
        # 1. Perform search on each dataset
        # 2. Merge and re-rank results
        # 3. Apply the requested top_k limit
        
        # For now, just search the first dataset
        if dataset_ids:
            first_dataset = dataset_ids[0]
            result: SearchResponse = await search_vectors(
                search_request, first_dataset, tenant_id, 
                deeplake_service, cache_manager, metrics_service, auth_info
            )
            
            # Update metrics for multi-dataset search
            query_time = time.time() - start_time
            metrics_service.record_search_query(
                "multi-dataset", "vector", query_time,
                len(result.results), result.stats.vectors_scanned, tenant_id
            )
            
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one dataset ID must be provided"
            )
        
    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "multi_dataset_search", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_error("internal_error", "multi_dataset_search", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/datasets/{dataset_id}/search/hybrid", response_model=SearchResponse)
async def hybrid_search(
    search_request: HybridSearchRequest,
    dataset_id: str = Path(..., description="Dataset ID"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("search_vectors"))
) -> SearchResponse:
    """
    Perform hybrid search combining vector similarity and text search.
    
    Hybrid search combines the strengths of both vector similarity search 
    (semantic understanding) and text search (keyword matching) to provide 
    more comprehensive and accurate search results.
    """
    
    start_time = time.time()
    
    try:
        # Validate dataset exists and tenant has access
        await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # Validate that we have either query_text or query_vector
        if not search_request.query_text and not search_request.query_vector:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either query_text or query_vector must be provided"
            )
        
        # Set default options if not provided
        options = search_request.options or SearchOptions()
        
        # Create cache key for hybrid search
        cache_key = None
        if search_request.query_text:
            query_data = f"{dataset_id}:{search_request.query_text}:{search_request.vector_weight}:{search_request.text_weight}"
            if options.filters:
                query_data += f":{str(options.filters)}"
            cache_key = _hash_query(query_data)
        
        # Try to get from cache
        cached_result = None
        if cache_key:
            try:
                cached_result = await cache_manager.get(f"hybrid_search:{cache_key}")
                if cached_result:
                    logger.info("Cache hit for hybrid search", cache_key=cache_key)
                    metrics_service.record_cache_operation("get", "hit")
                    return cached_result
            except Exception as e:
                logger.warning("Cache get failed", error=str(e))
                metrics_service.record_cache_operation("get", "error")
        
        # Initialize hybrid search service
        hybrid_service = HybridSearchService(deeplake_service)
        
        # Map fusion method from string to enum
        fusion_method = FusionMethod.WEIGHTED_SUM  # default
        if hasattr(search_request, 'fusion_method') and search_request.fusion_method:
            try:
                fusion_method = FusionMethod(search_request.fusion_method)
            except ValueError:
                logger.warning(f"Invalid fusion method: {search_request.fusion_method}, using default")
        
        # Perform hybrid search
        result = await hybrid_service.hybrid_search(
            dataset_id=dataset_id,
            query_text=search_request.query_text or "",
            query_vector=search_request.query_vector,
            options=options,
            vector_weight=search_request.vector_weight,
            text_weight=search_request.text_weight,
            fusion_method=fusion_method,
            tenant_id=tenant_id
        )
        
        # Cache the result
        if cache_key and result:
            try:
                await cache_manager.set(f"hybrid_search:{cache_key}", result, ttl=settings.redis.search_cache_ttl)
                logger.info("Cached hybrid search result", cache_key=cache_key)
                metrics_service.record_cache_operation("set", "success")
            except Exception as e:
                logger.warning("Cache set failed", error=str(e))
                metrics_service.record_cache_operation("set", "error")
        
        # Record metrics
        query_time = time.time() - start_time
        metrics_service.record_search_query(
            dataset_id, "hybrid", query_time,
            len(result.results), result.stats.vectors_scanned, tenant_id
        )
        
        logger.info(
            "Hybrid search completed",
            dataset_id=dataset_id,
            results_count=len(result.results),
            query_time_ms=result.query_time_ms,
            vector_weight=search_request.vector_weight,
            text_weight=search_request.text_weight,
            fusion_method=fusion_method.value,
            tenant_id=tenant_id
        )
        
        return result
        
    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "hybrid_search", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidSearchParametersException as e:
        metrics_service.record_error("invalid_parameters", "hybrid_search", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DeepLakeServiceException as e:
        metrics_service.record_error("service_error", "hybrid_search", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Hybrid search failed", error=str(e), dataset_id=dataset_id)
        metrics_service.record_error("internal_error", "hybrid_search", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )