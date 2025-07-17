<!--
SPDX-FileCopyrightText: 2023 Deep Lake Team

SPDX-License-Identifier: MIT
-->

# Release Notes

All notable releases of this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-07-16

### 🔒 Security Hardening Release

This release addresses critical security vulnerabilities and improves the overall security posture of the Deep Lake Vector Service.

### 🚨 **BREAKING CHANGES**

#### Authentication Changes
- **Hardcoded API Keys Removed**: The default development API key `dev-12345-abcdef-67890-ghijkl` has been removed
- **JWT Secret Required**: `JWT_SECRET_KEY` environment variable is now required for service startup
- **Environment Variables**: All authentication now requires proper environment variable configuration

#### Migration Required
1. **Generate JWT Secret**: 
   ```bash
   export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

2. **Generate API Key**:
   ```bash
   python scripts/generate_api_key_quick.py
   ```

3. **Update Environment**: Use the provided `bashrc_exports.sh` template or create a `.env` file

### ✅ **New Features**

#### Always-Available Documentation
- **API Documentation**: `/docs` and `/redoc` endpoints now always accessible
- **Interactive Testing**: Swagger UI available in all environments for API testing
- **Development Experience**: Improved developer experience with persistent documentation access

#### Enhanced Configuration
- **Environment Support**: Comprehensive `.env` file support for `uv run`
- **Validation**: Improved Pydantic settings with better error messages
- **Flexibility**: Added support for optional configuration parameters

#### Security Tools
- **API Key Generator**: `generate_api_key_quick.py` for secure key creation
- **Environment Templates**: `bashrc_exports.sh` for easy environment setup
- **Secure Defaults**: All security-sensitive values now use secure generation

### 🔧 **Improvements**

#### Service Startup
- **uv Compatibility**: Fixed all issues with `uv run` startup
- **Error Handling**: Better error messages for missing configuration
- **Validation**: Comprehensive validation of required environment variables

#### Documentation Updates
- **Security Examples**: All examples now use environment variables
- **Configuration Guide**: Updated setup instructions for secure configuration
- **Best Practices**: Added security best practices throughout documentation

### 🐛 **Bug Fixes**

#### Authentication System
- **Pydantic Validation**: Fixed environment variable loading issues
- **JWT Configuration**: Resolved JWT_SECRET_KEY mapping problems
- **Service Startup**: Fixed startup failures with missing configuration

#### Documentation Access
- **Conditional Logic**: Removed debug-only restrictions on documentation
- **Endpoint Availability**: Documentation endpoints now work in all environments
- **Root Endpoint**: Improved root endpoint to show available documentation

### 📚 **Documentation**

#### Updated Files
- **CHANGELOG.md**: Comprehensive change documentation
- **ROADMAP.md**: Updated to reflect completed security improvements
- **README.md**: Revised authentication and configuration sections
- **SECURITY.md**: Enhanced security documentation

#### New Files
- **bashrc_exports.sh**: Environment variable configuration template
- **generate_api_key_quick.py**: Secure API key generation tool
- **.env**: Production-ready environment configuration example

### 🔐 **Security Impact**

#### Eliminated Risks
- **Hardcoded Credentials**: All hardcoded API keys and secrets removed
- **Test Exposure**: Cleaned up test files to prevent credential leakage
- **Example Security**: All examples now use environment variables

#### Enhanced Security
- **Secure Generation**: All keys now use cryptographically secure generation
- **Environment Isolation**: Proper separation of configuration from code
- **Validation**: Strong validation of security-sensitive configuration

### 🚀 **Getting Started with v1.0.1**

1. **Update Environment**:
   ```bash
   # Generate JWT secret
   export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   
   # Generate API key
   python scripts/generate_api_key_quick.py
   export API_KEY="your-generated-api-key"
   ```

2. **Start Service**:
   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Test Documentation**:
   ```bash
   # Visit http://localhost:8000/docs
   # Click "Authorize" and enter your API key
   ```

### 🎯 **Next Steps**

The security foundation is now solid. Next release will focus on:
- Cosine similarity distance metric implementation
- Advanced metadata filtering
- Grafana monitoring dashboards
- Performance optimizations

---

## [1.0.0] - 2025-07-16

### Added
- **Multi-Protocol API Support**: HTTP REST API and gRPC API for high-performance integrations
- **Vector Database Operations**: Complete CRUD operations for vectors and datasets
- **Multi-Tenant Architecture**: Secure tenant isolation with per-tenant dataset management
- **Authentication & Authorization**: API key and JWT token authentication with role-based access control
- **Search Capabilities**: Vector similarity search with L2 norm distance calculation
- **Batch Operations**: Bulk vector insertion up to 1,000 vectors with performance tracking
- **Caching System**: Redis-based caching for improved performance
- **Monitoring & Metrics**: Prometheus metrics integration with comprehensive observability
- **Health Checks**: Kubernetes-ready liveness and readiness probes
- **Production Deployment**: Docker containers and Kubernetes manifests for scalable deployment
- **Configuration Management**: Environment-based configuration with structured logging
- **Error Handling**: Comprehensive error handling with structured error responses
- **API Documentation**: OpenAPI/Swagger integration for interactive API documentation
- **Client Libraries**: Python async and sync client examples
- **Development Tools**: Docker Compose for local development environment

### Security
- **Secure Authentication**: Fixed development API key system with JWT token support
- **Tenant Isolation**: Multi-tenant data isolation with quota management
- **Input Validation**: Comprehensive request validation using Pydantic models
- **Error Sanitization**: Secure error responses that don't leak sensitive information

### Performance
- **Concurrent Processing**: Async/await implementation for high-throughput operations
- **Connection Pooling**: Efficient database connection management
- **Batch Processing**: Optimised bulk operations with configurable batch sizes
- **Caching Strategy**: Multi-level caching for frequently accessed data
- **Thread Pool Management**: Configurable thread pools for CPU-intensive operations

### Compatibility
- **Python Support**: Python 3.9+ compatibility
- **Deep Lake Integration**: Deep Lake 4.0+ compatibility with modern API usage
- **Database Support**: Redis for caching and session management
- **Container Support**: Docker and Kubernetes deployment ready
- **Cloud Ready**: Configurable storage locations for cloud deployments

### Documentation
- **API Reference**: Complete OpenAPI specification with interactive documentation
- **Deployment Guide**: Comprehensive deployment instructions for Docker and Kubernetes
- **Development Setup**: Local development environment configuration
- **Usage Examples**: Python client examples with both async and sync implementations
- **Configuration Guide**: Environment variable configuration documentation

### Testing
- **Unit Tests**: Comprehensive unit test coverage for core functionality
- **Integration Tests**: End-to-end integration tests for API endpoints
- **Performance Tests**: Load testing for concurrent operations
- **Test Infrastructure**: Pytest configuration with async test support

### Known Limitations
- **Search Algorithms**: Currently limited to exact vector search (L2 norm only)
- **Text Search**: Text search endpoint exists but requires embedding service integration
- **Index Types**: Advanced indexing algorithms (HNSW, IVF) not yet implemented
- **Distance Metrics**: Limited to L2 norm distance calculation
- **Horizontal Scaling**: Single-instance deployment model

### Dependencies
- **FastAPI**: Modern Python web framework for HTTP API
- **gRPC**: High-performance RPC framework
- **Deep Lake**: Vector database storage engine (4.0+)
- **Redis**: Caching and session management
- **Prometheus**: Metrics collection and monitoring
- **Pydantic**: Data validation and serialisation
- **Uvicorn**: ASGI server for production deployment

### Deployment Requirements
- **Python**: 3.9 or higher
- **Memory**: Minimum 2GB RAM recommended
- **Storage**: Configurable storage location for vector data
- **Network**: HTTP (8000) and gRPC (50051) ports for API access
- **Dependencies**: Redis instance for caching (optional but recommended)

### Migration Notes
- This is the initial release of the Deep Lake Vector Service
- No migration required for new installations
- Configuration is managed through environment variables
- Default development settings are provided for quick setup

### Breaking Changes
- N/A (initial release)

### Deprecations
- N/A (initial release)

---

## Development Status

This release represents a production-ready foundation for vector database operations.
The service provides approximately 30-40% of a full-featured vector database platform.

**Current Capabilities:**
- ✅ Core vector operations (CRUD, search)
- ✅ Multi-tenant architecture
- ✅ Production-ready infrastructure
- ✅ Authentication and authorization
- ✅ Monitoring and observability

**Planned Enhancements:**
- 🔄 Advanced search algorithms (HNSW, ANN)
- 🔄 Text search and semantic search
- 🔄 Additional distance metrics (cosine, dot product)
- 🔄 Horizontal scaling support
- 🔄 Enterprise features (advanced RBAC, audit logging)

---

## Support

For issues, questions, or contributions:
- **Issues**: Create an issue in the project repository
- **Documentation**: Refer to the README.md and docs/ directory
- **Contributing**: See CONTRIBUTING.md for contribution guidelines
- **License**: MIT License (see LICENSE file)

---

**Full Changelog**: https://github.com/your-org/deeplake-vector-service/commits/v1.0.0