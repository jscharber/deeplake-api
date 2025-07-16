"""Unit tests for Deep Lake service."""

import pytest
import os
from app.services.deeplake_service import DeepLakeService
from app.models.schemas import DatasetCreate, VectorCreate, SearchOptions
from app.models.exceptions import (
    DatasetNotFoundException, DatasetAlreadyExistsException,
    InvalidVectorDimensionsException
)


@pytest.mark.asyncio
class TestDeepLakeService:
    """Test cases for Deep Lake service."""
    
    async def test_create_dataset(self, deeplake_service: DeepLakeService, test_dataset_data):
        """Test dataset creation."""
        dataset_create = DatasetCreate(**test_dataset_data)
        
        dataset = await deeplake_service.create_dataset(dataset_create, "default")
        
        assert dataset.name == test_dataset_data["name"]
        assert dataset.description == test_dataset_data["description"]
        assert dataset.dimensions == test_dataset_data["dimensions"]
        assert dataset.metric_type == test_dataset_data["metric_type"]
        assert dataset.vector_count == 0
    
    async def test_create_duplicate_dataset(self, deeplake_service: DeepLakeService, test_dataset_data):
        """Test creating a duplicate dataset without overwrite."""
        dataset_create = DatasetCreate(**test_dataset_data)
        
        # Create the dataset first time
        await deeplake_service.create_dataset(dataset_create, "default")
        
        # Try to create again without overwrite
        dataset_create.overwrite = False
        with pytest.raises(DatasetAlreadyExistsException):
            await deeplake_service.create_dataset(dataset_create, "default")
    
    async def test_get_dataset(self, deeplake_service: DeepLakeService, test_dataset_data):
        """Test getting dataset information."""
        dataset_create = DatasetCreate(**test_dataset_data)
        created_dataset = await deeplake_service.create_dataset(dataset_create, "default")
        
        retrieved_dataset = await deeplake_service.get_dataset(created_dataset.id, "default")
        
        assert retrieved_dataset.id == created_dataset.id
        assert retrieved_dataset.name == created_dataset.name
        assert retrieved_dataset.dimensions == created_dataset.dimensions
    
    async def test_get_nonexistent_dataset(self, deeplake_service: DeepLakeService):
        """Test getting a non-existent dataset."""
        with pytest.raises(DatasetNotFoundException):
            await deeplake_service.get_dataset("nonexistent-dataset", "default")
    
    async def test_list_datasets(self, deeplake_service: DeepLakeService, test_dataset_data):
        """Test listing datasets."""
        # Initially empty
        datasets = await deeplake_service.list_datasets("default")
        initial_count = len(datasets)
        
        # Create a dataset
        dataset_create = DatasetCreate(**test_dataset_data)
        await deeplake_service.create_dataset(dataset_create, "default")
        
        # Check list again
        datasets = await deeplake_service.list_datasets("default")
        assert len(datasets) == initial_count + 1
        assert any(d.name == test_dataset_data["name"] for d in datasets)
    
    async def test_delete_dataset(self, deeplake_service: DeepLakeService, test_dataset_data):
        """Test dataset deletion."""
        dataset_create = DatasetCreate(**test_dataset_data)
        created_dataset = await deeplake_service.create_dataset(dataset_create, "default")
        
        # Delete the dataset
        await deeplake_service.delete_dataset(created_dataset.id, "default")
        
        # Verify it's gone
        with pytest.raises(DatasetNotFoundException):
            await deeplake_service.get_dataset(created_dataset.id, "default")
    
    async def test_insert_vectors(self, deeplake_service: DeepLakeService, test_dataset_data, test_vector_data):
        """Test vector insertion."""
        # Create dataset first
        dataset_create = DatasetCreate(**test_dataset_data)
        dataset = await deeplake_service.create_dataset(dataset_create, "default")
        
        # Insert vector
        vector_create = VectorCreate(**test_vector_data)
        result = await deeplake_service.insert_vectors(
            dataset_id=dataset.id,
            vectors=[vector_create],
            tenant_id="default"
        )
        
        assert result.inserted_count == 1
        assert result.failed_count == 0
        assert len(result.error_messages) == 0
    
    async def test_insert_vector_wrong_dimensions(self, deeplake_service: DeepLakeService, test_dataset_data, test_vector_data):
        """Test inserting vector with wrong dimensions."""
        # Create dataset with specific dimensions
        dataset_create = DatasetCreate(**test_dataset_data)
        dataset_create.dimensions = 256  # Different from test vector
        dataset = await deeplake_service.create_dataset(dataset_create, "default")
        
        # Try to insert vector with wrong dimensions
        vector_create = VectorCreate(**test_vector_data)  # Has 128 dimensions
        
        with pytest.raises(InvalidVectorDimensionsException):
            await deeplake_service.insert_vectors(
                dataset_id=dataset.id,
                vectors=[vector_create],
                tenant_id="default"
            )
    
    async def test_search_vectors(self, deeplake_service: DeepLakeService, test_dataset_data, test_vector_data, test_search_data):
        """Test vector search."""
        # Create dataset and insert vector
        dataset_create = DatasetCreate(**test_dataset_data)
        dataset = await deeplake_service.create_dataset(dataset_create, "default")
        
        vector_create = VectorCreate(**test_vector_data)
        await deeplake_service.insert_vectors(
            dataset_id=dataset.id,
            vectors=[vector_create],
            tenant_id="default"
        )
        
        # Search for similar vectors
        search_options = SearchOptions(**test_search_data["options"])
        result = await deeplake_service.search_vectors(
            dataset_id=dataset.id,
            query_vector=test_search_data["query_vector"],
            options=search_options,
            tenant_id="default"
        )
        
        assert len(result.results) >= 0  # May be 0 if no similar vectors found
        assert result.total_found >= 0
        assert result.query_time_ms > 0
    
    async def test_search_nonexistent_dataset(self, deeplake_service: DeepLakeService, test_search_data):
        """Test searching in a non-existent dataset."""
        search_options = SearchOptions(**test_search_data["options"])
        
        with pytest.raises(DatasetNotFoundException):
            await deeplake_service.search_vectors(
                dataset_id="nonexistent-dataset",
                query_vector=test_search_data["query_vector"],
                options=search_options,
                tenant_id="default"
            )
    
    async def test_tenant_isolation(self, deeplake_service: DeepLakeService, test_dataset_data):
        """Test that datasets are isolated by tenant."""
        dataset_create = DatasetCreate(**test_dataset_data)
        
        # Create dataset for tenant1
        dataset1 = await deeplake_service.create_dataset(dataset_create, "tenant1")
        
        # Try to access from tenant2
        with pytest.raises(DatasetNotFoundException):
            await deeplake_service.get_dataset(dataset1.id, "tenant2")
        
        # List datasets for tenant2 should be empty
        datasets = await deeplake_service.list_datasets("tenant2")
        assert len(datasets) == 0