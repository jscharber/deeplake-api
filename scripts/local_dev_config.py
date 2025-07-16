#!/usr/bin/env python3
"""
Local Development Configuration
===============================

This file sets up the environment for running the Deep Lake Vector Service
locally for debugging and development.
"""

import os
import sys
from pathlib import Path

def setup_local_environment():
    """Setup environment variables for local development."""
    
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()
    
    # Environment variables for local development
    env_vars = {
        # Storage and data
        "DEEPLAKE_STORAGE_LOCATION": str(project_root / "local_data" / "vectors"),
        "DEEPLAKE_TOKEN": "",  # Empty for local development
        "DEEPLAKE_ORG_ID": "",  # Empty for local development
        
        # Redis (use local Redis or disable)
        "REDIS_URL": "redis://localhost:6379/0",
        "CACHE_ENABLED": "false",  # Disable cache for debugging
        
        # Logging
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "console",
        
        # Server settings
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "DEBUG": "true",
        "WORKERS": "1",  # Single worker for debugging
        
        # Authentication (simplified for local dev)
        "AUTH_ENABLED": "true",
        "JWT_SECRET_KEY": "local-dev-secret-key-not-for-production",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRATION_HOURS": "24",
        
        # Monitoring (disable for local dev)
        "METRICS_ENABLED": "false",
        "PROMETHEUS_ENABLED": "false",
        
        # Database (if needed)
        "DATABASE_URL": "",  # Not needed for vector storage
        
        # Python settings
        "PYTHONPATH": str(project_root),
        "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✅ {key}={value}")
    
    # Create local data directories
    data_dir = Path(env_vars["DEEPLAKE_STORAGE_LOCATION"])
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created data directory: {data_dir}")
    
    # Add project root to Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        print(f"✅ Added to Python path: {project_root}")

def print_setup_info():
    """Print information about the local setup."""
    print("\n" + "="*60)
    print("🚀 DEEP LAKE VECTOR SERVICE - LOCAL DEVELOPMENT SETUP")
    print("="*60)
    
    print("\n📁 Project Structure:")
    print("   local_data/vectors/     - Local vector storage")
    print("   app/                    - Application code")
    print("   logs/                   - Application logs")
    
    print("\n🔧 Configuration:")
    print("   • Single worker for debugging")
    print("   • Cache disabled")
    print("   • Debug logging enabled")
    print("   • Metrics disabled")
    print("   • Local file storage")
    
    print("\n🐛 Debugging:")
    print("   • Set breakpoints in your IDE")
    print("   • Use print() statements")
    print("   • Check logs/ directory")
    
    print("\n🌐 Endpoints:")
    print("   Health:    http://localhost:8000/api/v1/health")
    print("   Datasets:  http://localhost:8000/api/v1/datasets/")
    print("   Vectors:   http://localhost:8000/api/v1/datasets/{id}/vectors/")
    print("   Docs:      http://localhost:8000/docs")
    
    print("\n🔑 API Key for testing:")
    print("   Authorization: ApiKey dev-12345-abcdef-67890-ghijkl")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    setup_local_environment()
    print_setup_info()
    
    print("\n🚀 Starting development server...")
    print("   Press Ctrl+C to stop")
    print("   Use 'python local_dev_config.py' to run")
    print("\n" + "-"*60)
    
    # Import and run the app
    try:
        import uvicorn
        from app.main import app
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Development server stopped")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("Make sure you have installed dependencies:")
        print("pip install -r requirements.txt")