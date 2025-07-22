#!/bin/bash

# Build script for Tributary AI services for DeepLake

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Building Tributary AI services for DeepLake..."
echo "Project root: $PROJECT_ROOT"

# Change to project root
cd "$PROJECT_ROOT"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Generate protobuf files
echo "Generating protobuf files..."
if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import grpc_tools" >/dev/null 2>&1; then
        ./scripts/generate_proto.sh
    else
        echo "Warning: grpc_tools not available, skipping protobuf generation"
    fi
else
    echo "Warning: python3 not available, skipping protobuf generation"
fi

# Run linting (if available)
if command -v black >/dev/null 2>&1; then
    echo "Running code formatting..."
    black app/ tests/ --line-length 88
fi

if command -v isort >/dev/null 2>&1; then
    echo "Running import sorting..."
    isort app/ tests/ --profile black
fi

if command -v flake8 >/dev/null 2>&1; then
    echo "Running linting..."
    flake8 app/ tests/ --max-line-length 88 --extend-ignore E203,W503
fi

# Run type checking (if available)
if command -v mypy >/dev/null 2>&1; then
    echo "Running type checking..."
    mypy app/ --ignore-missing-imports
fi

echo "Build completed successfully!"