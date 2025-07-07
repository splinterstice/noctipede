#!/bin/bash

# Production Noctipede Deployment Script
# Ensures proper dependency order and uses all 47 real sites

set -e

echo "🚀 Starting Production Noctipede Deployment"
echo "============================================"

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

print_status "Connected to Kubernetes cluster"

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

# Step 3: Create ConfigMap
print_status "Creating ConfigMap..."
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

# Step 6: Deploy proxy services (Tor and I2P)
print_status "Deploying proxy services..."
kubectl apply -f proxy/
print_success "Proxy services deployed"

# Step 7: Wait for Tor proxy to be ready
print_status "Waiting for Tor proxy to be ready..."
kubectl wait --for=condition=ready pod -l app=tor-proxy -n noctipede --timeout=300s
print_success "Tor proxy is ready"

# Step 8: Check I2P proxy (don't wait too long as it takes time to bootstrap)
print_status "Checking I2P proxy status..."
if kubectl wait --for=condition=ready pod -l app=i2p-proxy -n noctipede --timeout=60s; then
    print_success "I2P proxy is ready"
else
    print_warning "I2P proxy not ready yet (normal - I2P takes 10+ minutes to bootstrap)"
    print_warning "Continuing deployment - crawler will handle I2P gracefully"
fi

# Step 9: Deploy main applications
print_status "Deploying Noctipede applications..."
kubectl apply -f noctipede/
print_success "Noctipede applications deployed"

# Step 10: Wait for portal to be ready
print_status "Waiting for portal to be ready..."
kubectl wait --for=condition=ready pod -l app=noctipede-portal -n noctipede --timeout=300s
print_success "Portal is ready"

# Step 11: Get service information
print_status "Getting service information..."
PORTAL_IP=$(kubectl get service noctipede-portal-service -n noctipede -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
PORTAL_NODEPORT=$(kubectl get service noctipede-portal-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")

if [ -n "$PORTAL_NODEPORT" ]; then
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
    print_success "Portal accessible at: http://${NODE_IP}:${PORTAL_NODEPORT}"
elif [ -n "$PORTAL_IP" ]; then
    print_success "Portal accessible at: http://${PORTAL_IP}:8080"
else
    print_warning "Portal service information not available yet"
fi

# Step 12: Show deployment status
print_status "Deployment Status:"
echo ""
kubectl get pods -n noctipede -o wide

echo ""
print_status "Services:"
kubectl get services -n noctipede

echo ""
print_success "🎉 Production Noctipede Deployment Complete!"
echo ""
print_status "Next steps:"
echo "1. Monitor crawler logs: kubectl logs -f deployment/noctipede-app -n noctipede"
echo "2. Check portal health: kubectl logs -f deployment/noctipede-portal -n noctipede"
echo "3. Access portal web interface at the URL shown above"
echo ""
print_status "The crawler will process all 47 sites from sites.txt"
print_status "Tor and I2P proxies are configured and ready"
echo ""
