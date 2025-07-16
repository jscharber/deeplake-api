"""Vector search endpoints."""

import hashlib
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Path

from app.api.http.dependencies import (
    get_deeplake_service, get_current_tenant, authorize_operation,
    validate_dataset_access, get_cache_manager, get_metrics_service
)
from app.services.deeplake_service import DeepLakeService
from app.services.cache_service import CacheManager
from app.services.metrics_service import MetricsService
from app.models.schemas import (
    SearchRequest, TextSearchRequest, HybridSearchRequest, SearchResponse, SearchOptions
)
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
        # Validate dataset access
        await validate_dataset_access(dataset_id, tenant_id, deeplake_service)
        
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
    auth_info: dict = Depends(authorize_operation("search_vectors"))
) -> SearchResponse:
    """Search for similar vectors using text query (requires embedding model)."""
    
    start_time = time.time()
    
    try:
        # Validate dataset access
        await validate_dataset_access(dataset_id, tenant_id, deeplake_service)
        
        # Note: This is a simplified implementation
        # In a full implementation, you would:
        # 1. Use an embedding model to convert text to vector
        # 2. Perform vector search with the generated embedding
        
        # For now, we'll return an error indicating this feature needs an embedding service
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Text search requires an embedding service integration"
        )
        
    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "search_by_text", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_error("internal_error", "search_by_text", tenant_id)
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
    """Perform hybrid search combining vector and text search."""
    
    start_time = time.time()
    
    try:
        # Validate dataset access
        await validate_dataset_access(dataset_id, tenant_id, deeplake_service)
        
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
        
        # For now, if only vector search is provided, delegate to vector search
        if search_request.query_vector and not search_request.query_text:
            from app.models.schemas import SearchRequest
            vector_search = SearchRequest(
                query_vector=search_request.query_vector,
                options=search_request.options
            )
            result: SearchResponse = await search_vectors(vector_search, dataset_id, tenant_id, deeplake_service, cache_manager, metrics_service, auth_info)
            return result
        
        # Otherwise return not implemented
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Hybrid search requires additional implementation for text embedding and result fusion"
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
            await validate_dataset_access(dataset_id, tenant_id, deeplake_service)
        
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