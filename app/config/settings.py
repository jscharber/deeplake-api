"""Application configuration settings."""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class DeepLakeConfig(BaseSettings):
    """Deep Lake specific configuration."""
    
    storage_location: str = Field(
        default="./data/vectors",
        description="Storage location for Deep Lake datasets"
    )
    token: Optional[str] = Field(
        default=None,
        description="Deep Lake authentication token"
    )
    org_id: Optional[str] = Field(
        default=None,
        description="Deep Lake organization ID"
    )
    
    class Config:
        env_prefix = "DEEPLAKE_"
        env_file = ".env"
        extra = "ignore"


class HTTPConfig(BaseSettings):
    """HTTP server configuration."""
    
    host: str = Field(default="0.0.0.0", description="HTTP server host")
    port: int = Field(default=8000, description="HTTP server port")
    workers: int = Field(default=4, description="Number of worker processes")
    
    class Config:
        env_prefix = "HTTP_"


class GRPCConfig(BaseSettings):
    """gRPC server configuration."""
    
    host: str = Field(default="0.0.0.0", description="gRPC server host")
    port: int = Field(default=50051, description="gRPC server port")
    max_workers: int = Field(default=10, description="Maximum number of gRPC workers")
    
    class Config:
        env_prefix = "GRPC_"


class AuthConfig(BaseSettings):
    """Authentication configuration."""
    
    jwt_secret_key: Optional[str] = Field(
        default=None,
        description="JWT secret key (required, set via JWT_SECRET_KEY env var)"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=8760, description="JWT expiration in hours (default: 1 year)")
    
    class Config:
        # No env_prefix to allow direct JWT_SECRET_KEY mapping
        env_file = ".env"
        extra = "ignore"


class RedisConfig(BaseSettings):
    """Redis configuration for caching."""
    
    url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    
    # TTL configurations for different cache types
    default_ttl_seconds: int = Field(default=3600, description="Default cache TTL in seconds")
    search_cache_ttl: int = Field(default=300, description="Search results cache TTL in seconds")
    metadata_cache_ttl: int = Field(default=1800, description="Metadata cache TTL in seconds")
    dataset_cache_ttl: int = Field(default=900, description="Dataset info cache TTL in seconds")
    embedding_cache_ttl: int = Field(default=3600, description="Embedding cache TTL in seconds")
    
    # Connection configuration
    max_connections: int = Field(default=20, description="Maximum Redis connections")
    connection_timeout: int = Field(default=5, description="Redis connection timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts for Redis operations")
    
    # Memory optimization
    compress_cache: bool = Field(default=True, description="Enable cache compression")
    max_cache_size_mb: int = Field(default=512, description="Maximum cache size in MB")
    
    class Config:
        env_prefix = "REDIS_"
        env_file = ".env"
        extra = "ignore"


class MonitoringConfig(BaseSettings):
    """Monitoring and metrics configuration."""
    
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format")
    
    class Config:
        env_prefix = "MONITORING_"
        env_file = ".env"
        extra = "ignore"


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""
    
    requests_per_minute: int = Field(
        default=1000,
        description="Requests per minute per client"
    )
    burst: int = Field(default=100, description="Burst capacity")
    
    class Config:
        env_prefix = "RATE_LIMIT_"


class PerformanceConfig(BaseSettings):
    """Performance tuning configuration."""
    
    max_vector_batch_size: int = Field(
        default=1000,
        description="Maximum vectors per batch operation"
    )
    default_search_timeout: int = Field(
        default=30,
        description="Default search timeout in seconds"
    )
    max_concurrent_searches: int = Field(
        default=50,
        description="Maximum concurrent search operations"
    )
    
    # Thread pool configuration
    deeplake_thread_pool_workers: int = Field(
        default=10,
        description="Number of workers in DeepLake thread pool"
    )
    
    # HTTP request timeouts
    http_request_timeout: int = Field(
        default=300,
        description="HTTP request timeout in seconds"
    )
    http_keep_alive_timeout: int = Field(
        default=5,
        description="HTTP keep-alive timeout in seconds"
    )
    
    # Search performance
    vector_search_timeout: int = Field(
        default=30,
        description="Vector search operation timeout in seconds"
    )
    text_search_timeout: int = Field(
        default=15,
        description="Text search operation timeout in seconds"
    )
    hybrid_search_timeout: int = Field(
        default=45,
        description="Hybrid search operation timeout in seconds"
    )
    
    # Import/export performance
    import_batch_size: int = Field(
        default=100,
        description="Default batch size for import operations"
    )
    export_batch_size: int = Field(
        default=100,
        description="Default batch size for export operations"
    )
    import_timeout: int = Field(
        default=3600,
        description="Import operation timeout in seconds"
    )
    export_timeout: int = Field(
        default=1800,
        description="Export operation timeout in seconds"
    )
    
    # Database connection timeouts
    database_connection_timeout: int = Field(
        default=30,
        description="Database connection timeout in seconds"
    )
    database_query_timeout: int = Field(
        default=60,
        description="Database query timeout in seconds"
    )
    
    # Pagination and limits
    default_page_size: int = Field(
        default=100,
        description="Default page size for paginated results"
    )
    max_page_size: int = Field(
        default=1000,
        description="Maximum page size for paginated results"
    )
    max_search_results: int = Field(
        default=10000,
        description="Maximum number of search results"
    )
    
    class Config:
        env_prefix = "PERFORMANCE_"


class DevelopmentConfig(BaseSettings):
    """Development configuration."""
    
    debug: bool = Field(default=False, description="Debug mode")
    reload: bool = Field(default=False, description="Auto-reload on changes")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="CORS allowed origins"
    )
    default_api_key: Optional[str] = Field(
        default=None,
        description="Development API key (set via DEV_DEFAULT_API_KEY env var)"
    )
    
    class Config:
        env_prefix = "DEV_"
        env_file = ".env"
        extra = "ignore"


class EmbeddingConfig(BaseSettings):
    """Embedding service configuration."""
    
    # OpenAI configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for embeddings")
    openai_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model")
    
    # Sentence Transformers configuration
    sentence_transformers_model: str = Field(default="all-MiniLM-L6-v2", description="Sentence Transformers model name")
    
    # General embedding settings
    embedding_cache_ttl: int = Field(default=3600, description="Embedding cache TTL in seconds")
    max_text_length: int = Field(default=10000, description="Maximum text length for embedding")
    batch_size: int = Field(default=32, description="Batch size for embedding multiple texts")
    
    class Config:
        env_prefix = "EMBEDDING_"


class Settings(BaseSettings):
    """Main application settings."""
    
    app_name: str = "Tributary AI services for DeepLake"
    app_version: str = "1.0.0"
    
    # Sub-configurations
    deeplake: DeepLakeConfig = Field(default_factory=DeepLakeConfig)
    http: HTTPConfig = Field(default_factory=HTTPConfig)
    grpc: GRPCConfig = Field(default_factory=GRPCConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    development: DevelopmentConfig = Field(default_factory=DevelopmentConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields


# Global settings instance
settings = Settings()