#!/bin/bash
# Monitoring Stack Verification Script for Tributary AI Service for DeepLake

set -e

echo "🔍 Tributary AI Service - Monitoring Stack Verification"
echo "======================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:9093}"

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2
    
    echo -n "Checking $service_name... "
    
    # Add timeout and max-time to prevent hanging
    if curl -sf --connect-timeout 5 --max-time 10 "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ UP${NC}"
        return 0
    else
        echo -e "${RED}❌ DOWN${NC}"
        return 1
    fi
}

# Function to check Prometheus metrics
check_prometheus_metric() {
    local metric=$1
    local query_url="$PROMETHEUS_URL/api/v1/query?query=$metric"
    
    echo -n "  Checking metric '$metric'... "
    
    # Add timeout to metric queries
    response=$(curl -sf --connect-timeout 5 --max-time 10 "$query_url" 2>/dev/null || echo "")
    
    if [[ -z "$response" ]]; then
        echo -e "${RED}❌ Failed to query${NC}"
        return 1
    fi
    
    # Check if metric has data
    result_count=$(echo "$response" | grep -o '"result":\[' | wc -l)
    if [[ $result_count -gt 0 ]]; then
        # Check if result array is not empty
        if echo "$response" | grep -q '"result":\[\]'; then
            echo -e "${YELLOW}⚠️  No data${NC}"
        else
            echo -e "${GREEN}✅ Found${NC}"
        fi
    else
        echo -e "${RED}❌ Not found${NC}"
    fi
}

# 1. Check Service Health
echo ""
echo "📊 Service Health Checks:"
echo "------------------------"

services_ok=true

check_service "API Service" "$API_URL/api/v1/health" || services_ok=false
check_service "Prometheus" "$PROMETHEUS_URL/-/healthy" || services_ok=false
check_service "Grafana" "$GRAFANA_URL/api/health" || services_ok=false
check_service "AlertManager" "$ALERTMANAGER_URL/-/healthy" || services_ok=false

# 2. Check Prometheus Targets
echo ""
echo "🎯 Prometheus Targets:"
echo "----------------------"

targets_response=$(curl -sf --connect-timeout 5 --max-time 10 "$PROMETHEUS_URL/api/v1/targets" 2>/dev/null || echo "")
if [[ -n "$targets_response" ]]; then
    active_targets=$(echo "$targets_response" | grep -o '"health":"up"' | wc -l)
    total_targets=$(echo "$targets_response" | grep -o '"health":"' | wc -l)
    
    if [[ $active_targets -eq $total_targets ]] && [[ $total_targets -gt 0 ]]; then
        echo -e "${GREEN}✅ All targets up ($active_targets/$total_targets)${NC}"
    else
        echo -e "${YELLOW}⚠️  Some targets down ($active_targets/$total_targets)${NC}"
    fi
    
    # List targets
    echo "$targets_response" | grep -o '"job":"[^"]*"' | sed 's/"job":"//g' | sed 's/"//g' | sort | uniq | while read -r job; do
        echo "  - $job"
    done
else
    echo -e "${RED}❌ Failed to fetch targets${NC}"
fi

# 3. Check Key Metrics
echo ""
echo "📈 Prometheus Metrics:"
echo "----------------------"

# HTTP Metrics
echo "HTTP Metrics:"
check_prometheus_metric "http_requests_total"
check_prometheus_metric "http_request_duration_seconds_bucket"

# Business Metrics
echo ""
echo "Business Metrics:"
check_prometheus_metric "datasets_active_total"
check_prometheus_metric "vectors_total"
check_prometheus_metric "search_operations_total"
check_prometheus_metric "vector_operations_total"

# System Metrics
echo ""
echo "System Metrics:"
check_prometheus_metric "process_resident_memory_bytes"
check_prometheus_metric "active_connections"

# 4. Check Grafana Data Sources
echo ""
echo "📊 Grafana Configuration:"
echo "-------------------------"

# Use default credentials if not set
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASS:-admin}"

# Check data sources
datasources=$(curl -sf --connect-timeout 5 --max-time 10 -u "$GRAFANA_USER:$GRAFANA_PASS" "$GRAFANA_URL/api/datasources" 2>/dev/null || echo "")
if [[ -n "$datasources" ]]; then
    prometheus_configured=$(echo "$datasources" | grep -c '"type":"prometheus"' || true)
    if [[ $prometheus_configured -gt 0 ]]; then
        echo -e "${GREEN}✅ Prometheus data source configured${NC}"
    else
        echo -e "${RED}❌ Prometheus data source not found${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Could not check data sources (auth may be required)${NC}"
fi

# Check dashboards
dashboards=$(curl -sf --connect-timeout 5 --max-time 10 -u "$GRAFANA_USER:$GRAFANA_PASS" "$GRAFANA_URL/api/search?type=dash-db" 2>/dev/null || echo "")
if [[ -n "$dashboards" ]]; then
    dashboard_count=$(echo "$dashboards" | grep -c '"title"' || echo 0)
    echo -e "${GREEN}✅ Found $dashboard_count dashboards${NC}"
else
    echo -e "${YELLOW}⚠️  Could not check dashboards${NC}"
fi

# 5. Generate Test Traffic (Optional)
echo ""
echo "🚦 Generate Test Traffic?"
echo "-------------------------"
echo "Would you like to generate test traffic to verify metric collection?"
read -p "Generate test traffic? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    API_KEY="${API_KEY:-${DEEPLAKE_API_KEY:-test-api-key}}"
    
    echo "Generating test traffic..."
    
    # Create test dataset
    echo -n "Creating test dataset... "
    create_response=$(curl -sf --connect-timeout 5 --max-time 10 -X POST "$API_URL/api/v1/datasets" \
        -H "Authorization: ApiKey $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "dataset_id": "monitoring-test-'$(date +%s)'",
            "name": "Monitoring Test",
            "embedding_dimension": 128,
            "distance_metric": "cosine"
        }' 2>/dev/null || echo "failed")
    
    if [[ "$create_response" != "failed" ]]; then
        echo -e "${GREEN}✅${NC}"
        
        # Generate some requests
        echo -n "Generating API requests... "
        for i in {1..10}; do
            curl -sf --connect-timeout 2 --max-time 5 "$API_URL/api/v1/health" > /dev/null 2>&1 || true
        done
        echo -e "${GREEN}✅${NC}"
        
        # Wait for metrics to be scraped
        echo "Waiting 30 seconds for metrics to be scraped..."
        sleep 30
        
        # Re-check metrics
        echo ""
        echo "Re-checking metrics after traffic generation:"
        check_prometheus_metric "http_requests_total"
        check_prometheus_metric "datasets_active_total"
    else
        echo -e "${RED}❌ Failed${NC}"
        echo "Note: You may need to set API_KEY environment variable"
    fi
fi

# 6. Summary
echo ""
echo "📋 Summary:"
echo "-----------"

if [[ "$services_ok" == true ]]; then
    echo -e "${GREEN}✅ All services are running${NC}"
else
    echo -e "${RED}❌ Some services are down${NC}"
fi

# Check if metrics are being collected
metrics_found=$(curl -sf --connect-timeout 5 --max-time 10 "$PROMETHEUS_URL/api/v1/label/__name__/values" 2>/dev/null | grep -c "http_requests_total" || echo 0)
if [[ $metrics_found -gt 0 ]]; then
    echo -e "${GREEN}✅ Metrics are being collected${NC}"
else
    echo -e "${YELLOW}⚠️  No metrics found (may need to generate traffic)${NC}"
fi

echo ""
echo "For detailed verification, see: docs/monitoring-verification.md"
echo "Timestamp: $(date)"