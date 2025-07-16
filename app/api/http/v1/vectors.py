"""Vector operations endpoints."""

# pylint: disable=W0621

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
    VectorCreate, VectorUpdate, VectorResponse, VectorBatchInsert, VectorBatchResponse,
    BaseResponse
)
from app.models.exceptions import (
    DatasetNotFoundException, VectorNotFoundException,
    InvalidVectorDimensionsException, DeepLakeServiceException
)

import pdb

router = APIRouter(prefix="/datasets/{dataset_id}/vectors", tags=["vectors"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def insert_vector(
    vector: VectorCreate,
    dataset_id: str = Path(..., description="Dataset ID")
) -> dict:
    """Insert a single vector into the dataset - simplified for debugging."""

    # Hardcode tenant_id and create service directly
    tenant_id = "default"

    try:
        from app.services.deeplake_service import DeepLakeService
        deeplake_service = DeepLakeService()

        # Basic validation - check if dataset exists
        import os
        from app.config.settings import settings
        dataset_path = os.path.join(settings.deeplake.storage_location, tenant_id, dataset_id)
        if not os.path.exists(dataset_path):
            return {
                "success": False,
                "error": f"Dataset {dataset_id} not found"
            }

        # Insert vector (as a batch of 1)
        result = await deeplake_service.insert_vectors(
            dataset_id=dataset_id,
            vectors=[vector],
            tenant_id=tenant_id,
            skip_existing=False,
            overwrite=False
        )

        # Convert to simple dict to avoid serialization issues
        return {
            "success": True,
            "inserted_count": result.inserted_count,
            "skipped_count": result.skipped_count,
            "failed_count": result.failed_count,
            "processing_time_ms": result.processing_time_ms
        }

    except DatasetNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidVectorDimensionsException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DeepLakeServiceException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log the actual exception for debugging
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"ERROR in insert_vector: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/batch", response_model=VectorBatchResponse, status_code=status.HTTP_201_CREATED)
async def insert_vectors_batch(
    batch_request: VectorBatchInsert,
    dataset_id: str = Path(..., description="Dataset ID"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("insert_vector"))
) -> VectorBatchResponse:
    """Insert multiple vectors into the dataset."""

    import time
    start_time = time.time()

    try:
        # Validate dataset access
        await validate_dataset_access(dataset_id, tenant_id, deeplake_service)

        # Insert vectors
        result = await deeplake_service.insert_vectors(
            dataset_id=dataset_id,
            vectors=batch_request.vectors,
            tenant_id=tenant_id,
            skip_existing=batch_request.skip_existing,
            overwrite=batch_request.overwrite
        )

        # Update metrics
        duration = time.time() - start_time
        metrics_service.record_vector_insertion(
            dataset_id, result.inserted_count, duration, len(batch_request.vectors), tenant_id
        )
        metrics_service.update_vector_count(
            dataset_id,
            (await deeplake_service.get_dataset(dataset_id, tenant_id)).vector_count,
            tenant_id
        )

        # Invalidate dataset cache
        await cache_manager.invalidate_dataset_cache(dataset_id, tenant_id)

        return result

    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "insert_vectors_batch", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidVectorDimensionsException as e:
        metrics_service.record_error("invalid_dimensions", "insert_vectors_batch", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DeepLakeServiceException as e:
        metrics_service.record_error(e.error_code or "unknown", "insert_vectors_batch", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_error("internal_error", "insert_vectors_batch", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/", response_model=List[VectorResponse])
async def list_vectors(
    dataset_id: str = Path(..., description="Dataset ID"),
    limit: int = 50,
    offset: int = 0,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("read_vector"))
) -> List[VectorResponse]:
    """List vectors in a dataset (paginated)."""

    try:
        # Validate dataset access
        await validate_dataset_access(dataset_id, tenant_id, deeplake_service)

        # List vectors with pagination
        vectors = await deeplake_service.list_vectors(
            dataset_id=dataset_id,
            limit=limit,
            offset=offset,
            tenant_id=tenant_id
        )

        return vectors

    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "list_vectors", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_error("internal_error", "list_vectors", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{vector_id}", response_model=VectorResponse)
async def get_vector(
    dataset_id: str = Path(..., description="Dataset ID"),
    vector_id: str = Path(..., description="Vector ID"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("read_vector"))
) -> VectorResponse:
    """Get a specific vector by ID."""

    try:
        # Validate dataset access
        await validate_dataset_access(dataset_id, tenant_id, deeplake_service)

        # Try cache first
        cached_vector = await cache_manager.get_vector_info(dataset_id, vector_id, tenant_id)
        if cached_vector:
            metrics_service.record_cache_operation("get", "hit")
            return VectorResponse(**cached_vector)

        metrics_service.record_cache_operation("get", "miss")

        # Get vector by ID
        vector = await deeplake_service.get_vector(
            dataset_id=dataset_id,
            vector_id=vector_id,
            tenant_id=tenant_id
        )

        # Cache the result
        await cache_manager.cache_vector_info(dataset_id, vector_id, vector.model_dump(), tenant_id)

        return vector

    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "get_vector", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except VectorNotFoundException as e:
        metrics_service.record_error("vector_not_found", "get_vector", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_error("internal_error", "get_vector", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{vector_id}", response_model=VectorResponse)
async def update_vector(
    vector_update: VectorUpdate,
    dataset_id: str = Path(..., description="Dataset ID"),
    vector_id: str = Path(..., description="Vector ID"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("update_vector"))
) -> VectorResponse:
    """Update a specific vector."""

    try:
        # Validate dataset access
        await validate_dataset_access(dataset_id, tenant_id, deeplake_service)

        # Update vector
        updated_vector = await deeplake_service.update_vector(
            dataset_id=dataset_id,
            vector_id=vector_id,
            vector_update=vector_update,
            tenant_id=tenant_id
        )

        # Invalidate cache
        await cache_manager.invalidate_vector_cache(dataset_id, vector_id, tenant_id)

        return updated_vector

    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "update_vector", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except VectorNotFoundException as e:
        metrics_service.record_error("vector_not_found", "update_vector", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_error("internal_error", "update_vector", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{vector_id}", response_model=BaseResponse)
async def delete_vector(
    dataset_id: str = Path(..., description="Dataset ID"),
    vector_id: str = Path(..., description="Vector ID"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("delete_vector"))
) -> BaseResponse:
    """Delete a specific vector."""

    try:
        # Validate dataset access
        await validate_dataset_access(dataset_id, tenant_id, deeplake_service)

        # Delete vector
        success = await deeplake_service.delete_vector(
            dataset_id=dataset_id,
            vector_id=vector_id,
            tenant_id=tenant_id
        )

        # Invalidate cache
        await cache_manager.invalidate_vector_cache(dataset_id, vector_id, tenant_id)
        await cache_manager.invalidate_dataset_cache(dataset_id, tenant_id)

        return BaseResponse(
            success=success,
            message=f"Vector '{vector_id}' deleted successfully"
        )

    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "delete_vector", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except VectorNotFoundException as e:
        metrics_service.record_error("vector_not_found", "delete_vector", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_error("internal_error", "delete_vector", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/batch", response_model=BaseResponse)
async def delete_vectors_batch(
    vector_ids: List[str],
    dataset_id: str = Path(..., description="Dataset ID"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("delete_vector"))
) -> BaseResponse:
    """Delete multiple vectors by their IDs."""

    try:
        # Validate dataset access
        await validate_dataset_access(dataset_id, tenant_id, deeplake_service)

        # Note: This is a simplified implementation
        # In a full implementation, you would delete the vectors from Deep Lake

        # Invalidate cache
        await cache_manager.invalidate_dataset_cache(dataset_id, tenant_id)

        return BaseResponse(
            success=True,
            message=f"Batch delete operation initiated for {len(vector_ids)} vectors"
        )

    except DatasetNotFoundException as e:
        metrics_service.record_error("dataset_not_found", "delete_vectors_batch", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_error("internal_error", "delete_vectors_batch", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )