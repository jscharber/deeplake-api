"""Dataset service gRPC handler."""

import grpc
from typing import Any, Dict
from datetime import datetime

from app.config.logging import get_logger, LoggingMixin
from app.services.deeplake_service import DeepLakeService
from app.services.auth_service import AuthService
from app.services.metrics_service import MetricsService
from app.models.exceptions import (
    DatasetNotFoundException, DatasetAlreadyExistsException,
    AuthenticationException, AuthorizationException,
    DeepLakeServiceException
)


class DatasetServicer(LoggingMixin):
    """Dataset service gRPC handler."""
    
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
    
    async def CreateDataset(self, request: Any, context: Any) -> Any:
        """Create a new dataset."""
        import time
        start_time = time.time()
        
        try:
            # Authenticate and authorize
            auth_info = self._authenticate_request(context)
            self._authorize_operation(auth_info, "create_dataset", context)
            
            tenant_id = auth_info["tenant_id"]
            
            # Convert gRPC request to internal model
            from app.models.schemas import DatasetCreate
            dataset_create = DatasetCreate(
                name=request.name,
                description=request.description,
                dimensions=request.dimensions,
                metric_type=request.metric_type,
                index_type=request.index_type,
                metadata=dict(request.metadata),
                storage_location=request.storage_location,
                overwrite=request.overwrite
            )
            
            # Create dataset
            dataset = await self.deeplake_service.create_dataset(dataset_create, tenant_id)
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_grpc_request(
                "DatasetService", "CreateDataset", "OK", duration, tenant_id
            )
            
            # Convert to gRPC response
            # Note: In a full implementation, you would convert to the protobuf message
            # For now, we'll return a mock response structure
            return {
                "dataset": {
                    "id": dataset.id,
                    "name": dataset.name,
                    "description": dataset.description,
                    "dimensions": dataset.dimensions,
                    "metric_type": dataset.metric_type,
                    "index_type": dataset.index_type,
                    "metadata": dataset.metadata,
                    "storage_location": dataset.storage_location,
                    "vector_count": dataset.vector_count,
                    "storage_size": dataset.storage_size,
                    "created_at": dataset.created_at.isoformat(),
                    "updated_at": dataset.updated_at.isoformat(),
                    "tenant_id": dataset.tenant_id or ""
                },
                "message": "Dataset created successfully"
            }
            
        except DatasetAlreadyExistsException as e:
            self.metrics_service.record_grpc_request(
                "DatasetService", "CreateDataset", "ALREADY_EXISTS", time.time() - start_time, 
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details(str(e))
            raise
            
        except DeepLakeServiceException as e:
            self.metrics_service.record_grpc_request(
                "DatasetService", "CreateDataset", "INVALID_ARGUMENT", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            raise
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "DatasetService", "CreateDataset", "INTERNAL", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            self.logger.error("Unexpected error in CreateDataset", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise
    
    async def GetDataset(self, request: Any, context: Any) -> Any:
        """Get dataset information."""
        import time
        start_time = time.time()
        
        try:
            # Authenticate and authorize
            auth_info = self._authenticate_request(context)
            self._authorize_operation(auth_info, "read_dataset", context)
            
            tenant_id = auth_info["tenant_id"]
            
            # Get dataset
            dataset = await self.deeplake_service.get_dataset(request.dataset_id, tenant_id)
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_grpc_request(
                "DatasetService", "GetDataset", "OK", duration, tenant_id
            )
            
            # Convert to gRPC response
            return {
                "dataset": {
                    "id": dataset.id,
                    "name": dataset.name,
                    "description": dataset.description,
                    "dimensions": dataset.dimensions,
                    "metric_type": dataset.metric_type,
                    "index_type": dataset.index_type,
                    "metadata": dataset.metadata,
                    "storage_location": dataset.storage_location,
                    "vector_count": dataset.vector_count,
                    "storage_size": dataset.storage_size,
                    "created_at": dataset.created_at.isoformat(),
                    "updated_at": dataset.updated_at.isoformat(),
                    "tenant_id": dataset.tenant_id or ""
                }
            }
            
        except DatasetNotFoundException as e:
            self.metrics_service.record_grpc_request(
                "DatasetService", "GetDataset", "NOT_FOUND", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            raise
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "DatasetService", "GetDataset", "INTERNAL", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            self.logger.error("Unexpected error in GetDataset", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise
    
    async def ListDatasets(self, request: Any, context: Any) -> Any:
        """List datasets for tenant."""
        import time
        start_time = time.time()
        
        try:
            # Authenticate and authorize
            auth_info = self._authenticate_request(context)
            self._authorize_operation(auth_info, "list_datasets", context)
            
            tenant_id = auth_info["tenant_id"]
            
            # List datasets
            datasets = await self.deeplake_service.list_datasets(
                tenant_id=tenant_id,
                limit=request.limit or 100,
                offset=request.offset or 0
            )
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_grpc_request(
                "DatasetService", "ListDatasets", "OK", duration, tenant_id
            )
            
            # Convert to gRPC response
            dataset_list = []
            for dataset in datasets:
                dataset_list.append({
                    "id": dataset.id,
                    "name": dataset.name,
                    "description": dataset.description,
                    "dimensions": dataset.dimensions,
                    "metric_type": dataset.metric_type,
                    "index_type": dataset.index_type,
                    "metadata": dataset.metadata,
                    "storage_location": dataset.storage_location,
                    "vector_count": dataset.vector_count,
                    "storage_size": dataset.storage_size,
                    "created_at": dataset.created_at.isoformat(),
                    "updated_at": dataset.updated_at.isoformat(),
                    "tenant_id": dataset.tenant_id or ""
                })
            
            return {
                "datasets": dataset_list,
                "total_count": len(dataset_list)
            }
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "DatasetService", "ListDatasets", "INTERNAL", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            self.logger.error("Unexpected error in ListDatasets", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise
    
    async def DeleteDataset(self, request: Any, context: Any) -> Any:
        """Delete a dataset."""
        import time
        start_time = time.time()
        
        try:
            # Authenticate and authorize
            auth_info = self._authenticate_request(context)
            self._authorize_operation(auth_info, "delete_dataset", context)
            
            tenant_id = auth_info["tenant_id"]
            
            # Delete dataset
            await self.deeplake_service.delete_dataset(request.dataset_id, tenant_id)
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_grpc_request(
                "DatasetService", "DeleteDataset", "OK", duration, tenant_id
            )
            
            return {
                "message": f"Dataset '{request.dataset_id}' deleted successfully"
            }
            
        except DatasetNotFoundException as e:
            self.metrics_service.record_grpc_request(
                "DatasetService", "DeleteDataset", "NOT_FOUND", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            raise
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "DatasetService", "DeleteDataset", "INTERNAL", time.time() - start_time,
                auth_info.get("tenant_id") if 'auth_info' in locals() else None
            )
            self.logger.error("Unexpected error in DeleteDataset", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise