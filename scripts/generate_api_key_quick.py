#!/usr/bin/env python3
"""
Quick API Key Generator (Non-Interactive)
========================================

This script generates a secure API key for the Tributary AI services for DeepLake without prompts
and automatically configures it as the default development API key.
"""

import os
import secrets

def update_env_file(api_key: str) -> None:
    """Update .env file with the generated API key."""
    env_file = ".env"
    
    # Read current .env file
    lines = []
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            lines = f.readlines()
    
    # Update or add DEV_DEFAULT_API_KEY
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("DEV_DEFAULT_API_KEY=") or line.startswith("# DEV_DEFAULT_API_KEY="):
            lines[i] = f"DEV_DEFAULT_API_KEY={api_key}\n"
            updated = True
            break
    
    if not updated:
        lines.append(f"\n# Generated Development API Key\nDEV_DEFAULT_API_KEY={api_key}\n")
    
    # Write updated .env file
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Updated {env_file} with DEV_DEFAULT_API_KEY")

def main():
    """Generate API key with defaults."""
    # Check for JWT secret
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        print("❌ ERROR: JWT_SECRET_KEY environment variable is required")
        print("   Set it with: export JWT_SECRET_KEY=$(python -c \"import secrets; print(secrets.token_urlsafe(32))\")")
        exit(1)
    
    # Generate API key with defaults
    api_key = secrets.token_urlsafe(32)
    tenant_id = "default"
    key_name = "Generated Development Key"
    permissions = ["read", "write", "admin"]
    
    # Update .env file
    update_env_file(api_key)
    
    print("🔑 Tributary AI services for DeepLake - API Key Generated")
    print("=" * 50)
    print(f"API_KEY={api_key}")
    print(f"TENANT_ID={tenant_id}")
    print(f"PERMISSIONS={','.join(permissions)}")
    print()
    print("📋 Usage:")
    print(f"   export API_KEY={api_key}")
    print(f"   curl -H 'Authorization: ApiKey {api_key}' http://localhost:8000/api/v1/health")
    print()
    print("🔄 Next Steps:")
    print("   1. Restart the service to load the new API key:")
    print("      uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    print("   2. Test the API key with the curl command above")

if __name__ == "__main__":
    main()