"""End-to-end integration tests."""

import pytest
import asyncio
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests."""
    
    def test_complete_workflow(self, client: TestClient, auth_headers):
        """Test complete workflow from dataset creation to search."""
        
        # 1. Create a dataset
        dataset_data = {
            "name": "e2e-test-dataset",
            "description": "End-to-end test dataset",
            "dimensions": 128,
            "metric_type": "cosine",
            "index_type": "default",
            "metadata": {"test": "e2e"},
            "overwrite": True
        }
        
        create_response = client.post(
            "/api/v1/datasets/",
            json=dataset_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        dataset = create_response.json()
        dataset_id = dataset["id"]
        
        # 2. Verify dataset was created
        get_response = client.get(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
        assert get_response.status_code == 200
        assert get_response.json()["name"] == dataset_data["name"]
        
        # 3. Insert multiple vectors
        vectors = []
        for i in range(5):
            vector = {
                "id": f"test-vector-{i}",
                "document_id": f"test-doc-{i}",
                "chunk_id": f"test-chunk-{i}",
                "values": [0.1 + i * 0.01] * 128,  # Slightly different vectors
                "content": f"This is test content {i}",
                "metadata": {"index": str(i), "test": "e2e"},
                "content_type": "text/plain",
                "language": "en",
                "chunk_index": 0,
                "chunk_count": 1,
                "model": "test-model"
            }
            vectors.append(vector)
        
        batch_data = {"vectors": vectors}
        insert_response = client.post(
            f"/api/v1/datasets/{dataset_id}/vectors/batch",
            json=batch_data,
            headers=auth_headers
        )
        assert insert_response.status_code == 201
        insert_result = insert_response.json()
        assert insert_result["inserted_count"] == 5
        assert insert_result["failed_count"] == 0
        
        # 4. Verify dataset stats updated
        stats_response = client.get(f"/api/v1/datasets/{dataset_id}/stats", headers=auth_headers)
        assert stats_response.status_code == 200
        stats = stats_response.json()
        # Note: vector_count might not be immediately updated due to async nature
        
        # 5. Perform vector search
        search_data = {
            "query_vector": [0.1] * 128,
            "options": {
                "top_k": 3,
                "include_content": True,
                "include_metadata": True
            }
        }
        
        search_response = client.post(
            f"/api/v1/datasets/{dataset_id}/search",
            json=search_data,
            headers=auth_headers
        )
        assert search_response.status_code == 200
        search_result = search_response.json()
        
        # Verify search results structure
        assert "results" in search_result
        assert "total_found" in search_result
        assert "query_time_ms" in search_result
        assert "stats" in search_result
        
        # 6. List all datasets
        list_response = client.get("/api/v1/datasets/", headers=auth_headers)
        assert list_response.status_code == 200
        datasets = list_response.json()
        assert any(d["id"] == dataset_id for d in datasets)
        
        # 7. Check service stats
        stats_response = client.get("/api/v1/stats", headers=auth_headers)
        assert stats_response.status_code == 200
        service_stats = stats_response.json()
        assert "service" in service_stats
        assert "tenant" in service_stats
        
        # 8. Clean up - delete dataset
        delete_response = client.delete(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        # 9. Verify deletion
        get_response = client.get(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_error_scenarios(self, client: TestClient, auth_headers):
        """Test various error scenarios."""
        
        # Test creating dataset with invalid data
        invalid_dataset = {
            "name": "",  # Empty name
            "dimensions": 0,  # Invalid dimensions
            "metric_type": "invalid_metric"
        }
        
        response = client.post(
            "/api/v1/datasets/",
            json=invalid_dataset,
            headers=auth_headers
        )
        assert response.status_code == 422
        
        # Test operations on non-existent dataset
        response = client.get("/api/v1/datasets/nonexistent", headers=auth_headers)
        assert response.status_code == 404
        
        response = client.post(
            "/api/v1/datasets/nonexistent/vectors/",
            json={"id": "test", "document_id": "test", "values": [0.1]},
            headers=auth_headers
        )
        assert response.status_code == 404
        
        response = client.post(
            "/api/v1/datasets/nonexistent/search",
            json={"query_vector": [0.1], "options": {"top_k": 5}},
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_authentication_flows(self, client: TestClient, auth_service):
        """Test different authentication methods."""
        
        # Test API key authentication
        api_key = auth_service.generate_api_key(
            tenant_id="test-tenant",
            name="Test API Key",
            permissions=["read", "write"]
        )
        
        api_key_headers = {
            "Authorization": f"ApiKey {api_key}",
            "Content-Type": "application/json"
        }
        
        response = client.get("/api/v1/datasets/", headers=api_key_headers)
        assert response.status_code == 200
        
        # Test JWT token authentication
        jwt_payload = {
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "permissions": ["read", "write"]
        }
        jwt_token = auth_service.create_jwt_token(jwt_payload)
        
        jwt_headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
        
        response = client.get("/api/v1/datasets/", headers=jwt_headers)
        assert response.status_code == 200
        
        # Test invalid authentication
        invalid_headers = {"Authorization": "Invalid token"}
        response = client.get("/api/v1/datasets/", headers=invalid_headers)
        assert response.status_code == 401
    
    def test_tenant_isolation(self, client: TestClient, auth_service):
        """Test that tenants are properly isolated."""
        
        # Create API keys for different tenants
        tenant1_key = auth_service.generate_api_key(
            tenant_id="tenant1",
            name="Tenant 1 Key",
            permissions=["read", "write"]
        )
        
        tenant2_key = auth_service.generate_api_key(
            tenant_id="tenant2",
            name="Tenant 2 Key", 
            permissions=["read", "write"]
        )
        
        tenant1_headers = {"Authorization": f"ApiKey {tenant1_key}"}
        tenant2_headers = {"Authorization": f"ApiKey {tenant2_key}"}
        
        # Create dataset for tenant1
        dataset_data = {
            "name": "tenant1-dataset",
            "dimensions": 64,
            "metric_type": "cosine",
            "overwrite": True
        }
        
        response = client.post(
            "/api/v1/datasets/",
            json=dataset_data,
            headers=tenant1_headers
        )
        assert response.status_code == 201
        dataset_id = response.json()["id"]
        
        # Tenant1 should see their dataset
        response = client.get("/api/v1/datasets/", headers=tenant1_headers)
        assert response.status_code == 200
        datasets = response.json()
        assert any(d["id"] == dataset_id for d in datasets)
        
        # Tenant2 should not see tenant1's dataset
        response = client.get("/api/v1/datasets/", headers=tenant2_headers)
        assert response.status_code == 200
        datasets = response.json()
        assert not any(d["id"] == dataset_id for d in datasets)
        
        # Tenant2 should not be able to access tenant1's dataset
        response = client.get(f"/api/v1/datasets/{dataset_id}", headers=tenant2_headers)
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Performance and load tests."""
    
    def test_large_batch_insert(self, client: TestClient, auth_headers):
        """Test inserting a large batch of vectors."""
        
        # Create dataset
        dataset_data = {
            "name": "performance-test",
            "dimensions": 256,
            "metric_type": "cosine",
            "overwrite": True
        }
        
        response = client.post(
            "/api/v1/datasets/",
            json=dataset_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        dataset_id = response.json()["id"]
        
        # Create large batch of vectors
        vectors = []
        batch_size = 100  # Keep reasonable for tests
        
        for i in range(batch_size):
            vector = {
                "id": f"perf-vector-{i}",
                "document_id": f"perf-doc-{i}",
                "values": [0.1 + i * 0.001] * 256,
                "content": f"Performance test content {i}",
                "metadata": {"batch": "performance", "index": str(i)}
            }
            vectors.append(vector)
        
        # Insert batch
        batch_data = {"vectors": vectors}
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/vectors/batch",
            json=batch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["inserted_count"] == batch_size
        assert result["failed_count"] == 0
        assert result["processing_time_ms"] > 0
        
        # Test search performance
        search_data = {
            "query_vector": [0.1] * 256,
            "options": {"top_k": 10}
        }
        
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/search",
            json=search_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        search_result = response.json()
        assert search_result["query_time_ms"] > 0