"""Unit tests for HTTP API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health and monitoring endpoints."""
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "Tributary AI services for DeepLake"
        assert data["version"] == "1.0.0"
        assert "dependencies" in data
    
    def test_liveness_check(self, client: TestClient):
        """Test liveness check endpoint."""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "alive"
    
    def test_readiness_check(self, client: TestClient):
        """Test readiness check endpoint."""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ready"


class TestDatasetEndpoints:
    """Test dataset management endpoints."""
    
    def test_create_dataset_unauthorized(self, client: TestClient, test_dataset_data):
        """Test creating dataset without authorization."""
        response = client.post("/api/v1/datasets/", json=test_dataset_data)
        assert response.status_code == 401
    
    def test_create_dataset_authorized(self, client: TestClient, test_dataset_data, auth_headers):
        """Test creating dataset with authorization."""
        response = client.post(
            "/api/v1/datasets/", 
            json=test_dataset_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == test_dataset_data["name"]
        assert data["dimensions"] == test_dataset_data["dimensions"]
    
    def test_list_datasets_authorized(self, client: TestClient, auth_headers):
        """Test listing datasets with authorization."""
        response = client.get("/api/v1/datasets/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_dataset_not_found(self, client: TestClient, auth_headers):
        """Test getting non-existent dataset."""
        response = client.get("/api/v1/datasets/nonexistent", headers=auth_headers)
        assert response.status_code == 404
    
    def test_dataset_lifecycle(self, client: TestClient, test_dataset_data, auth_headers):
        """Test complete dataset lifecycle."""
        # Create dataset
        create_response = client.post(
            "/api/v1/datasets/",
            json=test_dataset_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        dataset = create_response.json()
        dataset_id = dataset["id"]
        
        # Get dataset
        get_response = client.get(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
        assert get_response.status_code == 200
        
        # Get dataset stats
        stats_response = client.get(f"/api/v1/datasets/{dataset_id}/stats", headers=auth_headers)
        assert stats_response.status_code == 200
        
        # Delete dataset
        delete_response = client.delete(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response = client.get(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
        assert get_response.status_code == 404


class TestVectorEndpoints:
    """Test vector operation endpoints."""
    
    def test_insert_vector_unauthorized(self, client: TestClient, test_vector_data):
        """Test inserting vector without authorization."""
        response = client.post(
            "/api/v1/datasets/test-dataset/vectors/",
            json=test_vector_data
        )
        assert response.status_code == 401
    
    def test_insert_vector_nonexistent_dataset(self, client: TestClient, test_vector_data, auth_headers):
        """Test inserting vector into non-existent dataset."""
        response = client.post(
            "/api/v1/datasets/nonexistent/vectors/",
            json=test_vector_data,
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_vector_operations_with_dataset(self, client: TestClient, test_dataset_data, test_vector_data, auth_headers):
        """Test vector operations with a real dataset."""
        # Create dataset first
        create_response = client.post(
            "/api/v1/datasets/",
            json=test_dataset_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        dataset = create_response.json()
        dataset_id = dataset["id"]
        
        # Insert single vector
        vector_response = client.post(
            f"/api/v1/datasets/{dataset_id}/vectors/",
            json=test_vector_data,
            headers=auth_headers
        )
        assert vector_response.status_code == 201
        vector_result = vector_response.json()
        assert vector_result["inserted_count"] == 1
        
        # Insert batch of vectors
        batch_data = {"vectors": [test_vector_data]}
        batch_response = client.post(
            f"/api/v1/datasets/{dataset_id}/vectors/batch",
            json=batch_data,
            headers=auth_headers
        )
        assert batch_response.status_code == 201
        
        # List vectors
        list_response = client.get(f"/api/v1/datasets/{dataset_id}/vectors/", headers=auth_headers)
        assert list_response.status_code == 200


class TestSearchEndpoints:
    """Test search endpoints."""
    
    def test_search_unauthorized(self, client: TestClient, test_search_data):
        """Test search without authorization."""
        response = client.post(
            "/api/v1/datasets/test-dataset/search",
            json=test_search_data
        )
        assert response.status_code == 401
    
    def test_search_nonexistent_dataset(self, client: TestClient, test_search_data, auth_headers):
        """Test search in non-existent dataset."""
        response = client.post(
            "/api/v1/datasets/nonexistent/search",
            json=test_search_data,
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_search_with_dataset(self, client: TestClient, test_dataset_data, test_vector_data, test_search_data, auth_headers):
        """Test search with a real dataset."""
        # Create dataset
        create_response = client.post(
            "/api/v1/datasets/",
            json=test_dataset_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        dataset = create_response.json()
        dataset_id = dataset["id"]
        
        # Insert vector
        client.post(
            f"/api/v1/datasets/{dataset_id}/vectors/",
            json=test_vector_data,
            headers=auth_headers
        )
        
        # Search
        search_response = client.post(
            f"/api/v1/datasets/{dataset_id}/search",
            json=test_search_data,
            headers=auth_headers
        )
        assert search_response.status_code == 200
        
        search_result = search_response.json()
        assert "results" in search_result
        assert "total_found" in search_result
        assert "query_time_ms" in search_result
    
    def test_text_search_not_implemented(self, client: TestClient, auth_headers):
        """Test text search returns not implemented."""
        # Create dataset first
        dataset_data = {
            "name": "text-search-test",
            "dimensions": 128,
            "metric_type": "cosine",
            "overwrite": True
        }
        create_response = client.post(
            "/api/v1/datasets/",
            json=dataset_data,
            headers=auth_headers
        )
        dataset_id = create_response.json()["id"]
        
        # Try text search
        text_search_data = {
            "query_text": "test query",
            "options": {"top_k": 10}
        }
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/search/text",
            json=text_search_data,
            headers=auth_headers
        )
        assert response.status_code == 400  # Bad request due to missing sentence-transformers


class TestAuthenticationAndAuthorization:
    """Test authentication and authorization."""
    
    def test_no_auth_header(self, client: TestClient):
        """Test request without auth header."""
        response = client.get("/api/v1/datasets/")
        assert response.status_code == 401
    
    def test_invalid_auth_header(self, client: TestClient):
        """Test request with invalid auth header."""
        headers = {"Authorization": "Invalid header"}
        response = client.get("/api/v1/datasets/", headers=headers)
        assert response.status_code == 401
    
    def test_invalid_api_key(self, client: TestClient):
        """Test request with invalid API key."""
        headers = {"Authorization": "ApiKey invalid-key"}
        response = client.get("/api/v1/datasets/", headers=headers)
        assert response.status_code == 401
    
    def test_valid_jwt_token(self, client: TestClient, jwt_headers):
        """Test request with valid JWT token."""
        response = client.get("/api/v1/datasets/", headers=jwt_headers)
        assert response.status_code == 200
    
    def test_admin_only_endpoint(self, client: TestClient, auth_headers):
        """Test admin-only endpoint access."""
        response = client.get("/api/v1/metrics", headers=auth_headers)
        assert response.status_code == 200  # Should work with admin permissions


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_json(self, client: TestClient, auth_headers):
        """Test request with invalid JSON."""
        headers = {**auth_headers, "Content-Type": "application/json"}
        response = client.post(
            "/api/v1/datasets/",
            data="invalid json",
            headers=headers
        )
        assert response.status_code == 422
    
    def test_validation_errors(self, client: TestClient, auth_headers):
        """Test request with validation errors."""
        invalid_data = {
            "name": "",  # Empty name
            "dimensions": -1,  # Invalid dimensions
            "metric_type": "invalid"  # Invalid metric type
        }
        response = client.post(
            "/api/v1/datasets/",
            json=invalid_data,
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_request_id_header(self, client: TestClient):
        """Test that request ID is included in responses."""
        response = client.get("/api/v1/health")
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers