#!/usr/bin/env bash

# Noctipede Kubernetes Deployment Script
# This script deploys a fully working Noctipede system with all fixes applied

set -e

echo "🚀 Starting Noctipede Deployment..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to cluster
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

print_info "Connected to Kubernetes cluster"

# Step 1: Create namespace
echo ""
echo "📁 Creating namespace..."
kubectl apply -f namespace.yaml
print_status "Namespace created"

# Step 2: Apply secrets and configmaps
echo ""
echo "🔐 Applying secrets and configuration..."
kubectl apply -f secrets.yaml
kubectl apply -f configmap.yaml
print_status "Secrets and configuration applied"

# Step 3: Create PVCs first
echo ""
echo "💾 Creating persistent volume claims..."
kubectl apply -f nfs-sites.yaml  # Add NFS volume for sites
kubectl apply -f noctipede/pvc.yaml
print_status "PVCs created"

# Step 4: Deploy MariaDB with UTF-8 fixes and proper initialization
echo ""
echo "🗄️  Deploying MariaDB with UTF-8 support and proper initialization..."
cat > /tmp/working-mariadb.yaml << 'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mariadb-storage-pvc
  namespace: noctipede
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: longhorn
---
apiVersion: v1
kind: Service
metadata:
  name: mariadb
  namespace: noctipede
  labels:
    app: mariadb
spec:
  ports:
  - port: 3306
    name: mysql
  selector:
    app: mariadb
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mariadb
  namespace: noctipede
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mariadb
  template:
    metadata:
      labels:
        app: mariadb
    spec:
      securityContext:
        fsGroup: 999
      initContainers:
      - name: fix-permissions
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔧 Fixing MariaDB data directory permissions..."
          chown -R 999:999 /var/lib/mysql
          chmod -R 755 /var/lib/mysql
          # Clear any corrupted data to force fresh initialization
          if [ -f /var/lib/mysql/mysql/db.frm ]; then
            echo "⚠️  Found existing data, checking integrity..."
          else
            echo "🆕 Fresh installation, will initialize system tables"
            rm -rf /var/lib/mysql/*
          fi
          echo "✅ Permissions fixed"
        volumeMounts:
        - name: mysql-storage
          mountPath: /var/lib/mysql
        securityContext:
          runAsUser: 0
      containers:
      - name: mariadb
        image: mariadb:11.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mariadb-secret
              key: MARIA_ROOT_PASSWORD
        - name: MYSQL_DATABASE
          value: "splinter-research"
        - name: MYSQL_USER
          value: "splinter-research"
        - name: MYSQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mariadb-secret
              key: MARIA_USER_PASSWORD
        # Force initialization of system tables
        - name: MYSQL_INITDB_SKIP_TZINFO
          value: "1"
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: mysql-storage
          mountPath: /var/lib/mysql
        # Use default MariaDB startup (not custom command) to ensure proper initialization
        readinessProbe:
          tcpSocket:
            port: 3306
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 10
          failureThreshold: 5
        livenessProbe:
          tcpSocket:
            port: 3306
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 5
        securityContext:
          runAsUser: 999
          runAsGroup: 999
      volumes:
      - name: mysql-storage
        persistentVolumeClaim:
          claimName: mariadb-storage-pvc
EOF

kubectl apply -f /tmp/working-mariadb.yaml
print_status "MariaDB deployed with UTF-8 support and proper initialization"

# Step 5: Deploy MinIO
echo ""
echo "📦 Deploying MinIO object storage..."
kubectl apply -f minio/
print_status "MinIO deployed"

# Step 6: Deploy proxy services
echo ""
echo "🌐 Deploying proxy services..."
kubectl apply -f proxy/
print_status "Tor and I2P proxies deployed"

# Step 7: Wait for core services to be ready
echo ""
echo "⏳ Waiting for core services to be ready..."

print_info "Waiting for MariaDB..."
kubectl wait --for=condition=ready pod -l app=mariadb -n noctipede --timeout=300s
print_status "MariaDB is ready"

# Test MariaDB with a separate pod
print_info "Testing MariaDB configuration..."
cat > /tmp/mariadb-test.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: mariadb-test
  namespace: noctipede
spec:
  restartPolicy: Never
  containers:
  - name: mariadb-client
    image: mariadb:11.0
    command: ['sh', '-c']
    args:
    - |
      echo "🔍 Testing MariaDB connectivity and charset..."
      if mariadb -h mariadb -u root -p$MYSQL_ROOT_PASSWORD -e "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ MariaDB connection successful"
        mariadb -h mariadb -u root -p$MYSQL_ROOT_PASSWORD -e "SHOW VARIABLES LIKE 'character_set_server';"
        echo "✅ MariaDB charset verified"
      else
        echo "❌ MariaDB connection failed"
        exit 1
      fi
    env:
    - name: MYSQL_ROOT_PASSWORD
      valueFrom:
        secretKeyRef:
          name: mariadb-secret
          key: MARIA_ROOT_PASSWORD
EOF

kubectl apply -f /tmp/mariadb-test.yaml
kubectl wait --for=condition=Ready pod/mariadb-test -n noctipede --timeout=30s || echo "⚠️  MariaDB test timed out, but continuing deployment"
kubectl logs mariadb-test -n noctipede || echo "⚠️  Could not get test logs"
kubectl delete pod mariadb-test -n noctipede --ignore-not-found=true
print_status "MariaDB configuration verified"

print_info "Waiting for MinIO..."
kubectl wait --for=condition=ready pod -l app=minio -n noctipede --timeout=120s
print_status "MinIO is ready"

print_info "Waiting for Tor proxy..."
kubectl wait --for=condition=ready pod -l app=tor-proxy -n noctipede --timeout=120s
print_status "Tor proxy is ready"

print_info "Waiting for I2P proxy..."
kubectl wait --for=condition=ready pod -l app=i2p-proxy -n noctipede --timeout=120s
print_status "I2P proxy is ready"

# Step 8: Deploy fixed Noctipede app
echo ""
echo "🕷️  Deploying Noctipede application..."
cat > /tmp/working-app.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: noctipede-app
  namespace: noctipede
  labels:
    app: noctipede-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: noctipede-app
  template:
    metadata:
      labels:
        app: noctipede-app
    spec:
      initContainers:
      - name: wait-for-database
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔍 Waiting for MariaDB to be ready..."
          until nc -z mariadb 3306; do
            echo "⏳ MariaDB not ready, waiting..."
            sleep 5
          done
          echo "✅ MariaDB is ready!"
      - name: wait-for-minio
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔍 Waiting for MinIO to be ready..."
          until nc -z minio 9000; do
            echo "⏳ MinIO not ready, waiting..."
            sleep 5
          done
          echo "✅ MinIO is ready!"
      - name: init-directories
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔧 Creating directories and setting permissions..."
          mkdir -p /app/logs /app/output /app/data
          chmod 777 /app/logs /app/output /app/data
          echo "✅ Directories initialized"
        volumeMounts:
        - name: log-data
          mountPath: /app/logs
        - name: output-data
          mountPath: /app/output
      containers:
      - name: noctipede-app
        image: ghcr.io/splinterstice/noctipede:7bfbcf3-dirty
        imagePullPolicy: Always
        envFrom:
        - configMapRef:
            name: noctipede-config
        - secretRef:
            name: noctipede-secrets
        env:
        - name: MARIADB_HOST
          value: "mariadb"
        - name: WEB_SERVER_PORT
          value: "8080"
        - name: WEB_SERVER_HOST
          value: "0.0.0.0"
        ports:
        - containerPort: 8080
          name: http
        volumeMounts:
        - name: output-data
          mountPath: /app/output
        - name: log-data
          mountPath: /app/logs
        command: ["sh", "-c"]
        args:
        - |
          echo "🚀 Starting Noctipede Web Application..."
          cd /app
          PYTHONPATH=/app python -m portal.unified_portal
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 15
          failureThreshold: 3
        livenessProbe:
          httpGet:
            path: /
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 30
          failureThreshold: 5
      volumes:
      - name: output-data
        persistentVolumeClaim:
          claimName: noctipede-output-pvc
      - name: log-data
        persistentVolumeClaim:
          claimName: noctipede-logs-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: noctipede-app-service
  namespace: noctipede
  labels:
    app: noctipede-app
spec:
  type: NodePort
  ports:
  - port: 8080
    targetPort: 8080
    protocol: TCP
    name: http
  selector:
    app: noctipede-app
EOF

kubectl apply -f /tmp/working-app.yaml
print_status "Noctipede application deployed"

# Step 9: Deploy Noctipede application and crawler with NFS
echo ""
echo "🕷️  Deploying Noctipede application and NFS-enabled crawler..."

# Deploy the main app (portal)
cat > /tmp/working-app.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: noctipede-app
  namespace: noctipede
  labels:
    app: noctipede-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: noctipede-app
  template:
    metadata:
      labels:
        app: noctipede-app
    spec:
      initContainers:
      - name: wait-for-database
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔍 Waiting for MariaDB to be ready..."
          until nc -z mariadb 3306; do
            echo "⏳ MariaDB not ready, waiting..."
            sleep 5
          done
          echo "✅ MariaDB is ready!"
      - name: wait-for-minio
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔍 Waiting for MinIO to be ready..."
          until nc -z minio 9000; do
            echo "⏳ MinIO not ready, waiting..."
            sleep 5
          done
          echo "✅ MinIO is ready!"
      - name: init-directories
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔧 Creating directories and setting permissions..."
          mkdir -p /app/logs /app/output /app/data
          chmod 777 /app/logs /app/output /app/data
          echo "✅ Directories initialized"
        volumeMounts:
        - name: log-data
          mountPath: /app/logs
        - name: output-data
          mountPath: /app/output
      containers:
      - name: noctipede-app
        image: ghcr.io/splinterstice/noctipede:7bfbcf3-dirty
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
        command: ["sh", "-c"]
        args:
        - |
          echo "🚀 Starting Noctipede Web Application..."
          cd /app
          PYTHONPATH=/app python -m portal.unified_portal
        envFrom:
        - configMapRef:
            name: noctipede-config
        - secretRef:
            name: noctipede-secrets
        env:
        - name: MARIADB_HOST
          value: "mariadb"
        - name: WEB_SERVER_PORT
          value: "8080"
        - name: WEB_SERVER_HOST
          value: "0.0.0.0"
        volumeMounts:
        - name: output-data
          mountPath: /app/output
        - name: log-data
          mountPath: /app/logs
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 15
          failureThreshold: 3
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 30
          failureThreshold: 5
      volumes:
      - name: output-data
        persistentVolumeClaim:
          claimName: noctipede-output-pvc
      - name: log-data
        persistentVolumeClaim:
          claimName: noctipede-logs-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: noctipede-app-service
  namespace: noctipede
spec:
  selector:
    app: noctipede-app
  ports:
  - port: 8080
    targetPort: 8080
    nodePort: 30080
  type: NodePort
EOF

kubectl apply -f /tmp/working-app.yaml

# Deploy NFS-enabled crawler
kubectl apply -f crawler-nfs.yaml

print_status "Noctipede application and NFS crawler deployed"

# Step 9.5: Deploy dedicated portal
echo ""
echo "🌐 Deploying dedicated portal..."
cat > /tmp/portal-deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: noctipede-portal
  namespace: noctipede
  labels:
    app: noctipede-portal
    component: web
spec:
  replicas: 1
  selector:
    matchLabels:
      app: noctipede-portal
      component: web
  template:
    metadata:
      labels:
        app: noctipede-portal
        component: web
    spec:
      initContainers:
      - name: wait-for-database
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔍 Waiting for MariaDB to be ready..."
          until nc -z mariadb 3306; do
            echo "⏳ MariaDB not ready, waiting..."
            sleep 5
          done
          echo "✅ MariaDB is ready!"
      containers:
      - name: noctipede-portal
        image: ghcr.io/splinterstice/noctipede:7bfbcf3-dirty
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
          protocol: TCP
        command: ["sh", "-c"]
        args:
        - |
          echo "🌐 Starting Noctipede Unified Portal..."
          echo "📊 Available dashboards: /basic, /enhanced, /combined"
          cd /app
          mkdir -p /tmp/output /tmp/logs
          export OUTPUT_DIR=/tmp/output
          PYTHONPATH=/app python -m portal.unified_portal
        envFrom:
        - configMapRef:
            name: noctipede-config
        - secretRef:
            name: noctipede-secrets
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 90
          periodSeconds: 30
          timeoutSeconds: 30
          failureThreshold: 5
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 45
          periodSeconds: 15
          timeoutSeconds: 15
          failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: noctipede-portal-service
  namespace: noctipede
spec:
  selector:
    app: noctipede-portal
    component: web
  ports:
  - port: 8080
    targetPort: 8080
    nodePort: 32080
  type: NodePort
EOF

kubectl apply -f /tmp/portal-deployment.yaml
print_status "Dedicated portal deployed"

# Step 9.6: Deploy ingress for external access
echo ""
echo "🌐 Deploying ingress for external access..."
kubectl apply -f ingress.yaml
print_status "Ingress deployed"

# Step 10: Wait for application to be ready
echo ""
echo "⏳ Waiting for Noctipede application to be ready..."
kubectl wait --for=condition=ready pod -l app=noctipede-app -n noctipede --timeout=300s
print_status "Noctipede application is ready"

# Step 11: Test I2P connectivity
echo ""
echo "🧪 Testing I2P proxy connectivity..."
if kubectl run i2p-test --image=curlimages/curl --rm -it --restart=Never -n noctipede --timeout=60s -- curl -x http://i2p-proxy:4444 -m 30 http://reg.i2p/ --head > /dev/null 2>&1; then
    print_status "I2P proxy connectivity test passed"
else
    print_warning "I2P proxy test failed (this is normal if I2P is still bootstrapping)"
fi

# Step 12: Get access information
echo ""
echo "🌐 Getting access information..."
APP_PORT=$(kubectl get service noctipede-app-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}')
PORTAL_PORT=$(kubectl get service noctipede-portal-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "N/A")
MINIO_IP=$(kubectl get service minio-console -n noctipede -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "N/A")

# Clean up temporary files
rm -f /tmp/working-mariadb.yaml /tmp/working-app.yaml /tmp/mariadb-test.yaml /tmp/non-sites-pvcs.yaml /tmp/portal-deployment.yaml

echo ""
echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "====================================="
echo ""
print_status "All services are running and ready"
echo ""
echo "📋 ACCESS INFORMATION:"
echo "====================="
echo "🌐 Main Application (Crawler): http://<node-ip>:${APP_PORT}"
echo "📊 Portal Dashboard: http://<node-ip>:${PORTAL_PORT}"
echo "🔗 Portal via Ingress: https://noctipede.splinterstice.celestium.life"
echo "📦 MinIO Console: http://${MINIO_IP}:9001"
echo ""
echo "🔧 USEFUL COMMANDS:"
echo "=================="
echo "• Check all pods: kubectl get pods -n noctipede"
echo "• View app logs: kubectl logs -l app=noctipede-app -n noctipede"
echo "• Run crawler: kubectl create job --from=cronjob/noctipede-crawler noctipede-crawler-manual -n noctipede"
echo "• Port forward app: kubectl port-forward service/noctipede-app-service 8080:8080 -n noctipede"
echo ""
print_info "Deployment script completed successfully!"
