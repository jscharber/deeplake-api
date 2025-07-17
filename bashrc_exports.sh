# Deep Lake Vector Service - Environment Variables
# Add these to your ~/.bashrc file

# ====================================
# REQUIRED ENVIRONMENT VARIABLES
# ====================================

# JWT Secret Key (REQUIRED - generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
export JWT_SECRET_KEY="atTIB1W8fqVPqZd-s-QxntahTXMTFYh3z61yhqKs1uU"

# API Key for client requests (generate with: python scripts/generate_api_key_quick.py)
export API_KEY="E1GgjhOtyi_04Enhq_pVCXyk0OVdxZ-SNXUtRc2cERU"

# ====================================
# OPTIONAL CONFIGURATION
# ====================================

# Service URLs
export API_BASE_URL="http://localhost:8000"

# Deep Lake Configuration
export DEEPLAKE_STORAGE_LOCATION="./data/vectors"
# export DEEPLAKE_TOKEN="your_deeplake_token_here"
# export DEEPLAKE_ORG_ID="your_org_id_here"

# HTTP Server Configuration
export HTTP_HOST="0.0.0.0"
export HTTP_PORT="8000"
export HTTP_WORKERS="4"

# gRPC Server Configuration
export GRPC_HOST="0.0.0.0"
export GRPC_PORT="50051"
export GRPC_MAX_WORKERS="10"

# Authentication
export JWT_ALGORITHM="HS256"
export JWT_EXPIRATION_HOURS="24"

# Redis Configuration (for caching)
export REDIS_URL="redis://localhost:6379/0"
export REDIS_TTL_SECONDS="3600"

# Monitoring
export MONITORING_ENABLE_METRICS="true"
export MONITORING_METRICS_PORT="9090"
export MONITORING_LOG_LEVEL="INFO"
export MONITORING_LOG_FORMAT="json"

# Rate Limiting
export RATE_LIMIT_REQUESTS_PER_MINUTE="1000"
export RATE_LIMIT_BURST="100"

# Performance Tuning
export PERFORMANCE_MAX_VECTOR_BATCH_SIZE="1000"
export PERFORMANCE_DEFAULT_SEARCH_TIMEOUT="30"
export PERFORMANCE_MAX_CONCURRENT_SEARCHES="50"

# Development
export DEV_DEBUG="false"
export DEV_RELOAD="false"
export DEV_CORS_ORIGINS='["http://localhost:3000", "http://localhost:8080"]'

# ====================================
# CONVENIENCE ALIASES
# ====================================

# Start the service
alias start-deeplake="JWT_SECRET_KEY=\$JWT_SECRET_KEY python -m app.main"

# Test the service
alias test-deeplake="curl -H 'Authorization: ApiKey \$API_KEY' http://localhost:8000/api/v1/health"

# Generate new API key
alias generate-api-key="JWT_SECRET_KEY=\$JWT_SECRET_KEY python scripts/generate_api_key_quick.py"

# Run examples
alias run-python-example="API_KEY=\$API_KEY python docs/examples/python_client.py"
alias run-curl-examples="API_KEY=\$API_KEY bash docs/examples/curl_examples.sh"

# Cleanup datasets
alias cleanup-datasets="API_KEY=\$API_KEY python scripts/cleanup_datasets.py"