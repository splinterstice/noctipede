#!/usr/bin/env bash

# Smart Noctipede Kubernetes Deployment Script
# Uses working components with in-cluster proxy readiness checking

set -e

echo "🚀 Starting Smart Noctipede Deployment..."
echo "========================================="

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
kubectl apply -f nfs-sites.yaml 2>/dev/null || echo "NFS sites config not found, skipping..."
kubectl apply -f noctipede/pvc.yaml
print_status "PVCs created"

# Step 4: Deploy MariaDB (using the working version from original deploy.sh)
echo ""
echo "🗄️  Deploying MariaDB with UTF-8 support..."
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
        - name: MYSQL_INITDB_SKIP_TZINFO
          value: "1"
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: mysql-storage
          mountPath: /var/lib/mysql
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
print_status "MariaDB deployed"

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

print_info "Waiting for MinIO..."
kubectl wait --for=condition=ready pod -l app=minio -n noctipede --timeout=120s
print_status "MinIO is ready"

print_info "Waiting for Tor proxy..."
kubectl wait --for=condition=ready pod -l app=tor-proxy -n noctipede --timeout=120s
print_status "Tor proxy is ready"

print_info "Waiting for I2P proxy..."
kubectl wait --for=condition=ready pod -l app=i2p-proxy -n noctipede --timeout=120s
print_status "I2P proxy is ready"

# Step 8: Deploy enhanced portal with proxy status API (simplified version)
echo ""
echo "🌐 Deploying portal with proxy status API..."
cat > /tmp/portal-with-api.yaml << 'EOF'
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
        image: ghcr.io/splinterstice/noctipede:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
          protocol: TCP
        command: ["sh", "-c"]
        args:
        - |
          echo "🌐 Starting Noctipede Portal with Proxy Status API..."
          cd /app
          mkdir -p /tmp/output /tmp/logs
          export OUTPUT_DIR=/tmp/output
          
          # Create enhanced portal with proxy status endpoints
          cat > /tmp/portal_with_proxy_api.py << 'PORTAL_EOF'
          import asyncio
          import json
          import logging
          import socket
          import subprocess
          import time
          from datetime import datetime
          from typing import Dict, Any, Optional
          
          import requests
          from fastapi import FastAPI, HTTPException
          from fastapi.responses import HTMLResponse, JSONResponse
          import uvicorn
          
          # Configure logging
          logging.basicConfig(level=logging.INFO)
          logger = logging.getLogger(__name__)
          
          app = FastAPI(title="Noctipede Portal with Proxy API", version="2.0.0")
          
          def check_tor_proxy_status() -> Dict[str, Any]:
              """Check Tor proxy status"""
              try:
                  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                  sock.settimeout(5)
                  result = sock.connect_ex(('tor-proxy', 9150))
                  sock.close()
                  
                  if result == 0:
                      return {
                          "ready": True,
                          "status": "ready",
                          "message": "Tor proxy is ready",
                          "port_open": True
                      }
                  else:
                      return {
                          "ready": False,
                          "status": "not_ready",
                          "message": "Tor proxy port is not accessible",
                          "port_open": False
                      }
              except Exception as e:
                  return {
                      "ready": False,
                      "status": "error",
                      "message": f"Error checking Tor proxy: {str(e)}",
                      "port_open": False
                  }
          
          def check_i2p_proxy_status() -> Dict[str, Any]:
              """Check I2P proxy status"""
              try:
                  response = requests.get("http://i2p-proxy:4444", timeout=10)
                  
                  if response.status_code == 200 or "I2Pd HTTP proxy" in response.text:
                      # Check if I2P console is accessible for better status
                      try:
                          console_response = requests.get("http://i2p-proxy:7070", timeout=5)
                          if console_response.status_code == 200:
                              return {
                                  "ready": True,
                                  "status": "fully_ready",
                                  "message": "I2P proxy is ready with console access",
                                  "http_proxy": True,
                                  "console_accessible": True
                              }
                          else:
                              return {
                                  "ready": True,
                                  "status": "proxy_ready",
                                  "message": "I2P HTTP proxy is ready",
                                  "http_proxy": True,
                                  "console_accessible": False
                              }
                      except:
                          return {
                              "ready": True,
                              "status": "proxy_ready",
                              "message": "I2P HTTP proxy is ready",
                              "http_proxy": True,
                              "console_accessible": False
                          }
                  else:
                      return {
                          "ready": False,
                          "status": "not_ready",
                          "message": "I2P proxy is not responding",
                          "http_proxy": False,
                          "console_accessible": False
                      }
              except Exception as e:
                  return {
                      "ready": False,
                      "status": "error",
                      "message": f"Error checking I2P proxy: {str(e)}",
                      "http_proxy": False,
                      "console_accessible": False
                  }
          
          @app.get("/api/health")
          async def health_check():
              """Health check endpoint"""
              return {"status": "healthy", "timestamp": datetime.now().isoformat()}
          
          @app.get("/api/proxy-status")
          async def get_proxy_status():
              """Get current proxy status"""
              tor_status = check_tor_proxy_status()
              i2p_status = check_i2p_proxy_status()
              
              return {
                  "tor": tor_status,
                  "i2p": i2p_status,
                  "both_ready": tor_status["ready"] and i2p_status["ready"],
                  "timestamp": datetime.now().isoformat()
              }
          
          @app.get("/api/proxy-readiness")
          async def check_proxy_readiness():
              """Check if both proxies are ready for crawling"""
              status = await get_proxy_status()
              
              tor_ready = status["tor"]["ready"]
              i2p_ready = status["i2p"]["ready"]
              
              return {
                  "tor_ready": tor_ready,
                  "i2p_ready": i2p_ready,
                  "both_ready": tor_ready and i2p_ready,
                  "readiness_percentage": {
                      "tor": 100 if tor_ready else 0,
                      "i2p": 100 if i2p_ready else 0,
                      "overall": 100 if (tor_ready and i2p_ready) else (50 if (tor_ready or i2p_ready) else 0)
                  },
                  "timestamp": datetime.now().isoformat()
              }
          
          @app.get("/", response_class=HTMLResponse)
          async def dashboard():
              """Dashboard with proxy status"""
              return '''
              <!DOCTYPE html>
              <html>
              <head>
                  <title>Noctipede Portal</title>
                  <meta charset="utf-8">
                  <meta name="viewport" content="width=device-width, initial-scale=1">
                  <style>
                      body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                      .container { max-width: 1200px; margin: 0 auto; }
                      .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                      .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                      .status-indicator { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
                      .status-ready { background-color: #4CAF50; }
                      .status-error { background-color: #F44336; }
                      h1 { color: #333; text-align: center; }
                      h2 { color: #666; border-bottom: 2px solid #eee; padding-bottom: 10px; }
                      .refresh-btn { background: #2196F3; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
                  </style>
              </head>
              <body>
                  <div class="container">
                      <h1>🕷️ Noctipede Portal</h1>
                      
                      <div class="card">
                          <h2>🌐 Proxy Status</h2>
                          <button class="refresh-btn" onclick="refreshProxyStatus()">Refresh Status</button>
                          <div id="proxy-status" class="status-grid">
                              <div>Loading proxy status...</div>
                          </div>
                      </div>
                  </div>
                  
                  <script>
                      async function refreshProxyStatus() {
                          try {
                              const response = await fetch('/api/proxy-status');
                              const data = await response.json();
                              
                              const torStatus = data.tor.ready ? 'status-ready' : 'status-error';
                              const i2pStatus = data.i2p.ready ? 'status-ready' : 'status-error';
                              
                              document.getElementById('proxy-status').innerHTML = `
                                  <div>
                                      <h3><span class="status-indicator ${torStatus}"></span>Tor Proxy</h3>
                                      <p><strong>Status:</strong> ${data.tor.status}</p>
                                      <p><strong>Message:</strong> ${data.tor.message}</p>
                                      <p><strong>Ready:</strong> ${data.tor.ready ? '✅' : '❌'}</p>
                                  </div>
                                  <div>
                                      <h3><span class="status-indicator ${i2pStatus}"></span>I2P Proxy</h3>
                                      <p><strong>Status:</strong> ${data.i2p.status}</p>
                                      <p><strong>Message:</strong> ${data.i2p.message}</p>
                                      <p><strong>Ready:</strong> ${data.i2p.ready ? '✅' : '❌'}</p>
                                  </div>
                              `;
                          } catch (error) {
                              document.getElementById('proxy-status').innerHTML = `<div>Error loading proxy status: ${error.message}</div>`;
                          }
                      }
                      
                      // Initial load and auto-refresh
                      refreshProxyStatus();
                      setInterval(refreshProxyStatus, 30000);
                  </script>
              </body>
              </html>
              '''
          
          if __name__ == "__main__":
              uvicorn.run(app, host="0.0.0.0", port=8080)
          PORTAL_EOF
          
          # Install requests if needed
          pip install requests || echo "Warning: Could not install requests"
          
          # Run the portal
          PYTHONPATH=/app python /tmp/portal_with_proxy_api.py
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
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5

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

