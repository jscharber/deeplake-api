#!/bin/bash

# Start Monitoring Stack for Tributary AI Service
# This script starts all monitoring services including the dashboard

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🚀 Starting Tributary AI Service Monitoring Stack..."
echo "=================================================="

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed or not in PATH"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from example..."
    cp .env.example .env
    echo "✅ Please edit .env file with your configuration"
fi

# Start monitoring services
echo "🔧 Starting monitoring services..."
docker-compose up -d monitoring-dashboard prometheus grafana alertmanager redis

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
echo "==================="

services=(
    "monitoring-dashboard:8080:Monitoring Dashboard"
    "prometheus:9090:Prometheus"
    "grafana:3000:Grafana"
    "alertmanager:9093:AlertManager"
    "redis:6379:Redis"
)

all_healthy=true

for service_info in "${services[@]}"; do
    IFS=':' read -r service port name <<< "$service_info"
    
    echo -n "Checking $name... "
    
    if docker-compose ps $service | grep -q "Up"; then
        echo "✅ Running"
    else
        echo "❌ Not Running"
        all_healthy=false
    fi
done

echo ""

if [ "$all_healthy" = true ]; then
    echo "🎉 All monitoring services are running!"
    echo ""
    echo "📊 Access URLs:"
    echo "==============="
    echo "• Monitoring Dashboard: http://localhost:8080"
    echo "• Grafana Dashboards:   http://localhost:3000 (admin/admin)"
    echo "• Prometheus Metrics:   http://localhost:9090"
    echo "• AlertManager:         http://localhost:9093"
    echo ""
    echo "📚 Quick Commands:"
    echo "==================="
    echo "• View logs:            docker-compose logs -f"
    echo "• Stop services:        docker-compose down"
    echo "• Restart service:      docker-compose restart [service-name]"
    echo "• Run verification:     bash scripts/verify_monitoring.sh"
    echo ""
    echo "🎯 Start here: http://localhost:8080"
else
    echo "❌ Some services failed to start. Check logs:"
    echo "   docker-compose logs"
fi