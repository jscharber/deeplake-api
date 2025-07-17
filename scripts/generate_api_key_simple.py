#!/usr/bin/env python3
"""
Simple API Key Generator for Deep Lake Vector Service
==================================================

This script generates a secure API key for the Deep Lake Vector Service.
"""

import os
import sys
import secrets
import jwt
import hashlib
from datetime import datetime, timezone

def generate_jwt_secret():
    """Generate a secure JWT secret key."""
    return secrets.token_urlsafe(32)

def generate_api_key():
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)

def main():
    """Generate API key and show usage instructions."""
    print("🔑 Deep Lake Vector Service - API Key Generator")
    print("=" * 50)
    
    # Check for JWT secret
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        jwt_secret = generate_jwt_secret()
        print(f"📝 Generated JWT Secret: {jwt_secret}")
        print(f"   Set environment variable: export JWT_SECRET_KEY={jwt_secret}")
        print()
    
    # Get input (use defaults if not interactive)
    try:
        tenant_id = input("Enter tenant ID (default: 'default'): ").strip() or "default"
        key_name = input("Enter API key name (default: 'Generated Key'): ").strip() or "Generated Key"
        
        print("\nSelect permissions (comma-separated):")
        print("  - read: Read access to datasets and vectors")
        print("  - write: Write access (create/update vectors)")
        print("  - admin: Admin access (manage datasets, view metrics)")
        permissions_input = input("Permissions (default: 'read,write'): ").strip() or "read,write"
        permissions = [p.strip() for p in permissions_input.split(",")]
    except (EOFError, KeyboardInterrupt):
        # Use defaults if not interactive
        tenant_id = "default"
        key_name = "Generated Key"
        permissions = ["read", "write"]
        print("Using defaults: tenant_id='default', permissions=['read', 'write']")
    
    # Generate the API key
    api_key = generate_api_key()
    
    print("\n✅ API Key Generated Successfully!")
    print("=" * 50)
    print(f"🔑 API Key: {api_key}")
    print(f"👤 Tenant ID: {tenant_id}")
    print(f"📝 Name: {key_name}")
    print(f"🔐 Permissions: {', '.join(permissions)}")
    print()
    print("📋 Usage Examples:")
    print(f"   curl -H 'Authorization: ApiKey {api_key}' http://localhost:8000/api/v1/health")
    print(f"   export API_KEY={api_key}")
    print()
    print("⚠️  Security Notes:")
    print("   - Store this API key securely")
    print("   - Do not commit it to version control")
    print("   - Use environment variables in production")
    print()
    print("🚀 Next Steps:")
    print("   1. Start the service with the JWT secret:")
    print(f"      JWT_SECRET_KEY={jwt_secret} python -m app.main")
    print("   2. Use the API key in your requests")
    print("   3. Test with: curl -H 'Authorization: ApiKey {api_key}' http://localhost:8000/api/v1/health")

if __name__ == "__main__":
    main()