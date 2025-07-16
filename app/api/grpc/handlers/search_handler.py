"""Search service gRPC handler."""

import grpc
from typing import Any, Dict, List

from app.config.logging import get_logger, LoggingMixin
from app.services.deeplake_service import DeepLakeService
from app.services.auth_service import AuthService
from app.services.metrics_service import MetricsService
from app.models.exceptions import (
    DatasetNotFoundException, InvalidVectorDimensionsException,
    InvalidSearchParametersException, AuthenticationException,
    AuthorizationException, DeepLakeServiceException
)


class SearchServicer(LoggingMixin):
    """Search service gRPC handler."""
    
    def __init__(
        self,
        deeplake_service: DeepLakeService,
        auth_service: AuthService,
        metrics_service: MetricsService
    ):
        super().__init__()
        self.deeplake_service = deeplake_service
        self.auth_service = auth_service
        self.metrics_service = metrics_service
    
    def _authenticate_request(self, context: grpc.ServicerContext) -> Dict[str, Any]:
        """Authenticate gRPC request."""
        try:
            # Extract metadata
            metadata = dict(context.invocation_metadata())
            auth_header = metadata.get('authorization')
            
            if not auth_header:
                raise AuthenticationException("Missing authorization header")
            
            # Authenticate
            auth_info = self.auth_service.authenticate_request(auth_header)
            return auth_info
            
        except AuthenticationException as e:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details(str(e))
            raise
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Authentication service error")
            raise
    
    def _authorize_operation(
        self,
        auth_info: Dict[str, Any],
        operation: str,
        context: grpc.ServicerContext
    ) -> None:
        """Authorize gRPC operation."""
        try:
            self.auth_service.authorize_operation(auth_info, operation)
        except AuthorizationException as e:
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            context.set_details(str(e))
            raise
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Authorization service error")
            raise
    
    async def SearchVectors(self, request: Any, context: Any) -> Any:
        """Search for similar vectors."""
        import time
        start_time = time.time()
        
        try:
            # Authenticate and authorize
            auth_info = self._authenticate_request(context)
            self._authorize_operation(auth_info, "search_vectors", context)
            
            tenant_id = auth_info["tenant_id"]
            
            # Convert gRPC request to internal models
            from app.models.schemas import SearchOptions
            search_options = SearchOptions(
                top_k=request.options.top_k or 10,
                threshold=request.options.threshold if request.options.threshold > 0 else None,
                metric_type=request.options.metric_type or None,
                include_content=request.options.include_content,
                include_metadata=request.options.include_metadata,
                filters=dict(request.options.filters),
                deduplicate=request.options.deduplicate,
                group_by_document=request.options.group_by_document,
                rerank=request.options.rerank,
                ef_search=request.options.ef_search if request.options.ef_search > 0 else None,
                nprobe=request.options.nprobe if request.options.nprobe > 0 else None,
                max_distance=request.options.max_distance if request.options.max_distance > 0 else None,
                min_score=request.options.min_score if request.options.min_score > 0 else None
            )
            
            # Perform search
            search_response = await self.deeplake_service.search_vectors(
                dataset_id=request.dataset_id,
                query_vector=list(request.query_vector),
                options=search_options,
                tenant_id=tenant_id
            )
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_grpc_request(
                "SearchService", "SearchVectors", "OK", duration, tenant_id
            )
            self.metrics_service.record_search_query(
                request.dataset_id, "vector", duration,
                len(search_response.results),
                search_response.stats.vectors_scanned,
                tenant_id
            )
            
            # Convert to gRPC response
            results = []
            for result in search_response.results:
                vector_data = {
                    "id": result.vector.id,
                    "dataset_id": result.vector.dataset_id,
                    "document_id": result.vector.document_id,
                    "chunk_id": result.vector.chunk_id or "",
                    "values": result.vector.values,
                    "content": result.vector.content or "",
                    "content_hash": result.vector.content_hash or "",
                    "metadata": result.vector.metadata,
                    "content_type": result.vector.content_type or "",
                    "language": result.vector.language or "",
                    "chunk_index": result.vector.chunk_index or 0,
                    "chunk_count": result.vector.chunk_count or 1,
                    "model": result.vector.model or "",
                    "dimensions": result.vector.dimensions,
                    "created_at": result.vector.created_at.isoformat(),
                    "updated_at": result.vector.updated_at.isoformat(),
                    "tenant_id": result.vector.tenant_id or ""
                }
                
                search_result = {
                    "vector": vector_data,
                    "score": result.score,
                    "distance": result.distance,
                    "rank": result.rank,
                    "explanation": result.explanation or {}
                }
                results.append(search_result)
            
            return {
                "results": results,
                "total_found": search_response.total_found,
                "has_more": search_response.has_more,
                "query_time_ms": search_response.query_time_ms,
                "stats": {
                    "vectors_scanned": search_response.stats.vectors_scanned,
                    "index_hits": search_response.stats.index_hits,
                    "filtered_results": search_response.stats.filtered_results,
                    "reranking_time_ms": search_response.stats.reranking_time_ms,
                    "database_time_ms": search_response.stats.database_time_ms,
                    "post_processing_time_ms": search_response.stats.post_processing_time_ms
                }
            }
            
        except DatasetNotFoundException as e:
            self.metrics_service.record_grpc_request(
                "SearchService", "SearchVectors", "NOT_FOUND", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            raise
            
        except InvalidVectorDimensionsException as e:
            self.metrics_service.record_grpc_request(
                "SearchService", "SearchVectors", "INVALID_ARGUMENT", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            raise
            
        except InvalidSearchParametersException as e:
            self.metrics_service.record_grpc_request(
                "SearchService", "SearchVectors", "INVALID_ARGUMENT", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            raise
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "SearchService", "SearchVectors", "INTERNAL", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            self.logger.error("Unexpected error in SearchVectors", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise
    
    async def SearchByText(self, request: Any, context: Any) -> Any:
        """Search using text query."""
        import time
        start_time = time.time()
        
        try:
            # Authenticate and authorize
            auth_info = self._authenticate_request(context)
            self._authorize_operation(auth_info, "search_vectors", context)
            
            tenant_id = auth_info["tenant_id"]
            
            # Note: This is a simplified implementation
            # In a full implementation, you would convert text to embedding first
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_grpc_request(
                "SearchService", "SearchByText", "UNIMPLEMENTED", duration, tenant_id
            )
            
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("Text search requires embedding service integration")
            raise
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "SearchService", "SearchByText", "INTERNAL", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            self.logger.error("Unexpected error in SearchByText", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise
    
    async def HybridSearch(self, request: Any, context: Any) -> Any:
        """Perform hybrid search."""
        import time
        start_time = time.time()
        
        try:
            # Authenticate and authorize
            auth_info = self._authenticate_request(context)
            self._authorize_operation(auth_info, "search_vectors", context)
            
            tenant_id = auth_info["tenant_id"]
            
            # Note: This is a simplified implementation
            # In a full implementation, you would combine vector and text search
            
            # If only vector search is provided, delegate to vector search
            if request.query_vector and not request.query_text:
                # Create a SearchVectorsRequest and delegate
                vector_search_request = type('Request', (), {
                    'dataset_id': request.dataset_id,
                    'query_vector': request.query_vector,
                    'options': request.options,
                    'tenant_id': request.tenant_id
                })()
                
                return await self.SearchVectors(vector_search_request, context)
            
            # Otherwise not implemented
            self.metrics_service.record_grpc_request(
                "SearchService", "HybridSearch", "UNIMPLEMENTED", time.time() - start_time, tenant_id
            )
            
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("Hybrid search requires additional implementation")
            raise
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "SearchService", "HybridSearch", "INTERNAL", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            self.logger.error("Unexpected error in HybridSearch", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise