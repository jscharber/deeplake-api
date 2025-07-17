"""Custom exceptions for the Tributary AI services for DeepLake."""

from typing import Optional, Dict, Any


class DeepLakeServiceException(Exception):
    """Base exception for Deep Lake service errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class DatasetNotFoundException(DeepLakeServiceException):
    """Exception raised when a dataset is not found."""
    
    def __init__(self, dataset_id: str, tenant_id: Optional[str] = None):
        message = f"Dataset '{dataset_id}' not found"
        if tenant_id:
            message += f" for tenant '{tenant_id}'"
        super().__init__(message, "DATASET_NOT_FOUND", {"dataset_id": dataset_id, "tenant_id": tenant_id})


class DatasetAlreadyExistsException(DeepLakeServiceException):
    """Exception raised when trying to create a dataset that already exists."""
    
    def __init__(self, dataset_name: str, tenant_id: Optional[str] = None):
        message = f"Dataset '{dataset_name}' already exists"
        if tenant_id:
            message += f" for tenant '{tenant_id}'"
        super().__init__(message, "DATASET_ALREADY_EXISTS", {"dataset_name": dataset_name, "tenant_id": tenant_id})


class VectorNotFoundException(DeepLakeServiceException):
    """Exception raised when a vector is not found."""
    
    def __init__(self, vector_id: str, dataset_id: str):
        message = f"Vector '{vector_id}' not found in dataset '{dataset_id}'"
        super().__init__(message, "VECTOR_NOT_FOUND", {"vector_id": vector_id, "dataset_id": dataset_id})


class InvalidVectorDimensionsException(DeepLakeServiceException):
    """Exception raised when vector dimensions don't match dataset dimensions."""
    
    def __init__(self, expected: int, actual: int):
        message = f"Vector dimensions mismatch: expected {expected}, got {actual}"
        super().__init__(message, "INVALID_VECTOR_DIMENSIONS", {"expected": expected, "actual": actual})


class InvalidSearchParametersException(DeepLakeServiceException):
    """Exception raised when search parameters are invalid."""
    
    def __init__(self, message: str, parameters: Dict[str, Any]):
        super().__init__(message, "INVALID_SEARCH_PARAMETERS", parameters)


class AuthenticationException(DeepLakeServiceException):
    """Exception raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_FAILED")


class AuthorizationException(DeepLakeServiceException):
    """Exception raised when authorization fails."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "AUTHORIZATION_FAILED")


class RateLimitExceededException(DeepLakeServiceException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMIT_EXCEEDED")


class StorageException(DeepLakeServiceException):
    """Exception raised when storage operations fail."""
    
    def __init__(self, message: str, operation: str):
        super().__init__(message, "STORAGE_ERROR", {"operation": operation})


class CacheException(DeepLakeServiceException):
    """Exception raised when cache operations fail."""
    
    def __init__(self, message: str, operation: str):
        super().__init__(message, "CACHE_ERROR", {"operation": operation})


class ValidationException(DeepLakeServiceException):
    """Exception raised when input validation fails."""
    
    def __init__(self, message: str, field: str, value: Any):
        super().__init__(message, "VALIDATION_ERROR", {"field": field, "value": value})


class ServiceUnavailableException(DeepLakeServiceException):
    """Exception raised when service is temporarily unavailable."""
    
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, "SERVICE_UNAVAILABLE")