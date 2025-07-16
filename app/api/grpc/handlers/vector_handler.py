"""Vector service gRPC handler."""

import grpc
from typing import Any, Dict, List

from app.config.logging import get_logger, LoggingMixin
from app.services.deeplake_service import DeepLakeService
from app.services.auth_service import AuthService
from app.services.metrics_service import MetricsService
from app.models.exceptions import (
    DatasetNotFoundException, VectorNotFoundException,
    InvalidVectorDimensionsException, AuthenticationException,
    AuthorizationException, DeepLakeServiceException
)


class VectorServicer(LoggingMixin):
    """Vector service gRPC handler."""
    
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
    
    async def InsertVector(self, request: Any, context: Any) -> Any:
        """Insert a single vector."""
        import time
        start_time = time.time()
        
        try:
            # Authenticate and authorize
            auth_info = self._authenticate_request(context)
            self._authorize_operation(auth_info, "insert_vector", context)
            
            tenant_id = auth_info["tenant_id"]
            
            # Convert gRPC request to internal model
            from app.models.schemas import VectorCreate
            vector_create = VectorCreate(
                id=request.vector.id or None,
                document_id=request.vector.document_id,
                chunk_id=request.vector.chunk_id or None,
                values=list(request.vector.values),
                content=request.vector.content or None,
                content_hash=request.vector.content_hash or None,
                metadata=dict(request.vector.metadata),
                content_type=request.vector.content_type or None,
                language=request.vector.language or None,
                chunk_index=request.vector.chunk_index or None,
                chunk_count=request.vector.chunk_count or None,
                model=request.vector.model or None
            )
            
            # Insert vector
            result = await self.deeplake_service.insert_vectors(
                dataset_id=request.dataset_id,
                vectors=[vector_create],
                tenant_id=tenant_id,
                skip_existing=request.skip_existing,
                overwrite=request.overwrite
            )
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_grpc_request(
                "VectorService", "InsertVector", "OK", duration, tenant_id
            )
            self.metrics_service.record_vector_insertion(
                request.dataset_id, result.inserted_count, duration, 1, tenant_id
            )
            
            # Return response
            return {
                "vector_id": vector_create.id or "generated",
                "message": "Vector inserted successfully"
            }
            
        except DatasetNotFoundException as e:
            self.metrics_service.record_grpc_request(
                "VectorService", "InsertVector", "NOT_FOUND", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            raise
            
        except InvalidVectorDimensionsException as e:
            self.metrics_service.record_grpc_request(
                "VectorService", "InsertVector", "INVALID_ARGUMENT", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            raise
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "VectorService", "InsertVector", "INTERNAL", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            self.logger.error("Unexpected error in InsertVector", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise
    
    async def InsertVectors(self, request: Any, context: Any) -> Any:
        """Insert multiple vectors."""
        import time
        start_time = time.time()
        
        try:
            # Authenticate and authorize
            auth_info = self._authenticate_request(context)
            self._authorize_operation(auth_info, "insert_vector", context)
            
            tenant_id = auth_info["tenant_id"]
            
            # Convert gRPC request to internal models
            from app.models.schemas import VectorCreate
            vectors = []
            for grpc_vector in request.vectors:
                vector_create = VectorCreate(
                    id=grpc_vector.id or None,
                    document_id=grpc_vector.document_id,
                    chunk_id=grpc_vector.chunk_id or None,
                    values=list(grpc_vector.values),
                    content=grpc_vector.content or None,
                    content_hash=grpc_vector.content_hash or None,
                    metadata=dict(grpc_vector.metadata),
                    content_type=grpc_vector.content_type or None,
                    language=grpc_vector.language or None,
                    chunk_index=grpc_vector.chunk_index or None,
                    chunk_count=grpc_vector.chunk_count or None,
                    model=grpc_vector.model or None
                )
                vectors.append(vector_create)
            
            # Insert vectors
            result = await self.deeplake_service.insert_vectors(
                dataset_id=request.dataset_id,
                vectors=vectors,
                tenant_id=tenant_id,
                skip_existing=request.skip_existing,
                overwrite=request.overwrite
            )
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_grpc_request(
                "VectorService", "InsertVectors", "OK", duration, tenant_id
            )
            self.metrics_service.record_vector_insertion(
                request.dataset_id, result.inserted_count, duration, len(vectors), tenant_id
            )
            
            # Return response
            return {
                "inserted_count": result.inserted_count,
                "skipped_count": result.skipped_count,
                "failed_count": result.failed_count,
                "error_messages": result.error_messages,
                "processing_time_ms": result.processing_time_ms
            }
            
        except DatasetNotFoundException as e:
            self.metrics_service.record_grpc_request(
                "VectorService", "InsertVectors", "NOT_FOUND", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            raise
            
        except InvalidVectorDimensionsException as e:
            self.metrics_service.record_grpc_request(
                "VectorService", "InsertVectors", "INVALID_ARGUMENT", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            raise
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "VectorService", "InsertVectors", "INTERNAL", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            self.logger.error("Unexpected error in InsertVectors", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise
    
    async def GetVector(self, request: Any, context: Any) -> Any:
        """Get a specific vector by ID."""
        import time
        start_time = time.time()
        
        try:
            # Authenticate and authorize
            auth_info = self._authenticate_request(context)
            self._authorize_operation(auth_info, "read_vector", context)
            
            tenant_id = auth_info["tenant_id"]
            
            # Note: This is a simplified implementation
            # In a full implementation, you would retrieve the vector by ID
            
            # For now, return not found
            raise VectorNotFoundException(request.vector_id, request.dataset_id)
            
        except VectorNotFoundException as e:
            self.metrics_service.record_grpc_request(
                "VectorService", "GetVector", "NOT_FOUND", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            raise
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "VectorService", "GetVector", "INTERNAL", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            self.logger.error("Unexpected error in GetVector", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise
    
    async def ListVectors(self, request: Any, context: Any) -> Any:
        """List vectors in a dataset."""
        import time
        start_time = time.time()
        
        try:
            # Authenticate and authorize
            auth_info = self._authenticate_request(context)
            self._authorize_operation(auth_info, "read_vector", context)
            
            tenant_id = auth_info["tenant_id"]
            
            # Note: This is a simplified implementation
            # In a full implementation, you would retrieve paginated vectors
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_grpc_request(
                "VectorService", "ListVectors", "OK", duration, tenant_id
            )
            
            # Return empty list for now
            return {
                "vectors": [],
                "total_count": 0
            }
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "VectorService", "ListVectors", "INTERNAL", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            self.logger.error("Unexpected error in ListVectors", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise