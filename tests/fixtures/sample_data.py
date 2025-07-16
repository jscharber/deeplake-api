"""Sample data fixtures for testing."""

import random
from typing import List, Dict, Any


def generate_sample_vectors(count: int, dimensions: int) -> List[Dict[str, Any]]:
    """Generate sample vectors for testing."""
    vectors = []
    
    for i in range(count):
        vector = {
            "id": f"sample-vector-{i}",
            "document_id": f"sample-doc-{i // 5}",  # 5 vectors per document
            "chunk_id": f"sample-chunk-{i}",
            "values": [random.random() for _ in range(dimensions)],
            "content": f"This is sample content for vector {i}. " * 10,  # Longer content
            "content_hash": f"hash-{i}",
            "metadata": {
                "source": "sample_data",
                "category": random.choice(["tech", "science", "business", "art"]),
                "priority": str(random.choice([1, 2, 3])),
                "index": str(i)
            },
            "content_type": "text/plain",
            "language": "en",
            "chunk_index": i % 5,
            "chunk_count": 5,
            "model": "sample-embedding-model"
        }
        vectors.append(vector)
    
    return vectors


def generate_sample_datasets(count: int) -> List[Dict[str, Any]]:
    """Generate sample datasets for testing."""
    datasets = []
    
    dimensions_options = [128, 256, 512, 768, 1536]
    metric_options = ["cosine", "euclidean", "manhattan", "dot_product"]
    
    for i in range(count):
        dataset = {
            "name": f"sample-dataset-{i}",
            "description": f"Sample dataset {i} for testing purposes",
            "dimensions": random.choice(dimensions_options),
            "metric_type": random.choice(metric_options),
            "index_type": "default",
            "metadata": {
                "created_by": "sample_data_generator",
                "purpose": "testing",
                "category": random.choice(["test", "demo", "benchmark"]),
                "version": "1.0"
            },
            "overwrite": True
        }
        datasets.append(dataset)
    
    return datasets


def generate_search_queries(dimensions: int, count: int = 10) -> List[Dict[str, Any]]:
    """Generate sample search queries for testing."""
    queries = []
    
    for i in range(count):
        query = {
            "query_vector": [random.random() for _ in range(dimensions)],
            "options": {
                "top_k": random.choice([5, 10, 20, 50]),
                "threshold": random.uniform(0.1, 0.9),
                "include_content": random.choice([True, False]),
                "include_metadata": random.choice([True, False]),
                "filters": {"category": random.choice(["tech", "science", "business"])} if random.choice([True, False]) else {},
                "deduplicate": random.choice([True, False]),
                "group_by_document": random.choice([True, False])
            }
        }
        queries.append(query)
    
    return queries


def generate_sample_embeddings(text_samples: List[str], dimensions: int) -> List[List[float]]:
    """Generate sample embeddings for given text samples."""
    embeddings = []
    
    for i, text in enumerate(text_samples):
        # Simple hash-based embedding generation for testing
        # In real usage, you'd use an actual embedding model
        seed = hash(text) % 1000000
        random.seed(seed)
        embedding = [random.gauss(0, 1) for _ in range(dimensions)]
        
        # Normalize the embedding
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        embeddings.append(embedding)
    
    return embeddings


# Sample text data for testing
SAMPLE_TEXTS = [
    "Artificial intelligence is transforming the way we work and live.",
    "Machine learning algorithms can identify patterns in large datasets.",
    "Deep learning models require significant computational resources.",
    "Natural language processing enables computers to understand human language.",
    "Computer vision allows machines to interpret and analyze visual information.",
    "Robotics combines AI with mechanical engineering to create autonomous systems.",
    "Data science involves extracting insights from structured and unstructured data.",
    "Cloud computing provides scalable infrastructure for modern applications.",
    "Cybersecurity protects digital systems from threats and vulnerabilities.",
    "Blockchain technology enables secure and transparent transactions.",
    "The Internet of Things connects everyday devices to the internet.",
    "Virtual reality creates immersive digital experiences.",
    "Augmented reality overlays digital information on the real world.",
    "Quantum computing promises to solve complex problems exponentially faster.",
    "Edge computing brings processing power closer to data sources.",
    "5G networks enable faster and more reliable wireless communication.",
    "Autonomous vehicles use AI to navigate roads safely.",
    "Smart cities leverage technology to improve urban living.",
    "Renewable energy sources are becoming more efficient and affordable.",
    "Biotechnology advances are revolutionizing healthcare and medicine."
]


def get_sample_text_embeddings(dimensions: int = 128) -> List[Dict[str, Any]]:
    """Get sample vectors with text content and embeddings."""
    embeddings = generate_sample_embeddings(SAMPLE_TEXTS, dimensions)
    
    vectors = []
    for i, (text, embedding) in enumerate(zip(SAMPLE_TEXTS, embeddings)):
        vector = {
            "id": f"text-vector-{i}",
            "document_id": f"text-doc-{i // 4}",  # 4 vectors per document
            "chunk_id": f"text-chunk-{i}",
            "values": embedding,
            "content": text,
            "metadata": {
                "source": "sample_texts",
                "topic": "technology",
                "length": len(text),
                "word_count": len(text.split())
            },
            "content_type": "text/plain",
            "language": "en",
            "model": "sample-text-embedding-model"
        }
        vectors.append(vector)
    
    return vectors