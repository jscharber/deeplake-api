"""FastAPI dependencies for HTTP API."""

from typing import Optional, Dict, Any, Callable
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.deeplake_service import DeepLakeService
from app.services.auth_service import AuthService
from app.services.cache_service import CacheService, CacheManager
from app.services.metrics_service import MetricsService
from app.models.exceptions import AuthenticationException, AuthorizationException


# Global service instances (initialized in main.py)
_deeplake_service: Optional[DeepLakeService] = None
_auth_service: Optional[AuthService] = None
_cache_service: Optional[CacheService] = None
_cache_manager: Optional[CacheManager] = None
_metrics_service: Optional[MetricsService] = None

security = HTTPBearer(auto_error=False)


def init_dependencies(
    deeplake_service: DeepLakeService,
    auth_service: AuthService,
    cache_service: CacheService,
    metrics_service: MetricsService
) -> None:
    """Initialize global service dependencies."""
    global _deeplake_service, _auth_service, _cache_service, _cache_manager, _metrics_service
    _deeplake_service = deeplake_service
    _auth_service = auth_service
    _cache_service = cache_service
    _cache_manager = CacheManager(cache_service)
    _metrics_service = metrics_service


def get_deeplake_service() -> DeepLakeService:
    """Get Deep Lake service dependency."""
    if _deeplake_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Deep Lake service not available"
        )
    return _deeplake_service


def get_auth_service() -> AuthService:
    """Get authentication service dependency."""
    if _auth_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )
    return _auth_service


def get_cache_manager() -> CacheManager:
    """Get cache manager dependency."""
    if _cache_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service not available"
        )
    return _cache_manager


def get_metrics_service() -> MetricsService:
    """Get metrics service dependency."""
    if _metrics_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics service not available"
        )
    return _metrics_service


async def get_current_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """Get current authentication information."""
    try:
        # Extract authorization header
        auth_header = None
        if credentials:
            auth_header = f"{credentials.scheme} {credentials.credentials}"
        elif "authorization" in request.headers:
            auth_header = request.headers["authorization"]
        elif "x-api-key" in request.headers:
            auth_header = f"ApiKey {request.headers['x-api-key']}"
        
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Authenticate request
        auth_info = auth_service.authenticate_request(auth_header)
        
        # Store auth info in request state
        request.state.auth_info = auth_info
        
        return auth_info
        
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


async def get_current_tenant(
    auth_info: Dict[str, Any] = Depends(get_current_auth)
) -> str:
    """Get current tenant ID."""
    return str(auth_info["tenant_id"])


def authorize_operation(
    operation: str,
    resource: Optional[str] = None
) -> Callable:
    """Create a dependency for operation authorization."""
    async def authorize(
        auth_info: Dict[str, Any] = Depends(get_current_auth),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> Dict[str, Any]:
        try:
            auth_service.authorize_operation(auth_info, operation, resource)
            return auth_info
        except AuthorizationException as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authorization service error"
            )
    
    return authorize


def require_permission(permission: str) -> Callable:
    """Create a dependency that requires a specific permission."""
    async def check_permission(
        auth_info: Dict[str, Any] = Depends(get_current_auth),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> Dict[str, Any]:
        tenant_id = auth_info["tenant_id"]
        permissions = auth_info.get("permissions", [])
        
        if not auth_service.check_permission(tenant_id, permission, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        
        return auth_info
    
    return check_permission


class PaginationParams:
    """Pagination parameters."""
    
    def __init__(
        self,
        page: int = 1,
        page_size: int = 50,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ):
        # Support both page/page_size and limit/offset patterns
        if limit is not None or offset is not None:
            self.limit = min(limit or 100, 1000)  # Max 1000 items
            self.offset = max(offset or 0, 0)
            self.page = (self.offset // self.limit) + 1 if self.limit > 0 else 1
            self.page_size = self.limit
        else:
            self.page = max(page, 1)
            self.page_size = min(max(page_size, 1), 1000)  # Between 1 and 1000
            self.offset = (self.page - 1) * self.page_size
            self.limit = self.page_size


def get_pagination_params(
    page: int = 1,
    page_size: int = 50,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> PaginationParams:
    """Get pagination parameters dependency."""
    return PaginationParams(page, page_size, limit, offset)


async def validate_dataset_access(
    dataset_id: str,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service)
) -> str:
    """Validate that the current tenant has access to the dataset."""
    try:
        # Check if dataset exists and belongs to tenant
        await deeplake_service.get_dataset(dataset_id, tenant_id)
        return dataset_id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found or access denied"
        )


def get_request_id(request: Request) -> str:
    """Get or generate a request ID for tracing."""
    return str(request.headers.get("x-request-id", request.state.get("request_id", "unknown")))