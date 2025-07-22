"""
Rate limit management endpoints.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from app.config.logging import get_logger
from app.services.rate_limit_service import RateLimitService, TenantUsageStats
from app.api.http.dependencies import (
    get_current_tenant, authorize_operation, get_rate_limit_service
)
from app.models.exceptions import RateLimitExceededException

logger = get_logger(__name__)
router = APIRouter(tags=["rate-limits"])


class RateLimitUpdateRequest(BaseModel):
    """Rate limit update request."""
    requests_per_minute: Optional[int] = Field(None, ge=1, le=100000)
    requests_per_hour: Optional[int] = Field(None, ge=1, le=5000000)
    requests_per_day: Optional[int] = Field(None, ge=1, le=100000000)
    burst_size: Optional[int] = Field(None, ge=1, le=10000)


class RateLimitResponse(BaseModel):
    """Rate limit information response."""
    tenant_id: str
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_size: int
    strategy: str
    operation_limits: Dict[str, int]


class UsageStatsResponse(BaseModel):
    """Usage statistics response."""
    tenant_id: str
    current_minute: int
    current_hour: int
    current_day: int
    total_requests: int
    operations: Dict[str, int]
    limits: RateLimitResponse




@router.get("/rate-limits/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    tenant_id: str = Depends(get_current_tenant),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    auth_info: dict = Depends(authorize_operation("read_metrics"))
) -> UsageStatsResponse:
    """Get current usage statistics for the tenant."""
    try:
        # Get usage stats
        stats = await rate_limit_service.get_tenant_usage(tenant_id)
        
        # Get current limits
        limits = rate_limit_service._get_tenant_limits(tenant_id)
        
        return UsageStatsResponse(
            tenant_id=tenant_id,
            current_minute=stats.current_minute,
            current_hour=stats.current_hour,
            current_day=stats.current_day,
            total_requests=stats.total_requests,
            operations=stats.operations,
            limits=RateLimitResponse(
                tenant_id=tenant_id,
                requests_per_minute=limits["requests_per_minute"],
                requests_per_hour=limits["requests_per_hour"],
                requests_per_day=limits["requests_per_day"],
                burst_size=limits["burst_size"],
                strategy=rate_limit_service.config.strategy.value,
                operation_limits=rate_limit_service.config.operation_limits
            )
        )
        
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rate-limits", response_model=RateLimitResponse)
async def get_rate_limits(
    tenant_id: str = Depends(get_current_tenant),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    auth_info: dict = Depends(authorize_operation("read_metrics"))
) -> RateLimitResponse:
    """Get current rate limits for the tenant."""
    try:
        limits = rate_limit_service._get_tenant_limits(tenant_id)
        
        return RateLimitResponse(
            tenant_id=tenant_id,
            requests_per_minute=limits["requests_per_minute"],
            requests_per_hour=limits["requests_per_hour"],
            requests_per_day=limits["requests_per_day"],
            burst_size=limits["burst_size"],
            strategy=rate_limit_service.config.strategy.value,
            operation_limits=rate_limit_service.config.operation_limits
        )
        
    except Exception as e:
        logger.error(f"Failed to get rate limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/rate-limits/{target_tenant_id}")
async def update_tenant_rate_limits(
    target_tenant_id: str = Path(..., description="Target tenant ID"),
    request: RateLimitUpdateRequest = ...,
    tenant_id: str = Depends(get_current_tenant),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    auth_info: dict = Depends(authorize_operation("admin"))
) -> Dict[str, str]:
    """Update rate limits for a specific tenant (admin only)."""
    try:
        # Build limits dict from request
        limits = {}
        if request.requests_per_minute is not None:
            limits["requests_per_minute"] = request.requests_per_minute
        if request.requests_per_hour is not None:
            limits["requests_per_hour"] = request.requests_per_hour
        if request.requests_per_day is not None:
            limits["requests_per_day"] = request.requests_per_day
        if request.burst_size is not None:
            limits["burst_size"] = request.burst_size
        
        if not limits:
            raise HTTPException(
                status_code=400,
                detail="At least one limit must be specified"
            )
        
        # Update tenant limits
        await rate_limit_service.update_tenant_limits(target_tenant_id, limits)
        
        logger.info(
            f"Admin {tenant_id} updated rate limits for tenant {target_tenant_id}: {limits}"
        )
        
        return {
            "message": f"Rate limits updated for tenant {target_tenant_id}",
            "updated_limits": limits
        }
        
    except Exception as e:
        logger.error(f"Failed to update rate limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/rate-limits/{target_tenant_id}/reset")
async def reset_tenant_rate_limits(
    target_tenant_id: str = Path(..., description="Target tenant ID"),
    tenant_id: str = Depends(get_current_tenant),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    auth_info: dict = Depends(authorize_operation("admin"))
) -> Dict[str, str]:
    """Reset rate limits for a specific tenant (admin only)."""
    try:
        await rate_limit_service.reset_tenant_limits(target_tenant_id)
        
        logger.info(
            f"Admin {tenant_id} reset rate limits for tenant {target_tenant_id}"
        )
        
        return {
            "message": f"Rate limits reset for tenant {target_tenant_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to reset rate limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/rate-limits/usage/{target_tenant_id}", response_model=UsageStatsResponse)
async def get_tenant_usage_stats(
    target_tenant_id: str = Path(..., description="Target tenant ID"),
    tenant_id: str = Depends(get_current_tenant),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    auth_info: dict = Depends(authorize_operation("admin"))
) -> UsageStatsResponse:
    """Get usage statistics for any tenant (admin only)."""
    try:
        # Get usage stats
        stats = await rate_limit_service.get_tenant_usage(target_tenant_id)
        
        # Get current limits
        limits = rate_limit_service._get_tenant_limits(target_tenant_id)
        
        return UsageStatsResponse(
            tenant_id=target_tenant_id,
            current_minute=stats.current_minute,
            current_hour=stats.current_hour,
            current_day=stats.current_day,
            total_requests=stats.total_requests,
            operations=stats.operations,
            limits=RateLimitResponse(
                tenant_id=target_tenant_id,
                requests_per_minute=limits["requests_per_minute"],
                requests_per_hour=limits["requests_per_hour"],
                requests_per_day=limits["requests_per_day"],
                burst_size=limits["burst_size"],
                strategy=rate_limit_service.config.strategy.value,
                operation_limits=rate_limit_service.config.operation_limits
            )
        )
        
    except Exception as e:
        logger.error(f"Failed to get tenant usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/rate-limits/health")
async def get_rate_limit_health(
    tenant_id: str = Depends(get_current_tenant),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    auth_info: dict = Depends(authorize_operation("admin"))
) -> Dict[str, Any]:
    """Get rate limiting system health (admin only)."""
    try:
        health_info = {
            "status": "healthy",
            "redis_connected": rate_limit_service.redis_client is not None,
            "strategy": rate_limit_service.config.strategy.value,
            "default_limits": {
                "requests_per_minute": rate_limit_service.config.requests_per_minute,
                "requests_per_hour": rate_limit_service.config.requests_per_hour,
                "requests_per_day": rate_limit_service.config.requests_per_day,
                "burst_size": rate_limit_service.config.burst_size,
            },
            "operation_limits": rate_limit_service.config.operation_limits,
            "tenant_overrides": len(rate_limit_service.config.tenant_limits)
        }
        
        # Test Redis connection if available
        if rate_limit_service.redis_client:
            try:
                await rate_limit_service.redis_client.ping()
                health_info["redis_status"] = "connected"
            except Exception as e:
                health_info["redis_status"] = f"error: {e}"
                health_info["status"] = "degraded"
        else:
            health_info["redis_status"] = "disabled"
            health_info["status"] = "degraded"
        
        return health_info
        
    except Exception as e:
        logger.error(f"Failed to get rate limit health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-rate-limit")
async def test_rate_limit(
    operation: str = Query("test", description="Operation to test"),
    cost: int = Query(1, ge=1, le=100, description="Request cost"),
    tenant_id: str = Depends(get_current_tenant),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    auth_info: dict = Depends(authorize_operation("read_metrics"))
) -> Dict[str, Any]:
    """Test rate limiting for current tenant."""
    try:
        # Check rate limit
        status = await rate_limit_service.check_rate_limit(
            tenant_id=tenant_id,
            operation=operation,
            cost=cost
        )
        
        return {
            "tenant_id": tenant_id,
            "operation": operation,
            "cost": cost,
            "allowed": status.allowed,
            "limit": status.limit,
            "remaining": status.remaining,
            "reset_at": status.reset_at.isoformat(),
            "retry_after": status.retry_after
        }
        
    except RateLimitExceededException as e:
        return {
            "tenant_id": tenant_id,
            "operation": operation,
            "cost": cost,
            "allowed": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Failed to test rate limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))