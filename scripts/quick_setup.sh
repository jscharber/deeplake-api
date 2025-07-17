#!/bin/bash
# Quick Setup Script for Deep Lake Vector Service
# This script sets up the environment with secure credentials

echo "🚀 Deep Lake Vector Service - Quick Setup"
echo "========================================="

# Check if JWT_SECRET_KEY is already set
if [ -z "$JWT_SECRET_KEY" ]; then
    echo "📝 Generating JWT secret..."
    export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "   JWT_SECRET_KEY=$JWT_SECRET_KEY"
    echo "   (Add to your .env file or export manually)"
else
    echo "✅ JWT_SECRET_KEY already set"
fi

# Generate API key
echo ""
echo "🔑 Generating API key..."
API_KEY=$(JWT_SECRET_KEY=$JWT_SECRET_KEY python scripts/generate_api_key_simple.py | grep "🔑 API Key:" | cut -d' ' -f3)

if [ -n "$API_KEY" ]; then
    echo "✅ API Key generated: $API_KEY"
    export API_KEY=$API_KEY
    
    echo ""
    echo "🚀 Environment Ready!"
    echo "===================="
    echo "JWT_SECRET_KEY=$JWT_SECRET_KEY"
    echo "API_KEY=$API_KEY"
    echo ""
    echo "📋 Quick Commands:"
    echo "   # Start service"
    echo "   JWT_SECRET_KEY=$JWT_SECRET_KEY python -m app.main"
    echo ""
    echo "   # Test API"
    echo "   curl -H 'Authorization: ApiKey $API_KEY' http://localhost:8000/api/v1/health"
    echo ""
    echo "   # Run examples"
    echo "   API_KEY=$API_KEY python docs/examples/python_client.py"
    echo "   API_KEY=$API_KEY bash docs/examples/curl_examples.sh"
else
    echo "❌ Failed to generate API key"
    exit 1
fi