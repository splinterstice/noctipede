# Crawler Configuration Fixes - July 9, 2025

## Issues Resolved

### 1. **Crawler Init Failure**
- **Problem**: Crawler jobs failing with `Init:CrashLoopBackOff` due to sites.txt not found
- **Root Cause**: Looking for sites.txt in `/app/data/sites.txt` instead of `/nfs-sites/sites.txt`
- **Fix**: Updated crawler-nfs.yaml to use correct NFS mount path

### 2. **Configuration Inconsistencies**
- **Problem**: I2P crawler using `os.getenv()` instead of centralized settings
- **Fix**: Updated I2P crawler to use `self.settings.i2p_proxy_host` etc.

### 3. **Missing Configuration Values**
- **Problem**: `MAX_CRAWL_DEPTH` and `MAX_OFFSITE_DEPTH` missing from configmap
- **Fix**: Added missing values with proper comments

### 4. **Boolean Configuration Clarity**
- **Problem**: Users unclear about boolean environment variable meanings
- **Fix**: Added comprehensive comments explaining each boolean setting

## Files Modified

1. **k8s/crawler-nfs.yaml**
   - Fixed sites.txt path from `/app/data/sites.txt` to `/nfs-sites/sites.txt`
   - Updated init container verification logic
   - Fixed environment variable `SITES_FILE_PATH`

2. **k8s/configmap.yaml**
   - Added missing `MAX_CRAWL_DEPTH: "10"` and `MAX_OFFSITE_DEPTH: "1"`
   - Added comprehensive boolean comments for all settings
   - Documented what each boolean value means

3. **crawlers/i2p.py**
   - Replaced `os.getenv()` calls with `self.settings` usage
   - Consistent configuration management across all crawlers

4. **config/settings.py**
   - Added `use_i2p_internal_proxies: bool` field
   - Enhanced settings validation

## Results

- ✅ Crawler successfully processes **48 sites** (up from 10)
- ✅ All configuration values properly respected from configmap
- ✅ Consistent settings management across all components
- ✅ Clear documentation for boolean configuration values
- ✅ NFS sites.txt integration working perfectly
- ✅ Both manual and scheduled crawler jobs functional

## Testing Verified

- Init containers pass verification
- Sites.txt correctly loaded from NFS mount
- System readiness checks pass
- Crawler manager starts successfully
- All network types (Tor/I2P/Clearnet) accessible
- Configuration changes applied without full rebuild needed

## Deployment Status

- Current deployment: **Fully operational**
- Sites crawled: **48 sites** from NFS mount
- Network status: **Tor: OK, I2P: OK (11/11 proxies active)**
- System readiness: **Ready for crawling**

## Commands for Future Reference

```bash
# Create manual crawler job
kubectl create job --from=cronjob/noctipede-crawler-nfs noctipede-crawler-manual -n noctipede

# Check crawler status
kubectl get pods -n noctipede | grep crawler

# View crawler logs
kubectl logs <crawler-pod-name> -n noctipede -c noctipede-crawler

# Check sites count
kubectl logs <crawler-pod-name> -n noctipede -c verify-sites-file
```
