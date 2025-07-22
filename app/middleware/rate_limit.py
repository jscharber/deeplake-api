"""
Rate limiting middleware for FastAPI.
"""

import time
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config.logging import get_logger
from app.services.rate_limit_service import RateLimitService, RateLimitStatus
from app.models.exceptions import RateLimitExceededException

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits per tenant."""
    
    def __init__(
        self,
        app: ASGIApp,
        rate_limit_service: Optional[RateLimitService] = None,
        get_tenant_id: Optional[Callable] = None,
        get_operation: Optional[Callable] = None,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.rate_limit_service = rate_limit_service
        self.get_tenant_id = get_tenant_id
        self.get_operation = get_operation
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/metrics",
            "/"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiting."""
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Get rate limit service from app state if not provided during init
        rate_limit_service = self.rate_limit_service
        if rate_limit_service is None:
            rate_limit_service = getattr(request.app.state, 'rate_limit_service', None)
        
        # Skip rate limiting if service is not available
        if rate_limit_service is None:
            return await call_next(request)
        
        # Skip OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # Get tenant ID
            tenant_id = await self._get_tenant_id(request)
            if not tenant_id:
                # No tenant ID, skip rate limiting
                return await call_next(request)
            
            # Get operation type
            operation = self._get_operation(request)
            
            # Determine request cost
            cost = self._get_request_cost(request, operation)
            
            # Check rate limit
            start_time = time.time()
            status = await rate_limit_service.check_rate_limit(
                tenant_id=tenant_id,
                operation=operation,
                cost=cost
            )
            
            # Add rate limit headers
            response = await call_next(request)
            response = self._add_rate_limit_headers(response, status)
            
            # Log rate limit check
            duration = time.time() - start_time
            logger.debug(
                "Rate limit check",
                tenant_id=tenant_id,
                operation=operation,
                allowed=status.allowed,
                remaining=status.remaining,
                duration_ms=duration * 1000
            )
            
            return response
            
        except RateLimitExceededException as e:
            # Rate limit exceeded
            status = RateLimitStatus(
                allowed=False,
                limit=e.details.get("limit", 1000),
                remaining=0,
                reset_at=e.details.get("reset_at"),
                retry_after=e.details.get("retry_after", 60)
            )
            
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": str(e),
                    "retry_after": status.retry_after
                }
            )
            
            response = self._add_rate_limit_headers(response, status)
            
            logger.warning(
                "Rate limit exceeded",
                tenant_id=tenant_id,
                operation=operation,
                limit=status.limit
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Don't block request on rate limit errors
            return await call_next(request)
    
    async def _get_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request."""
        if self.get_tenant_id:
            return await self.get_tenant_id(request)
        
        # Default implementation - check various sources
        # 1. Check state (set by auth middleware)
        if hasattr(request.state, "tenant_id"):
            return request.state.tenant_id
        
        # 2. Check headers
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        
        # 3. Check auth info
        if hasattr(request.state, "auth_info"):
            auth_info = request.state.auth_info
            if isinstance(auth_info, dict):
                return auth_info.get("tenant_id")
        
        # 4. Check API key info
        if hasattr(request.state, "api_key_info"):
            return request.state.api_key_info.get("tenant_id", "default")
        
        return None
    
    def _get_operation(self, request: Request) -> Optional[str]:
        """Determine operation type from request."""
        if self.get_operation:
            return self.get_operation(request)
        
        # Map HTTP method and path to operation
        path = request.url.path
        method = request.method
        
        # Search operations
        if "/search" in path:
            if "/hybrid" in path:
                return "hybrid_search"
            elif "/text" in path:
                return "text_search"
            else:
                return "search"
        
        # Vector operations
        if "/vectors" in path:
            if method == "POST":
                if "/batch" in path:
                    return "batch_insert"
                return "insert"
            elif method == "DELETE":
                return "delete"
            elif method == "GET":
                return "list"
        
        # Dataset operations
        if "/datasets" in path and method == "POST":
            return "create_dataset"
        
        # Import/Export
        if "/import" in path:
            return "import"
        if "/export" in path:
            return "export"
        
        # Index operations
        if "/index" in path:
            return "index_operation"
        
        # Default by method
        return method.lower()
    
    def _get_request_cost(
        self,
        request: Request,
        operation: Optional[str]
    ) -> int:
        """Calculate request cost based on operation type."""
        # Expensive operations have higher cost
        expensive_operations = {
            "batch_insert": 10,
            "import": 50,
            "export": 20,
            "create_dataset": 5,
            "index_operation": 20,
            "hybrid_search": 3,
        }
        
        if operation in expensive_operations:
            return expensive_operations[operation]
        
        # Check for batch size in request
        if hasattr(request.state, "batch_size"):
            return max(1, request.state.batch_size // 100)
        
        return 1
    
    def _add_rate_limit_headers(
        self,
        response: Response,
        status: RateLimitStatus
    ) -> Response:
        """Add rate limit headers to response."""
        response.headers["X-RateLimit-Limit"] = str(status.limit)
        response.headers["X-RateLimit-Remaining"] = str(status.remaining)
        response.headers["X-RateLimit-Reset"] = str(int(status.reset_at.timestamp()))
        
        if status.retry_after:
            response.headers["Retry-After"] = str(status.retry_after)
        
        return response


def create_rate_limit_middleware(
    rate_limit_service: RateLimitService,
    **kwargs
) -> RateLimitMiddleware:
    """Factory function to create rate limit middleware."""
    return lambda app: RateLimitMiddleware(
        app,
        rate_limit_service,
        **kwargs
    )