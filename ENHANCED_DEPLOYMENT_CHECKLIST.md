# Enhanced Deployment Checklist

## 🎯 **Pre-Deployment Verification**

Before running `k8s/deploy.sh`, ensure the following components are in place:

### **✅ Required Files**
- [ ] `portal/unified_portal.py` - Includes enhanced dashboard routes
- [ ] `portal/templates/enhanced_dashboard.html` - Enhanced dashboard template
- [ ] `portal/basic_enhanced_metrics.py` - Basic enhanced metrics collector
- [ ] `ai_reports/` directory with all AI Reports modules
- [ ] `static/ai_reports/` directory with JavaScript and CSS files
- [ ] `database/migrations/add_ai_reports_tables.sql` - Database schema updates

### **✅ Configuration Files**
- [ ] `requirements.txt` includes `psutil>=5.9.0` and `aiohttp>=3.8.5`
- [ ] `k8s/secrets.yaml` has all required environment variables
- [ ] `k8s/configmap.yaml` includes AI Reports configuration

### **✅ Docker Image**
- [ ] Latest Docker image includes all new files
- [ ] Image is pushed to `ghcr.io/splinterstice/noctipede:latest`
- [ ] Dependencies are properly installed in the image

## 🚀 **Deployment Process**

### **1. Run Enhanced Deployment**
```bash
cd k8s/
./deploy.sh
```

### **2. Verify Deployment**
The deploy script will automatically run enhanced verification, or run manually:
```bash
./verify-enhanced-deployment.sh
```

### **3. Expected Results**
After successful deployment, you should have:

#### **✅ Working Dashboards**
- **Basic Dashboard**: `https://noctipede.splinterstice.celestium.life/`
- **Enhanced Dashboard**: `https://noctipede.splinterstice.celestium.life/enhanced`
- **Combined Dashboard**: `https://noctipede.splinterstice.celestium.life/combined`
- **AI Reports**: `https://noctipede.splinterstice.celestium.life/ai-reports`

#### **✅ Working API Endpoints**
- **Basic Metrics**: `/api/metrics`
- **Enhanced Metrics**: `/api/enhanced-metrics`
- **AI Reports API**: `/api/ai-reports/*`
- **Health Check**: `/api/health`

#### **✅ Enhanced Features**
- System resource monitoring (CPU, Memory, Disk)
- Database performance metrics
- MinIO storage statistics
- Ollama AI service status
- Network connectivity tests
- Service health monitoring

## 🔧 **Troubleshooting**

### **Enhanced Dashboard Times Out**
If the enhanced dashboard times out:

1. **Check Pod Logs**:
   ```bash
   kubectl logs -l app=noctipede-app -n noctipede
   ```

2. **Check Enhanced Metrics API**:
   ```bash
   curl https://noctipede.splinterstice.celestium.life/api/enhanced-metrics
   ```

3. **Verify Dependencies**:
   ```bash
   kubectl exec -it deployment/noctipede-app -n noctipede -- python -c "import psutil, aiohttp; print('Dependencies OK')"
   ```

### **Missing Dependencies**
If dependencies are missing, the system will gracefully fall back to basic enhanced metrics using only the standard library.

### **AI Reports Not Working**
If AI Reports features are not working:

1. **Check Static Files**:
   ```bash
   curl https://noctipede.splinterstice.celestium.life/static/ai_reports/js/ai_reports.js
   ```

2. **Check Database Migration**:
   ```bash
   kubectl exec -it deployment/noctipede-app -n noctipede -- python database/migrate_ai_reports.py
   ```

3. **Check API Routes**:
   ```bash
   curl https://noctipede.splinterstice.celestium.life/api/ai-reports/templates
   ```

## 📊 **Feature Availability Matrix**

| Feature | Basic Dashboard | Enhanced Dashboard | AI Reports |
|---------|----------------|-------------------|------------|
| Crawler Stats | ✅ | ✅ | ✅ |
| System Resources | ❌ | ✅ | ✅ |
| Database Metrics | ❌ | ✅ | ✅ |
| MinIO Storage | ❌ | ✅ | ✅ |
| Ollama AI Status | ❌ | ✅ | ✅ |
| Network Tests | ❌ | ✅ | ✅ |
| Service Health | ❌ | ✅ | ✅ |
| SQL Querying | ❌ | ❌ | ✅ |
| MemeCLIP Analysis | ❌ | ❌ | ✅ |
| Screenshot Capture | ❌ | ❌ | ✅ |
| AI Report Generation | ❌ | ❌ | ✅ |

## 🎯 **Success Criteria**

The deployment is successful when:

- [ ] All dashboards load without timeout
- [ ] Enhanced metrics API returns data
- [ ] No critical errors in pod logs
- [ ] Basic crawler functionality works
- [ ] Database is accessible and populated
- [ ] Static files are served correctly

## 🔄 **Fallback Behavior**

The system is designed with robust fallbacks:

1. **Enhanced Metrics**: Falls back to basic enhanced metrics if dependencies missing
2. **AI Reports**: Gracefully degrades if AI services unavailable
3. **Database**: Uses mock data if database connection fails
4. **Network Tests**: Shows "unknown" status if network tests fail

This ensures the system remains functional even if some advanced features are unavailable.

## 📝 **Post-Deployment Tasks**

After successful deployment:

1. **Test All Dashboards**: Verify each dashboard loads and displays data
2. **Check Metrics**: Ensure metrics are being collected and displayed
3. **Verify Crawling**: Test that the crawler can still function normally
4. **Monitor Logs**: Watch for any errors or warnings in the logs
5. **Performance Check**: Ensure the enhanced features don't impact performance

## 🎉 **Deployment Complete**

Once all checks pass, your enhanced Noctipede deployment is ready with:
- **4 Dashboard Variants** for different use cases
- **Advanced System Monitoring** with detailed metrics
- **AI-Powered Analytics** for comprehensive reporting
- **Robust Fallback System** ensuring reliability
- **Production-Ready Configuration** with proper error handling
