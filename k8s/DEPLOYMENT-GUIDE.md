# Noctipede Kubernetes Deployment Guide

## 🚀 Complete Deployment with All Fixes

This guide covers deploying Noctipede with all the latest fixes and enhancements, including:

- ✅ **Unified Portal** with all three dashboard types (Basic, Enhanced, Combined)
- ✅ **Fixed Service Health Card** with proper data handling
- ✅ **Enhanced Ollama AI Service Card** with response time metrics
- ✅ **Comprehensive AI Configuration** options
- ✅ **Latest Docker Image** with all fixes applied

## 📋 Prerequisites

- Kubernetes cluster with kubectl configured
- Longhorn or another storage provisioner
- External Ollama service (optional, for AI features)

## 🔧 Configuration Options

### AI Analysis Configuration

The `configmap.yaml` now includes comprehensive AI configuration options:

```yaml
# AI Analysis Configuration - NEW: Enable/disable AI features
AI_ANALYSIS_ENABLED: "true"           # Master switch for all AI analysis
AI_TEXT_ANALYSIS_ENABLED: "true"      # Enable AI text content analysis
AI_IMAGE_ANALYSIS_ENABLED: "true"     # Enable AI image analysis
AI_CONTENT_MODERATION_ENABLED: "true" # Enable AI content moderation
AI_REPORTS_ENABLED: "true"            # Enable AI-powered reports in portal
AI_BATCH_SIZE: "10"                   # Number of items to process in AI batch
AI_RETRY_ATTEMPTS: "3"                # Number of retry attempts for AI requests
AI_REQUEST_TIMEOUT: "60"              # Timeout for AI requests in seconds
AI_QUEUE_MAX_SIZE: "100"              # Maximum size of AI processing queue
```

### Portal Configuration

```yaml
# Portal Configuration - NEW: Dashboard options
PORTAL_TYPE: "unified"                 # Portal type: unified, basic, enhanced, combined
PORTAL_DEFAULT_DASHBOARD: "combined"   # Default dashboard to show
PORTAL_ENABLE_AI_REPORTS: "true"       # Enable AI reports in portal
PORTAL_METRICS_CACHE_SECONDS: "30"     # Cache duration for metrics
PORTAL_AUTO_REFRESH_SECONDS: "60"      # Auto-refresh interval for dashboards
```

## 🚀 Deployment Steps

### 1. Quick Deployment

```bash
# Navigate to k8s directory
cd k8s/

# Run the deployment script
./deploy.sh
```

### 2. Verify Deployment

```bash
# Run verification script
./verify-deployment.sh
```

### 3. Access the Portal

```bash
# Port forward to access locally
kubectl port-forward service/noctipede-portal-service 8080:8080 -n noctipede

# Visit in browser
open http://localhost:8080
```

## 📊 Dashboard Access

The unified portal provides access to all dashboard types:

- **Dashboard Selector**: `http://localhost:8080/` - Choose your dashboard
- **Basic Dashboard**: `http://localhost:8080/basic` - Simple, clean interface
- **Enhanced Dashboard**: `http://localhost:8080/enhanced` - Advanced metrics with fixed cards
- **Combined Dashboard**: `http://localhost:8080/combined` - Comprehensive view

## 🔧 Configuration Customization

### Enable/Disable AI Features

Edit `configmap.yaml` to control AI features:

```bash
# Disable all AI analysis
AI_ANALYSIS_ENABLED: "false"

# Enable only text analysis
AI_TEXT_ANALYSIS_ENABLED: "true"
AI_IMAGE_ANALYSIS_ENABLED: "false"
AI_CONTENT_MODERATION_ENABLED: "false"

# Apply changes
kubectl apply -f configmap.yaml

# Restart pods to pick up changes
kubectl rollout restart deployment/noctipede-portal -n noctipede
```

### Change Default Dashboard

```bash
# Set enhanced dashboard as default
PORTAL_DEFAULT_DASHBOARD: "enhanced"

# Apply and restart
kubectl apply -f configmap.yaml
kubectl rollout restart deployment/noctipede-portal -n noctipede
```

## 🐛 Troubleshooting

### Portal Not Starting

```bash
# Check pod logs
kubectl logs -l app=noctipede-portal -n noctipede

# Check pod status
kubectl get pods -n noctipede

# Restart portal
kubectl rollout restart deployment/noctipede-portal -n noctipede
```

### Service Health Card Issues

The Service Health card has been fixed to handle both string and object service formats. If you see issues:

```bash
# Check API response format
kubectl port-forward service/noctipede-portal-service 8080:8080 -n noctipede &
curl -s http://localhost:8080/api/metrics | jq '.services'
```

### Ollama AI Service Card Issues

The duplicate card has been removed and response time metrics added. If you see issues:

```bash
# Check Ollama connectivity
kubectl logs -l app=noctipede-portal -n noctipede | grep -i ollama

# Verify Ollama endpoint in config
kubectl get configmap noctipede-config -n noctipede -o yaml | grep OLLAMA_ENDPOINT
```

## 📈 Monitoring

### Check System Health

```bash
# All pods status
kubectl get pods -n noctipede

# Service status
kubectl get services -n noctipede

# Portal health
curl -s http://localhost:8080/api/health
```

### View Logs

```bash
# Portal logs
kubectl logs -l app=noctipede-portal -n noctipede -f

# All application logs
kubectl logs -l app=noctipede-app -n noctipede -f

# Database logs
kubectl logs -l app=mariadb -n noctipede -f
```

## 🔄 Updates

### Deploy New Image Version

```bash
# Update image in deploy.sh
# Change: image: ghcr.io/splinterstice/noctipede:7bfbcf3-dirty
# To:     image: ghcr.io/splinterstice/noctipede:new-version

# Redeploy
./deploy.sh

# Or update existing deployment
kubectl set image deployment/noctipede-portal noctipede-portal=ghcr.io/splinterstice/noctipede:new-version -n noctipede
```

### Update Configuration

```bash
# Edit configmap.yaml
vim configmap.yaml

# Apply changes
kubectl apply -f configmap.yaml

# Restart to pick up changes
kubectl rollout restart deployment/noctipede-portal -n noctipede
```

## 🎯 Key Features Deployed

### ✅ Fixed Issues

1. **Service Health Card**: Now properly handles both string and object service status formats
2. **Ollama AI Service Card**: Removed duplicate card, added response time metrics with color coding
3. **Unified Portal**: Single portal serving all three dashboard types
4. **Enhanced Dashboard**: All cards working correctly with proper data handling

### ✅ New Features

1. **Comprehensive AI Configuration**: Full control over AI analysis features
2. **Portal Configuration**: Customizable dashboard behavior
3. **Response Time Metrics**: Color-coded performance indicators
4. **Dashboard Selection**: Easy switching between dashboard types
5. **Improved Error Handling**: Graceful fallbacks for all scenarios

## 📞 Support

If you encounter issues:

1. Run `./verify-deployment.sh` to check system status
2. Check pod logs for specific error messages
3. Verify configuration in `configmap.yaml`
4. Ensure all required services are running

The deployment script (`deploy.sh`) now includes all fixes and will deploy a fully functional Noctipede system with the unified portal and comprehensive AI configuration options.
