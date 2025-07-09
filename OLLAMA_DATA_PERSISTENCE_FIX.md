# Ollama Data Persistence Fix

## 🚨 **Issue Identified:**

The Ollama usage stats were being reset on container restarts because:
1. **No Persistent Volume**: `/app/data` directory was not mounted to persistent storage
2. **Ephemeral Storage**: Data stored in container filesystem was lost on restart
3. **Missing PVC**: No PersistentVolumeClaim defined for application data

## ✅ **Permanent Fixes Applied:**

### **1. Added Data PVC**
**File**: `k8s/noctipede/pvc.yaml`
```yaml
# Added new PVC for application data
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: noctipede-data-pvc
  namespace: noctipede
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 2Gi
  storageClassName: longhorn
```

### **2. Created Enhanced Portal Deployment**
**File**: `k8s/noctipede/enhanced-portal-deployment-with-data.yaml`
- **Added data volume mount**: `/app/data` → `noctipede-data-pvc`
- **Init container support**: Creates and sets permissions for `/app/data`
- **Persistent storage**: Ollama stats survive container restarts

### **3. Updated Deploy Script**
**File**: `k8s/deploy.sh`
- **Replaced inline portal deployment** with external YAML file
- **Uses enhanced deployment** with data persistence
- **Cleaner deployment process** with proper volume management

## 📊 **Before vs After:**

### **Before (Data Loss Issue):**
```
Container Filesystem:
├── /app/data/ollama_usage_stats.json ❌ (lost on restart)
├── /app/logs/ ✅ (persistent via noctipede-logs-pvc)
└── /app/output/ ✅ (persistent via noctipede-output-pvc)
```

### **After (Data Persistence Fixed):**
```
Persistent Volumes:
├── /app/data/ ✅ (persistent via noctipede-data-pvc)
├── /app/logs/ ✅ (persistent via noctipede-logs-pvc)
└── /app/output/ ✅ (persistent via noctipede-output-pvc)
```

## 🔧 **Technical Details:**

### **Volume Mount Configuration:**
```yaml
volumeMounts:
- name: data-storage
  mountPath: /app/data
- name: log-data
  mountPath: /app/logs
- name: output-data
  mountPath: /app/output

volumes:
- name: data-storage
  persistentVolumeClaim:
    claimName: noctipede-data-pvc
```

### **Ollama Stats File Location:**
- **Path**: `/app/data/ollama_usage_stats.json`
- **Storage**: Persistent volume (survives restarts)
- **Access**: ReadWriteMany (shared across pods)

## 🚀 **Deployment Ready:**

All changes are permanent and deployable via:

```bash
make ghcr-deploy  # Build latest image
cd k8s
./destroy.sh      # Clean slate
./deploy.sh       # Deploy with data persistence
```

## 📋 **Expected Results:**

### **Ollama Counter Behavior:**
- **✅ Persistent**: Counters survive container restarts
- **✅ Accurate**: No more counter resets
- **✅ Reliable**: Data stored on persistent volume
- **✅ Shared**: Multiple pods can access same stats file

### **Portal Metrics:**
- **✅ Consistent**: Ollama usage metrics remain accurate
- **✅ Historical**: Usage data preserved across deployments
- **✅ Reliable**: No more "counters reset" issues

## 🧪 **Verification Commands:**

### **Check Data Volume:**
```bash
kubectl get pvc noctipede-data-pvc -n noctipede
kubectl describe pvc noctipede-data-pvc -n noctipede
```

### **Verify Mount Points:**
```bash
kubectl exec -it deployment/noctipede-portal -n noctipede -- df -h /app/data
kubectl exec -it deployment/noctipede-portal -n noctipede -- ls -la /app/data/
```

### **Test Persistence:**
```bash
# Create test file
kubectl exec -it deployment/noctipede-portal -n noctipede -- touch /app/data/test-persistence.txt

# Restart pod
kubectl rollout restart deployment/noctipede-portal -n noctipede

# Check if file persists
kubectl exec -it deployment/noctipede-portal -n noctipede -- ls -la /app/data/test-persistence.txt
```

## 🎯 **Summary:**

The Ollama data persistence issue is now **completely resolved**:

1. **✅ Added noctipede-data-pvc** for persistent application data
2. **✅ Enhanced portal deployment** with data volume mount
3. **✅ Updated deploy.sh** to use enhanced deployment
4. **✅ All changes permanent** and deployable via standard workflow

Ollama usage stats will now persist across container restarts! 🎉
