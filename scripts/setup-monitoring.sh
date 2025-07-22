#!/bin/bash

# DeepLake API Monitoring Setup Script
# This script sets up Grafana dashboards and Prometheus monitoring

set -e

echo "🚀 Setting up DeepLake API Monitoring..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it first."
    exit 1
fi

# Check if we're in the correct directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found. Please run this script from the project root."
    exit 1
fi

print_status "Checking monitoring configuration..."

# Ensure directories exist
mkdir -p deployment/grafana/provisioning/dashboards
mkdir -p deployment/grafana/provisioning/datasources
mkdir -p deployment/grafana/dashboards

# Check if dashboards exist
DASHBOARDS=(
    "service-overview.json"
    "vector-operations.json"
    "search-performance.json"
    "tenant-analytics.json"
    "cache-and-errors.json"
)

for dashboard in "${DASHBOARDS[@]}"; do
    if [ ! -f "deployment/grafana/dashboards/$dashboard" ]; then
        print_warning "Dashboard $dashboard not found. Monitoring may not work properly."
    fi
done

# Check if provisioning files exist
if [ ! -f "deployment/grafana/provisioning/dashboards/dashboards.yaml" ]; then
    print_warning "Dashboards provisioning configuration not found."
fi

if [ ! -f "deployment/grafana/provisioning/datasources/prometheus.yaml" ]; then
    print_warning "Prometheus datasource configuration not found."
fi

print_status "Starting monitoring stack..."

# Start Prometheus and Grafana
docker-compose up -d prometheus grafana

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 10

# Check if Prometheus is accessible
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    print_status "✅ Prometheus is running at http://localhost:9090"
else
    print_error "❌ Prometheus is not accessible. Check docker-compose logs."
    exit 1
fi

# Check if Grafana is accessible
if curl -s http://localhost:3000/api/health > /dev/null; then
    print_status "✅ Grafana is running at http://localhost:3000"
else
    print_error "❌ Grafana is not accessible. Check docker-compose logs."
    exit 1
fi

# Start the main service
print_status "Starting DeepLake API service..."
docker-compose up -d deeplake-service

# Wait for service to be ready
print_status "Waiting for DeepLake service to start..."
sleep 15

# Check if the service is accessible
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    print_status "✅ DeepLake API service is running at http://localhost:8000"
else
    print_warning "⚠️  DeepLake API service may not be ready yet. Check docker-compose logs."
fi

# Check if metrics endpoint is accessible
if curl -s http://localhost:8000/api/v1/metrics/prometheus > /dev/null; then
    print_status "✅ Metrics endpoint is accessible at http://localhost:8000/api/v1/metrics/prometheus"
else
    print_warning "⚠️  Metrics endpoint is not accessible. Authentication may be required."
fi

print_status "🎉 Monitoring setup complete!"
echo ""
echo "Access your monitoring tools:"
echo "  📊 Grafana: http://localhost:3000 (admin/admin)"
echo "  📈 Prometheus: http://localhost:9090"
echo "  🔧 DeepLake API: http://localhost:8000"
echo "  📋 API Docs: http://localhost:8000/docs"
echo ""
echo "Available Dashboards:"
echo "  • Service Overview - Overall health and performance"
echo "  • Vector Operations - Vector storage and manipulation"
echo "  • Search Performance - Search query performance"
echo "  • Tenant Analytics - Multi-tenant usage patterns"
echo "  • Cache & Errors - Caching and error monitoring"
echo ""
echo "Next steps:"
echo "  1. Open Grafana and explore the dashboards"
echo "  2. Configure alerting rules for production monitoring"
echo "  3. Customize dashboards for your specific needs"
echo "  4. Set up log aggregation for comprehensive monitoring"
echo ""
print_status "For detailed documentation, see: deployment/grafana/README.md"