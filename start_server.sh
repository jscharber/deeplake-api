#!/bin/bash
# Start the server with proper environment variables

# Load environment from .env file
set -a
source .env
set +a

# Export the key explicitly to make sure it's available
export JWT_SECRET_KEY="${JWT_SECRET_KEY}"
export DEV_DEFAULT_API_KEY="${DEV_DEFAULT_API_KEY}"

echo "Starting server with:"
echo "  JWT_SECRET_KEY: ${JWT_SECRET_KEY:0:10}..."
echo "  DEV_DEFAULT_API_KEY: ${DEV_DEFAULT_API_KEY:0:10}..."

# Start the server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload