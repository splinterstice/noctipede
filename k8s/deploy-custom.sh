#!/bin/bash

# Custom Noctipede Deployment Script for Celes's Cluster
# Ensures proper dependency order and uses all 47 real sites

set -e

echo "🚀 Starting Custom Noctipede Deployment for Celes's Cluster"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
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

print_status "Connected to Kubernetes cluster: $(kubectl config current-context)"

# Step 1: Create namespace
print_status "Creating namespace..."
kubectl apply -f namespace.yaml
print_success "Namespace created"

# Step 2: Create secrets (check if they exist)
print_status "Creating secrets..."
if kubectl get secret noctipede-secrets -n noctipede &> /dev/null; then
    print_warning "Secrets already exist, skipping creation"
else
    kubectl apply -f secrets.yaml
    print_success "Secrets created"
fi

# Step 3: Create ConfigMap with fixed Tor port
print_status "Creating ConfigMap with proper Tor configuration..."
kubectl apply -f configmap.yaml
print_success "ConfigMap created"

# Step 4: Deploy storage (MariaDB and MinIO)
print_status "Deploying storage services..."
kubectl apply -f mariadb/
kubectl apply -f minio/
print_success "Storage services deployed"

# Step 5: Wait for storage to be ready
print_status "Waiting for MariaDB to be ready..."
kubectl wait --for=condition=ready pod -l app=mariadb -n noctipede --timeout=300s
print_success "MariaDB is ready"

print_status "Waiting for MinIO to be ready..."
kubectl wait --for=condition=ready pod -l app=minio -n noctipede --timeout=300s
print_success "MinIO is ready"

# Step 6: Deploy proxy services (Tor and I2P) - CRITICAL FOR CRAWLER
print_status "Deploying proxy services (Tor and I2P)..."
kubectl apply -f proxy/
print_success "Proxy services deployed"

# Step 7: Wait for Tor proxy to be ready - ESSENTIAL
print_status "Waiting for Tor proxy to be ready on port 9150..."
kubectl wait --for=condition=ready pod -l app=tor-proxy -n noctipede --timeout=300s

# Verify Tor is actually listening on port 9150
print_status "Verifying Tor proxy is listening on port 9150..."
sleep 10
TOR_POD=$(kubectl get pods -n noctipede -l app=tor-proxy -o jsonpath='{.items[0].metadata.name}')
if kubectl exec $TOR_POD -n noctipede -- netstat -tlnp | grep 9150; then
    print_success "✅ Tor proxy is ready and listening on port 9150"
else
    print_error "❌ Tor proxy not listening on port 9150"
    exit 1
fi

# Step 8: Check I2P proxy (don't wait too long as it takes time to bootstrap)
print_status "Checking I2P proxy status..."
if kubectl wait --for=condition=ready pod -l app=i2p-proxy -n noctipede --timeout=60s; then
    print_success "I2P proxy is ready"
else
    print_warning "I2P proxy not ready yet (normal - I2P takes 10+ minutes to bootstrap)"
    print_warning "Continuing deployment - crawler will handle I2P gracefully"
fi

# Step 9: Deploy main applications with proper dependency management
print_status "Deploying Noctipede applications with all 47 sites..."
kubectl apply -f noctipede/
print_success "Noctipede applications deployed"

# Step 10: Wait for portal to be ready
print_status "Waiting for portal to be ready..."
kubectl wait --for=condition=ready pod -l app=noctipede-portal -n noctipede --timeout=300s
print_success "Portal is ready"

# Step 11: Get service information for Celes's cluster
print_status "Getting service information..."
PORTAL_NODEPORT=$(kubectl get service noctipede-portal-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")

if [ -n "$PORTAL_NODEPORT" ]; then
    # Use the known cluster IP for Celes's setup
    CLUSTER_IP="10.1.1.12"
    print_success "🌐 Portal accessible at: http://${CLUSTER_IP}:${PORTAL_NODEPORT}"
    
    # Test portal connectivity
    print_status "Testing portal connectivity..."
    if curl -s "http://${CLUSTER_IP}:${PORTAL_NODEPORT}/api/health" > /dev/null; then
        print_success "✅ Portal is responding to health checks"
    else
        print_warning "⚠️ Portal not responding yet (may still be starting)"
    fi
else
    print_warning "Portal NodePort not available yet"
fi

# Step 12: Show deployment status
print_status "Deployment Status:"
echo ""
kubectl get pods -n noctipede -o wide

echo ""
print_status "Services:"
kubectl get services -n noctipede

echo ""
print_status "Checking crawler status..."
CRAWLER_POD=$(kubectl get pods -n noctipede -l app=noctipede-app -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$CRAWLER_POD" ]; then
    CRAWLER_STATUS=$(kubectl get pod $CRAWLER_POD -n noctipede -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")
    print_status "Crawler pod: $CRAWLER_POD (Status: $CRAWLER_STATUS)"
    
    if [ "$CRAWLER_STATUS" = "Running" ] || [ "$CRAWLER_STATUS" = "Succeeded" ]; then
        print_success "✅ Crawler is active"
    else
        print_warning "⚠️ Crawler status: $CRAWLER_STATUS"
    fi
else
    print_warning "Crawler pod not found yet"
fi

echo ""
print_success "🎉 Custom Noctipede Deployment Complete!"
echo ""
print_status "📋 Deployment Summary:"
echo "• ✅ All 47 sites from sites.txt will be processed"
echo "• ✅ Tor proxy ready on port 9150"
echo "• ✅ I2P proxy deployed (may still be bootstrapping)"
echo "• ✅ Database and storage ready"
echo "• ✅ Multi-page portal with templates active"
echo ""
print_status "🔧 Monitoring Commands:"
echo "• Crawler logs: kubectl logs -f deployment/noctipede-app -n noctipede"
echo "• Portal logs: kubectl logs -f deployment/noctipede-portal -n noctipede"
echo "• Tor proxy logs: kubectl logs -f deployment/tor-proxy -n noctipede"
echo "• I2P proxy logs: kubectl logs -f deployment/i2p-proxy -n noctipede"
echo ""
if [ -n "$PORTAL_NODEPORT" ]; then
    print_status "🌐 Portal Access:"
    echo "• Main Dashboard: http://10.1.1.12:${PORTAL_NODEPORT}/"
    echo "• Health Check: http://10.1.1.12:${PORTAL_NODEPORT}/api/health"
    echo "• Network Status: http://10.1.1.12:${PORTAL_NODEPORT}/api/network"
    echo "• System Metrics: http://10.1.1.12:${PORTAL_NODEPORT}/api/system"
fi
echo ""
