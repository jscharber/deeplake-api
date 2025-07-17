"""Metrics service for monitoring and observability."""

import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest
)

from app.config.settings import settings
from app.config.logging import get_logger, LoggingMixin


class MetricsService(LoggingMixin):
    """Prometheus metrics service."""
    
    def __init__(self) -> None:
        super().__init__()
        self.registry = CollectorRegistry()
        self._initialize_metrics()
        
    def _initialize_metrics(self) -> None:
        """Initialize all metrics."""
        
        # Service info
        self.service_info = Info(
            'deeplake_service_info',
            'Tributary AI services for DeepLake information',
            registry=self.registry
        )
        self.service_info.info({
            'version': '1.0.0',
            'service': 'Tributary AI services for DeepLake',
            'build_date': datetime.now(timezone.utc).isoformat()
        })
        
        # HTTP Request metrics
        self.http_requests_total = Counter(
            'deeplake_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code', 'tenant_id'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'deeplake_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'tenant_id'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        self.http_requests_in_progress = Gauge(
            'deeplake_http_requests_in_progress',
            'Number of HTTP requests currently being processed',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # gRPC Request metrics
        self.grpc_requests_total = Counter(
            'deeplake_grpc_requests_total',
            'Total gRPC requests',
            ['service', 'method', 'status_code', 'tenant_id'],
            registry=self.registry
        )
        
        self.grpc_request_duration = Histogram(
            'deeplake_grpc_request_duration_seconds',
            'gRPC request duration in seconds',
            ['service', 'method', 'tenant_id'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        # Dataset metrics
        self.datasets_total = Gauge(
            'deeplake_datasets_total',
            'Total number of datasets',
            ['tenant_id'],
            registry=self.registry
        )
        
        self.dataset_operations_total = Counter(
            'deeplake_dataset_operations_total',
            'Total dataset operations',
            ['operation', 'status', 'tenant_id'],
            registry=self.registry
        )
        
        self.dataset_operation_duration = Histogram(
            'deeplake_dataset_operation_duration_seconds',
            'Dataset operation duration in seconds',
            ['operation', 'tenant_id'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        # Vector metrics
        self.vectors_total = Gauge(
            'deeplake_vectors_total',
            'Total number of vectors',
            ['dataset_id', 'tenant_id'],
            registry=self.registry
        )
        
        self.vectors_inserted_total = Counter(
            'deeplake_vectors_inserted_total',
            'Total vectors inserted',
            ['dataset_id', 'tenant_id'],
            registry=self.registry
        )
        
        self.vector_insertion_duration = Histogram(
            'deeplake_vector_insertion_duration_seconds',
            'Vector insertion duration in seconds',
            ['dataset_id', 'tenant_id'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
            registry=self.registry
        )
        
        self.vector_batch_size = Histogram(
            'deeplake_vector_batch_size',
            'Vector batch size distribution',
            ['dataset_id', 'tenant_id'],
            buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
            registry=self.registry
        )
        
        # Search metrics
        self.search_queries_total = Counter(
            'deeplake_search_queries_total',
            'Total search queries',
            ['dataset_id', 'search_type', 'tenant_id'],
            registry=self.registry
        )
        
        self.search_query_duration = Histogram(
            'deeplake_search_query_duration_seconds',
            'Search query duration in seconds',
            ['dataset_id', 'search_type', 'tenant_id'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        self.search_results_returned = Histogram(
            'deeplake_search_results_returned',
            'Number of search results returned',
            ['dataset_id', 'search_type', 'tenant_id'],
            buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
            registry=self.registry
        )
        
        self.search_vectors_scanned = Histogram(
            'deeplake_search_vectors_scanned',
            'Number of vectors scanned during search',
            ['dataset_id', 'tenant_id'],
            buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_operations_total = Counter(
            'deeplake_cache_operations_total',
            'Total cache operations',
            ['operation', 'status'],
            registry=self.registry
        )
        
        self.cache_hit_ratio = Gauge(
            'deeplake_cache_hit_ratio',
            'Cache hit ratio',
            registry=self.registry
        )
        
        # Storage metrics
        self.storage_size_bytes = Gauge(
            'deeplake_storage_size_bytes',
            'Total storage size in bytes',
            ['dataset_id', 'tenant_id'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'deeplake_errors_total',
            'Total errors',
            ['error_type', 'operation', 'tenant_id'],
            registry=self.registry
        )
        
        # Performance metrics
        self.active_connections = Gauge(
            'deeplake_active_connections',
            'Number of active connections',
            ['protocol'],
            registry=self.registry
        )
        
        self.memory_usage_bytes = Gauge(
            'deeplake_memory_usage_bytes',
            'Memory usage in bytes',
            ['component'],
            registry=self.registry
        )
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float, tenant_id: Optional[str] = None) -> None:
        """Record HTTP request metrics."""
        labels = {
            'method': method,
            'endpoint': endpoint,
            'status_code': str(status_code),
            'tenant_id': tenant_id or 'unknown'
        }
        
        self.http_requests_total.labels(**labels).inc()
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint,
            tenant_id=tenant_id or 'unknown'
        ).observe(duration)
    
    def record_grpc_request(self, service: str, method: str, status_code: str, duration: float, tenant_id: Optional[str] = None) -> None:
        """Record gRPC request metrics."""
        labels = {
            'service': service,
            'method': method,
            'status_code': status_code,
            'tenant_id': tenant_id or 'unknown'
        }
        
        self.grpc_requests_total.labels(**labels).inc()
        self.grpc_request_duration.labels(
            service=service,
            method=method,
            tenant_id=tenant_id or 'unknown'
        ).observe(duration)
    
    def record_dataset_operation(self, operation: str, status: str, duration: float, tenant_id: Optional[str] = None) -> None:
        """Record dataset operation metrics."""
        labels = {
            'operation': operation,
            'status': status,
            'tenant_id': tenant_id or 'unknown'
        }
        
        self.dataset_operations_total.labels(**labels).inc()
        self.dataset_operation_duration.labels(
            operation=operation,
            tenant_id=tenant_id or 'unknown'
        ).observe(duration)
    
    def record_vector_insertion(self, dataset_id: str, count: int, duration: float, batch_size: int, tenant_id: Optional[str] = None) -> None:
        """Record vector insertion metrics."""
        tenant = tenant_id or 'unknown'
        
        self.vectors_inserted_total.labels(
            dataset_id=dataset_id,
            tenant_id=tenant
        ).inc(count)
        
        self.vector_insertion_duration.labels(
            dataset_id=dataset_id,
            tenant_id=tenant
        ).observe(duration)
        
        self.vector_batch_size.labels(
            dataset_id=dataset_id,
            tenant_id=tenant
        ).observe(batch_size)
    
    def record_search_query(self, dataset_id: str, search_type: str, duration: float, results_count: int, vectors_scanned: int, tenant_id: Optional[str] = None) -> None:
        """Record search query metrics."""
        tenant = tenant_id or 'unknown'
        
        self.search_queries_total.labels(
            dataset_id=dataset_id,
            search_type=search_type,
            tenant_id=tenant
        ).inc()
        
        self.search_query_duration.labels(
            dataset_id=dataset_id,
            search_type=search_type,
            tenant_id=tenant
        ).observe(duration)
        
        self.search_results_returned.labels(
            dataset_id=dataset_id,
            search_type=search_type,
            tenant_id=tenant
        ).observe(results_count)
        
        self.search_vectors_scanned.labels(
            dataset_id=dataset_id,
            tenant_id=tenant
        ).observe(vectors_scanned)
    
    def record_cache_operation(self, operation: str, status: str) -> None:
        """Record cache operation metrics."""
        self.cache_operations_total.labels(
            operation=operation,
            status=status
        ).inc()
    
    def update_cache_hit_ratio(self, ratio: float) -> None:
        """Update cache hit ratio."""
        self.cache_hit_ratio.set(ratio)
    
    def update_storage_size(self, dataset_id: str, size_bytes: int, tenant_id: Optional[str] = None) -> None:
        """Update storage size metrics."""
        self.storage_size_bytes.labels(
            dataset_id=dataset_id,
            tenant_id=tenant_id or 'unknown'
        ).set(size_bytes)
    
    def update_vector_count(self, dataset_id: str, count: int, tenant_id: Optional[str] = None) -> None:
        """Update vector count metrics."""
        self.vectors_total.labels(
            dataset_id=dataset_id,
            tenant_id=tenant_id or 'unknown'
        ).set(count)
    
    def update_dataset_count(self, count: int, tenant_id: Optional[str] = None) -> None:
        """Update dataset count metrics."""
        self.datasets_total.labels(
            tenant_id=tenant_id or 'unknown'
        ).set(count)
    
    def record_error(self, error_type: str, operation: str, tenant_id: Optional[str] = None) -> None:
        """Record error metrics."""
        self.errors_total.labels(
            error_type=error_type,
            operation=operation,
            tenant_id=tenant_id or 'unknown'
        ).inc()
    
    def update_active_connections(self, protocol: str, count: int) -> None:
        """Update active connections metrics."""
        self.active_connections.labels(protocol=protocol).set(count)
    
    def update_memory_usage(self, component: str, bytes_used: int) -> None:
        """Update memory usage metrics."""
        self.memory_usage_bytes.labels(component=component).set(bytes_used)
    
    @asynccontextmanager
    async def track_request_duration(self, metric_recorder: Callable, *args: Any, **kwargs: Any) -> Any:
        """Context manager to track request duration."""
        start_time = time.time()
        self.http_requests_in_progress.labels(
            method=kwargs.get('method', 'unknown'),
            endpoint=kwargs.get('endpoint', 'unknown')
        ).inc()
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            metric_recorder(duration=duration, *args, **kwargs)
            self.http_requests_in_progress.labels(
                method=kwargs.get('method', 'unknown'),
                endpoint=kwargs.get('endpoint', 'unknown')
            ).dec()
    
    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format."""
        return str(generate_latest(self.registry).decode('utf-8'))
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of key metrics."""
        try:
            return {
                'service_info': {
                    'version': '1.0.0',
                    'uptime_seconds': time.time() - self._start_time if hasattr(self, '_start_time') else 0,
                },
                'requests': {
                    'http_total': self._get_counter_value(self.http_requests_total),
                    'grpc_total': self._get_counter_value(self.grpc_requests_total),
                },
                'datasets': {
                    'total': self._get_gauge_value(self.datasets_total),
                },
                'vectors': {
                    'total': self._get_gauge_value(self.vectors_total),
                    'inserted_total': self._get_counter_value(self.vectors_inserted_total),
                },
                'searches': {
                    'total': self._get_counter_value(self.search_queries_total),
                },
                'errors': {
                    'total': self._get_counter_value(self.errors_total),
                },
                'cache': {
                    'hit_ratio': self._get_gauge_value(self.cache_hit_ratio),
                    'operations_total': self._get_counter_value(self.cache_operations_total),
                },
            }
        except Exception as e:
            self.logger.error("Failed to get metrics summary", error=str(e))
            return {'error': str(e)}
    
    def _get_counter_value(self, counter: Any) -> float:
        """Get the total value of a counter metric."""
        try:
            total = 0.0
            for sample in counter.collect()[0].samples:
                if sample.name.endswith('_total'):
                    total += sample.value
            return total
        except Exception:
            return 0.0
    
    def _get_gauge_value(self, gauge: Any) -> float:
        """Get the current value of a gauge metric."""
        try:
            for sample in gauge.collect()[0].samples:
                return float(sample.value)
            return 0.0
        except Exception:
            return 0.0
    
    def start_tracking_uptime(self) -> None:
        """Start tracking service uptime."""
        self._start_time = time.time()