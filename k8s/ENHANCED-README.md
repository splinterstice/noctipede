# 🕷️ Enhanced Noctipede Kubernetes Deployment

This enhanced deployment includes smart proxy readiness checking, improved dashboard functionality, and comprehensive Ollama statistics reporting.

## 🚀 Quick Start

```bash
# Deploy enhanced version
./deploy-enhanced.sh

# Check status
kubectl get pods -n noctipede

# Clean up enhanced version
./destroy-enhanced.sh
```

## ✨ New Features

### 🎯 Smart Proxy Readiness Checking
- **Crawler waits for 100% proxy readiness** via Portal API
- **Real-time proxy status monitoring** with detailed health checks
- **Graceful fallback** if proxies aren't fully ready
- **Comprehensive proxy testing** (port connectivity, SOCKS functionality, I2P bootstrapping)

### 📊 Enhanced Portal Dashboard
- **Live proxy status indicators** with visual health status
- **Complete Ollama statistics** including model counts and running instances
- **Real-time system metrics** with auto-refresh every 30 seconds
- **Responsive design** that works on mobile and desktop

### 🔌 New API Endpoints
- `/api/proxy-status` - Detailed proxy health information
- `/api/proxy-readiness` - Boolean readiness check for automation
- `/api/system-metrics` - Comprehensive system statistics
- `/api/health` - Service health check

## 🏗️ Architecture Improvements

### Enhanced Components

1. **Smart Crawler** (`noctipede-smart-crawler`)
   - Waits for Portal API confirmation that both Tor and I2P are 100% ready
   - Includes pre-crawl proxy verification
   - Enhanced error handling and logging

2. **Enhanced Portal** (`noctipede-portal`)
   - Real-time proxy status monitoring
   - Comprehensive Ollama integration
   - Live dashboard with auto-refresh
   - RESTful API for automation

3. **Proxy Status API**
   - Tor proxy: Tests SOCKS5 connectivity and port availability
   - I2P proxy: Checks HTTP proxy, console access, and tunnel status
   - Caching to prevent excessive checks

## 📋 Deployment Process

The enhanced deployment follows this improved order:

1. **Infrastructure Setup**
   - Namespace, secrets, configmaps
   - Persistent volume claims
   - MariaDB and MinIO

2. **Proxy Services**
   - Tor proxy with persistent storage
   - I2P proxy with bootstrap configuration

3. **Enhanced Portal**
   - Deploys with proxy status API
   - Waits for database and proxy services
   - Provides readiness endpoints

4. **Smart Crawler**
   - Waits for Portal API confirmation
   - Verifies both proxies are 100% ready
   - Includes comprehensive pre-crawl checks

## 🔧 Configuration

### New Environment Variables

```yaml
# Proxy readiness checking
PROXY_READINESS_CHECK: "true"
PORTAL_API_ENDPOINT: "http://noctipede-portal-service:8080"

# Enhanced I2P configuration
I2P_NETWORK_TIMEOUT: "15"
I2P_SITE_TIMEOUT: "30"
I2P_FALLBACK_ENABLED: "true"
I2P_MAX_RETRIES: "3"

# Ollama optimization
OLLAMA_KEEP_ALIVE: "5s"
OLLAMA_CONCURRENT_REQUESTS: "1"
OLLAMA_TIMEOUT: "30s"
```

### Proxy Status Checking

The enhanced portal performs these checks:

**Tor Proxy:**
- Port 9150 connectivity test
- SOCKS5 proxy functionality test
- Connection to Tor check service

**I2P Proxy:**
- HTTP proxy port 4444 availability
- Web console port 7070 accessibility
- Tunnel status and bootstrap verification

## 📊 Monitoring & Access

### Enhanced Dashboard
- **URL**: `http://<node-ip>:32080`
- **Features**: Live proxy status, Ollama stats, system metrics
- **Auto-refresh**: Every 30 seconds

### API Endpoints

```bash
# Check proxy readiness (for automation)
curl http://<node-ip>:32080/api/proxy-readiness

# Get detailed proxy status
curl http://<node-ip>:32080/api/proxy-status

# Get system metrics including Ollama
curl http://<node-ip>:32080/api/system-metrics

# Health check
curl http://<node-ip>:32080/api/health
```

### Monitoring Commands

```bash
# Check all pods
kubectl get pods -n noctipede

# View enhanced portal logs
kubectl logs -l app=noctipede-portal -n noctipede

# View smart crawler logs
kubectl logs -l app=noctipede-smart-crawler -n noctipede

# Check proxy status via API
kubectl exec -n noctipede deployment/noctipede-portal -- \
  curl -s http://localhost:8080/api/proxy-readiness

# Port forward for local access
kubectl port-forward service/noctipede-portal-service 8080:8080 -n noctipede
```

## 🔍 Troubleshooting

### Common Issues

1. **Crawler Waiting for Proxies**
   ```bash
   # Check proxy status
   kubectl logs -l app=noctipede-smart-crawler -n noctipede
   
   # Check portal API
   kubectl exec -n noctipede deployment/noctipede-portal -- \
     curl -s http://localhost:8080/api/proxy-status | jq .
   ```

2. **Dashboard Not Loading**
   ```bash
   # Check portal logs
   kubectl logs -l app=noctipede-portal -n noctipede
   
   # Verify service
   kubectl get service noctipede-portal-service -n noctipede
   ```

3. **Ollama Stats Missing**
   ```bash
   # Check Ollama connectivity
   kubectl exec -n noctipede deployment/noctipede-portal -- \
     curl -s http://ollama.ollama-service.svc.cluster.local:11434/api/tags
   ```

### Proxy Status Interpretation

**Tor Proxy Status:**
- `fully_functional`: Ready for .onion crawling
- `port_open_only`: Basic connectivity, may work
- `port_closed`: Not ready, crawler will skip Tor sites

**I2P Proxy Status:**
- `fully_functional`: Ready for .i2p crawling with tunnels active
- `proxy_only`: HTTP proxy ready, but console not accessible
- `bootstrapping`: Still initializing (normal for first 5-15 minutes)
- `not_responding`: Not ready, crawler will skip I2P sites

## 🚀 Advanced Usage

### Manual Proxy Status Check

```bash
# Get readiness percentage
kubectl exec -n noctipede deployment/noctipede-portal -- \
  curl -s http://localhost:8080/api/proxy-readiness | \
  jq '.readiness_percentage'

# Wait for both proxies to be ready
while true; do
  status=$(kubectl exec -n noctipede deployment/noctipede-portal -- \
    curl -s http://localhost:8080/api/proxy-readiness | jq -r '.both_ready')
  if [ "$status" = "true" ]; then
    echo "Both proxies are ready!"
    break
  fi
  echo "Waiting for proxies... (Tor: $(kubectl exec -n noctipede deployment/noctipede-portal -- curl -s http://localhost:8080/api/proxy-readiness | jq -r '.tor_ready'), I2P: $(kubectl exec -n noctipede deployment/noctipede-portal -- curl -s http://localhost:8080/api/proxy-readiness | jq -r '.i2p_ready'))"
  sleep 30
done
```

### Scheduled Crawling

The enhanced deployment includes a CronJob that:
- Runs every 6 hours
- Performs quick proxy readiness check
- Proceeds with crawling even if proxies aren't fully ready
- Logs proxy status for debugging

## 📈 Performance Improvements

### Smart Initialization
- **Parallel proxy startup** with health monitoring
- **Cached status checks** to reduce API overhead
- **Graceful degradation** if services aren't fully ready

### Enhanced Monitoring
- **Real-time dashboard** with live updates
- **Comprehensive metrics** including Ollama model usage
- **API-driven status** for automation and monitoring tools

## 🔄 Migration from Standard Deployment

To upgrade from the standard deployment:

```bash
# Destroy current deployment
./destroy.sh

# Deploy enhanced version
./deploy-enhanced.sh
```

The enhanced version is fully backward compatible and includes all features from the standard deployment plus the new enhancements.

## 📝 Notes

- **I2P Bootstrap Time**: I2P can take 5-15 minutes to fully bootstrap on first run
- **Proxy Readiness**: The crawler will wait up to 30 minutes for both proxies to be ready
- **Graceful Fallback**: If proxies aren't ready, the crawler continues with limited functionality
- **API Caching**: Proxy status is cached for 30 seconds to prevent excessive checks
- **Auto-refresh**: Dashboard updates every 30 seconds automatically

## 🆘 Support

For issues with the enhanced deployment:

1. **Check proxy status**: Use the `/api/proxy-status` endpoint
2. **Review logs**: Check both portal and crawler logs
3. **Verify connectivity**: Test proxy services directly
4. **Monitor resources**: Check pod resource usage and limits

The enhanced deployment provides comprehensive logging and monitoring to help diagnose any issues quickly.
