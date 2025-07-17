#!/usr/bin/env python3
"""
Generate API Key for Deep Lake Vector Service
===========================================

This script generates a secure API key for the Deep Lake Vector Service.
"""

import os
import sys
import secrets

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_jwt_secret():
    """Generate a secure JWT secret key."""
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
        # Set it for this session
        os.environ["JWT_SECRET_KEY"] = jwt_secret
    
    try:
        # Import after ensuring environment variable is set
        from app.services.auth_service import AuthService
        
        # Initialize auth service
        auth_service = AuthService()
        
        # Generate API key
        tenant_id = input("Enter tenant ID (default: 'default'): ").strip() or "default"
        key_name = input("Enter API key name (default: 'Generated Key'): ").strip() or "Generated Key"
        
        print("\nSelect permissions (comma-separated):")
        print("  - read: Read access to datasets and vectors")
        print("  - write: Write access (create/update vectors)")
        print("  - admin: Admin access (manage datasets, view metrics)")
        permissions_input = input("Permissions (default: 'read,write'): ").strip() or "read,write"
        permissions = [p.strip() for p in permissions_input.split(",")]
        
        # Generate the API key
        api_key = auth_service.generate_api_key(
            tenant_id=tenant_id,
            name=key_name,
            permissions=permissions
        )
        
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
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure to set the JWT_SECRET_KEY environment variable:")
        print(f"   export JWT_SECRET_KEY={generate_jwt_secret()}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()