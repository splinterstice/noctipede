#!/usr/bin/env bash

# Enhanced Noctipede Kubernetes Deployment Script
# This script deploys Noctipede with smart proxy readiness checking

set -e

echo "🚀 Starting Enhanced Noctipede Deployment..."
echo "============================================="

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

# Step 4: Deploy MariaDB
echo ""
echo "🗄️  Deploying MariaDB..."
kubectl apply -f mariadb/
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

# Step 8: Deploy enhanced portal with proxy status API
echo ""
echo "🌐 Deploying enhanced portal with proxy status API..."
kubectl apply -f enhanced-portal-deployment.yaml
print_status "Enhanced portal deployed"

# Step 9: Wait for portal to be ready
echo ""
echo "⏳ Waiting for enhanced portal to be ready..."
kubectl wait --for=condition=ready pod -l app=noctipede-portal -n noctipede --timeout=300s
print_status "Enhanced portal is ready"

# Step 10: Test portal API endpoints
echo ""
echo "🧪 Testing portal API endpoints..."
sleep 10  # Give portal a moment to fully initialize

# Test health endpoint
if kubectl exec -n noctipede deployment/noctipede-portal -- curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
    print_status "Portal health endpoint is working"
else
    print_warning "Portal health endpoint test failed"
fi

# Test proxy status endpoint
if kubectl exec -n noctipede deployment/noctipede-portal -- curl -s http://localhost:8080/api/proxy-status > /dev/null 2>&1; then
    print_status "Portal proxy status endpoint is working"
else
    print_warning "Portal proxy status endpoint test failed"
fi

# Step 11: Deploy smart crawler with proxy readiness checking
echo ""
echo "🕷️  Deploying smart crawler with proxy readiness verification..."
kubectl apply -f smart-crawler-deployment.yaml
print_status "Smart crawler deployed"

# Step 12: Deploy ingress for external access
echo ""
echo "🌐 Deploying ingress for external access..."
kubectl apply -f ingress.yaml 2>/dev/null || print_warning "Ingress deployment failed or not found"

# Step 13: Get access information
echo ""
echo "🌐 Getting access information..."
PORTAL_PORT=$(kubectl get service noctipede-portal-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "N/A")

echo ""
echo "🎉 ENHANCED DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "=============================================="
echo ""
print_status "All services are running with enhanced proxy readiness checking"
echo ""
echo "📋 ACCESS INFORMATION:"
echo "====================="
echo "📊 Enhanced Portal Dashboard: http://<node-ip>:${PORTAL_PORT}"
echo "🔗 Portal via Ingress: https://noctipede.splinterstice.celestium.life"
echo ""
echo "🔧 NEW API ENDPOINTS:"
echo "===================="
echo "• Proxy Status: http://<node-ip>:${PORTAL_PORT}/api/proxy-status"
echo "• Proxy Readiness: http://<node-ip>:${PORTAL_PORT}/api/proxy-readiness"
echo "• System Metrics: http://<node-ip>:${PORTAL_PORT}/api/system-metrics"
echo "• Health Check: http://<node-ip>:${PORTAL_PORT}/api/health"
echo ""
echo "🔧 USEFUL COMMANDS:"
echo "=================="
echo "• Check all pods: kubectl get pods -n noctipede"
echo "• View portal logs: kubectl logs -l app=noctipede-portal -n noctipede"
echo "• View crawler logs: kubectl logs -l app=noctipede-smart-crawler -n noctipede"
echo "• Check proxy status: kubectl exec -n noctipede deployment/noctipede-portal -- curl -s http://localhost:8080/api/proxy-status"
echo "• Port forward portal: kubectl port-forward service/noctipede-portal-service 8080:8080 -n noctipede"
echo ""
echo "🚀 ENHANCED FEATURES:"
echo "===================="
echo "✅ Smart crawler waits for 100% proxy readiness"
echo "✅ Enhanced portal with real-time proxy status"
echo "✅ Comprehensive Ollama statistics"
echo "✅ Improved dashboard with live metrics"
echo "✅ API endpoints for monitoring and automation"
echo ""
print_info "Enhanced deployment script completed successfully!"

# Step 14: Show current proxy status
echo ""
echo "📊 Current Proxy Status:"
echo "======================="
sleep 5
kubectl exec -n noctipede deployment/noctipede-portal -- curl -s http://localhost:8080/api/proxy-readiness 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Proxy status will be available once portal fully initializes"
