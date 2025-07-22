"""Test configuration and fixtures."""

import os
import tempfile
import shutil
import asyncio
from typing import AsyncGenerator, Generator
import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app modules
os.environ["DEEPLAKE_STORAGE_LOCATION"] = tempfile.mkdtemp()
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["DEV_DEBUG"] = "true"
os.environ["MONITORING_LOG_LEVEL"] = "ERROR"  # Reduce log noise in tests

from app.main import app
from app.services.deeplake_service import DeepLakeService
from app.services.auth_service import AuthService
from app.services.cache_service import CacheService
from app.services.metrics_service import MetricsService
from app.services.rate_limit_service import RateLimitService
from app.services.backup_service import BackupService
from app.api.http.dependencies import init_dependencies


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def temp_storage() -> Generator[str, None, None]:
    """Create a temporary storage directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix='deeplake_test_')
    yield temp_dir
    # Clean up
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
async def deeplake_service(temp_storage: str) -> AsyncGenerator[DeepLakeService, None]:
    """Create a Deep Lake service instance for testing."""
    # Override storage location
    original_location = os.environ.get("DEEPLAKE_STORAGE_LOCATION")
    os.environ["DEEPLAKE_STORAGE_LOCATION"] = temp_storage
    
    service = DeepLakeService()
    try:
        yield service
    finally:
        # Clean up service state
        await service.close()
        # Clear any cached datasets
        if hasattr(service, 'datasets'):
            service.datasets.clear()
        
        # Restore original location
        if original_location:
            os.environ["DEEPLAKE_STORAGE_LOCATION"] = original_location
        else:
            os.environ.pop("DEEPLAKE_STORAGE_LOCATION", None)


@pytest.fixture(scope="function")
def auth_service() -> AuthService:
    """Create an auth service instance for testing."""
    return AuthService()


@pytest.fixture(scope="function")
async def cache_service() -> AsyncGenerator[CacheService, None]:
    """Create a cache service instance for testing."""
    service = CacheService()
    # Don't initialize Redis for tests to avoid dependency
    service.enabled = False
    yield service
    await service.close()


@pytest.fixture(scope="function")
def metrics_service() -> MetricsService:
    """Create a metrics service instance for testing."""
    return MetricsService()


@pytest.fixture(scope="function")
async def rate_limit_service() -> AsyncGenerator[RateLimitService, None]:
    """Create a rate limit service instance for testing."""
    service = RateLimitService()
    # Don't initialize Redis for tests to avoid dependency
    service.enabled = False
    yield service
    await service.close()


@pytest.fixture(scope="function")  
async def test_services(
    deeplake_service: DeepLakeService,
    auth_service: AuthService,
    cache_service: CacheService,
    metrics_service: MetricsService,
    rate_limit_service: RateLimitService
) -> tuple:
    """Initialize all test services using isolated fixtures."""
    # Create backup service with deeplake_service dependency
    backup_service = BackupService(deeplake_service=deeplake_service)
    
    init_dependencies(
        deeplake_service=deeplake_service,
        auth_service=auth_service,
        cache_service=cache_service,
        metrics_service=metrics_service,
        rate_limit_service=rate_limit_service,
        backup_service=backup_service
    )
    return deeplake_service, auth_service, cache_service, metrics_service, rate_limit_service, backup_service


@pytest.fixture(scope="function")
async def client(test_services) -> TestClient:
    """Create a test client for the FastAPI app."""
    # The test_services fixture already initializes dependencies
    # Create a new FastAPI app instance without lifespan to avoid startup conflicts
    from fastapi import FastAPI
    from app.main import app as original_app
    
    # Create a test app without lifespan
    test_app = FastAPI(
        title=original_app.title,
        description=original_app.description,
        version=original_app.version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Copy all routes from the original app
    for route in original_app.routes:
        test_app.routes.append(route)
    
    # Copy middleware
    test_app.user_middleware = original_app.user_middleware[:]
    test_app.middleware_stack = original_app.middleware_stack
    
    # Set up the app state with test services
    test_app.state.deeplake_service = test_services[0]
    test_app.state.auth_service = test_services[1]
    test_app.state.cache_service = test_services[2]
    test_app.state.metrics_service = test_services[3]
    test_app.state.rate_limit_service = test_services[4]
    test_app.state.backup_service = test_services[5]
    
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def cleanup_global_state():
    """Clean up global state before and after each test."""
    # Before test: store original global state
    import app.api.http.dependencies as deps
    original_state = {
        '_deeplake_service': getattr(deps, '_deeplake_service', None),
        '_auth_service': getattr(deps, '_auth_service', None),
        '_cache_service': getattr(deps, '_cache_service', None),
        '_cache_manager': getattr(deps, '_cache_manager', None),
        '_metrics_service': getattr(deps, '_metrics_service', None),
        '_rate_limit_service': getattr(deps, '_rate_limit_service', None),
        '_backup_service': getattr(deps, '_backup_service', None),
    }
    
    yield
    
    # After test: restore original state
    for key, value in original_state.items():
        setattr(deps, key, value)


@pytest.fixture
def test_dataset_data():
    """Sample dataset data for testing."""
    import uuid
    unique_name = f"test-dataset-{uuid.uuid4().hex[:8]}"
    return {
        "name": unique_name,
        "description": "A test dataset for unit tests",
        "dimensions": 128,
        "metric_type": "cosine",
        "index_type": "default",
        "metadata": {"test": "true"},
        "overwrite": True
    }


@pytest.fixture
def test_vector_data():
    """Sample vector data for testing."""
    return {
        "id": "test-vector-1",
        "document_id": "test-doc-1",
        "chunk_id": "test-chunk-1",
        "values": [0.1] * 128,
        "content": "This is test content",
        "metadata": {"test": "true"},
        "content_type": "text/plain",
        "language": "en",
        "chunk_index": 0,
        "chunk_count": 1,
        "model": "test-model"
    }


@pytest.fixture
def test_search_data():
    """Sample search data for testing."""
    return {
        "query_vector": [0.1] * 128,
        "options": {
            "top_k": 10,
            "include_content": True,
            "include_metadata": True
        }
    }


@pytest.fixture
async def auth_headers(test_services):
    """Generate auth headers for testing."""
    # Use the auth service from test_services to ensure consistency
    auth_service = test_services[1]  # auth_service is the second item in the tuple
    
    # Create a test API key
    api_key = auth_service.generate_api_key(
        tenant_id="default",
        name="Test API Key",
        permissions=["read", "write", "admin"]
    )
    
    return {
        "Authorization": f"ApiKey {api_key}",
        "Content-Type": "application/json"
    }


@pytest.fixture
async def jwt_headers(test_services):
    """Generate JWT auth headers for testing."""
    # Use the auth service from test_services to ensure consistency
    auth_service = test_services[1]  # auth_service is the second item in the tuple
    
    # Create a test JWT token
    payload = {
        "tenant_id": "default",
        "user_id": "test-user",
        "permissions": ["read", "write", "admin"]
    }
    token = auth_service.create_jwt_token(payload)
    
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }