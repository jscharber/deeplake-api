# Frequently Asked Questions (FAQ)

This document answers the most common questions about the Tributary AI Service for DeepLake.

## 🎯 General Questions

### What is the Tributary AI Service for DeepLake?

The Tributary AI Service for DeepLake is a universal vector database service that provides HTTP and gRPC APIs for storing, searching, and managing high-dimensional vectors. It's built on top of DeepLake and designed for production use with features like multi-tenancy, rate limiting, and comprehensive monitoring.

### What can I use it for?

Common use cases include:
- **Semantic Search**: Find documents, images, or other content by meaning
- **Recommendation Systems**: Build personalized recommendations
- **Similarity Search**: Find similar items in large datasets
- **RAG Applications**: Retrieval-Augmented Generation for AI applications
- **Content Moderation**: Detect similar or duplicate content
- **Fraud Detection**: Identify suspicious patterns in data

### How does it compare to other vector databases?

| Feature | Tributary AI Service | Pinecone | Weaviate | Qdrant |
|---------|-------------|----------|----------|--------|
| **Open Source** | ✅ | ❌ | ✅ | ✅ |
| **Self-hosted** | ✅ | ❌ | ✅ | ✅ |
| **Multi-tenancy** | ✅ | ✅ | ✅ | ✅ |
| **Hybrid Search** | ✅ | ❌ | ✅ | ✅ |
| **Python SDK** | ✅ | ✅ | ✅ | ✅ |
| **REST API** | ✅ | ✅ | ✅ | ✅ |
| **gRPC API** | ✅ | ❌ | ✅ | ✅ |

## 🚀 Getting Started

### How do I get started?

1. **Install**: Use Docker or follow the [installation guide](./installation.md)
2. **Get API Key**: Contact your administrator for an API key
3. **Create Dataset**: Create your first dataset via API
4. **Add Vectors**: Add some vectors with metadata
5. **Search**: Perform your first similarity search

See our [Quick Start Guide](./quickstart.md) for detailed instructions.

### What are the system requirements?

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 10GB
- Network: 1Gbps

**Recommended for Production:**
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 100GB+ SSD
- Network: 10Gbps+

### How do I get an API key?

API keys are managed by your system administrator. Contact them to:
1. Create a new API key
2. Set appropriate permissions
3. Configure rate limits
4. Set up tenant isolation

## 🔐 Authentication & Security

### How does authentication work?

The API uses API key authentication with the following format:
```bash
curl -H "Authorization: ApiKey your-api-key-here" \
     http://localhost:8000/api/v1/datasets
```

### Are there different types of API keys?

Yes, there are several types:
- **User Keys**: For individual users with limited permissions
- **Service Keys**: For applications with specific permissions
- **Admin Keys**: For administrative operations
- **Read-only Keys**: For read-only access

### How do I secure my API key?

- **Never commit API keys to version control**
- **Use environment variables** for API keys
- **Rotate keys regularly** (every 90 days)
- **Use different keys for different environments**
- **Monitor key usage** for suspicious activity

### Is data encrypted?

Yes:
- **Data in transit**: TLS 1.3 encryption
- **Data at rest**: AES-256 encryption
- **API keys**: Hashed and salted storage
- **Backups**: Encrypted backups

## 📊 Vectors and Embeddings

### What vector dimensions are supported?

- **Minimum**: 1 dimension
- **Maximum**: 4096 dimensions
- **Common sizes**: 384, 768, 1536 (OpenAI), 1024
- **Recommendation**: Use consistent dimensions within a dataset

### What embedding models can I use?

Popular embedding models:
- **OpenAI**: text-embedding-ada-002 (1536 dims)
- **Sentence Transformers**: all-MiniLM-L6-v2 (384 dims)
- **Hugging Face**: Various models (128-1024 dims)
- **Custom**: Your own trained embeddings

### How do I generate embeddings?

```python
# OpenAI embeddings
import openai

response = openai.Embedding.create(
    model="text-embedding-ada-002",
    input="Your text here"
)
embedding = response['data'][0]['embedding']

# Sentence Transformers
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode("Your text here")
```

### Can I use different embedding models in the same dataset?

No, all vectors in a dataset must have the same dimensions. If you need different models:
1. Create separate datasets for each model
2. Use a consistent embedding model across your application
3. Consider using a higher-dimensional model that works for all content

## 🔍 Search and Retrieval

### What distance metrics are supported?

- **Cosine**: Measures angle between vectors (default)
- **Euclidean**: Measures straight-line distance
- **Dot Product**: Measures similarity via dot product
- **Manhattan**: L1 distance
- **Hamming**: For binary vectors

### How do I choose the right distance metric?

- **Cosine**: Best for text embeddings and normalized vectors
- **Euclidean**: Good for image embeddings and spatial data
- **Dot Product**: When vectors are already normalized
- **Manhattan**: For high-dimensional sparse data
- **Hamming**: For binary embeddings

### What is hybrid search?

Hybrid search combines vector similarity with text search:

```python
# Hybrid search example
results = await client.hybrid_search(
    dataset_id="documents",
    query_vector=[0.1, 0.2, ...],  # Vector component
    query_text="machine learning",  # Text component
    alpha=0.7,  # 70% vector, 30% text
    k=10
)
```

### How fast is search?

Performance depends on:
- **Dataset size**: Larger datasets = slower search
- **Vector dimensions**: Higher dimensions = slower search
- **Index type**: HNSW > IVF > Flat for speed
- **k value**: More results = slower search

Typical performance:
- **Small datasets** (<10K vectors): <10ms
- **Medium datasets** (10K-1M vectors): 10-100ms
- **Large datasets** (>1M vectors): 100ms-1s

## 📈 Performance and Scaling

### How many vectors can I store?

- **Technical limit**: Billions of vectors
- **Practical limits**: Depends on resources and performance needs
- **Recommendation**: Start small and scale based on usage

### How do I optimize performance?

1. **Use appropriate indexing**: HNSW for most cases
2. **Optimize vector dimensions**: Use smallest effective dimension
3. **Use metadata filtering**: Reduce search space
4. **Batch operations**: Use batch endpoints for bulk operations
5. **Caching**: Enable Redis caching
6. **Resources**: Allocate sufficient CPU and memory

### Can I scale horizontally?

Yes, the API supports horizontal scaling:
- **Load balancing**: Multiple API instances
- **Database sharding**: Distribute data across instances
- **Caching**: Shared Redis cache
- **Auto-scaling**: Kubernetes HPA

### What are the rate limits?

Default rate limits (per tenant):
- **Requests per minute**: 1,000
- **Requests per hour**: 50,000
- **Requests per day**: 1,000,000
- **Burst size**: 100

Enterprise customers can request higher limits.

## 💾 Data Management

### How do I backup my data?

The API provides automatic backups:
- **Frequency**: Daily by default
- **Retention**: 30 days by default
- **Storage**: S3 or local storage
- **Compression**: Automatic compression

Manual backups:
```bash
# Create backup
curl -X POST "http://localhost:8000/api/v1/backups" \
  -H "Authorization: ApiKey your-api-key" \
  -d '{"type": "full", "description": "Manual backup"}'
```

### How do I export my data?

```bash
# Export dataset
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/export" \
  -H "Authorization: ApiKey your-api-key" \
  -d '{"format": "json", "include_vectors": true}'
```

Supported formats:
- **JSON**: Human-readable, all features
- **CSV**: Tabular format, metadata only
- **Parquet**: Efficient binary format

### Can I import data from other systems?

Yes, the API supports importing from:
- **JSON files**: Native format
- **CSV files**: With proper schema
- **Parquet files**: Efficient for large datasets
- **Other vector databases**: Via custom scripts

### How do I delete data?

```bash
# Delete specific vectors
curl -X DELETE "http://localhost:8000/api/v1/datasets/my-dataset/vectors/vector-id" \
  -H "Authorization: ApiKey your-api-key"

# Delete entire dataset
curl -X DELETE "http://localhost:8000/api/v1/datasets/my-dataset" \
  -H "Authorization: ApiKey your-api-key"
```

## 🛠️ Development and Integration

### What SDKs are available?

- **Python**: Full-featured async SDK
- **JavaScript**: Browser and Node.js support
- **Go**: High-performance SDK
- **Java**: Enterprise-ready SDK
- **REST API**: Use any HTTP client

### How do I integrate with my application?

1. **Install SDK**: `pip install deeplake-api-client`
2. **Initialize client**: Provide API key and base URL
3. **Create dataset**: Define your data schema
4. **Add vectors**: Insert your embeddings
5. **Search**: Implement search functionality

### Are there code examples?

Yes! Check out our [examples directory](./examples/README.md):
- Basic usage examples
- Integration tutorials
- Production patterns
- Performance optimization

### How do I test my integration?

```python
# Test script
import asyncio
from deeplake_api import DeepLakeClient

async def test_integration():
    client = DeepLakeClient(api_key="your-api-key")
    
    # Test dataset creation
    dataset = await client.create_dataset(
        name="test-dataset",
        embedding_dimension=384
    )
    
    # Test vector operations
    await client.add_vectors(
        dataset_id="test-dataset",
        vectors=[[0.1] * 384],
        metadata=[{"test": True}]
    )
    
    # Test search
    results = await client.search(
        dataset_id="test-dataset",
        query_vector=[0.1] * 384,
        k=1
    )
    
    print(f"Test passed: {len(results)} results")

asyncio.run(test_integration())
```

## 🔧 Troubleshooting

### Common error messages

**"Dataset not found"**
- Check dataset name spelling
- Verify API key has access
- Ensure dataset was created successfully

**"Vector dimension mismatch"**
- Check vector dimensions match dataset
- Verify embedding model output
- Ensure consistent dimension across all vectors

**"Rate limit exceeded"**
- Slow down request rate
- Implement exponential backoff
- Contact admin for higher limits

**"Authentication failed"**
- Check API key format
- Verify API key is valid
- Ensure correct authorization header

### How do I debug issues?

1. **Check logs**: Enable debug logging
2. **Test connectivity**: Use health check endpoint
3. **Verify configuration**: Check environment variables
4. **Monitor resources**: Check CPU, memory, disk usage
5. **Contact support**: Provide error messages and logs

### Where can I get help?

- **Documentation**: [docs.yourcompany.com](https://docs.yourcompany.com)
- **GitHub Issues**: [github.com/your-org/deeplake-api/issues](https://github.com/your-org/deeplake-api/issues)
- **Community Forum**: [community.yourcompany.com](https://community.yourcompany.com)
- **Email Support**: [support@yourcompany.com](mailto:support@yourcompany.com)

## 💰 Pricing and Limits

### Is there a free tier?

Yes, the free tier includes:
- **1,000 vectors** per dataset
- **10 datasets** per tenant
- **1,000 requests** per day
- **Community support**

### What are the paid plans?

**Starter Plan** ($29/month):
- 100K vectors
- 100 datasets
- 100K requests/day
- Email support

**Professional Plan** ($99/month):
- 1M vectors
- Unlimited datasets
- 1M requests/day
- Priority support

**Enterprise Plan** (Custom):
- Unlimited vectors
- Custom limits
- SLA guarantee
- Dedicated support

### How is usage calculated?

- **Storage**: Number of vectors × dimensions × 4 bytes
- **Requests**: API calls per time period
- **Bandwidth**: Data transfer in/out
- **Compute**: Search operations and indexing

### Can I monitor my usage?

Yes, through the API:
```bash
# Check usage
curl -X GET "http://localhost:8000/api/v1/usage" \
  -H "Authorization: ApiKey your-api-key"
```

## 🔮 Future Features

### What's on the roadmap?

**Q1 2024**:
- Advanced indexing algorithms
- Multi-modal search support
- Enhanced monitoring

**Q2 2024**:
- Graph-based search
- Federated search
- Advanced analytics

**Q3 2024**:
- Real-time streaming
- Edge deployment
- Mobile SDKs

**Q4 2024**:
- Machine learning integration
- AutoML features
- Advanced security

### How do I request features?

1. **GitHub Issues**: Create feature request
2. **Community Forum**: Discuss with community
3. **Email**: Contact product team
4. **Enterprise**: Dedicated feature requests

### Can I contribute?

Yes! We welcome contributions:
- **Bug reports**: Report issues on GitHub
- **Feature requests**: Suggest new features
- **Code contributions**: Submit pull requests
- **Documentation**: Improve docs and examples

## 📞 Support

### What support options are available?

**Community Support** (Free):
- GitHub issues
- Community forum
- Documentation
- FAQ

**Email Support** (Paid plans):
- Response within 24 hours
- Technical assistance
- Configuration help

**Priority Support** (Enterprise):
- Response within 4 hours
- Phone support
- Dedicated engineer
- Custom solutions

### How do I contact support?

- **General**: [support@yourcompany.com](mailto:support@yourcompany.com)
- **Technical**: [tech-support@yourcompany.com](mailto:tech-support@yourcompany.com)
- **Sales**: [sales@yourcompany.com](mailto:sales@yourcompany.com)
- **Emergency**: [emergency@yourcompany.com](mailto:emergency@yourcompany.com)

### What information should I include?

When contacting support:
- **API version**: Current version
- **Error messages**: Complete error text
- **Steps to reproduce**: Exact steps
- **Environment**: OS, Python version, etc.
- **Configuration**: Relevant settings (sanitized)

---

## 🔗 Additional Resources

- **[Quick Start Guide](./quickstart.md)**: Get up and running quickly
- **[API Reference](./api/http/README.md)**: Complete API documentation
- **[Examples](./examples/README.md)**: Code examples and tutorials
- **[Troubleshooting](./troubleshooting.md)**: Common issues and solutions
- **[Architecture](./architecture.md)**: System design and architecture

## 📝 Still Have Questions?

If you can't find the answer here:
1. Check the [troubleshooting guide](./troubleshooting.md)
2. Search our [community forum](https://community.yourcompany.com)
3. Browse [GitHub issues](https://github.com/your-org/deeplake-api/issues)
4. Contact [support](mailto:support@yourcompany.com)

We're here to help! 🚀