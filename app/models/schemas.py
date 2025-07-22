"""Pydantic models for HTTP API request/response schemas."""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import numpy as np


class BaseResponse(BaseModel):
    """Base response model with common fields."""
    
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseResponse):
    """Error response model."""
    
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class DatasetCreate(BaseModel):
    """Dataset creation request model."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Dataset name")
    description: Optional[str] = Field(None, max_length=500, description="Dataset description")
    dimensions: int = Field(..., ge=1, le=10000, description="Vector dimensions")
    metric_type: str = Field(default="cosine", description="Distance metric type")
    index_type: str = Field(default="default", description="Index type: default, flat, hnsw, ivf")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="Dataset metadata")
    storage_location: Optional[str] = Field(None, description="Custom storage location")
    overwrite: bool = Field(default=False, description="Overwrite existing dataset")
    
    @field_validator('metric_type')
    @classmethod
    def validate_metric_type(cls, v: str) -> str:
        allowed_metrics = ['cosine', 'euclidean', 'manhattan', 'dot_product']
        if v not in allowed_metrics:
            raise ValueError(f"metric_type must be one of {allowed_metrics}")
        return v
    
    @field_validator('index_type')
    @classmethod
    def validate_index_type(cls, v: str) -> str:
        allowed_types = ['default', 'flat', 'hnsw', 'ivf']
        if v not in allowed_types:
            raise ValueError(f"index_type must be one of {allowed_types}")
        return v


class DatasetUpdate(BaseModel):
    """Dataset update request model."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, str]] = None


class DatasetResponse(BaseModel):
    """Dataset response model."""
    
    id: str
    name: str
    description: Optional[str] = None
    dimensions: int
    metric_type: str
    index_type: str
    metadata: Dict[str, Any]
    storage_location: str
    vector_count: int = 0
    storage_size: int = 0
    created_at: datetime
    updated_at: datetime
    tenant_id: Optional[str] = None


class DatasetStats(BaseModel):
    """Dataset statistics model."""
    
    dataset: DatasetResponse
    vector_count: int
    storage_size: int
    metadata_stats: Dict[str, int]
    index_stats: Optional[Dict[str, Any]] = None


class VectorCreate(BaseModel):
    """Vector creation request model."""
    
    id: Optional[str] = Field(None, description="Vector ID (auto-generated if not provided)")
    document_id: str = Field(..., description="Document ID")
    chunk_id: Optional[str] = Field(None, description="Chunk ID")
    values: List[float] = Field(..., description="Vector values")
    content: Optional[str] = Field(None, description="Text content")
    content_hash: Optional[str] = Field(None, description="Content hash")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Vector metadata - supports any JSON-serializable data")
    content_type: Optional[str] = Field(None, description="Content type")
    language: Optional[str] = Field(None, description="Content language")
    chunk_index: Optional[int] = Field(None, ge=0, description="Chunk index")
    chunk_count: Optional[int] = Field(None, ge=1, description="Total chunks")
    model: Optional[str] = Field(None, description="Embedding model used")
    
    @field_validator('values')
    @classmethod
    def validate_values(cls, v: List[float]) -> List[float]:
        if not v:
            raise ValueError("Vector values cannot be empty")
        if len(v) > 10000:
            raise ValueError("Vector dimensions cannot exceed 10000")
        return v


class VectorUpdate(BaseModel):
    """Vector update request model."""
    
    values: Optional[List[float]] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    content_type: Optional[str] = None
    language: Optional[str] = None


class VectorResponse(BaseModel):
    """Vector response model."""
    
    id: str
    dataset_id: str
    document_id: str
    chunk_id: Optional[str] = None
    values: List[float]
    content: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: Dict[str, Any]
    content_type: Optional[str] = None
    language: Optional[str] = None
    chunk_index: Optional[int] = None
    chunk_count: Optional[int] = None
    model: Optional[str] = None
    dimensions: int
    created_at: datetime
    updated_at: datetime
    tenant_id: Optional[str] = None


class VectorBatchInsert(BaseModel):
    """Batch vector insertion request model."""
    
    vectors: List[VectorCreate] = Field(..., min_length=1, max_length=1000)
    skip_existing: bool = Field(default=False, description="Skip existing vectors")
    overwrite: bool = Field(default=False, description="Overwrite existing vectors")
    batch_size: Optional[int] = Field(None, ge=1, le=1000, description="Batch size for processing")


class VectorBatchResponse(BaseModel):
    """Batch vector operation response model."""
    
    inserted_count: int
    skipped_count: int = 0
    failed_count: int = 0
    error_messages: List[str] = Field(default_factory=list)
    processing_time_ms: float


class SearchOptions(BaseModel):
    """Search options model."""
    
    top_k: int = Field(default=10, ge=1, le=1000, description="Number of results to return")
    threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Similarity threshold")
    metric_type: Optional[str] = Field(None, description="Distance metric override")
    include_content: bool = Field(default=True, description="Include content in results")
    include_metadata: bool = Field(default=True, description="Include metadata in results")
    filters: Optional[Union[Dict[str, Any], str]] = Field(default=None, description="Advanced metadata filters - supports simple dict, complex expressions, or SQL-like strings")
    deduplicate: bool = Field(default=False, description="Remove duplicate results")
    group_by_document: bool = Field(default=False, description="Group results by document")
    rerank: bool = Field(default=False, description="Apply reranking")
    ef_search: Optional[int] = Field(None, ge=1, description="HNSW ef_search parameter")
    nprobe: Optional[int] = Field(None, ge=1, description="IVF nprobe parameter")
    max_distance: Optional[float] = Field(None, ge=0.0, description="Maximum distance")
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum score")


class SearchRequest(BaseModel):
    """Vector search request model."""
    
    query_vector: List[float] = Field(..., description="Query vector")
    options: Optional[SearchOptions] = Field(default=None)
    
    @field_validator('query_vector')
    @classmethod
    def validate_query_vector(cls, v: List[float]) -> List[float]:
        if not v:
            raise ValueError("Query vector cannot be empty")
        if len(v) > 10000:
            raise ValueError("Query vector dimensions cannot exceed 10000")
        return v


class TextSearchRequest(BaseModel):
    """Text-based search request model."""
    
    query_text: str = Field(..., min_length=1, max_length=10000, description="Query text")
    options: Optional[SearchOptions] = Field(default=None)


class HybridSearchRequest(BaseModel):
    """Hybrid search request model."""
    
    query_vector: Optional[List[float]] = None
    query_text: Optional[str] = Field(None, min_length=1, max_length=10000)
    options: Optional[SearchOptions] = Field(default=None)
    vector_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Vector search weight")
    text_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Text search weight")
    fusion_method: Optional[str] = Field(default="weighted_sum", description="Result fusion method: weighted_sum, reciprocal_rank_fusion, comb_sum, comb_mnz, borda_count")
    
    @model_validator(mode='after')
    def validate_weights(self) -> 'HybridSearchRequest':
        if abs(self.vector_weight + self.text_weight - 1.0) > 0.01:
            raise ValueError("Vector weight and text weight must sum to 1.0")
        return self


class SearchResultItem(BaseModel):
    """Single search result item."""
    
    vector: VectorResponse
    score: float
    distance: float
    rank: int
    explanation: Optional[Dict[str, str]] = None


class SearchStats(BaseModel):
    """Search statistics model."""
    
    vectors_scanned: int
    index_hits: int
    filtered_results: int
    reranking_time_ms: float = 0.0
    database_time_ms: float = 0.0
    post_processing_time_ms: float = 0.0


class SearchResponse(BaseModel):
    """Search response model."""
    
    results: List[SearchResultItem]
    total_found: int
    has_more: bool
    query_time_ms: float
    embedding_time_ms: float = 0.0
    stats: SearchStats


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str
    service: str
    version: str
    timestamp: datetime
    dependencies: Dict[str, str]


class ServiceInfo(BaseModel):
    """Service information metrics."""
    version: str
    uptime_seconds: float

class RequestMetrics(BaseModel):
    """Request metrics."""
    http_total: float
    grpc_total: float

class DatasetMetrics(BaseModel):
    """Dataset metrics."""
    total: float

class VectorMetrics(BaseModel):
    """Vector metrics."""
    total: float
    inserted_total: float

class SearchMetrics(BaseModel):
    """Search metrics."""
    total: float

class ErrorMetrics(BaseModel):
    """Error metrics."""
    total: float

class CacheMetrics(BaseModel):
    """Cache metrics."""
    hit_ratio: float
    operations_total: float

class MetricsData(BaseModel):
    """Structured metrics data."""
    service_info: ServiceInfo
    requests: RequestMetrics
    datasets: DatasetMetrics
    vectors: VectorMetrics
    searches: SearchMetrics
    errors: ErrorMetrics
    cache: CacheMetrics

class MetricsResponse(BaseModel):
    """Metrics response model."""
    
    metrics: MetricsData
    timestamp: datetime


class PaginatedResponse(BaseModel):
    """Paginated response model."""
    
    items: List[Any]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool