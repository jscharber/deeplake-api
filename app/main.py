"""Main application entry point."""

import asyncio
import uvicorn
from contextlib import asynccontextmanager
from typing import Callable, Any, Dict
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time

from app.config.settings import settings
from app.config.logging import configure_logging, get_logger
from app.api.http.v1 import datasets, vectors, search, health, import_export, indexes, rate_limits, backup
from app.api.http.dependencies import init_dependencies
from app.services.deeplake_service import DeepLakeService
from app.services.auth_service import AuthService
from app.services.cache_service import CacheService
from app.services.metrics_service import MetricsService
from app.services.rate_limit_service import RateLimitService
from app.services.backup_service import BackupService
from app.middleware.rate_limit import RateLimitMiddleware
from app.models.exceptions import DeepLakeServiceException


# Configure logging
configure_logging(settings.monitoring.log_level, settings.monitoring.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Application lifespan manager."""
    logger.info("Starting Tributary AI services for DeepLake", version="1.0.0")

    # Initialize services
    try:
        # Initialize metrics service
        metrics_service = MetricsService()
        metrics_service.start_tracking_uptime()

        # Initialize cache service
        cache_service = CacheService()
        await cache_service.initialize()

        # Initialize rate limit service
        rate_limit_service = RateLimitService(cache_service.redis_client)
        await rate_limit_service.initialize()

        # Initialize auth service
        auth_service = AuthService()

        # Initialize Deep Lake service
        deeplake_service = DeepLakeService()

        # Initialize backup service
        backup_service = BackupService(deeplake_service, cache_service)
        await backup_service.initialize()

        # Initialize dependencies
        init_dependencies(
            deeplake_service=deeplake_service,
            auth_service=auth_service,
            cache_service=cache_service,
            metrics_service=metrics_service,
            rate_limit_service=rate_limit_service,
            backup_service=backup_service,
        )

        # Store services in app state
        app.state.deeplake_service = deeplake_service
        app.state.auth_service = auth_service
        app.state.cache_service = cache_service
        app.state.metrics_service = metrics_service
        app.state.rate_limit_service = rate_limit_service
        app.state.backup_service = backup_service

        # Rate limiting service is now initialized and available in app.state
        # Middleware was added before app startup

        logger.info("All services initialized successfully")

        yield

    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise

    finally:
        # Shutdown services
        logger.info("Shutting down Tributary AI services for DeepLake")

        try:
            if hasattr(app.state, "deeplake_service"):
                await app.state.deeplake_service.close()

            if hasattr(app.state, "cache_service"):
                await app.state.cache_service.close()

            if hasattr(app.state, "rate_limit_service"):
                await app.state.rate_limit_service.close()

            if hasattr(app.state, "backup_service"):
                await app.state.backup_service.close()

            logger.info("All services shut down successfully")

        except Exception as e:
            logger.error("Error during service shutdown", error=str(e))


# Custom OpenAPI schema with proper security definitions
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title="Tributary AI services for DeepLake",
        version="1.0.0",
        description="Universal DeepLake vector database service with HTTP and gRPC APIs",
        routes=app.routes,
    )
    
    # Add custom security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "API Key authentication. Enter your API key directly (without 'ApiKey' prefix). The system will automatically format it as 'ApiKey your-key'"
        }
    }
    
    # Apply security to all endpoints except health checks
    for path_item in openapi_schema["paths"].values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "operationId" in operation:
                # Skip health endpoints (they should be public)
                if not any(tag in operation.get("tags", []) for tag in ["health"]):
                    # Override any existing security with our APIKeyHeader
                    operation["security"] = [{"APIKeyHeader": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Create FastAPI app
app = FastAPI(
    title="Tributary AI services for DeepLake",
    description="Universal DeepLake vector database service with HTTP and gRPC APIs",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set custom OpenAPI schema
app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.development.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
# Note: The RateLimitService will be initialized during lifespan startup
app.add_middleware(
    RateLimitMiddleware,
    exclude_paths=[
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/metrics",
        "/"
    ]
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable[..., Any]) -> Any:
    """Add request timing and logging."""
    start_time = time.time()

    # Generate request ID
    import uuid

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Log request start
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        request_id=request_id,
        client_ip=request.client.host if request.client else "unknown",
    )

    try:
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id

        # Record metrics if available
        if hasattr(app.state, "metrics_service"):
            endpoint = request.url.path
            tenant_id = getattr(request.state, "auth_info", {}).get("tenant_id")

            app.state.metrics_service.record_http_request(
                method=request.method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration=process_time,
                tenant_id=tenant_id,
            )

        # Log request completion
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration_ms=process_time * 1000,
            request_id=request_id,
        )

        return response

    except Exception as e:
        # Calculate processing time for errors too
        process_time = time.time() - start_time

        # Log error
        logger.error(
            "Request failed",
            method=request.method,
            url=str(request.url),
            error=str(e),
            duration_ms=process_time * 1000,
            request_id=request_id,
        )

        # Record error metrics if available
        if hasattr(app.state, "metrics_service"):
            endpoint = request.url.path
            tenant_id = getattr(request.state, "auth_info", {}).get("tenant_id")

            app.state.metrics_service.record_http_request(
                method=request.method,
                endpoint=endpoint,
                status_code=500,
                duration=process_time,
                tenant_id=tenant_id,
            )

        raise


# Exception handlers
@app.exception_handler(DeepLakeServiceException)
async def deeplake_exception_handler(
    request: Request, exc: DeepLakeServiceException
) -> JSONResponse:
    """Handle Deep Lake service exceptions."""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    import traceback

    error_details = {
        "error": str(exc),
        "type": str(type(exc)),
        "traceback": traceback.format_exc(),
    }

    logger.error(
        "Unhandled exception",
        **error_details,
        request_id=getattr(request.state, "request_id", "unknown"),
        exc_info=True,
    )

    # For debugging, include error details in response
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "debug": {"error": str(exc), "type": str(type(exc).__name__)},
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")
app.include_router(vectors.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(import_export.router, prefix="/api/v1")
app.include_router(indexes.router, prefix="/api/v1")
app.include_router(rate_limits.router, prefix="/api/v1")
app.include_router(backup.router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with service information."""
    return {
        "service": "Tributary AI services for DeepLake",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_url": "/api/v1/health",
    }


def main() -> None:
    """Main entry point for running the service."""
    logger.info(
        "Starting HTTP server",
        host=settings.http.host,
        port=settings.http.port,
        workers=settings.http.workers,
        debug=settings.development.debug,
    )

    uvicorn.run(
        "app.main:app",
        host=settings.http.host,
        port=settings.http.port,
        workers=1 if settings.development.debug else settings.http.workers,
        reload=settings.development.reload,
        log_level=settings.monitoring.log_level.lower(),
        access_log=False,  # We handle logging in middleware
    )


if __name__ == "__main__":
    main()
