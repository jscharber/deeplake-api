#!/bin/bash

# Test script for Deep Lake Vector Service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Running tests for Deep Lake Vector Service..."
echo "Project root: $PROJECT_ROOT"

# Change to project root
cd "$PROJECT_ROOT"

# Create test environment variables
export DEEPLAKE_STORAGE_LOCATION="./test_data"
export JWT_SECRET_KEY="test-secret-key"
export REDIS_URL="redis://localhost:6379/1"  # Use different DB for tests
export DEV_DEBUG="true"

# Create test data directory
mkdir -p test_data

# Run tests with coverage
if command -v pytest >/dev/null 2>&1; then
    echo "Running pytest..."
    pytest tests/ \
        --cov=app \
        --cov-report=term-missing \
        --cov-report=html:htmlcov \
        --cov-report=xml:coverage.xml \
        --cov-fail-under=80 \
        -v
else
    echo "pytest not available, running with python -m unittest"
    python -m unittest discover tests/
fi

# Cleanup test data
rm -rf test_data

echo "Tests completed successfully!"