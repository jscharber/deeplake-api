"""Unit tests for distance metrics implementation."""

import pytest
import numpy as np
from fastapi.testclient import TestClient
from typing import Dict, Any


class TestDistanceMetrics:
    """Test all supported distance metrics."""
    
    @pytest.mark.parametrize("metric_type", ["cosine", "euclidean", "manhattan", "dot_product", "hamming"])
    def test_dataset_creation_with_metrics(self, client: TestClient, auth_headers: Dict[str, str], metric_type: str):
        """Test that datasets can be created with all supported metrics."""
        dataset_data = {
            "name": f"test-{metric_type}-dataset",
            "dimensions": 4,
            "metric_type": metric_type,
            "overwrite": True
        }
        
        response = client.post("/api/v1/datasets/", json=dataset_data, headers=auth_headers)
        assert response.status_code == 201
        
        dataset = response.json()
        assert dataset["metric_type"] == metric_type
        assert dataset["dimensions"] == 4
    
    def test_invalid_metric_type(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test that invalid metric types are rejected."""
        dataset_data = {
            "name": "test-invalid-metric",
            "dimensions": 4,
            "metric_type": "invalid_metric",
            "overwrite": True
        }
        
        response = client.post("/api/v1/datasets/", json=dataset_data, headers=auth_headers)
        assert response.status_code == 422
        
        error_detail = response.json()
        assert "metric_type must be one of" in str(error_detail)
    
    def test_cosine_metric_search(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test cosine similarity search behavior."""
        # Create dataset with cosine metric
        dataset_data = {
            "name": "test-cosine-search",
            "dimensions": 3,
            "metric_type": "cosine",
            "overwrite": True
        }
        
        response = client.post("/api/v1/datasets/", json=dataset_data, headers=auth_headers)
        assert response.status_code == 201
        dataset_id = response.json()["id"]
        
        # Insert test vector
        vector_data = {
            "document_id": "cosine-test-doc",
            "values": [1.0, 0.0, 0.0]  # Unit vector along x-axis
        }
        
        response = client.post(f"/api/v1/datasets/{dataset_id}/vectors/", 
                             json=vector_data, headers=auth_headers)
        assert response.status_code == 201
        
        # Search with parallel vector (should have high cosine similarity)
        search_data = {
            "query_vector": [2.0, 0.0, 0.0],  # Parallel vector
            "options": {"top_k": 1}
        }
        
        response = client.post(f"/api/v1/datasets/{dataset_id}/search",
                             json=search_data, headers=auth_headers)
        assert response.status_code == 200
        
        results = response.json()["results"]
        assert len(results) == 1
        
        # Cosine similarity between parallel vectors should be 1.0
        assert abs(results[0]["score"] - 1.0) < 0.001
        assert results[0]["distance"] < 0.001
        
        # Clean up
        client.delete(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
    
    def test_euclidean_metric_search(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test Euclidean distance search behavior."""
        # Create dataset with euclidean metric
        dataset_data = {
            "name": "test-euclidean-search",
            "dimensions": 2,
            "metric_type": "euclidean",
            "overwrite": True
        }
        
        response = client.post("/api/v1/datasets/", json=dataset_data, headers=auth_headers)
        assert response.status_code == 201
        dataset_id = response.json()["id"]
        
        # Insert test vector
        vector_data = {
            "document_id": "euclidean-test-doc",
            "values": [0.0, 0.0]  # Origin point
        }
        
        response = client.post(f"/api/v1/datasets/{dataset_id}/vectors/", 
                             json=vector_data, headers=auth_headers)
        assert response.status_code == 201
        
        # Search with vector at distance 5 from origin
        search_data = {
            "query_vector": [3.0, 4.0],  # Distance = sqrt(9+16) = 5
            "options": {"top_k": 1}
        }
        
        response = client.post(f"/api/v1/datasets/{dataset_id}/search",
                             json=search_data, headers=auth_headers)
        assert response.status_code == 200
        
        results = response.json()["results"]
        assert len(results) == 1
        
        # Euclidean distance should be 5.0
        assert abs(results[0]["distance"] - 5.0) < 0.001
        # Score should be inverse-related to distance
        assert results[0]["score"] < 1.0
        
        # Clean up
        client.delete(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
    
    def test_manhattan_metric_search(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test Manhattan distance search behavior."""
        # Create dataset with manhattan metric
        dataset_data = {
            "name": "test-manhattan-search",
            "dimensions": 2,
            "metric_type": "manhattan",
            "overwrite": True
        }
        
        response = client.post("/api/v1/datasets/", json=dataset_data, headers=auth_headers)
        assert response.status_code == 201
        dataset_id = response.json()["id"]
        
        # Insert test vector
        vector_data = {
            "document_id": "manhattan-test-doc",
            "values": [1.0, 1.0]
        }
        
        response = client.post(f"/api/v1/datasets/{dataset_id}/vectors/", 
                             json=vector_data, headers=auth_headers)
        assert response.status_code == 201
        
        # Search with vector that has Manhattan distance of 4
        search_data = {
            "query_vector": [3.0, 3.0],  # Manhattan distance = |3-1| + |3-1| = 4
            "options": {"top_k": 1}
        }
        
        response = client.post(f"/api/v1/datasets/{dataset_id}/search",
                             json=search_data, headers=auth_headers)
        assert response.status_code == 200
        
        results = response.json()["results"]
        assert len(results) == 1
        
        # Manhattan distance should be 4.0
        assert abs(results[0]["distance"] - 4.0) < 0.001
        
        # Clean up
        client.delete(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
    
    def test_dot_product_metric_search(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test dot product metric search behavior."""
        # Create dataset with dot_product metric
        dataset_data = {
            "name": "test-dot-product-search",
            "dimensions": 2,
            "metric_type": "dot_product",
            "overwrite": True
        }
        
        response = client.post("/api/v1/datasets/", json=dataset_data, headers=auth_headers)
        assert response.status_code == 201
        dataset_id = response.json()["id"]
        
        # Insert test vector
        vector_data = {
            "document_id": "dot-product-test-doc",
            "values": [1.0, 2.0]
        }
        
        response = client.post(f"/api/v1/datasets/{dataset_id}/vectors/", 
                             json=vector_data, headers=auth_headers)
        assert response.status_code == 201
        
        # Search with vector that has dot product of 5
        search_data = {
            "query_vector": [1.0, 2.0],  # Dot product = 1*1 + 2*2 = 5
            "options": {"top_k": 1}
        }
        
        response = client.post(f"/api/v1/datasets/{dataset_id}/search",
                             json=search_data, headers=auth_headers)
        assert response.status_code == 200
        
        results = response.json()["results"]
        assert len(results) == 1
        
        # Dot product score should be 5.0
        assert abs(results[0]["score"] - 5.0) < 0.001
        
        # Clean up
        client.delete(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
    
    def test_hamming_metric_search(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test Hamming distance search behavior."""
        # Create dataset with hamming metric
        dataset_data = {
            "name": "test-hamming-search",
            "dimensions": 4,
            "metric_type": "hamming",
            "overwrite": True
        }
        
        response = client.post("/api/v1/datasets/", json=dataset_data, headers=auth_headers)
        assert response.status_code == 201
        dataset_id = response.json()["id"]
        
        # Insert test vector (will be binarized as [1, 1, 0, 0])
        vector_data = {
            "document_id": "hamming-test-doc",
            "values": [0.8, 0.7, 0.3, 0.2]  # Above/below 0.5 threshold
        }
        
        response = client.post(f"/api/v1/datasets/{dataset_id}/vectors/", 
                             json=vector_data, headers=auth_headers)
        assert response.status_code == 201
        
        # Search with vector that differs in 2 positions (will be binarized as [1, 0, 1, 0])
        search_data = {
            "query_vector": [0.9, 0.1, 0.6, 0.4],  # Hamming distance = 2/4 = 0.5
            "options": {"top_k": 1}
        }
        
        response = client.post(f"/api/v1/datasets/{dataset_id}/search",
                             json=search_data, headers=auth_headers)
        assert response.status_code == 200
        
        results = response.json()["results"]
        assert len(results) == 1
        
        # Hamming distance should be 0.5, so score should be 0.5
        assert abs(results[0]["score"] - 0.5) < 0.001
        assert abs(results[0]["distance"] - 0.5) < 0.001
        
        # Clean up
        client.delete(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)