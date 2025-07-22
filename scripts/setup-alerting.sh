#!/bin/bash

# DeepLake API Alerting System Setup Script
# This script helps set up and configure the alerting system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_DIR="$PROJECT_DIR/deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}==== $1 ====${NC}"
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

check_dependencies() {
    print_step "Checking dependencies"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker is installed"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    print_success "Docker Compose is installed"
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed. Please install curl first."
        exit 1
    fi
    print_success "curl is installed"
}

check_env_file() {
    print_step "Checking environment configuration"
    
    ENV_FILE="$PROJECT_DIR/.env"
    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env file not found. Creating template..."
        cat > "$ENV_FILE" << EOF
# DeepLake API Configuration
JWT_SECRET_KEY=your-secret-key-here-$(openssl rand -hex 32)
GRAFANA_PASSWORD=admin

# Optional - DeepLake Cloud
DEEPLAKE_TOKEN=
DEEPLAKE_ORG_ID=

# Alerting Configuration (update these with your actual values)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
PAGERDUTY_INTEGRATION_KEY=your-pagerduty-integration-key
ALERT_EMAIL_TO=oncall@yourcompany.com
ALERT_EMAIL_FROM=alerts@yourcompany.com
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=alerts@yourcompany.com
SMTP_PASSWORD=your-smtp-password
EOF
        print_success "Created .env template file"
        print_warning "Please edit .env file with your actual configuration values"
    else
        print_success ".env file exists"
    fi
}

validate_config() {
    print_step "Validating configuration files"
    
    # Check if alertmanager.yml exists
    if [ ! -f "$DEPLOYMENT_DIR/alertmanager.yml" ]; then
        print_error "alertmanager.yml not found in deployment directory"
        exit 1
    fi
    print_success "alertmanager.yml exists"
    
    # Check if prometheus.yml exists
    if [ ! -f "$DEPLOYMENT_DIR/prometheus.yml" ]; then
        print_error "prometheus.yml not found in deployment directory"
        exit 1
    fi
    print_success "prometheus.yml exists"
    
    # Check if prometheus-alerts.yml exists
    if [ ! -f "$DEPLOYMENT_DIR/prometheus-alerts.yml" ]; then
        print_error "prometheus-alerts.yml not found in deployment directory"
        exit 1
    fi
    print_success "prometheus-alerts.yml exists"
    
    # Validate Prometheus configuration
    if command -v promtool &> /dev/null; then
        print_step "Validating Prometheus configuration"
        if promtool check config "$DEPLOYMENT_DIR/prometheus.yml" &> /dev/null; then
            print_success "Prometheus configuration is valid"
        else
            print_error "Prometheus configuration is invalid"
            promtool check config "$DEPLOYMENT_DIR/prometheus.yml"
            exit 1
        fi
    else
        print_warning "promtool not found, skipping Prometheus config validation"
    fi
}

start_services() {
    print_step "Starting DeepLake API with alerting stack"
    
    cd "$PROJECT_DIR"
    
    # Start services
    if docker-compose up -d; then
        print_success "Services started successfully"
    else
        print_error "Failed to start services"
        exit 1
    fi
    
    # Wait for services to be ready
    print_step "Waiting for services to be ready"
    
    # Wait for Prometheus
    echo -n "Waiting for Prometheus to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:9090/-/ready &> /dev/null; then
            echo " ✓"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Wait for Alertmanager
    echo -n "Waiting for Alertmanager to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:9093/-/ready &> /dev/null; then
            echo " ✓"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Wait for DeepLake API
    echo -n "Waiting for DeepLake API to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/v1/health &> /dev/null; then
            echo " ✓"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Wait for Grafana
    echo -n "Waiting for Grafana to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:3000/api/health &> /dev/null; then
            echo " ✓"
            break
        fi
        echo -n "."
        sleep 2
    done
}

