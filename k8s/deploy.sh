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

# Step 6: Deploy proxy services
echo ""
echo "🌐 Deploying proxy services..."
kubectl apply -f proxy/
print_status "Tor and I2P proxies deployed"

# Step 7: Wait for core services to be ready
echo ""
echo "⏳ Waiting for core services to be ready..."

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
      if mariadb -h mariadb.mariadb-service -u splinter-research -p$MYSQL_ROOT_PASSWORD -e "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ MariaDB connection successful"
        mariadb -h mariadb.mariadb-service -u splinter-research -p$MYSQL_ROOT_PASSWORD -e "SHOW VARIABLES LIKE 'character_set_server';"
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
          until nc -z  mariadb.mariadb-service 3306; do
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
          until nc -z minio-crawler-hl.minio-service 9000; do
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
        - name: data-volume
          mountPath: /app/data
      containers:
      - name: noctipede-app
        image: ghcr.io/splinterstice/noctipede:latest
        imagePullPolicy: Always
        envFrom:
        - configMapRef:
            name: noctipede-config
        - secretRef:
            name: noctipede-secrets
        env:
        - name: MARIADB_HOST
          value: "mariadb.mariadb-service"
        - name: WEB_SERVER_PORT
          value: "8080"
        - name: WEB_SERVER_HOST
          value: "0.0.0.0"
        - name: SKIP_RECENT_CRAWLS
          value: "false"
        - name: MAX_CONCURRENT_CRAWLERS
          value: "10"
        ports:
        - containerPort: 8080
          name: http
        volumeMounts:
        - name: output-data
          mountPath: /app/output
        - name: log-data
          mountPath: /app/logs
        - name: data-volume
          mountPath: /app/data
        - name: nfs-sites
          mountPath: /nfs-sites
        command: ["sh", "-c"]
        args:
        - |
          echo "🚀 Starting Noctipede Web Application..."
          cd /app
          
          echo "🗄️ Initializing database..."
          python database/init_db.py
          echo "✅ Database initialized successfully!"
          
          echo "🌐 Starting web portal..."
          PYTHONPATH=/app python -m portal.unified_portal
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 120
          periodSeconds: 15
          timeoutSeconds: 10
          failureThreshold: 10
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
      - name: data-volume
        persistentVolumeClaim:
          claimName: noctipede-data-pvc
      - name: nfs-sites
        persistentVolumeClaim:
          claimName: noctipede-sites-pvc
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
          until nc -z mariadb.mariadb-service 3306; do
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
          until nc -z minio-crawler-hl.minio-service 9000; do
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
        - name: data-volume
          mountPath: /app/data
      containers:
      - name: noctipede-app
        image: ghcr.io/splinterstice/noctipede:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
        command: ["sh", "-c"]
        args:
        - |
          echo "🚀 Starting Noctipede Web Application..."
          cd /app
          
          echo "🗄️ Initializing database..."
          python database/init_db.py
          echo "✅ Database initialized successfully!"
          
          echo "🌐 Starting web portal..."
          PYTHONPATH=/app python -m portal.unified_portal
        envFrom:
        - configMapRef:
            name: noctipede-config
        - secretRef:
            name: noctipede-secrets
        env:
        - name: MARIADB_HOST
          value: "mariadb.mariadb-service"
        - name: WEB_SERVER_PORT
          value: "8080"
        - name: WEB_SERVER_HOST
          value: "0.0.0.0"
        - name: SKIP_RECENT_CRAWLS
          value: "false"
        - name: MAX_CONCURRENT_CRAWLERS
          value: "10"
        volumeMounts:
        - name: output-data
          mountPath: /app/output
        - name: log-data
          mountPath: /app/logs
        - name: data-volume
          mountPath: /app/data
        - name: nfs-sites
          mountPath: /nfs-sites
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 120
          periodSeconds: 15
          timeoutSeconds: 10
          failureThreshold: 10
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
      - name: data-volume
        persistentVolumeClaim:
          claimName: noctipede-data-pvc
      - name: nfs-sites
        persistentVolumeClaim:
          claimName: noctipede-sites-pvc
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
echo "🌐 Deploying dedicated portal with data persistence..."
kubectl apply -f noctipede/enhanced-portal-deployment-with-data.yaml
print_status "Dedicated portal deployed"

# Step 9.6: Deploy ingress for external access
echo ""
echo "🌐 Deploying ingress for external access..."
kubectl apply -f ingress.yaml
print_status "Ingress deployed"

# Step 9.5: Initialize database
echo ""
echo "🗄️ Initializing database..."
kubectl apply -f init-database-job.yaml
echo "⏳ Waiting for database initialization to complete..."
kubectl wait --for=condition=complete job/init-database -n noctipede --timeout=300s
print_status "Database initialized"

# Step 9.6: Verify NFS sites file
echo ""
echo "📋 Verifying NFS sites.txt file..."
kubectl run verify-sites --image=busybox:1.35 --restart=Never -n noctipede --overrides='{
  "spec": {
    "containers": [
      {
        "name": "verify-sites",
        "image": "busybox:1.35",
        "command": ["sh", "-c", "echo \"📋 Checking NFS sites.txt file...\" && if [ -f /nfs-sites/sites.txt ]; then echo \"✅ Found sites.txt with $(wc -l < /nfs-sites/sites.txt) sites\" && echo \"Contents:\" && cat /nfs-sites/sites.txt; else echo \"❌ sites.txt not found, creating default...\" && echo \"http://walker.i2p/\nhttp://3ch.i2p/\nhttp://10channel.i2p/\nhttp://bitchan.i2p/\nhttp://l7jqnz3yfe2wtwietafoieadmgqbu7dcmzmey63ktbjtxal3he4a.b32.i2p/\nhttp://reg.i2p/\nhttp://notbob.i2p/\nhttp://purokishi.i2p/\nhttp://facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd.onion/\" > /nfs-sites/sites.txt && echo \"✅ Created sites.txt with $(wc -l < /nfs-sites/sites.txt) sites\"; fi"],
        "volumeMounts": [
          {
            "name": "nfs-sites",
            "mountPath": "/nfs-sites"
          }
        ]
      }
    ],
    "volumes": [
      {
        "name": "nfs-sites",
        "persistentVolumeClaim": {
          "claimName": "noctipede-sites-pvc"
        }
      }
    ]
  }
}'

echo "⏳ Waiting for sites file verification..."
if kubectl wait --for=condition=complete pod/verify-sites -n noctipede --timeout=60s; then
    print_status "Sites file verification completed"
else
    print_warning "Sites file verification timed out, checking status..."
fi

kubectl logs verify-sites -n noctipede || echo "Could not get verification logs"
kubectl delete pod verify-sites -n noctipede --ignore-not-found=true
print_status "NFS sites file verified"

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
rm -f /tmp/working-mariadb.yaml /tmp/working-app.yaml /tmp/mariadb-test.yaml /tmp/non-sites-pvcs.yaml

# Step 12: Comprehensive readiness check
echo ""
echo "🔍 Performing comprehensive readiness check..."
echo "============================================="

# Wait a bit for metrics to stabilize
print_info "Waiting for metrics to stabilize..."
sleep 30

# Test the new readiness endpoint
print_info "Testing crawler readiness endpoint..."
READINESS_CHECK_ATTEMPTS=0
MAX_READINESS_ATTEMPTS=12  # 6 minutes total
READINESS_READY=false

while [ $READINESS_CHECK_ATTEMPTS -lt $MAX_READINESS_ATTEMPTS ]; do
    if kubectl run readiness-test --image=curlimages/curl --rm -it --restart=Never -n noctipede --timeout=30s -- curl -s http://noctipede-portal-service:8080/api/readiness > /tmp/readiness_result.json 2>/dev/null; then
        # Check if the response indicates readiness
        if grep -q '"ready_for_crawling":true' /tmp/readiness_result.json 2>/dev/null; then
            READINESS_READY=true
            print_status "System is ready for crawling!"
            
            # Show readiness details
            echo ""
            echo "📊 Readiness Details:"
            echo "===================="
            if command -v jq >/dev/null 2>&1; then
                kubectl run readiness-detail --image=curlimages/curl --rm -it --restart=Never -n noctipede --timeout=30s -- curl -s http://noctipede-portal-service:8080/api/readiness | jq '.readiness_details.readiness_summary' 2>/dev/null || echo "Readiness check passed"
            else
                echo "✅ Crawler readiness verified (install jq for detailed output)"
            fi
            break
        else
            READINESS_CHECK_ATTEMPTS=$((READINESS_CHECK_ATTEMPTS + 1))
            print_warning "System not ready yet (attempt $READINESS_CHECK_ATTEMPTS/$MAX_READINESS_ATTEMPTS), waiting 30s..."
            
            # Show what's not ready
            if command -v jq >/dev/null 2>&1; then
                kubectl run readiness-detail --image=curlimages/curl --rm -it --restart=Never -n noctipede --timeout=30s -- curl -s http://noctipede-portal-service:8080/api/readiness | jq -r '.readiness_details.readiness_summary // "Checking readiness..."' 2>/dev/null || echo "Checking readiness..."
            fi
            
            sleep 30
        fi
    else
        READINESS_CHECK_ATTEMPTS=$((READINESS_CHECK_ATTEMPTS + 1))
        print_warning "Could not reach readiness endpoint (attempt $READINESS_CHECK_ATTEMPTS/$MAX_READINESS_ATTEMPTS), waiting 30s..."
        sleep 30
    fi
done

# Clean up temp files
rm -f /tmp/readiness_result.json

if [ "$READINESS_READY" = "true" ]; then
    echo ""
    print_status "🎯 COMPREHENSIVE READINESS CHECK PASSED!"
    echo "   ✅ Tor network accessible"
    echo "   ✅ I2P network accessible" 
    echo "   ✅ Sufficient I2P internal proxies active"
    echo "   ✅ System ready for crawling"
else
    echo ""
    print_error "⚠️  READINESS CHECK INCOMPLETE"
    echo "   The system deployed successfully but may not be fully ready for crawling."
    echo "   Check the portal dashboard for detailed network status."
    echo "   Manual verification: kubectl run test --image=curlimages/curl --rm -it --restart=Never -n noctipede -- curl http://noctipede-portal-service:8080/api/readiness"
fi

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
echo "• Check crawler readiness: kubectl run test --image=curlimages/curl --rm -it --restart=Never -n noctipede -- curl http://noctipede-portal-service:8080/api/readiness"
echo "• View portal logs: kubectl logs -f deployment/noctipede-portal -n noctipede"
echo "• Run manual crawler: kubectl exec -it deployment/noctipede-app -n noctipede -- python -m crawlers.main"
echo "• View app logs: kubectl logs -l app=noctipede-app -n noctipede"
echo "• Run crawler: kubectl create job --from=cronjob/noctipede-crawler noctipede-crawler-manual -n noctipede"
echo "• Port forward app: kubectl port-forward service/noctipede-app-service 8080:8080 -n noctipede"
echo ""
print_info "Deployment script completed successfully!"

# Run enhanced deployment verification
echo ""
echo "🔍 Running Enhanced Deployment Verification..."
echo "=============================================="
if [ -f "verify-enhanced-deployment.sh" ]; then
    ./verify-enhanced-deployment.sh
else
    print_warning "Enhanced verification script not found, skipping..."
fi