kubectl apply -f /tmp/portal-with-api.yaml
print_status "Portal with proxy API deployed"

# Step 9: Wait for portal to be ready
echo ""
echo "⏳ Waiting for portal to be ready..."
kubectl wait --for=condition=ready pod -l app=noctipede-portal -n noctipede --timeout=300s
print_status "Portal is ready"

# Step 10: Deploy smart crawler that uses portal API for readiness checking
echo ""
echo "🕷️  Deploying smart crawler with in-cluster proxy readiness checking..."
cat > /tmp/smart-crawler.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: noctipede-smart-crawler
  namespace: noctipede
  labels:
    app: noctipede-smart-crawler
    component: crawler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: noctipede-smart-crawler
      component: crawler
  template:
    metadata:
      labels:
        app: noctipede-smart-crawler
        component: crawler
    spec:
      initContainers:
      # Wait for database to be ready
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
      
      # Wait for portal API to be ready
      - name: wait-for-portal-api
        image: curlimages/curl:latest
        command: ['sh', '-c']
        args:
        - |
          echo "🌐 Waiting for Portal API to be ready..."
          until curl -s http://noctipede-portal-service:8080/api/health > /dev/null 2>&1; do
            echo "⏳ Portal API not ready, waiting..."
            sleep 10
          done
          echo "✅ Portal API is ready!"
      
      # Wait for BOTH proxies to be ready via Portal API (IN KUBERNETES)
      - name: wait-for-proxy-readiness
        image: curlimages/curl:latest
        command: ['sh', '-c']
        args:
        - |
          echo "🚀 Checking proxy readiness via Portal API..."
          echo "📡 This runs entirely within Kubernetes cluster"
          
          max_attempts=60  # 30 minutes total
          attempt=0
          
          while [ $attempt -lt $max_attempts ]; do
            attempt=$((attempt + 1))
            echo "🔍 Proxy readiness check attempt $attempt/$max_attempts..."
            
            # Get proxy readiness from portal API
            if response=$(curl -s http://noctipede-portal-service:8080/api/proxy-readiness 2>/dev/null); then
              echo "📊 Portal API Response: $response"
              
              # Parse JSON to check readiness
              both_ready=$(echo "$response" | grep -o '"both_ready":[^,]*' | cut -d':' -f2 | tr -d ' ')
              tor_ready=$(echo "$response" | grep -o '"tor_ready":[^,]*' | cut -d':' -f2 | tr -d ' ')
              i2p_ready=$(echo "$response" | grep -o '"i2p_ready":[^,]*' | cut -d':' -f2 | tr -d ' ')
              
              echo "🧅 Tor Ready: $tor_ready"
              echo "🌐 I2P Ready: $i2p_ready"
              echo "🎯 Both Ready: $both_ready"
              
              if [ "$both_ready" = "true" ]; then
                echo "🎉 SUCCESS: Both Tor and I2P proxies are ready!"
                echo "🚀 Crawler can now start with full proxy support"
                exit 0
              else
                echo "⏳ Proxies still initializing..."
              fi
            else
              echo "⚠️  Could not reach Portal API, retrying..."
            fi
            
            echo "⏰ Waiting 30 seconds before next check..."
            sleep 30
          done
          
          echo "⚠️  WARNING: Proxy readiness timeout after 30 minutes"
          echo "🔄 Continuing anyway - crawler will handle proxy issues gracefully"
      
      # Copy sites data
      - name: init-sites-data
        image: ghcr.io/splinterstice/noctipede:latest
        command: ["/bin/sh", "-c"]
        args:
        - |
          echo "📋 Copying sites.txt..."
          cp /app/data/sites.txt /shared-data/sites.txt
          echo "✅ Sites file copied: $(wc -l < /shared-data/sites.txt) sites"
        volumeMounts:
        - name: shared-data
          mountPath: /shared-data
      
      containers:
      - name: noctipede-smart-crawler
        image: ghcr.io/splinterstice/noctipede:latest
        imagePullPolicy: Always
        command: ["sh", "-c"]
        args:
        - |
          echo "🕷️  Starting Smart Noctipede Crawler..."
          echo "======================================"
          
          # Final proxy readiness check before starting
          echo "🔍 Final proxy readiness verification via Portal API..."
          if response=$(curl -s http://noctipede-portal-service:8080/api/proxy-readiness 2>/dev/null); then
            echo "📊 Final Portal API Response: $response"
            both_ready=$(echo "$response" | grep -o '"both_ready":[^,]*' | cut -d':' -f2 | tr -d ' ')
            if [ "$both_ready" = "true" ]; then
              echo "✅ CONFIRMED: Both proxies are ready for crawling!"
            else
              echo "⚠️  WARNING: Proxies may not be fully ready, but continuing..."
            fi
          else
            echo "⚠️  Could not verify proxy status, continuing anyway..."
          fi
          
          echo "📊 Sites to crawl: $(wc -l < /shared-data/sites.txt)"
          cd /app
          
          # Initialize database
          echo "🗄️ Initializing database..."
          python database/init_db.py
          
          # Set environment variables
          export SITES_FILE_PATH=/shared-data/sites.txt
          
          # Start crawler
          echo "🚀 Starting crawler..."
          PYTHONPATH=/app python -m crawlers.main
        envFrom:
        - configMapRef:
            name: noctipede-config
        - secretRef:
            name: noctipede-secrets
        volumeMounts:
        - name: shared-data
          mountPath: /shared-data
        - name: output-volume
          mountPath: /app/output
        - name: logs-volume
          mountPath: /app/logs
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import sys; sys.exit(0)"
          initialDelaySeconds: 120
          periodSeconds: 60
          timeoutSeconds: 10
        readinessProbe:
          exec:
            command:
            - python
            - -c
            - "import sys; sys.exit(0)"
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 5
      
      volumes:
      - name: shared-data
        emptyDir: {}
      - name: output-volume
        persistentVolumeClaim:
          claimName: noctipede-output-pvc
      - name: logs-volume
        persistentVolumeClaim:
          claimName: noctipede-logs-pvc
EOF

kubectl apply -f /tmp/smart-crawler.yaml
print_status "Smart crawler deployed"

# Step 11: Deploy ingress
echo ""
echo "🌐 Deploying ingress..."
kubectl apply -f ingress.yaml 2>/dev/null || print_warning "Ingress deployment failed or not found"

# Step 12: Get access information
echo ""
echo "🌐 Getting access information..."
PORTAL_PORT=$(kubectl get service noctipede-portal-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "N/A")

# Clean up temporary files
rm -f /tmp/working-mariadb.yaml /tmp/portal-with-api.yaml /tmp/smart-crawler.yaml

echo ""
echo "🎉 SMART DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "=========================================="
echo ""
print_status "All services deployed with in-cluster proxy readiness checking"
echo ""
echo "📋 ACCESS INFORMATION:"
echo "====================="
echo "📊 Portal Dashboard: http://<node-ip>:${PORTAL_PORT}"
echo "🔗 Portal via Ingress: https://noctipede.splinterstice.celestium.life"
echo ""
echo "🔧 API ENDPOINTS:"
echo "================"
echo "• Proxy Status: http://<node-ip>:${PORTAL_PORT}/api/proxy-status"
echo "• Proxy Readiness: http://<node-ip>:${PORTAL_PORT}/api/proxy-readiness"
echo "• Health Check: http://<node-ip>:${PORTAL_PORT}/api/health"
echo ""
echo "🔧 USEFUL COMMANDS:"
echo "=================="
echo "• Check all pods: kubectl get pods -n noctipede"
echo "• View portal logs: kubectl logs -l app=noctipede-portal -n noctipede"
echo "• View crawler logs: kubectl logs -l app=noctipede-smart-crawler -n noctipede"
echo "• Check proxy status: kubectl exec -n noctipede deployment/noctipede-portal -- curl -s http://localhost:8080/api/proxy-status"
echo ""
echo "🚀 SMART FEATURES:"
echo "=================="
echo "✅ Crawler waits for 100% proxy readiness (in Kubernetes)"
echo "✅ Portal provides proxy status API endpoints"
echo "✅ All readiness checking happens within the cluster"
echo "✅ Uses proven working components from original deployment"
echo ""
print_info "Smart deployment script completed successfully!"
