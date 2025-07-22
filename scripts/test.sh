#!/bin/bash

# Modern pytest runner for DeepLake API service
# Supports multiple test categories and configurations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}====== $1 ======${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Change to project root
cd "$PROJECT_ROOT"

# Set test environment variables
export DEEPLAKE_STORAGE_LOCATION="./test_data"
export JWT_SECRET_KEY="test-secret-key-for-testing-only-$(date +%s)"
export REDIS_URL="redis://localhost:6379/1"  # Use different DB for tests
export DEV_DEBUG="true"
export DEV_DEFAULT_API_KEY="test-api-key-$(openssl rand -hex 16)"

# Create test data directory
mkdir -p test_data

# Function to run specific test categories
run_tests() {
    local test_type="$1"
    local markers="$2"
    local description="$3"
    
    print_header "$description"
    
    if [ -n "$markers" ]; then
        pytest tests/ \
            -m "$markers" \
            --cov=app \
            --cov-report=term-missing \
            --cov-report=html:htmlcov \
            --cov-report=xml:coverage.xml \
            --cov-fail-under=25 \
            -v \
            --tb=short
    else
        pytest tests/ \
            --cov=app \
            --cov-report=term-missing \
            --cov-report=html:htmlcov \
            --cov-report=xml:coverage.xml \
            --cov-fail-under=25 \
            -v \
            --tb=short
    fi
}

# Handle command line arguments
case "${1:-all}" in
    "unit")
        run_tests "unit" "unit" "Unit Tests"
        ;;
    "integration")
        run_tests "integration" "integration" "Integration Tests"
        ;;
    "monitoring")
        print_warning "Monitoring tests require monitoring stack (Prometheus, Grafana, etc.)"
        run_tests "monitoring" "monitoring" "Monitoring & Alerting Tests"
        ;;
    "fast")
        run_tests "fast" "not slow and not monitoring" "Fast Tests (excluding slow and monitoring tests)"
        ;;
    "comprehensive")
        print_header "Comprehensive API Tests"
        pytest tests/integration/test_api_comprehensive.py -v --tb=short
        ;;
    "coverage")
        print_header "Full Test Suite with Detailed Coverage"
        pytest tests/ \
            --cov=app \
            --cov-report=term-missing \
            --cov-report=html:htmlcov \
            --cov-report=xml:coverage.xml \
            --cov-fail-under=25 \
            -v \
            --tb=short \
            --cov-report=term:skip-covered
        ;;
    "help")
        echo "DeepLake API Test Runner"
        echo "========================"
        echo
        echo "Usage: $0 [test_type]"
        echo
        echo "Test Types:"
        echo "  all           - Run all tests (default)"
        echo "  unit          - Run unit tests only"
        echo "  integration   - Run integration tests only"
        echo "  monitoring    - Run monitoring/alerting tests (requires monitoring stack)"
        echo "  fast          - Run fast tests (exclude slow and monitoring tests)"
        echo "  comprehensive - Run comprehensive API tests (converted from curl_examples.sh)"
        echo "  coverage      - Run all tests with detailed coverage report"
        echo "  help          - Show this help message"
        echo
        echo "Examples:"
        echo "  ./scripts/test.sh                    # Run all tests"
        echo "  ./scripts/test.sh unit              # Unit tests only"
        echo "  ./scripts/test.sh fast              # Fast tests for development"
        echo "  ./scripts/test.sh comprehensive     # Full API workflow tests"
        echo
        echo "Environment Variables:"
        echo "  PYTEST_ARGS - Additional pytest arguments"
        echo "  TEST_VERBOSE - Set to '1' for verbose output"
        ;;
    "all"|*)
        print_header "Running All Tests"
        
        # Check if pytest is available
        if ! command -v pytest >/dev/null 2>&1; then
            print_error "pytest not available. Please install test dependencies:"
            echo "pip install -e .[test]"
            exit 1
        fi
        
        # Run different test suites
        print_header "Unit Tests"
        run_tests "unit" "unit" "Unit Tests" || print_warning "Some unit tests failed"
        
        echo
        print_header "Integration Tests"
        run_tests "integration" "integration and not monitoring" "Integration Tests (excluding monitoring)" || print_warning "Some integration tests failed"
        
        echo
        print_header "Comprehensive API Tests"
        pytest tests/integration/test_api_comprehensive.py -v --tb=short || print_warning "Some comprehensive API tests failed"
        
        # Optionally run monitoring tests if monitoring stack is available
        echo
        print_header "Monitoring Tests (Optional)"
        if curl -s http://localhost:9090/-/healthy >/dev/null 2>&1; then
            print_success "Monitoring stack detected, running monitoring tests"
            run_tests "monitoring" "monitoring" "Monitoring Tests" || print_warning "Some monitoring tests failed"
        else
            print_warning "Monitoring stack not available, skipping monitoring tests"
            echo "To run monitoring tests, start the monitoring stack with docker-compose"
        fi
        ;;
esac

# Cleanup test data
rm -rf test_data

# Final status
if [ $? -eq 0 ]; then
    print_success "Test run completed!"
    echo
    echo "📊 Coverage Report: htmlcov/index.html"
    echo "🔍 XML Report: coverage.xml"
else
    print_error "Some tests failed!"
    exit 1
fi