check_services() {
    print_step "Checking service health"
    
    # Check Prometheus
    if curl -s http://localhost:9090/-/healthy &> /dev/null; then
        print_success "Prometheus is healthy"
    else
        print_error "Prometheus is not healthy"
    fi
    
    # Check Alertmanager
    if curl -s http://localhost:9093/-/healthy &> /dev/null; then
        print_success "Alertmanager is healthy"
    else
        print_error "Alertmanager is not healthy"
    fi
    
    # Check DeepLake API
    if curl -s http://localhost:8000/api/v1/health &> /dev/null; then
        print_success "DeepLake API is healthy"
    else
        print_error "DeepLake API is not healthy"
    fi
    
    # Check Grafana
    if curl -s http://localhost:3000/api/health &> /dev/null; then
        print_success "Grafana is healthy"
    else
        print_error "Grafana is not healthy"
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping &> /dev/null; then
        print_success "Redis is healthy"
    else
        print_error "Redis is not healthy"
    fi
}

test_alerts() {
    print_step "Testing alert system"
    
    # Send test alert
    print_step "Sending test alert to Alertmanager"
    
    TEST_ALERT='{
        "labels": {
            "alertname": "TestAlert",
            "severity": "warning",
            "service": "deeplake-api"
        },
        "annotations": {
            "summary": "Test alert from setup script",
            "description": "This is a test alert to verify the alerting system is working"
        }
    }'
    
    if curl -s -X POST http://localhost:9093/api/v1/alerts \
        -H "Content-Type: application/json" \
        -d "[$TEST_ALERT]" &> /dev/null; then
        print_success "Test alert sent successfully"
        print_warning "Check your configured notification channels for the test alert"
    else
        print_error "Failed to send test alert"
    fi
}

show_urls() {
    print_step "Service URLs"
    
    echo "📊 Grafana:      http://localhost:3000"
    echo "📈 Prometheus:   http://localhost:9090"
    echo "🔔 Alertmanager: http://localhost:9093"
    echo "🚀 DeepLake API: http://localhost:8000"
    echo "🔧 Redis:        redis://localhost:6379"
    echo ""
    echo "📋 Health Checks:"
    echo "  DeepLake API: http://localhost:8000/api/v1/health"
    echo "  Prometheus:   http://localhost:9090/-/healthy"
    echo "  Alertmanager: http://localhost:9093/-/healthy"
    echo "  Grafana:      http://localhost:3000/api/health"
    echo ""
    echo "📊 Metrics:"
    echo "  Prometheus metrics: http://localhost:8000/api/v1/metrics/prometheus"
    echo "  Service stats:      http://localhost:8000/api/v1/stats"
}

show_next_steps() {
    print_step "Next Steps"
    
    echo "1. 🔧 Configure notification channels:"
    echo "   - Edit deployment/alertmanager.yml"
    echo "   - Add your Slack webhook URL"
    echo "   - Add your PagerDuty integration key"
    echo "   - Configure email settings"
    echo ""
    echo "2. 📊 Access Grafana dashboards:"
    echo "   - Visit http://localhost:3000"
    echo "   - Login with admin/admin (or your configured password)"
    echo "   - Import pre-built dashboards"
    echo ""
    echo "3. 🧪 Test the system:"
    echo "   - Run: ./scripts/test-alerting.sh"
    echo "   - Monitor logs: docker-compose logs -f alertmanager"
    echo ""
    echo "4. 📚 Read documentation:"
    echo "   - deployment/alerting-setup.md"
    echo "   - Prometheus alerts: deployment/prometheus-alerts.yml"
    echo ""
    echo "5. 🔄 Restart services after config changes:"
    echo "   - docker-compose restart alertmanager"
    echo "   - docker-compose restart prometheus"
}

main() {
    echo -e "${GREEN}DeepLake API Alerting System Setup${NC}"
    echo "=================================="
    echo ""
    
    check_dependencies
    check_env_file
    validate_config
    start_services
    
    echo ""
    print_step "Setup complete!"
    
    check_services
    test_alerts
    show_urls
    show_next_steps
    
    echo ""
    print_success "Alerting system is ready to use!"
}

# Handle command line arguments
case "${1:-}" in
    "check")
        check_services
        ;;
    "start")
        start_services
        ;;
    "test")
        test_alerts
        ;;
    "urls")
        show_urls
        ;;
    "help")
        echo "Usage: $0 [check|start|test|urls|help]"
        echo ""
        echo "Commands:"
        echo "  check  - Check service health"
        echo "  start  - Start services"
        echo "  test   - Send test alert"
        echo "  urls   - Show service URLs"
        echo "  help   - Show this help"
        echo ""
        echo "Run without arguments to perform full setup"
        ;;
    *)
        main
        ;;
esac