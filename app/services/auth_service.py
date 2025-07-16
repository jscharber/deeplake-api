"""Authentication and authorization service."""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import secrets
import hashlib
from passlib.context import CryptContext

from app.config.settings import settings
from app.config.logging import get_logger, LoggingMixin
from app.models.exceptions import AuthenticationException, AuthorizationException


class AuthService(LoggingMixin):
    """Authentication and authorization service."""
    
    def __init__(self) -> None:
        super().__init__()
        self.secret_key = settings.auth.jwt_secret_key
        self.algorithm = settings.auth.jwt_algorithm
        self.expiration_hours = settings.auth.jwt_expiration_hours
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # In-memory store for API keys (in production, use a database)
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.tenants: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default tenant
        self._initialize_default_tenant()
    
    def _initialize_default_tenant(self) -> None:
        """Initialize a default tenant for development."""
        default_tenant = {
            'id': 'default',
            'name': 'Default Tenant',
            'created_at': datetime.now(timezone.utc),
            'active': True,
            'permissions': ['read', 'write', 'admin'],
            'quota': {
                'max_datasets': 100,
                'max_vectors_per_dataset': 1000000,
                'max_storage_bytes': 10 * 1024 * 1024 * 1024,  # 10GB
            }
        }
        self.tenants['default'] = default_tenant
        
        # Create a default API key with fixed value for development
        api_key = self._create_default_api_key(
            tenant_id='default',
            name='Default Development API Key',
            permissions=['read', 'write', 'admin']
        )
        self.logger.info("Default tenant and API key created", tenant_id='default', api_key=api_key)
    
    def _create_default_api_key(
        self,
        tenant_id: str,
        name: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None
    ) -> str:
        """Create the default development API key with a fixed value."""
        # Use the fixed development API key from settings
        api_key = settings.development.default_api_key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        self.api_keys[key_hash] = {
            'tenant_id': tenant_id,
            'name': name,
            'permissions': permissions,
            'created_at': datetime.now(timezone.utc),
            'expires_at': expires_at,
            'active': True,
            'last_used': None,
            'usage_count': 0,
        }
        
        self.logger.info("Default API key created", tenant_id=tenant_id, name=name, permissions=permissions)
        return api_key
    
    def generate_api_key(
        self,
        tenant_id: str,
        name: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None
    ) -> str:
        """Generate a new API key."""
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        self.api_keys[key_hash] = {
            'tenant_id': tenant_id,
            'name': name,
            'permissions': permissions,
            'created_at': datetime.now(timezone.utc),
            'expires_at': expires_at,
            'active': True,
            'last_used': None,
            'usage_count': 0,
        }
        
        self.logger.info("API key generated", tenant_id=tenant_id, name=name, permissions=permissions)
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify an API key and return associated information."""
        try:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            key_info = self.api_keys.get(key_hash)
            
            if not key_info:
                return None
            
            if not key_info['active']:
                return None
            
            if key_info['expires_at'] and datetime.now(timezone.utc) > key_info['expires_at']:
                return None
            
            # Update usage stats
            key_info['last_used'] = datetime.now(timezone.utc)
            key_info['usage_count'] += 1
            
            return key_info
            
        except Exception as e:
            self.logger.error("Failed to verify API key", error=str(e))
            return None
    
    def create_jwt_token(self, payload: Dict[str, Any]) -> str:
        """Create a JWT token."""
        try:
            # Set expiration
            payload['exp'] = datetime.now(timezone.utc) + timedelta(hours=self.expiration_hours)
            payload['iat'] = datetime.now(timezone.utc)
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return token
            
        except Exception as e:
            self.logger.error("Failed to create JWT token", error=str(e))
            raise AuthenticationException("Failed to create token")
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify a JWT token and return the payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return dict(payload) if isinstance(payload, dict) else {}
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationException("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationException(f"Invalid token: {str(e)}")
        except Exception as e:
            self.logger.error("Failed to verify JWT token", error=str(e))
            raise AuthenticationException("Token verification failed")
    
    def get_tenant_info(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant information."""
        return self.tenants.get(tenant_id)
    
    def check_permission(self, tenant_id: str, permission: str, user_permissions: List[str]) -> bool:
        """Check if a user has a specific permission."""
        tenant_info = self.get_tenant_info(tenant_id)
        if not tenant_info or not tenant_info.get('active', False):
            return False
        
        # Check if user has admin permission
        if 'admin' in user_permissions:
            return True
        
        # Check if user has the specific permission
        if permission in user_permissions:
            return True
        
        return False
    
    def check_quota(self, tenant_id: str, resource_type: str, current_usage: int) -> bool:
        """Check if tenant is within quota limits."""
        tenant_info = self.get_tenant_info(tenant_id)
        if not tenant_info:
            return False
        
        quota = tenant_info.get('quota', {})
        limit = quota.get(resource_type)
        
        if limit is None:
            return True  # No limit set
        
        return bool(current_usage < limit)
    
    def authenticate_request(self, authorization_header: Optional[str]) -> Dict[str, Any]:
        """Authenticate a request using API key or JWT token."""
        if not authorization_header:
            raise AuthenticationException("Missing authorization header")
        
        parts = authorization_header.split(' ')
        if len(parts) != 2:
            raise AuthenticationException("Invalid authorization header format")
        
        auth_type, credentials = parts
        
        if auth_type.lower() == 'bearer':
            # JWT token authentication
            try:
                payload = self.verify_jwt_token(credentials)
                tenant_id = payload.get('tenant_id')
                if not tenant_id:
                    raise AuthenticationException("Token missing tenant_id")
                
                return {
                    'tenant_id': tenant_id,
                    'user_id': payload.get('user_id'),
                    'permissions': payload.get('permissions', []),
                    'auth_type': 'jwt'
                }
            except Exception as e:
                raise AuthenticationException(f"JWT authentication failed: {str(e)}")
        
        elif auth_type.lower() == 'apikey':
            # API key authentication
            key_info = self.verify_api_key(credentials)
            if not key_info:
                raise AuthenticationException("Invalid API key")
            
            return {
                'tenant_id': key_info['tenant_id'],
                'api_key_name': key_info['name'],
                'permissions': key_info['permissions'],
                'auth_type': 'api_key'
            }
        
        else:
            raise AuthenticationException(f"Unsupported authentication type: {auth_type}")
    
    def authorize_operation(
        self,
        auth_info: Dict[str, Any],
        operation: str,
        resource: Optional[str] = None
    ) -> None:
        """Authorize an operation for an authenticated user."""
        tenant_id = auth_info['tenant_id']
        permissions = auth_info.get('permissions', [])
        
        # Check if tenant is active
        tenant_info = self.get_tenant_info(tenant_id)
        if not tenant_info or not tenant_info.get('active', False):
            raise AuthorizationException("Tenant is not active")
        
        # Map operations to required permissions
        permission_map = {
            'read_dataset': 'read',
            'list_datasets': 'read',
            'create_dataset': 'write',
            'update_dataset': 'write',
            'delete_dataset': 'admin',
            'read_vector': 'read',
            'insert_vector': 'write',
            'update_vector': 'write',
            'delete_vector': 'write',
            'search_vectors': 'read',
            'get_stats': 'read',
            'get_metrics': 'admin',
        }
        
        required_permission = permission_map.get(operation, 'admin')
        
        if not self.check_permission(tenant_id, required_permission, permissions):
            raise AuthorizationException(f"Insufficient permissions for operation: {operation}")
        
        self.logger.debug(
            "Operation authorized",
            tenant_id=tenant_id,
            operation=operation,
            required_permission=required_permission
        )
    
    def create_tenant(
        self,
        tenant_id: str,
        name: str,
        permissions: List[str],
        quota: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """Create a new tenant."""
        if tenant_id in self.tenants:
            raise ValueError(f"Tenant {tenant_id} already exists")
        
        tenant = {
            'id': tenant_id,
            'name': name,
            'created_at': datetime.now(timezone.utc),
            'active': True,
            'permissions': permissions,
            'quota': quota or {
                'max_datasets': 50,
                'max_vectors_per_dataset': 500000,
                'max_storage_bytes': 5 * 1024 * 1024 * 1024,  # 5GB
            }
        }
        
        self.tenants[tenant_id] = tenant
        self.logger.info("Tenant created", tenant_id=tenant_id, name=name)
        
        return tenant
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        try:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            key_info = self.api_keys.get(key_hash)
            
            if key_info:
                key_info['active'] = False
                self.logger.info("API key revoked", tenant_id=key_info['tenant_id'], name=key_info['name'])
                return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to revoke API key", error=str(e))
            return False
    
    def get_api_key_stats(self) -> Dict[str, Any]:
        """Get API key usage statistics."""
        total_keys = len(self.api_keys)
        active_keys = sum(1 for key in self.api_keys.values() if key['active'])
        
        by_tenant = {}
        for key_info in self.api_keys.values():
            tenant_id = key_info['tenant_id']
            if tenant_id not in by_tenant:
                by_tenant[tenant_id] = {'total': 0, 'active': 0}
            by_tenant[tenant_id]['total'] += 1
            if key_info['active']:
                by_tenant[tenant_id]['active'] += 1
        
        return {
            'total_keys': total_keys,
            'active_keys': active_keys,
            'by_tenant': by_tenant,
            'total_tenants': len(self.tenants),
        }