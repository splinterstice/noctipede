# Permanent Crawler Fixes

## 🚨 **Issues Identified:**

### **1. CronJob Using Wrong Image**
- **File**: `k8s/crawler-nfs.yaml`
- **Issue**: Using `ghcr.io/splinterstice/noctipede:i2p-database-fix` (old)
- **Fix**: Updated to `ghcr.io/splinterstice/noctipede:latest`

### **2. Bypassing Readiness System**
- **File**: `k8s/crawler-nfs.yaml`
- **Issue**: Direct `python -m crawlers.main` bypasses readiness checks
- **Fix**: Added comprehensive readiness check + use `crawlers.manager`

### **3. Concurrency Limitations**
- **File**: `k8s/crawler-nfs.yaml`
- **Issue**: Hardcoded limitations override ConfigMap settings
- **Fix**: Updated environment variables for proper concurrency

### **4. Analysis Disabled**
- **File**: `k8s/crawler-nfs.yaml`
- **Issue**: Content and image analysis disabled
- **Fix**: Enabled both analysis types

## ✅ **Permanent Changes Made:**

### **k8s/crawler-nfs.yaml:**

#### **Image Update:**
```yaml
# Before:
image: ghcr.io/splinterstice/noctipede:i2p-database-fix

# After:
image: ghcr.io/splinterstice/noctipede:latest
```

#### **Readiness Integration:**
```yaml
# Before:
PYTHONPATH=/app python -m crawlers.main

# After:
echo "🔍 Checking comprehensive system readiness..."
until curl -s http://noctipede-portal-service:8080/api/readiness | grep -q '"ready_for_crawling":true'; do
  echo "⏳ System not ready for crawling, waiting..."
  curl -s http://noctipede-portal-service:8080/api/readiness | grep -o '"readiness_summary":"[^"]*"' || echo "Unable to get readiness status"
  sleep 30
done
echo "✅ System is ready for crawling!"

PYTHONPATH=/app python -m crawlers.manager
```

#### **Concurrency Fixes:**
```yaml
# Before:
- name: OLLAMA_CONCURRENT_REQUESTS
  value: "1"
- name: CONTENT_ANALYSIS_ENABLED
  value: "false"
- name: IMAGE_ANALYSIS_ENABLED
  value: "false"

# After:
- name: OLLAMA_CONCURRENT_REQUESTS
  value: "3"  # Allow more concurrent AI requests
- name: CONTENT_ANALYSIS_ENABLED
  value: "true"  # Enable content analysis
- name: IMAGE_ANALYSIS_ENABLED
  value: "true"  # Enable image analysis
```

#### **Enhanced Init Container:**
```yaml
# Added portal service check:
until nc -z noctipede-portal-service 8080; do
  echo "⏳ Portal service not ready, waiting..."
  sleep 5
done
echo "✅ Portal service is ready!"
```

## 🔄 **Deployment Workflow:**

### **1. Build and Push Latest Image:**
```bash
make ghcr-deploy
```

### **2. Deploy with Fixed Configuration:**
```bash
cd k8s
./destroy.sh
./deploy.sh
```

### **3. Expected Behavior:**
- ✅ CronJob uses latest image with all fixes
- ✅ Crawler waits for comprehensive readiness (Tor + I2P)
- ✅ Uses proper concurrency settings from ConfigMap
- ✅ Enables content and image analysis
- ✅ Uses readiness-aware crawler manager

## 📊 **Expected Results:**

### **Before Fixes:**
- ❌ Crawler runs immediately (bypasses readiness)
- ❌ Single-threaded operation
- ❌ No content/image analysis
- ❌ Uses old image without readiness integration

### **After Fixes:**
- ✅ Crawler waits until both Tor AND I2P are ready
- ✅ Uses MAX_CONCURRENT_CRAWLERS setting (10 concurrent)
- ✅ Full content and image analysis enabled
- ✅ Uses latest image with all performance optimizations

## 🕐 **Timeline Expectations:**

### **Fresh Deployment:**
1. **0-5 minutes**: Services start, basic connectivity established
2. **5-30 minutes**: I2P network bootstrapping, 1-3 proxies active
3. **30+ minutes**: I2P network mature, 5+ proxies active → **Crawler starts**

### **Crawler Behavior:**
- **Readiness Check**: Every 30 seconds until system ready
- **Concurrency**: Up to 10 concurrent crawlers
- **Analysis**: Full AI-powered content and image analysis
- **Schedule**: Every 30 minutes (only if system ready)

## 🧪 **Testing Commands:**

### **Check Readiness:**
```bash
curl http://<node-ip>:30080/api/readiness
```

### **Monitor Crawler:**
```bash
kubectl logs -f job/noctipede-crawler-nfs-<timestamp> -n noctipede
```

### **Check CronJob Status:**
```bash
kubectl get cronjobs -n noctipede
kubectl describe cronjob noctipede-crawler-nfs -n noctipede
```

All changes are now permanent and deployable via standard workflow! 🎯
