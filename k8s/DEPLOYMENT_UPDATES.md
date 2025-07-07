# Deployment Script Updates

## ✅ **Updated deploy.sh with all fixes applied**

### 🔧 **MariaDB Fixes Applied:**
1. **Permission Fixes** - Added init container to fix directory permissions
2. **Security Context** - Added proper fsGroup and user/group settings
3. **Health Check Timeouts** - Extended timeouts to prevent false failures:
   - `readinessProbe`: 30s initial delay, 10s timeout, 5 failure threshold
   - `livenessProbe`: 60s initial delay, 10s timeout, 5 failure threshold
4. **UTF-8 Character Set** - Proper charset configuration for Unicode support

### 🌐 **Portal Fixes Applied:**
1. **Health Check Improvements** - Extended timeouts for slow startup:
   - `readinessProbe`: 30s initial delay, 15s timeout, 3 failure threshold  
   - `livenessProbe`: 60s initial delay, 30s timeout, 5 failure threshold
2. **Database Connection Timeouts** - Added environment variables:
   - `DB_CONNECT_TIMEOUT=30`
   - `DB_READ_TIMEOUT=30`
3. **Updated Image Tag** - Changed from `tor-fixed` to `latest`

### 🧪 **Testing Improvements:**
1. **MariaDB Test Pod** - Added separate pod for database verification
2. **Proper Cleanup** - Remove test pods after verification
3. **Connection Validation** - Test charset and connectivity

### 📋 **Script Structure:**
1. **Step 3**: Create PVCs first
2. **Step 4**: Deploy MariaDB with all fixes
3. **Step 5**: Deploy MinIO
4. **Step 6**: Deploy proxy services  
5. **Step 7**: Wait for core services + test MariaDB
6. **Step 8**: Deploy Noctipede app with fixes
7. **Step 9**: Deploy portal with fixes + other components
8. **Step 10**: Wait for app readiness
9. **Step 11**: Test I2P connectivity
10. **Step 12**: Get access information

### 🎯 **Key Improvements:**
- ✅ **No more CrashLoopBackOff** - Fixed permission and timeout issues
- ✅ **Single MariaDB instance** - Proper deployment prevents duplicates
- ✅ **Robust health checks** - Realistic timeouts prevent false failures
- ✅ **Database validation** - Separate test pod verifies functionality
- ✅ **Clean deployment** - Proper sequencing and dependency management

The deployment script now includes all the fixes that were manually applied to resolve the MariaDB and Portal issues.
