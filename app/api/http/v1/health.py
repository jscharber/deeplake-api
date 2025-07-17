"""Health check and monitoring endpoints."""

from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.http.dependencies import (
    get_deeplake_service, get_auth_service, get_cache_manager, get_metrics_service,
    require_permission, get_current_auth
)
from app.services.deeplake_service import DeepLakeService
from app.services.auth_service import AuthService
from app.services.cache_service import CacheManager
from app.services.metrics_service import MetricsService
from app.models.schemas import HealthResponse, MetricsResponse
from app.config.settings import settings


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> HealthResponse:
    """Health check endpoint."""
    
    # Check service dependencies
    dependencies = {}
    
    # Check Deep Lake service
    try:
        # Simple check - try to access storage location
        import os
        if os.path.exists(settings.deeplake.storage_location):
            dependencies["deeplake_storage"] = "healthy"
        else:
            dependencies["deeplake_storage"] = "unhealthy"
    except Exception:
        dependencies["deeplake_storage"] = "unhealthy"
    
    # Check cache service
    try:
        cache_stats = await cache_manager.cache.get_stats()
        if cache_stats.get("enabled", False):
            dependencies["cache"] = "healthy"
        else:
            dependencies["cache"] = "disabled"
    except Exception:
        dependencies["cache"] = "unhealthy"
    
    # Determine overall status
    unhealthy_deps = [k for k, v in dependencies.items() if v == "unhealthy"]
    overall_status = "unhealthy" if unhealthy_deps else "healthy"
    
    return HealthResponse(
        status=overall_status,
        service="Tributary AI services for DeepLake",
        version="1.0.0",
        timestamp=datetime.now(),
        dependencies=dependencies
    )


@router.get("/health/ready")
async def readiness_check(
    deeplake_service: DeepLakeService = Depends(get_deeplake_service)
) -> Dict[str, Any]:
    """Readiness check for Kubernetes."""
    try:
        # Verify critical services are ready
        import os
        if not os.path.exists(settings.deeplake.storage_location):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage location not accessible"
            )
        
        return {"status": "ready", "timestamp": datetime.now()}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check for Kubernetes."""
    return {"status": "alive", "timestamp": datetime.now()}


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: Dict[str, Any] = Depends(require_permission("admin"))
) -> MetricsResponse:
    """Get service metrics (admin only)."""
    try:
        metrics_summary = metrics_service.get_metrics_summary()
        
        return MetricsResponse(
            metrics=metrics_summary,
            timestamp=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get("/metrics/prometheus")
async def get_prometheus_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: Dict[str, Any] = Depends(require_permission("admin"))
) -> str:
    """Get Prometheus-formatted metrics (admin only)."""
    try:
        return metrics_service.get_metrics()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Prometheus metrics: {str(e)}"
        )


@router.get("/stats")
async def get_service_stats(
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    auth_service: AuthService = Depends(get_auth_service),
    cache_manager: CacheManager = Depends(get_cache_manager),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: Dict[str, Any] = Depends(get_current_auth)
) -> Dict[str, Any]:
    """Get comprehensive service statistics."""
    try:
        tenant_id = auth_info["tenant_id"]
        
        # Get datasets for current tenant
        datasets = await deeplake_service.list_datasets(tenant_id)
        
        # Calculate totals
        total_vectors = 0
        total_storage = 0
        for dataset in datasets:
            total_vectors += dataset.vector_count
            total_storage += dataset.storage_size
        
        # Get cache stats
        cache_stats = await cache_manager.cache.get_stats()
        
        # Get auth stats (only for admin users)
        auth_stats = {}
        if "admin" in auth_info.get("permissions", []):
            auth_stats = auth_service.get_api_key_stats()
        
        return {
            "service": {
                "name": "Tributary AI services for DeepLake",
                "version": "1.0.0",
                "uptime_seconds": getattr(metrics_service, '_start_time', 0),
            },
            "tenant": {
                "id": tenant_id,
                "datasets_count": len(datasets),
                "total_vectors": total_vectors,
                "total_storage_bytes": total_storage,
            },
            "cache": cache_stats,
            "auth": auth_stats,
            "timestamp": datetime.now(timezone.utc),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service stats: {str(e)}"
        )