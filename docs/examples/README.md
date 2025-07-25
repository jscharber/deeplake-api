# Examples & Tutorials

This directory contains comprehensive examples and tutorials for using the Tributary AI Service for DeepLake. Whether you're just getting started or looking for advanced use cases, you'll find practical code examples here.

## 📚 Quick Navigation

### Getting Started
- [Basic Usage](./basic-usage.md) - Your first vectors and searches
- [Python SDK Tutorial](./python-sdk-tutorial.md) - Complete Python SDK guide
- [JavaScript Tutorial](./javascript-tutorial.md) - Frontend integration
- [cURL Examples](./curl-examples.md) - HTTP API with cURL

### Common Use Cases
- [Document Search](./document-search.md) - Build a document search engine
- [Image Similarity](./image-similarity.md) - Find similar images
- [Recommendation System](./recommendation-system.md) - Build recommendations
- [Chatbot with Context](./chatbot-context.md) - Contextual chatbot

### Advanced Examples
- [Hybrid Search](./hybrid-search.md) - Vector + text search
- [Metadata Filtering](./metadata-filtering.md) - Complex filtering
- [Batch Operations](./batch-operations.md) - Efficient bulk operations
- [Real-time Search](./real-time-search.md) - Streaming search results

### Integration Examples
- [FastAPI Integration](./fastapi-integration.md) - Web API with FastAPI
- [React Frontend](./react-frontend.md) - React search interface
- [Jupyter Notebooks](./jupyter-notebooks.md) - Data science workflows
- [Streamlit App](./streamlit-app.md) - Interactive web apps

### Language Examples
- [Python](./python/) - Python examples and notebooks
- [JavaScript](./javascript/) - Node.js and browser examples
- [Go](./go/) - Go client examples
- [Java](./java/) - Java SDK examples

## 🚀 Quick Start Examples

### Python: Basic Vector Operations

```python
import asyncio
from deeplake_api import DeepLakeClient

async def main():
    # Initialize client
    client = DeepLakeClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )
    
    # Create dataset
    dataset = await client.create_dataset(
        name="quickstart",
        embedding_dimension=1536,
        description="Quick start example"
    )
    
    # Add vectors
    await client.add_vectors(
        dataset_id="quickstart",
        vectors=[[0.1] * 1536, [0.2] * 1536],
        metadata=[
            {"title": "First Document", "category": "tech"},
            {"title": "Second Document", "category": "science"}
        ]
    )
    
    # Search
    results = await client.search(
        dataset_id="quickstart",
        query_vector=[0.15] * 1536,
        k=5
    )
    
    print(f"Found {len(results)} similar vectors")
    for result in results:
        print(f"Score: {result.score:.3f}, Title: {result.metadata['title']}")

asyncio.run(main())
```

### JavaScript: Web Search Interface

```javascript
import { DeepLakeClient } from '@deeplake/api-client';

const client = new DeepLakeClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

async function searchDocuments(query) {
  try {
    // Get embedding for the query
    const embedding = await getEmbedding(query);
    
    // Search similar documents
    const results = await client.search({
      datasetId: 'documents',
      queryVector: embedding,
      k: 10,
      filter: {
        category: { $in: ['tech', 'science'] }
      }
    });
    
    return results.map(result => ({
      title: result.metadata.title,
      score: result.score,
      url: result.metadata.url
    }));
  } catch (error) {
    console.error('Search failed:', error);
    return [];
  }
}
```

### cURL: HTTP API

```bash
# Create dataset
curl -X POST "http://localhost:8000/api/v1/datasets" \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "example-dataset",
    "embedding_dimension": 1536,
    "description": "Example dataset"
  }'

# Add vectors
curl -X POST "http://localhost:8000/api/v1/datasets/example-dataset/vectors" \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
    "metadata": [
      {"title": "Document 1", "category": "tech"},
      {"title": "Document 2", "category": "science"}
    ]
  }'

# Search
curl -X POST "http://localhost:8000/api/v1/datasets/example-dataset/search" \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query_vector": [0.15, 0.25, 0.35],
    "k": 5,
    "filter": {"category": "tech"}
  }'
```

## 📖 Detailed Examples

### 1. Document Search Engine

Build a complete document search engine with semantic search capabilities:

```python
# examples/document-search.py
import asyncio
import openai
from deeplake_api import DeepLakeClient

class DocumentSearchEngine:
    def __init__(self, api_key, openai_key):
        self.client = DeepLakeClient(
            base_url="http://localhost:8000",
            api_key=api_key
        )
        openai.api_key = openai_key
        self.dataset_id = "documents"
    
    async def setup(self):
        """Initialize the search engine"""
        await self.client.create_dataset(
            name=self.dataset_id,
            embedding_dimension=1536,
            description="Document search engine"
        )
    
    async def index_document(self, title, content, metadata=None):
        """Index a document for search"""
        # Generate embedding
        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=f"{title}\n\n{content}"
        )
        embedding = response['data'][0]['embedding']
        
        # Add to dataset
        document_metadata = {
            "title": title,
            "content": content,
            **(metadata or {})
        }
        
        await self.client.add_vectors(
            dataset_id=self.dataset_id,
            vectors=[embedding],
            metadata=[document_metadata]
        )
    
    async def search(self, query, k=10, filter_dict=None):
        """Search for similar documents"""
        # Generate query embedding
        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=query
        )
        query_embedding = response['data'][0]['embedding']
        
        # Search
        results = await self.client.search(
            dataset_id=self.dataset_id,
            query_vector=query_embedding,
            k=k,
            filter=filter_dict
        )
        
        return [{
            "title": result.metadata["title"],
            "content": result.metadata["content"],
            "score": result.score
        } for result in results]

# Usage
async def main():
    engine = DocumentSearchEngine("your-api-key", "your-openai-key")
    await engine.setup()
    
    # Index documents
    await engine.index_document(
        "Introduction to Machine Learning",
        "Machine learning is a subset of artificial intelligence...",
        {"category": "tech", "author": "John Doe"}
    )
    
    # Search
    results = await engine.search("AI and neural networks", k=5)
    for result in results:
        print(f"Title: {result['title']}, Score: {result['score']:.3f}")

asyncio.run(main())
```

### 2. Image Similarity Search

Find similar images using visual embeddings:

```python
# examples/image-similarity.py
import asyncio
import numpy as np
from PIL import Image
from sentence_transformers import SentenceTransformer
from deeplake_api import DeepLakeClient

class ImageSimilaritySearch:
    def __init__(self, api_key):
        self.client = DeepLakeClient(
            base_url="http://localhost:8000",
            api_key=api_key
        )
        self.model = SentenceTransformer('clip-ViT-B-32')
        self.dataset_id = "images"
    
    async def setup(self):
        """Initialize image search"""
        await self.client.create_dataset(
            name=self.dataset_id,
            embedding_dimension=512,  # CLIP embedding dimension
            description="Image similarity search"
        )
    
    async def index_image(self, image_path, metadata=None):
        """Index an image for search"""
        # Load and encode image
        image = Image.open(image_path)
        embedding = self.model.encode(image)
        
        # Add to dataset
        image_metadata = {
            "path": image_path,
            "filename": image_path.split("/")[-1],
            **(metadata or {})
        }
        
        await self.client.add_vectors(
            dataset_id=self.dataset_id,
            vectors=[embedding.tolist()],
            metadata=[image_metadata]
        )
    
    async def search_by_image(self, image_path, k=10):
        """Search for similar images"""
        # Encode query image
        image = Image.open(image_path)
        query_embedding = self.model.encode(image)
        
        # Search
        results = await self.client.search(
            dataset_id=self.dataset_id,
            query_vector=query_embedding.tolist(),
            k=k
        )
        
        return [{
            "filename": result.metadata["filename"],
            "path": result.metadata["path"],
            "score": result.score
        } for result in results]
    
    async def search_by_text(self, text, k=10):
        """Search images by text description"""
        # Encode text query
        query_embedding = self.model.encode(text)
        
        # Search
        results = await self.client.search(
            dataset_id=self.dataset_id,
            query_vector=query_embedding.tolist(),
            k=k
        )
        
        return [{
            "filename": result.metadata["filename"],
            "path": result.metadata["path"],
            "score": result.score
        } for result in results]

# Usage
async def main():
    search_engine = ImageSimilaritySearch("your-api-key")
    await search_engine.setup()
    
    # Index images
    await search_engine.index_image(
        "images/cat.jpg",
        {"category": "animals", "type": "cat"}
    )
    
    # Search by image
    results = await search_engine.search_by_image("query_image.jpg")
    
    # Search by text
    text_results = await search_engine.search_by_text("cute cat photos")
    
    print(f"Found {len(results)} similar images")

asyncio.run(main())
```

### 3. Hybrid Search Example

Combine vector similarity with text search:

```python
# examples/hybrid-search.py
import asyncio
from deeplake_api import DeepLakeClient

async def hybrid_search_example():
    client = DeepLakeClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )
    
    # Create dataset
    await client.create_dataset(
        name="hybrid-search",
        embedding_dimension=1536,
        description="Hybrid search example"
    )
    
    # Add documents with both vectors and text
    documents = [
        {
            "vector": [0.1] * 1536,
            "metadata": {
                "title": "Machine Learning Fundamentals",
                "content": "Introduction to machine learning algorithms",
                "category": "tech",
                "tags": ["ml", "ai", "algorithms"]
            }
        },
        {
            "vector": [0.2] * 1536,
            "metadata": {
                "title": "Deep Learning with Python",
                "content": "Neural networks and deep learning techniques",
                "category": "tech",
                "tags": ["deep-learning", "python", "neural-networks"]
            }
        }
    ]
    
    for doc in documents:
        await client.add_vectors(
            dataset_id="hybrid-search",
            vectors=[doc["vector"]],
            metadata=[doc["metadata"]]
        )
    
    # Perform hybrid search
    results = await client.hybrid_search(
        dataset_id="hybrid-search",
        query_vector=[0.15] * 1536,
        query_text="machine learning neural networks",
        k=10,
        alpha=0.7,  # 70% vector, 30% text
        filter={
            "category": "tech",
            "tags": {"$in": ["ml", "ai"]}
        }
    )
    
    print("Hybrid Search Results:")
    for result in results:
        print(f"Title: {result.metadata['title']}")
        print(f"Combined Score: {result.combined_score:.3f}")
        print(f"Vector Score: {result.vector_score:.3f}")
        print(f"Text Score: {result.text_score:.3f}")
        print("---")

asyncio.run(hybrid_search_example())
```

### 4. Real-time Search with Streaming

Handle real-time search with streaming results:

```python
# examples/real-time-search.py
import asyncio
from deeplake_api import DeepLakeClient

async def real_time_search():
    client = DeepLakeClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )
    
    # Stream search results
    async for result in client.search_stream(
        dataset_id="documents",
        query_vector=[0.1] * 1536,
        k=100,
        batch_size=10
    ):
        print(f"Received result: {result.metadata['title']}, Score: {result.score}")
        
        # Process result in real-time
        if result.score > 0.9:
            print("High confidence match found!")
            # Take action on high-confidence results
            await process_high_confidence_result(result)

async def process_high_confidence_result(result):
    """Process high-confidence search results"""
    print(f"Processing high-confidence result: {result.metadata['title']}")
    # Add your processing logic here

asyncio.run(real_time_search())
```

## 🛠️ Development Tools

### Testing Framework

```python
# examples/testing-framework.py
import asyncio
import pytest
from deeplake_api import DeepLakeClient

class TestDeepLakeAPI:
    def __init__(self):
        self.client = DeepLakeClient(
            base_url="http://localhost:8000",
            api_key="test-api-key"
        )
        self.test_dataset = "test-dataset"
    
    async def setup_test_data(self):
        """Set up test data"""
        await self.client.create_dataset(
            name=self.test_dataset,
            embedding_dimension=128,
            description="Test dataset"
        )
        
        # Add test vectors
        test_vectors = [[0.1] * 128, [0.2] * 128, [0.3] * 128]
        test_metadata = [
            {"id": "test1", "category": "A"},
            {"id": "test2", "category": "B"},
            {"id": "test3", "category": "A"}
        ]
        
        await self.client.add_vectors(
            dataset_id=self.test_dataset,
            vectors=test_vectors,
            metadata=test_metadata
        )
    
    async def test_vector_search(self):
        """Test vector search functionality"""
        results = await self.client.search(
            dataset_id=self.test_dataset,
            query_vector=[0.15] * 128,
            k=5
        )
        
        assert len(results) > 0
        assert all(hasattr(result, 'score') for result in results)
        assert all(hasattr(result, 'metadata') for result in results)
        
        print("✅ Vector search test passed")
    
    async def test_metadata_filtering(self):
        """Test metadata filtering"""
        results = await self.client.search(
            dataset_id=self.test_dataset,
            query_vector=[0.15] * 128,
            k=5,
            filter={"category": "A"}
        )
        
        assert all(result.metadata["category"] == "A" for result in results)
        
        print("✅ Metadata filtering test passed")
    
    async def run_all_tests(self):
        """Run all tests"""
        await self.setup_test_data()
        await self.test_vector_search()
        await self.test_metadata_filtering()
        print("✅ All tests passed!")

# Run tests
async def main():
    tester = TestDeepLakeAPI()
    await tester.run_all_tests()

asyncio.run(main())
```

### Performance Benchmarking

```python
# examples/performance-benchmark.py
import asyncio
import time
import statistics
from deeplake_api import DeepLakeClient

async def benchmark_search_performance():
    client = DeepLakeClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )
    
    dataset_id = "benchmark-dataset"
    
    # Create test dataset
    await client.create_dataset(
        name=dataset_id,
        embedding_dimension=1536,
        description="Performance benchmark dataset"
    )
    
    # Add test vectors
    print("Adding test vectors...")
    batch_size = 100
    total_vectors = 1000
    
    for i in range(0, total_vectors, batch_size):
        vectors = [[0.1 + i/1000] * 1536 for _ in range(batch_size)]
        metadata = [{"id": f"doc_{i+j}", "batch": i//batch_size} 
                   for j in range(batch_size)]
        
        await client.add_vectors(
            dataset_id=dataset_id,
            vectors=vectors,
            metadata=metadata
        )
    
    print(f"Added {total_vectors} vectors")
    
    # Benchmark search performance
    print("Benchmarking search performance...")
    query_times = []
    
    for i in range(50):  # Run 50 search queries
        query_vector = [0.5 + i/100] * 1536
        
        start_time = time.time()
        results = await client.search(
            dataset_id=dataset_id,
            query_vector=query_vector,
            k=10
        )
        end_time = time.time()
        
        query_time = end_time - start_time
        query_times.append(query_time)
        
        print(f"Query {i+1}: {query_time:.3f}s, Results: {len(results)}")
    
    # Calculate statistics
    avg_time = statistics.mean(query_times)
    median_time = statistics.median(query_times)
    min_time = min(query_times)
    max_time = max(query_times)
    
    print(f"\nPerformance Statistics:")
    print(f"Average query time: {avg_time:.3f}s")
    print(f"Median query time: {median_time:.3f}s")
    print(f"Min query time: {min_time:.3f}s")
    print(f"Max query time: {max_time:.3f}s")
    print(f"Queries per second: {1/avg_time:.1f}")

asyncio.run(benchmark_search_performance())
```

## 📁 Directory Structure

```
examples/
├── README.md                 # This file
├── basic-usage.md           # Basic usage examples
├── python-sdk-tutorial.md   # Python SDK tutorial
├── javascript-tutorial.md   # JavaScript tutorial
├── curl-examples.md         # cURL examples
├── document-search.md       # Document search engine
├── image-similarity.md      # Image similarity search
├── recommendation-system.md # Recommendation system
├── chatbot-context.md      # Contextual chatbot
├── hybrid-search.md        # Hybrid search examples
├── metadata-filtering.md   # Complex filtering
├── batch-operations.md     # Batch operations
├── real-time-search.md     # Real-time search
├── fastapi-integration.md  # FastAPI integration
├── react-frontend.md       # React frontend
├── jupyter-notebooks.md    # Jupyter notebooks
├── streamlit-app.md        # Streamlit app
├── python/                 # Python examples
│   ├── basic_operations.py
│   ├── advanced_search.py
│   ├── batch_processing.py
│   └── notebooks/
├── javascript/             # JavaScript examples
│   ├── basic_operations.js
│   ├── web_search.js
│   └── react_example/
├── go/                     # Go examples
│   ├── basic_operations.go
│   └── batch_processing.go
├── java/                   # Java examples
│   ├── BasicOperations.java
│   └── BatchProcessing.java
└── notebooks/              # Jupyter notebooks
    ├── getting_started.ipynb
    ├── advanced_search.ipynb
    └── performance_analysis.ipynb
```

## 🔗 Related Documentation

- [API Reference](../api/http/README.md)
- [Python SDK](../sdk/python.md)
- [Authentication](../authentication.md)
- [Configuration](../configuration.md)
- [Deployment](../deployment/)

## 🆘 Need Help?

- **Issues**: [GitHub Issues](https://github.com/Tributary-ai-services/deeplake-api/issues)
- **Community**: [Discord](https://discord.gg/your-discord)
- **Documentation**: [Full Documentation](../README.md)
- **Support**: [support@yourcompany.com](mailto:support@yourcompany.com)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](../development/contributing.md) for details on:
- Adding new examples
- Improving existing examples
- Reporting issues
- Submitting pull requests

## 📄 License

These examples are licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.