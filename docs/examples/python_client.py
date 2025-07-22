"""
Python client example for Tributary AI services for DeepLake.

This example demonstrates how to use Tributary AI services for DeepLake
HTTP API with Python using the requests library.
"""

import asyncio
import httpx
import numpy as np
from typing import List, Dict, Any, Optional
import time


class DeepLakeClient:
    """Python client for Tributary AI services for DeepLake."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        jwt_token: Optional[str] = None,
        timeout: float = 30.0
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # Set up authentication headers
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"ApiKey {api_key}"
        elif jwt_token:
            self.headers["Authorization"] = f"Bearer {jwt_token}"
        else:
            raise ValueError("Either api_key or jwt_token must be provided")
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        response = await self.client.get("/api/v1/health")
        response.raise_for_status()
        return response.json()
    
    async def create_dataset(
        self,
        name: str,
        dimensions: int,
        description: str = "",
        metric_type: str = "cosine",
        index_type: str = "default",
        metadata: Optional[Dict[str, str]] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """Create a new dataset."""
        data = {
            "name": name,
            "description": description,
            "dimensions": dimensions,
            "metric_type": metric_type,
            "index_type": index_type,
            "metadata": metadata or {},
            "overwrite": overwrite
        }
        
        response = await self.client.post("/api/v1/datasets/", json=data)
        response.raise_for_status()
        return response.json()
    
    async def get_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Get dataset information."""
        response = await self.client.get(f"/api/v1/datasets/{dataset_id}")
        response.raise_for_status()
        return response.json()
    
    async def list_datasets(
        self,
        page: int = 1,
        page_size: int = 50
    ) -> List[Dict[str, Any]]:
        """List all datasets."""
        params = {"page": page, "page_size": page_size}
        response = await self.client.get("/api/v1/datasets/", params=params)
        response.raise_for_status()
        return response.json()
    
    async def delete_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Delete a dataset."""
        response = await self.client.delete(f"/api/v1/datasets/{dataset_id}")
        response.raise_for_status()
        return response.json()
    
    async def insert_vector(
        self,
        dataset_id: str,
        vector_id: str,
        document_id: str,
        values: List[float],
        content: str = "",
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Insert a single vector."""
        data = {
            "id": vector_id,
            "document_id": document_id,
            "values": values,
            "content": content,
            "metadata": metadata or {},
            **kwargs
        }
        
        response = await self.client.post(
            f"/api/v1/datasets/{dataset_id}/vectors/",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def insert_vectors_batch(
        self,
        dataset_id: str,
        vectors: List[Dict[str, Any]],
        skip_existing: bool = False,
        overwrite: bool = False,
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Insert multiple vectors in batch."""
        data = {
            "vectors": vectors,
            "skip_existing": skip_existing,
            "overwrite": overwrite
        }
        
        if batch_size:
            data["batch_size"] = batch_size
        
        response = await self.client.post(
            f"/api/v1/datasets/{dataset_id}/vectors/batch",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def search_vectors(
        self,
        dataset_id: str,
        query_vector: List[float],
        top_k: int = 10,
        threshold: Optional[float] = None,
        include_content: bool = True,
        include_metadata: bool = True,
        filters: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Search for similar vectors."""
        options = {
            "top_k": top_k,
            "include_content": include_content,
            "include_metadata": include_metadata,
            "filters": filters or {},
            **kwargs
        }
        
        if threshold is not None:
            options["threshold"] = threshold
        
        data = {
            "query_vector": query_vector,
            "options": options
        }
        
        response = await self.client.post(
            f"/api/v1/datasets/{dataset_id}/search",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def get_dataset_stats(self, dataset_id: str) -> Dict[str, Any]:
        """Get dataset statistics."""
        response = await self.client.get(f"/api/v1/datasets/{dataset_id}/stats")
        response.raise_for_status()
        return response.json()


# Example usage
async def main():
    """Example usage of the Tributary AI services for DeepLake client."""
    
    # Initialize client with API key from environment variable
    import os
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("ERROR: API_KEY environment variable is required")
        print("Usage: API_KEY=your_api_key python docs/examples/python_client.py")
        return
    
    async with DeepLakeClient(
        base_url="http://localhost:8000",
        api_key=api_key
    ) as client:
        
        print("🚀 Tributary AI services for DeepLake Python Client Example")
        print("=" * 50)
        
        # 1. Check service health
        print("\n1. Checking service health...")
        health = await client.health_check()
        print(f"Service status: {health['status']}")
        print(f"Service version: {health['version']}")
        
        # 2. Create a dataset
        print("\n2. Creating dataset...")
        dataset_name = f"python-example-{int(time.time())}"
        dataset = await client.create_dataset(
            name=dataset_name,
            dimensions=128,
            description="Example dataset created from Python client",
            metric_type="cosine",
            metadata={"source": "python_example", "version": "1.0"}
        )
        print(f"Created dataset: {dataset['name']} (ID: {dataset['id']})")
        dataset_id = dataset["id"]
        
        # 3. Generate some sample vectors
        print("\n3. Generating sample vectors...")
        vectors = []
        sample_texts = [
            "Artificial intelligence is transforming technology",
            "Machine learning enables pattern recognition",
            "Deep learning uses neural networks",
            "Natural language processing understands text",
            "Computer vision analyzes images"
        ]
        
        for i, text in enumerate(sample_texts):
            # Generate random vector (in real usage, use an embedding model)
            vector_values = np.random.random(128).tolist()
            
            vector = {
                "id": f"example-vector-{i}",
                "document_id": f"example-doc-{i}",
                "chunk_id": f"example-chunk-{i}",
                "values": vector_values,
                "content": text,
                "metadata": {
                    "category": "ai_tech",
                    "index": str(i),
                    "length": str(len(text))
                },
                "content_type": "text/plain",
                "language": "en",
                "model": "example-embedding-model"
            }
            vectors.append(vector)
        
        # 4. Insert vectors in batch
        print(f"\n4. Inserting {len(vectors)} vectors...")
        insert_result = await client.insert_vectors_batch(dataset_id, vectors)
        print(f"Inserted: {insert_result['inserted_count']} vectors")
        print(f"Failed: {insert_result['failed_count']} vectors")
        print(f"Processing time: {insert_result['processing_time_ms']:.2f} ms")
        
        # 5. Perform vector search
        print("\n5. Performing vector search...")
        query_vector = np.random.random(128).tolist()
        
        search_result = await client.search_vectors(
            dataset_id=dataset_id,
            query_vector=query_vector,
            top_k=3,
            include_content=True,
            include_metadata=True
        )
        
        print(f"Found {search_result['total_found']} similar vectors")
        print(f"Query time: {search_result['query_time_ms']:.2f} ms")
        
        # Display results
        for i, result in enumerate(search_result['results']):
            print(f"\nResult {i + 1}:")
            print(f"  Score: {result['score']:.4f}")
            print(f"  Distance: {result['distance']:.4f}")
            print(f"  Content: {result['vector']['content'][:50]}...")
            print(f"  Metadata: {result['vector']['metadata']}")
        
        # 6. Get dataset statistics
        print("\n6. Getting dataset statistics...")
        stats = await client.get_dataset_stats(dataset_id)
        print(f"Vector count: {stats['dataset']['vector_count']}")
        print(f"Storage size: {stats['dataset']['storage_size']} bytes")
        
        # 7. List all datasets
        print("\n7. Listing all datasets...")
        datasets = await client.list_datasets()
        print(f"Total datasets: {len(datasets)}")
        for ds in datasets:
            print(f"  - {ds['name']} ({ds['dimensions']}D, {ds['vector_count']} vectors)")
        
        # 8. Clean up - delete the dataset
        print(f"\n8. Cleaning up - deleting dataset {dataset_name}...")
        delete_result = await client.delete_dataset(dataset_id)
        print(f"Delete result: {delete_result['message']}")
        
        print("\n✅ Example completed successfully!")


# Synchronous client example
class SyncDeepLakeClient:
    """Synchronous version of the Tributary AI services for DeepLake client using requests."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        jwt_token: Optional[str] = None,
        timeout: float = 30.0
    ):
        import requests
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set up authentication headers
        if api_key:
            self.session.headers["Authorization"] = f"ApiKey {api_key}"
        elif jwt_token:
            self.session.headers["Authorization"] = f"Bearer {jwt_token}"
        else:
            raise ValueError("Either api_key or jwt_token must be provided")
        
        self.session.headers["Content-Type"] = "application/json"
    
    def create_dataset(self, name: str, dimensions: int, **kwargs) -> Dict[str, Any]:
        """Create a new dataset (synchronous)."""
        data = {
            "name": name,
            "dimensions": dimensions,
            **kwargs
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/datasets/",
            json=data,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def search_vectors(self, dataset_id: str, query_vector: List[float], **kwargs) -> Dict[str, Any]:
        """Search for similar vectors (synchronous)."""
        data = {
            "query_vector": query_vector,
            "options": kwargs
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/datasets/{dataset_id}/search",
            json=data,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()


def sync_example():
    """Synchronous example usage."""
    import os
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("ERROR: API_KEY environment variable is required")
        print("Usage: API_KEY=your_api_key python docs/examples/python_client.py")
        return
    
    client = SyncDeepLakeClient(api_key=api_key)
    
    # Create dataset
    dataset = client.create_dataset(
        name="sync-example",
        dimensions=64,
        description="Synchronous client example"
    )
    print(f"Created dataset: {dataset['name']}")
    
    # Search (with empty dataset)
    query_vector = [0.1] * 64
    results = client.search_vectors(
        dataset_id=dataset["id"],
        query_vector=query_vector,
        top_k=5
    )
    print(f"Search returned {len(results['results'])} results")


if __name__ == "__main__":
    # Run async example
    print("Running async example...")
    asyncio.run(main())
    
    # Uncomment to run sync example
    # print("\nRunning sync example...")
    # sync_example()