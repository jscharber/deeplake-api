"""Dataset management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.api.http.dependencies import (
    get_deeplake_service, get_current_tenant, authorize_operation,
    get_pagination_params, PaginationParams, validate_dataset_access,
    get_cache_manager, get_metrics_service
)
from app.services.deeplake_service import DeepLakeService
from app.services.cache_service import CacheManager
from app.services.metrics_service import MetricsService
from app.models.schemas import (
    DatasetCreate, DatasetUpdate, DatasetResponse, DatasetStats, 
    BaseResponse, ErrorResponse
)
from app.models.exceptions import (
    DatasetNotFoundException, DatasetAlreadyExistsException, 
    DeepLakeServiceException
)


router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    dataset_create: DatasetCreate,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("create_dataset"))
) -> DatasetResponse:
    """Create a new dataset."""
    
    import time
    start_time = time.time()
    
    try:
        # Create dataset
        dataset = await deeplake_service.create_dataset(dataset_create, tenant_id)
        
        # Update metrics
        duration = time.time() - start_time
        metrics_service.record_dataset_operation("create", "success", duration, tenant_id)
        metrics_service.update_dataset_count(
            len(await deeplake_service.list_datasets(tenant_id)), 
            tenant_id
        )
        
        # Cache dataset info
        await cache_manager.cache_dataset_info(
            dataset.id, 
            dataset.model_dump(), 
            tenant_id
        )
        
        return dataset
        
    except DatasetAlreadyExistsException as e:
        metrics_service.record_dataset_operation("create", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error("dataset_already_exists", "create_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except DeepLakeServiceException as e:
        metrics_service.record_dataset_operation("create", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error(e.error_code or "unknown", "create_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_dataset_operation("create", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error("internal_error", "create_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/", response_model=List[DatasetResponse])
async def list_datasets(
    pagination: PaginationParams = Depends(get_pagination_params),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("list_datasets"))
) -> List[DatasetResponse]:
    """List all datasets for the current tenant."""
    
    import time
    start_time = time.time()
    
    try:
        datasets = await deeplake_service.list_datasets(
            tenant_id=tenant_id,
            limit=pagination.limit,
            offset=pagination.offset
        )
        
        # Update metrics
        duration = time.time() - start_time
        metrics_service.record_dataset_operation("list", "success", duration, tenant_id)
        
        return datasets
        
    except DeepLakeServiceException as e:
        metrics_service.record_dataset_operation("list", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error(e.error_code or "unknown", "list_datasets", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_dataset_operation("list", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error("internal_error", "list_datasets", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("read_dataset"))
) -> DatasetResponse:
    """Get dataset information."""
    
    import time
    start_time = time.time()
    
    try:
        # Try to get from cache first
        cached_info = await cache_manager.get_dataset_info(dataset_id, tenant_id)
        if cached_info:
            metrics_service.record_cache_operation("get", "hit")
            return DatasetResponse(**cached_info)
        
        metrics_service.record_cache_operation("get", "miss")
        
        # Get from service
        dataset = await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # Cache the result
        await cache_manager.cache_dataset_info(dataset_id, dataset.model_dump(), tenant_id)
        
        # Update metrics
        duration = time.time() - start_time
        metrics_service.record_dataset_operation("get", "success", duration, tenant_id)
        
        return dataset
        
    except DatasetNotFoundException as e:
        metrics_service.record_dataset_operation("get", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error("dataset_not_found", "get_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DeepLakeServiceException as e:
        metrics_service.record_dataset_operation("get", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error(e.error_code or "unknown", "get_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_dataset_operation("get", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error("internal_error", "get_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: str,
    dataset_update: DatasetUpdate,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("update_dataset"))
) -> DatasetResponse:
    """Update dataset information."""
    
    import time
    start_time = time.time()
    
    try:
        # First, verify dataset exists
        await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # For now, we'll just return the current dataset since Deep Lake
        # doesn't support metadata updates in this implementation
        # In a full implementation, you would update the dataset metadata
        dataset = await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # Update cache
        await cache_manager.cache_dataset_info(dataset_id, dataset.model_dump(), tenant_id)
        
        # Update metrics
        duration = time.time() - start_time
        metrics_service.record_dataset_operation("update", "success", duration, tenant_id)
        
        return dataset
        
    except DatasetNotFoundException as e:
        metrics_service.record_dataset_operation("update", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error("dataset_not_found", "update_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DeepLakeServiceException as e:
        metrics_service.record_dataset_operation("update", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error(e.error_code or "unknown", "update_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_dataset_operation("update", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error("internal_error", "update_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{dataset_id}", response_model=BaseResponse)
async def delete_dataset(
    dataset_id: str,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("delete_dataset"))
) -> BaseResponse:
    """Delete a dataset."""
    
    import time
    start_time = time.time()
    
    try:
        # Delete dataset
        await deeplake_service.delete_dataset(dataset_id, tenant_id)
        
        # Invalidate cache
        await cache_manager.invalidate_dataset_cache(dataset_id, tenant_id)
        
        # Update metrics
        duration = time.time() - start_time
        metrics_service.record_dataset_operation("delete", "success", duration, tenant_id)
        metrics_service.update_dataset_count(
            len(await deeplake_service.list_datasets(tenant_id)), 
            tenant_id
        )
        
        return BaseResponse(
            success=True,
            message=f"Dataset '{dataset_id}' deleted successfully"
        )
        
    except DatasetNotFoundException as e:
        metrics_service.record_dataset_operation("delete", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error("dataset_not_found", "delete_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DeepLakeServiceException as e:
        metrics_service.record_dataset_operation("delete", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error(e.error_code or "unknown", "delete_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_dataset_operation("delete", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error("internal_error", "delete_dataset", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{dataset_id}/stats", response_model=DatasetStats)
async def get_dataset_stats(
    dataset_id: str,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("get_stats"))
) -> DatasetStats:
    """Get detailed dataset statistics."""
    
    import time
    start_time = time.time()
    
    try:
        # Get dataset info
        dataset = await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # Create stats response
        stats = DatasetStats(
            dataset=dataset,
            vector_count=dataset.vector_count,
            storage_size=dataset.storage_size,
            metadata_stats={},  # Could be enhanced to analyze metadata
        )
        
        # Update metrics
        duration = time.time() - start_time
        metrics_service.record_dataset_operation("get_stats", "success", duration, tenant_id)
        
        return stats
        
    except DatasetNotFoundException as e:
        metrics_service.record_dataset_operation("get_stats", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error("dataset_not_found", "get_dataset_stats", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DeepLakeServiceException as e:
        metrics_service.record_dataset_operation("get_stats", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error(e.error_code or "unknown", "get_dataset_stats", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        metrics_service.record_dataset_operation("get_stats", "failed", time.time() - start_time, tenant_id)
        metrics_service.record_error("internal_error", "get_dataset_stats", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )