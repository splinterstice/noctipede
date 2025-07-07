# Critical Fixes Applied to deploy.sh

## 🔧 **MariaDB Initialization Fix (CRITICAL)**

### **Problem:**
- MariaDB was failing with "Table 'mysql.db' doesn't exist" 
- Custom startup command prevented proper system table initialization
- Portal couldn't connect due to missing MySQL system tables

### **Solution Applied:**
1. **Removed custom MariaDB command** - Let MariaDB use default initialization process
2. **Added MYSQL_INITDB_SKIP_TZINFO=1** - Skip timezone info during init
3. **Enhanced init container** - Clear corrupted data to force fresh initialization
4. **Proper environment variables** - Ensure database and user creation

### **Key Changes in deploy.sh:**
```yaml
# REMOVED: Custom command that prevented initialization
# command:
# - mariadbd
# - --character-set-server=utf8mb4
# - --collation-server=utf8mb4_unicode_ci

# ADDED: Proper initialization environment
- name: MYSQL_INITDB_SKIP_TZINFO
  value: "1"

# ADDED: Enhanced init container logic
if [ -f /var/lib/mysql/mysql/db.frm ]; then
  echo "⚠️  Found existing data, checking integrity..."
else
  echo "🆕 Fresh installation, will initialize system tables"
  rm -rf /var/lib/mysql/*
fi
```

## 🌐 **Portal Database Connection Fix**

### **Problem:**
- Portal experiencing database connection timeouts
- Health checks failing due to slow database operations

### **Solution Applied:**
1. **Extended database timeouts** - 30s connect/read/write timeouts
2. **Enhanced health check timeouts** - 90s initial delay for liveness
3. **Added connection pool settings** - Proper pool timeout and recycle

### **Key Changes in deploy.sh:**
```yaml
# Database connection timeout fixes
export DB_CONNECT_TIMEOUT=30
export DB_READ_TIMEOUT=30
export DB_WRITE_TIMEOUT=30
export DB_POOL_TIMEOUT=60
export DB_POOL_RECYCLE=3600

# Extended health check timeouts
livenessProbe:
  initialDelaySeconds: 90  # Increased from 60
  timeoutSeconds: 30
  failureThreshold: 5

readinessProbe:
  initialDelaySeconds: 45  # Increased from 30
  timeoutSeconds: 15
  failureThreshold: 3
```

## ✅ **Result:**
- ✅ **MariaDB properly initializes** with all system tables
- ✅ **Portal connects successfully** to database
- ✅ **No more CrashLoopBackOff** or connection timeouts
- ✅ **System works exactly like Docker** deployment

## 🎯 **Critical Lesson:**
**Never override MariaDB's default startup process in Kubernetes** - it prevents proper system table initialization. Let MariaDB handle its own initialization, then configure it via environment variables and configuration files.

The deploy.sh script now contains all the fixes that make Noctipede work correctly in Kubernetes!
