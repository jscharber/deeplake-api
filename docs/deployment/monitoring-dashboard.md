# Monitoring Dashboard Deployment

The Tributary AI Service includes a comprehensive monitoring dashboard that provides centralized access to all observability tools and system documentation.

## 🚀 Quick Start

### With Docker Compose (Recommended)

The monitoring dashboard is included in the main Docker Compose stack:

```bash
# Start all services including monitoring dashboard
docker-compose up -d

# Access the dashboard
open http://localhost:8080
```

### Standalone Deployment

```bash
# Build the monitoring dashboard image
docker build -f Dockerfile.monitoring -t tas-monitoring-dashboard .

# Run the monitoring dashboard
docker run -d \
  --name monitoring-dashboard \
  -p 8080:8080 \
  -v $(pwd):/app \
  tas-monitoring-dashboard
```

### Manual Deployment

```bash
# Install dependencies
pip install markdown

# Start the server
python3 markdown_server.py
```

## 🌐 Access URLs

| Component | URL | Purpose |
|-----------|-----|---------|
| **Monitoring Dashboard** | http://localhost:8080 | Main observability hub |
| **API Service** | http://localhost:8000 | Main application API |
| **Grafana** | http://localhost:3000 | Dashboards and visualization |
| **Prometheus** | http://localhost:9090 | Metrics collection |
| **AlertManager** | http://localhost:9093 | Alert routing |

## 📊 Dashboard Features

### Service Cards
- **Real-time health monitoring** of all services
- **Status indicators** (UP/DOWN) with automatic refresh
- **Direct links** to service interfaces
- **Health check details** and response times

### Documentation Integration
- **Markdown rendering** with professional styling
- **Syntax highlighting** for code blocks
- **Table formatting** and responsive design
- **Navigation breadcrumbs** and back links

### Quick Access Panel
- **API Documentation** links
- **Health check** endpoints
- **Setup guides** and troubleshooting
- **Useful commands** reference

## 🔧 Configuration

### Environment Variables

```bash
# Port configuration
PORT=8080

# Optional: Custom host binding
HOST=0.0.0.0
```

### Docker Compose Service

```yaml
monitoring-dashboard:
  build:
    context: .
    dockerfile: Dockerfile.monitoring
  ports:
    - "8080:8080"
  environment:
    - PORT=8080
  restart: unless-stopped
  networks:
    - deeplake-network
```

## 🎨 Customization

### Logo Integration
The dashboard automatically displays the TAS logo from `/docs/images/tas-500-500.png`:

- **Dashboard header**: 80x80px with elegant styling
- **Documentation pages**: 60x60px with consistent branding
- **Professional appearance**: White background, rounded corners, shadows

### Styling Customization
Edit `monitoring-dashboard.html` to customize:

```css
/* Logo styling */
.logo {
    width: 80px;
    height: 80px;
    margin-bottom: 20px;
    border-radius: 12px;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
    background: white;
    padding: 10px;
}

/* Color scheme */
body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

## 🔍 Health Monitoring

The dashboard performs automatic health checks every 30 seconds:

### Monitored Services
- **API Service**: `/api/v1/health`
- **Prometheus**: `/-/healthy`
- **Grafana**: `/api/health`
- **AlertManager**: `/-/healthy`
- **Redis**: Connection status

### Status Indicators
- ✅ **Green**: Service healthy and responding
- ❌ **Red**: Service down or not responding  
- ⚠️ **Yellow**: Service partially available

## 🔄 Updates and Maintenance

### Updating the Dashboard

```bash
# Rebuild the monitoring dashboard
docker-compose build monitoring-dashboard

# Restart with new changes
docker-compose restart monitoring-dashboard
```

### Log Access

```bash
# View dashboard logs
docker-compose logs -f monitoring-dashboard

# Check health status
curl http://localhost:8080/monitoring-dashboard.html
```

## 📱 Mobile Support

The dashboard is fully responsive and includes:
- **Mobile-friendly layout** with touch-optimized buttons
- **Responsive grid** that adapts to screen size
- **Touch gestures** for navigation
- **Readable typography** on small screens

## 🔐 Security Considerations

### Network Security
- Dashboard runs on internal Docker network
- External access only through mapped ports
- No authentication required for read-only access

### Production Deployment
For production environments:

1. **Add authentication** if publicly accessible
2. **Use reverse proxy** with SSL termination
3. **Configure firewall** rules for port 8080
4. **Monitor access logs** for security events

## 🛠️ Troubleshooting

### Common Issues

**Dashboard not loading:**
```bash
# Check if service is running
docker-compose ps monitoring-dashboard

# Check logs
docker-compose logs monitoring-dashboard

# Verify port binding
netstat -tlnp | grep :8080
```

**Markdown not rendering:**
```bash
# Verify markdown library is installed
docker-compose exec monitoring-dashboard pip list | grep markdown

# Check server logs for errors
docker-compose logs monitoring-dashboard
```

**Health checks failing:**
```bash
# Test individual service health
curl http://localhost:8000/api/v1/health
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
```

### Service Dependencies

The monitoring dashboard depends on:
- **Python 3.11+** runtime environment
- **Markdown library** for document rendering
- **Network connectivity** to monitored services
- **File system access** for documentation files

## 📚 Related Documentation

- [Monitoring Guide](../monitoring.md) - Comprehensive monitoring setup
- [Observability Strategy](../observability.md) - Monitoring philosophy and approach
- [Production Deployment](./production.md) - Production environment setup
- [Docker Deployment](./docker.md) - Docker-specific configurations

---

*The monitoring dashboard serves as the central hub for all observability and system management tasks in the Tributary AI Service ecosystem.*