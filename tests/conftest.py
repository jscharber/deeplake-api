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
from app.api.http.dependencies import init_dependencies


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_storage() -> Generator[str, None, None]:
    """Create a temporary storage directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
async def deeplake_service(temp_storage: str) -> AsyncGenerator[DeepLakeService, None]:
    """Create a Deep Lake service instance for testing."""
    # Override storage location
    original_location = os.environ.get("DEEPLAKE_STORAGE_LOCATION")
    os.environ["DEEPLAKE_STORAGE_LOCATION"] = temp_storage
    
    service = DeepLakeService()
    yield service
    
    await service.close()
    
    # Restore original location
    if original_location:
        os.environ["DEEPLAKE_STORAGE_LOCATION"] = original_location


@pytest.fixture
def auth_service() -> AuthService:
    """Create an auth service instance for testing."""
    return AuthService()


@pytest.fixture
async def cache_service() -> AsyncGenerator[CacheService, None]:
    """Create a cache service instance for testing."""
    service = CacheService()
    # Don't initialize Redis for tests to avoid dependency
    service.enabled = False
    yield service
    await service.close()


@pytest.fixture
def metrics_service() -> MetricsService:
    """Create a metrics service instance for testing."""
    return MetricsService()


@pytest.fixture  
async def test_services(
    auth_service: AuthService,
    metrics_service: MetricsService
) -> tuple:
    """Initialize all test services."""
    # Create mock services for testing
    deeplake_service = DeepLakeService()
    cache_service = CacheService()
    cache_service.enabled = False  # Disable Redis for tests
    await cache_service.initialize()  # Initialize cache service
    
    init_dependencies(
        deeplake_service=deeplake_service,
        auth_service=auth_service,
        cache_service=cache_service,
        metrics_service=metrics_service
    )
    return deeplake_service, auth_service, cache_service, metrics_service


@pytest.fixture
async def client(test_services) -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_dataset_data():
    """Sample dataset data for testing."""
    return {
        "name": "test-dataset",
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
def auth_headers(auth_service: AuthService):
    """Generate auth headers for testing."""
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
def jwt_headers(auth_service: AuthService):
    """Generate JWT auth headers for testing."""
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