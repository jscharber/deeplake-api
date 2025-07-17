# Security Setup Guide

## Overview

This guide explains how to set up the Deep Lake Vector Service with secure configuration after the removal of hardcoded credentials.

## Required Environment Variables

### JWT Secret Key (Required)
```bash
export JWT_SECRET_KEY="your-secure-jwt-secret-key-min-32-chars"
```

**Generate a secure JWT secret:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Development API Key (Optional)
```bash
export DEV_DEFAULT_API_KEY="your-development-api-key"
```

## Quick Start

### 1. Generate JWT Secret
```bash
# Generate and set JWT secret
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 2. Generate API Key
```bash
# Use the built-in key generator
python scripts/generate_api_key.py
```

### 3. Start the Service
```bash
# Start with environment variables
JWT_SECRET_KEY=$JWT_SECRET_KEY python -m app.main
```

## Usage Examples

### With Generated API Key
```bash
# Set your API key
export API_KEY="your-generated-api-key"

# Test the service
curl -H "Authorization: ApiKey $API_KEY" http://localhost:8000/api/v1/health

# Run examples
API_KEY=$API_KEY python docs/examples/python_client.py
API_KEY=$API_KEY bash docs/examples/curl_examples.sh
```

### Docker Compose
```bash
# Set environment variables
export JWT_SECRET_KEY="your-secure-jwt-secret"

# Start services
docker-compose up
```

### Kubernetes
```bash
# Update secret.yaml with base64 encoded values
kubectl apply -f deployment/kubernetes/secret.yaml
kubectl apply -f deployment/kubernetes/
```

## Security Improvements

### ✅ What Was Fixed
- Removed hardcoded API key `dev-12345-abcdef-67890-ghijkl`
- Removed hardcoded JWT secret `your-secret-key-change-in-production`
- Made JWT secret key required via environment variable
- Updated all scripts and examples to use environment variables
- Added API key generator script

### ⚠️ Important Notes
- **JWT_SECRET_KEY is required** - service will not start without it
- **API keys are generated dynamically** - use the generator script
- **No default credentials** - all authentication is explicit
- **Environment variables only** - no hardcoded values in code

### 🔐 Best Practices
1. **Never commit credentials** to version control
2. **Use strong, random secrets** (32+ characters)
3. **Rotate keys regularly** in production
4. **Use separate keys** for different environments
5. **Store secrets securely** (e.g., HashiCorp Vault, AWS Secrets Manager)

## Migration Guide

### From Hardcoded Keys
If you were using the old hardcoded API key:

**Before:**
```bash
curl -H "Authorization: ApiKey dev-12345-abcdef-67890-ghijkl" http://localhost:8000/api/v1/health
```

**After:**
```bash
# Generate new API key
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export API_KEY=$(python scripts/generate_api_key.py)

# Use new API key
curl -H "Authorization: ApiKey $API_KEY" http://localhost:8000/api/v1/health
```

## Troubleshooting

### Service Won't Start
```
ValueError: JWT_SECRET_KEY environment variable is required
```
**Solution:** Set the JWT_SECRET_KEY environment variable

### API Key Not Working
```
401 Unauthorized
```
**Solution:** Generate a new API key using the generator script

### Examples Fail
```
ERROR: API_KEY environment variable is required
```
**Solution:** Set the API_KEY environment variable before running examples

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `JWT_SECRET_KEY` | ✅ Yes | JWT signing secret | `abc123...` |
| `API_KEY` | For examples | API key for requests | `xyz789...` |
| `DEV_DEFAULT_API_KEY` | No | Development API key | `dev-key-123` |
| `API_BASE_URL` | No | Service base URL | `http://localhost:8000` |

## Support

If you encounter issues:
1. Check environment variables are set correctly
2. Verify API key is valid using the health endpoint
3. Review logs for authentication errors
4. Generate new credentials if needed