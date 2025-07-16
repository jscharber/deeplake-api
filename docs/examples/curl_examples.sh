#!/bin/bash

# Deep Lake Vector Service - cURL Examples
# This script demonstrates how to use the Deep Lake Vector Service HTTP API with cURL

set -e

# Configuration
BASE_URL="http://localhost:8000"
API_KEY="dev-12345-abcdef-67890-ghijkl"  # Default development API key

# Helper function to make authenticated requests
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -n "$data" ]; then
        curl -s -X "$method" \
             -H "Authorization: ApiKey $API_KEY" \
             -H "Content-Type: application/json" \
             -d "$data" \
             "$BASE_URL$endpoint"
    else
        curl -s -X "$method" \
             -H "Authorization: ApiKey $API_KEY" \
             "$BASE_URL$endpoint"
    fi
}

echo "🚀 Deep Lake Vector Service cURL Examples"
echo "=========================================="

# 1. Health Check
echo
echo "1. Health Check"
echo "---------------"
curl -s "$BASE_URL/api/v1/health" | jq '.'

# 2. Create Dataset
echo
echo "2. Creating Dataset"
echo "-------------------"
DATASET_DATA='{
  "name": "curl-example-dataset",
  "description": "Example dataset created with cURL",
  "dimensions": 128,
  "metric_type": "cosine",
  "index_type": "default",
  "metadata": {
    "source": "curl_example",
    "version": "1.0"
  },
  "overwrite": true
}'

DATASET_RESPONSE=$(make_request "POST" "/api/v1/datasets/" "$DATASET_DATA")
echo "$DATASET_RESPONSE" | jq '.'

# Extract dataset ID for subsequent operations
DATASET_ID=$(echo "$DATASET_RESPONSE" | jq -r '.id')
echo "Dataset ID: $DATASET_ID"

# 3. Get Dataset Information
echo
echo "3. Getting Dataset Information"
echo "------------------------------"
make_request "GET" "/api/v1/datasets/$DATASET_ID" | jq '.'

# 4. List All Datasets
echo
echo "4. Listing All Datasets"
echo "-----------------------"
make_request "GET" "/api/v1/datasets/" | jq '.'

# 5. Insert Single Vector
echo
echo "5. Inserting Single Vector"
echo "---------------------------"
VECTOR_DATA='{
  "id": "curl-vector-1",
  "document_id": "curl-doc-1",
  "chunk_id": "curl-chunk-1",
  "values": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
  "content": "This is example content for the first vector",
  "metadata": {
    "category": "example",
    "priority": "high",
    "source": "curl"
  },
  "content_type": "text/plain",
  "language": "en",
  "chunk_index": 0,
  "chunk_count": 1,
  "model": "example-model"
}'

make_request "POST" "/api/v1/datasets/$DATASET_ID/vectors/" "$VECTOR_DATA" | jq '.'

# 6. Insert Multiple Vectors (Batch)
echo
echo "6. Inserting Multiple Vectors (Batch)"
echo "--------------------------------------"
BATCH_DATA='{
  "vectors": [
    {
      "id": "curl-vector-2",
      "document_id": "curl-doc-2",
      "values": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
      "content": "This is example content for the second vector",
      "metadata": {"category": "example", "index": "2"}
    },
    {
      "id": "curl-vector-3",
      "document_id": "curl-doc-3",
      "values": [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
      "content": "This is example content for the third vector",
      "metadata": {"category": "example", "index": "3"}
    }
  ],
  "skip_existing": false,
  "overwrite": false
}'

make_request "POST" "/api/v1/datasets/$DATASET_ID/vectors/batch" "$BATCH_DATA" | jq '.'

# 7. Search for Similar Vectors
echo
echo "7. Searching for Similar Vectors"
echo "---------------------------------"
SEARCH_DATA='{
  "query_vector": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85],
  "options": {
    "top_k": 5,
    "include_content": true,
    "include_metadata": true,
    "threshold": 0.0
  }
}'

SEARCH_RESULT=$(make_request "POST" "/api/v1/datasets/$DATASET_ID/search" "$SEARCH_DATA")
echo "$SEARCH_RESULT" | jq '.'

# 8. Get Dataset Statistics
echo
echo "8. Getting Dataset Statistics"
echo "-----------------------------"
make_request "GET" "/api/v1/datasets/$DATASET_ID/stats" | jq '.'

# 9. Service Statistics
echo
echo "9. Getting Service Statistics"
echo "-----------------------------"
make_request "GET" "/api/v1/stats" | jq '.'

# 10. Advanced Search with Filters
echo
echo "10. Advanced Search with Filters"
echo "---------------------------------"
FILTERED_SEARCH='{
  "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
  "options": {
    "top_k": 10,
    "include_content": true,
    "include_metadata": true,
    "filters": {
      "category": "example"
    },
    "deduplicate": false,
    "group_by_document": false
  }
}'

make_request "POST" "/api/v1/datasets/$DATASET_ID/search" "$FILTERED_SEARCH" | jq '.'

# 11. List Vectors in Dataset
echo
echo "11. Listing Vectors in Dataset"
echo "-------------------------------"
make_request "GET" "/api/v1/datasets/$DATASET_ID/vectors/?limit=10&offset=0" | jq '.'

# 12. Error Handling Examples
echo
echo "12. Error Handling Examples"
echo "---------------------------"

echo "12.1. Accessing non-existent dataset:"
make_request "GET" "/api/v1/datasets/nonexistent" | jq '.'

echo
echo "12.2. Invalid vector dimensions:"
INVALID_VECTOR='{
  "id": "invalid-vector",
  "document_id": "invalid-doc",
  "values": [0.1, 0.2, 0.3],
  "content": "This vector has wrong dimensions"
}'
make_request "POST" "/api/v1/datasets/$DATASET_ID/vectors/" "$INVALID_VECTOR" | jq '.'

echo
echo "12.3. Search with invalid query vector:"
INVALID_SEARCH='{
  "query_vector": [0.1, 0.2],
  "options": {"top_k": 5}
}'
make_request "POST" "/api/v1/datasets/$DATASET_ID/search" "$INVALID_SEARCH" | jq '.'

# 13. Clean up - Delete Dataset
echo
echo "13. Cleaning Up - Deleting Dataset"
echo "-----------------------------------"
make_request "DELETE" "/api/v1/datasets/$DATASET_ID" | jq '.'

# 14. Verify Deletion
echo
echo "14. Verifying Deletion"
echo "----------------------"
make_request "GET" "/api/v1/datasets/$DATASET_ID" | jq '.'

echo
echo "✅ cURL examples completed!"
echo
echo "📚 Additional Notes:"
echo "- The examples use the default development API key: dev-12345-abcdef-67890-ghijkl"
echo "- The service should be running on http://localhost:8000"
echo "- Use 'jq' for pretty JSON formatting (install with: apt-get install jq)"
echo "- For production use, always use HTTPS endpoints and generate secure API keys"
echo "- See the API documentation for more advanced features"