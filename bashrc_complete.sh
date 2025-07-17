# Deep Lake Vector Service - Complete Environment Configuration
# Add to your ~/.bashrc file

# ====================================
# REQUIRED ENVIRONMENT VARIABLES
# ====================================

export JWT_SECRET_KEY="atTIB1W8fqVPqZd-s-QxntahTXMTFYh3z61yhqKs1uU"
export API_KEY="E1GgjhOtyi_04Enhq_pVCXyk0OVdxZ-SNXUtRc2cERU"

# ====================================
# ACTIVE CONFIGURATION
# ====================================

# Service Configuration
export MONITORING_ENABLE_METRICS=false
export REDIS_URL=redis://localhost:6379/0
export PYTHONUNBUFFERED=1
export MONITORING_LOG_LEVEL=DEBUG
export DEEPLAKE_STORAGE_LOCATION=/home/jscharber/eng/deeplake-api/local_data/vectors

# WSL Configuration
export WSL2_GUI_APPS_ENABLED=1
export WSL_DISTRO_NAME=Ubuntu-24.04

# ====================================
# OPTIONAL CONFIGURATION (COMMENTED)
# ====================================

# Deep Lake Configuration
# export DEEPLAKE_TOKEN="your_deeplake_token_here"
# export DEEPLAKE_ORG_ID="your_org_id_here"

# HTTP Server Configuration
# export HTTP_HOST="0.0.0.0"
# export HTTP_PORT="8000"
# export HTTP_WORKERS="4"

# gRPC Server Configuration
# export GRPC_HOST="0.0.0.0"
# export GRPC_PORT="50051"
# export GRPC_MAX_WORKERS="10"

# Authentication Configuration
# export JWT_ALGORITHM="HS256"
# export JWT_EXPIRATION_HOURS="24"

# Redis Configuration (Extended)
# export REDIS_TTL_SECONDS="3600"

# Monitoring Configuration (Extended)
# export MONITORING_METRICS_PORT="9090"
# export MONITORING_LOG_FORMAT="json"

# Rate Limiting Configuration
# export RATE_LIMIT_REQUESTS_PER_MINUTE="1000"
# export RATE_LIMIT_BURST="100"

# Performance Tuning Configuration
# export PERFORMANCE_MAX_VECTOR_BATCH_SIZE="1000"
# export PERFORMANCE_DEFAULT_SEARCH_TIMEOUT="30"
# export PERFORMANCE_MAX_CONCURRENT_SEARCHES="50"

# Development Configuration
# export DEV_DEBUG="false"
# export DEV_RELOAD="false"
# export DEV_CORS_ORIGINS='["http://localhost:3000", "http://localhost:8080"]'
# export DEV_DEFAULT_API_KEY="your_development_api_key_here"

# Service URLs
# export API_BASE_URL="http://localhost:8000"

# Cache Configuration
# export CACHE_ENABLED="true"  # Enable Redis caching

# ====================================
# CONVENIENT ALIASES
# ====================================

alias start-deeplake="JWT_SECRET_KEY=$JWT_SECRET_KEY python -m app.main"
alias test-deeplake="curl -H 'Authorization: ApiKey $API_KEY' http://localhost:8000/api/v1/health"
alias generate-api-key="JWT_SECRET_KEY=$JWT_SECRET_KEY python scripts/generate_api_key_quick.py"

# Additional aliases (commented - uncomment if needed)
# alias run-python-example="API_KEY=$API_KEY python docs/examples/python_client.py"
# alias run-curl-examples="API_KEY=$API_KEY bash docs/examples/curl_examples.sh"
# alias cleanup-datasets="API_KEY=$API_KEY python scripts/cleanup_datasets.py"
# alias deeplake-logs="tail -f logs/deeplake.log"
# alias deeplake-status="curl -s http://localhost:8000/api/v1/health | jq"

# ====================================
# CONFIGURATION NOTES
# ====================================

# Variable Name Reference:
# - Use MONITORING_* prefix for monitoring config
# - Use DEEPLAKE_* prefix for Deep Lake specific config
# - Use HTTP_* prefix for HTTP server config
# - Use GRPC_* prefix for gRPC server config
# - Use JWT_* prefix for authentication config
# - Use REDIS_* prefix for Redis config
# - Use RATE_LIMIT_* prefix for rate limiting config
# - Use PERFORMANCE_* prefix for performance tuning
# - Use DEV_* prefix for development config

# Security Notes:
# - JWT_SECRET_KEY should be at least 32 characters
# - API_KEY should be generated using the provided scripts
# - Never commit these values to version control
# - Use different keys for different environments

# Performance Notes:
# - Adjust HTTP_WORKERS based on your CPU cores
# - Increase PERFORMANCE_MAX_CONCURRENT_SEARCHES for high load
# - Set MONITORING_LOG_LEVEL to INFO or ERROR in production
# - Enable CACHE_ENABLED for better performance with Redis