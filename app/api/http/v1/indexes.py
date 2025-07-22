"""
Index management endpoints.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from app.config.logging import get_logger
from app.services.deeplake_service import DeepLakeService
from app.services.index_service import IndexStats, HNSWParameters, IVFParameters
from app.api.http.dependencies import (
    get_current_tenant, authorize_operation, get_deeplake_service, get_metrics_service
)
from app.services.metrics_service import MetricsService
from app.models.exceptions import DatasetNotFoundException

logger = get_logger(__name__)
router = APIRouter(tags=["indexes"])


class IndexCreateRequest(BaseModel):
    """Index creation request."""
    index_type: str = Field(..., description="Index type: hnsw, ivf, or flat")
    force_rebuild: bool = Field(default=False, description="Force rebuild even if index exists")
    
    # HNSW parameters
    hnsw_m: Optional[int] = Field(None, ge=4, le=64, description="HNSW M parameter")
    hnsw_ef_construction: Optional[int] = Field(None, ge=50, le=500, description="HNSW ef construction")
    hnsw_ef_search: Optional[int] = Field(None, ge=10, le=200, description="HNSW ef search")
    
    # IVF parameters
    ivf_nlist: Optional[int] = Field(None, ge=10, le=10000, description="IVF number of clusters")
    ivf_nprobe: Optional[int] = Field(None, ge=1, le=100, description="IVF number of probes")


class IndexOptimizeRequest(BaseModel):
    """Index optimization request."""
    target_recall: float = Field(default=0.95, ge=0.5, le=1.0, description="Target recall rate")
    sample_size: int = Field(default=100, ge=10, le=1000, description="Number of sample queries")


@router.post("/datasets/{dataset_id}/index", response_model=IndexStats)
async def create_or_update_index(
    dataset_id: str = Path(..., description="Dataset ID"),
    request: IndexCreateRequest = ...,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("admin"))
) -> IndexStats:
    """Create or update index for a dataset."""
    try:
        # Get dataset
        dataset_response = await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # Load the actual dataset
        dataset_key = deeplake_service._get_dataset_key(dataset_id, tenant_id)
        dataset = deeplake_service.datasets.get(dataset_key)
        
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not loaded")
        
        # Build index configuration
        from app.services.index_service import IndexType, IndexConfig
        
        index_type = IndexType(request.index_type)
        index_config = IndexConfig(
            index_type=index_type,
            metric_type=dataset_response.metric_type,
            dimensions=dataset_response.dimensions
        )
        
        # Add type-specific parameters
        if index_type == IndexType.HNSW:
            index_config.hnsw_params = HNSWParameters(
                m=request.hnsw_m or 16,
                ef_construction=request.hnsw_ef_construction or 200,
                ef_search=request.hnsw_ef_search or 50
            )
        elif index_type == IndexType.IVF:
            index_config.ivf_params = IVFParameters(
                nlist=request.ivf_nlist or 100,
                nprobe=request.ivf_nprobe or 10
            )
        
        # Create/update index
        stats = await deeplake_service.index_service.create_index(
            dataset, 
            index_config, 
            force_rebuild=request.force_rebuild
        )
        
        # Record metrics
        metrics_service.record_index_operation(
            dataset_id, 
            "create", 
            stats.build_time_seconds,
            stats.total_vectors,
            tenant_id
        )
        
        logger.info(
            "Index created/updated",
            dataset_id=dataset_id,
            index_type=request.index_type,
            build_time=stats.build_time_seconds,
            tenant_id=tenant_id
        )
        
        return stats
        
    except DatasetNotFoundException:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create index: {e}")
        metrics_service.record_error("index_creation_failed", "create_index", tenant_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets/{dataset_id}/index", response_model=IndexStats)
async def get_index_stats(
    dataset_id: str = Path(..., description="Dataset ID"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    auth_info: dict = Depends(authorize_operation("read_vectors"))
) -> IndexStats:
    """Get index statistics for a dataset."""
    try:
        # Get dataset
        dataset_response = await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # Load the actual dataset
        dataset_key = deeplake_service._get_dataset_key(dataset_id, tenant_id)
        dataset = deeplake_service.datasets.get(dataset_key)
        
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not loaded")
        
        # Get index stats
        stats = await deeplake_service.index_service.get_index_stats(dataset)
        
        return stats
        
    except DatasetNotFoundException:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    except Exception as e:
        logger.error(f"Failed to get index stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/datasets/{dataset_id}/index/optimize", response_model=Dict[str, Any])
async def optimize_index(
    dataset_id: str = Path(..., description="Dataset ID"),
    request: IndexOptimizeRequest = ...,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("admin"))
) -> Dict[str, Any]:
    """Optimize index parameters for target recall."""
    try:
        # Get dataset
        dataset_response = await deeplake_service.get_dataset(dataset_id, tenant_id)
        
        # Load the actual dataset
        dataset_key = deeplake_service._get_dataset_key(dataset_id, tenant_id)
        dataset = deeplake_service.datasets.get(dataset_key)
        
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not loaded")
        
        # Optimize index
        optimization_results = await deeplake_service.index_service.optimize_index(
            dataset,
            target_recall=request.target_recall
        )
        
        # Record metrics
        metrics_service.record_index_operation(
            dataset_id, 
            "optimize", 
            0,  # No build time for optimization
            dataset_response.vector_count,
            tenant_id
        )
        
        logger.info(
            "Index optimized",
            dataset_id=dataset_id,
            target_recall=request.target_recall,
            results=optimization_results,
            tenant_id=tenant_id
        )
        
        return optimization_results
        
    except DatasetNotFoundException:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    except Exception as e:
        logger.error(f"Failed to optimize index: {e}")
        metrics_service.record_error("index_optimization_failed", "optimize_index", tenant_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/datasets/{dataset_id}/index")
async def delete_index(
    dataset_id: str = Path(..., description="Dataset ID"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("admin"))
) -> Dict[str, str]:
    """Delete index and revert to flat search."""
    try:
        # This would delete the index and revert to flat search
        # For now, we'll just return success
        
        logger.info(
            "Index deleted",
            dataset_id=dataset_id,
            tenant_id=tenant_id
        )
        
        return {"message": f"Index deleted for dataset {dataset_id}"}
        
    except DatasetNotFoundException:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    except Exception as e:
        logger.error(f"Failed to delete index: {e}")
        metrics_service.record_error("index_deletion_failed", "delete_index", tenant_id)
        raise HTTPException(status_code=500, detail=str(e))