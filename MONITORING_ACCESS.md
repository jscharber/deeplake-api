# 🔍 Monitoring Dashboard - Access Guide

## 📊 **Port Forwarding Setup**

If you're running in WSL2, Docker Desktop, or a remote environment, you'll need to set up port forwarding to access the monitoring services.

### **Required Ports:**
- **8000** - Tributary AI API Service
- **3000** - Grafana Dashboard  
- **9090** - Prometheus Metrics
- **9093** - AlertManager
- **8080** - Monitoring Dashboard (optional)

---

## 🚀 **Access URLs**

### **For Local Access:**
- **API Service**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

### **For WSL/Remote Access:**
Replace `localhost` with your WSL IP address (get with `hostname -I`):
- **API Service**: http://YOUR_WSL_IP:8000
- **API Docs**: http://YOUR_WSL_IP:8000/docs
- **Grafana**: http://YOUR_WSL_IP:3000 (admin/admin)
- **Prometheus**: http://YOUR_WSL_IP:9090
- **AlertManager**: http://YOUR_WSL_IP:9093
- **Monitoring Dashboard**: http://YOUR_WSL_IP:8080/monitoring-dashboard.html

---

## 🔧 **Port Forwarding Commands**

### **WSL2 Port Forwarding (Windows):**
Run these commands in **Windows PowerShell as Administrator**:

```powershell
# Forward all monitoring ports
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=172.x.x.x
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=172.x.x.x
netsh interface portproxy add v4tov4 listenport=9090 listenaddress=0.0.0.0 connectport=9090 connectaddress=172.x.x.x
netsh interface portproxy add v4tov4 listenport=9093 listenaddress=0.0.0.0 connectport=9093 connectaddress=172.x.x.x

# Replace 172.x.x.x with your WSL IP (get it with: wsl hostname -I)
```

### **SSH Tunnel (Remote Server):**
```bash
# Forward all ports through SSH tunnel
ssh -L 8000:localhost:8000 -L 3000:localhost:3000 -L 9090:localhost:9090 -L 9093:localhost:9093 user@your-server
```

### **Docker Desktop:**
Docker Desktop should automatically forward ports. If not:
1. Open Docker Desktop
2. Go to Settings → Resources → Port Forwarding
3. Add the required ports

---

## 📱 **Quick Service Check**

### **Test Service Accessibility:**
```bash
# Check if services respond
curl -s http://localhost:8000/api/v1/health
curl -s http://localhost:9090/-/healthy  
curl -s http://localhost:3000/api/health
curl -s http://localhost:9093/-/healthy
```

### **Get WSL IP Address:**
```bash
# In WSL terminal
hostname -I
# Or
ip route show | grep -i default | awk '{ print $3}'
```

### **Check Windows Firewall (if needed):**
```powershell
# Allow ports through Windows Firewall
New-NetFirewallRule -DisplayName "Monitoring Ports" -Direction Inbound -Protocol TCP -LocalPort 8000,3000,9090,9093 -Action Allow
```

---

## 🌐 **Web Dashboard Access**

### **Method 1: Direct File Access**
```
file:///home/jscharber/eng/deeplake-api/monitoring-dashboard.html
```

### **Method 2: Docker Compose (Recommended)**
```bash
# Start all monitoring services including dashboard
docker-compose up -d

# Or start just the monitoring stack
bash scripts/start-monitoring.sh

# Access: http://localhost:8080
```

### **Method 3: Standalone HTTP Server**
```bash
cd /home/jscharber/eng/deeplake-api
python3 markdown_server.py
# Then access: http://localhost:8080/monitoring-dashboard.html
```

### **Method 4: Copy to Web Server**
Copy `monitoring-dashboard.html` to your web server or hosting service.

---

## 🛠️ **Troubleshooting**

### **Service Not Accessible:**
1. **Check if service is running**: `docker-compose ps`
2. **Check port binding**: `netstat -tlnp | grep :PORT`
3. **Check firewall**: Ensure ports are not blocked
4. **Check Docker networks**: `docker network ls`

### **WSL2 Specific Issues:**
1. **Get WSL IP**: `wsl hostname -I`
2. **Restart WSL**: `wsl --shutdown` then restart
3. **Check Windows port proxy**: `netsh interface portproxy show all`

### **Health Checks Failing:**
1. **CORS Issues**: Use HTTP server method for dashboard
2. **Network Issues**: Check if services can communicate
3. **Authentication**: Some endpoints may require API keys

---

## 📊 **Service Status Commands**

```bash
# Check all services
docker-compose ps

# Check individual service logs
docker-compose logs -f grafana
docker-compose logs -f prometheus
docker-compose logs -f alertmanager

# Restart monitoring stack
docker-compose restart prometheus grafana alertmanager

# Run verification script
bash scripts/verify_monitoring.sh
```

---

## 🔗 **Quick Links Reference**

| Service | Port | Purpose | Default Login |
|---------|------|---------|---------------|
| **API** | 8000 | Main application | API Key required |
| **Grafana** | 3000 | Dashboards & visualization | admin/admin |
| **Prometheus** | 9090 | Metrics collection | None |
| **AlertManager** | 9093 | Alert routing | None |
| **Redis** | 6379 | Cache (internal) | None |

---

*💡 **Tip**: Bookmark the monitoring dashboard URL once you get port forwarding working. It provides a centralized hub for all your observability tools.*