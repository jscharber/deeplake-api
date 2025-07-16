#!/bin/bash

# Deep Lake Vector Service - Local Development Runner
# ==================================================

echo "🚀 Setting up Deep Lake Vector Service for local development..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

print_status "Python 3 found"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed"
    exit 1
fi

print_status "pip3 found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_status "Virtual environment exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
print_status "Virtual environment activated"

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    print_status "Dependencies installed"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Create local data directories
mkdir -p local_data/vectors
mkdir -p logs
print_status "Local directories created"

# Set environment variables
export DEEPLAKE_STORAGE_LOCATION="$(pwd)/local_data/vectors"
export REDIS_URL="redis://localhost:6379/0"
export CACHE_ENABLED="false"
export LOG_LEVEL="DEBUG"
export LOG_FORMAT="console"
export DEBUG="true"
export WORKERS="1"
export METRICS_ENABLED="false"
export PYTHONPATH="$(pwd)"
export PYTHONUNBUFFERED="1"
export PYTHONDONTWRITEBYTECODE="1"

print_status "Environment variables set"

echo ""
echo "🎯 Local Development Configuration:"
echo "   Storage:    $DEEPLAKE_STORAGE_LOCATION"
echo "   Cache:      Disabled"
echo "   Logging:    DEBUG level"
echo "   Workers:    1 (for debugging)"
echo "   Metrics:    Disabled"
echo ""

# Check if Redis is running (optional)
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        print_status "Redis is running (cache available but disabled)"
    else
        print_warning "Redis is not running (cache disabled anyway)"
    fi
else
    print_warning "Redis not installed (cache disabled)"
fi

echo ""
echo "🚀 Starting Deep Lake Vector Service..."
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Health: http://localhost:8000/api/v1/health"
echo ""
echo "🔑 Test API Key: dev-12345-abcdef-67890-ghijkl"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================================================================="

# Run the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

echo ""
print_status "Server stopped"