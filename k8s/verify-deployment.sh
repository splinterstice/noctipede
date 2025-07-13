#!/usr/bin/env bash

# Noctipede Deployment Verification Script
# Verifies that all components are working correctly after deployment

set -e

echo "🔍 Noctipede Deployment Verification"
echo "===================================="

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

echo ""
echo "📋 Checking Pod Status..."
echo "========================="

# Check all pods in noctipede namespace
kubectl get pods -n noctipede -o wide

echo ""
echo "🔍 Verifying Core Services..."
echo "============================="

# Check MariaDB
if kubectl get pod -l app=mariadb -n noctipede | grep -q Running; then
    print_status "MariaDB is running"
else
    print_error "MariaDB is not running"
fi

# Check MinIO
if kubectl get pod -l app=minio -n noctipede | grep -q Running; then
    print_status "MinIO is running"
else
    print_error "MinIO is not running"
fi

# Check Tor Proxy
if kubectl get pod -l app=tor-proxy -n noctipede | grep -q Running; then
    print_status "Tor proxy is running"
else
    print_warning "Tor proxy is not running"
fi

# Check I2P Proxy
if kubectl get pod -l app=i2p-proxy -n noctipede | grep -q Running; then
    print_status "I2P proxy is running"
else
    print_warning "I2P proxy is not running"
fi

# Check Noctipede Portal
if kubectl get pod -l app=noctipede-portal -n noctipede | grep -q Running; then
    print_status "Noctipede portal is running"
else
    print_error "Noctipede portal is not running"
fi

echo ""
echo "🌐 Testing Portal Connectivity..."
echo "================================="

# Get portal service details
PORTAL_PORT=$(kubectl get service noctipede-portal-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "N/A")
print_info "Portal NodePort: ${PORTAL_PORT}"

# Test portal health endpoint via port forward
print_info "Testing portal health endpoint..."
kubectl port-forward service/noctipede-portal-service 8080:8080 -n noctipede &
PF_PID=$!
sleep 5

if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
    print_status "Portal health endpoint is responding"
    
    # Test unified portal dashboards
    print_info "Testing unified portal dashboards..."
    
    if curl -s http://localhost:8080/ | grep -q "Dashboard Selection"; then
        print_status "Dashboard selector is working"
    else
        print_warning "Dashboard selector may have issues"
    fi
    
    if curl -s http://localhost:8080/basic | grep -q "Basic Dashboard"; then
        print_status "Basic dashboard is accessible"
    else
        print_warning "Basic dashboard may have issues"
    fi
    
    if curl -s http://localhost:8080/enhanced | grep -q "Enhanced"; then
        print_status "Enhanced dashboard is accessible"
    else
        print_warning "Enhanced dashboard may have issues"
    fi
    
    if curl -s http://localhost:8080/combined | grep -q "Combined"; then
        print_status "Combined dashboard is accessible"
    else
        print_warning "Combined dashboard may have issues"
    fi
    
    # Test API endpoints
    print_info "Testing API endpoints..."
    
    if curl -s http://localhost:8080/api/metrics > /dev/null 2>&1; then
        print_status "Metrics API is responding"
    else
        print_warning "Metrics API may have issues"
    fi
    
else
    print_error "Portal health endpoint is not responding"
fi

# Clean up port forward
kill $PF_PID 2>/dev/null || true

echo ""
echo "⚙️  Checking Configuration..."
echo "============================"

# Check ConfigMap
print_info "Verifying AI configuration options..."
if kubectl get configmap noctipede-config -n noctipede -o yaml | grep -q "AI_ANALYSIS_ENABLED"; then
    print_status "AI analysis configuration is present"
else
    print_warning "AI analysis configuration may be missing"
fi

if kubectl get configmap noctipede-config -n noctipede -o yaml | grep -q "PORTAL_TYPE"; then
    print_status "Portal configuration is present"
else
    print_warning "Portal configuration may be missing"
fi

echo ""
echo "📊 Service Status Summary..."
echo "============================"

kubectl get services -n noctipede

echo ""
echo "🔗 Access Information..."
echo "======================="

APP_PORT=$(kubectl get service noctipede-app-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "N/A")
PORTAL_PORT=$(kubectl get service noctipede-portal-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "N/A")

echo "📱 Portal Access:"
echo "  • NodePort: http://<node-ip>:${PORTAL_PORT}"
echo "  • Port Forward: kubectl port-forward service/noctipede-portal-service 8080:8080 -n noctipede"
echo "  • Then visit: http://localhost:8080"
echo ""
echo "📊 Available Dashboards:"
echo "  • Dashboard Selector: http://localhost:8080/"
echo "  • Basic Dashboard: http://localhost:8080/basic"
echo "  • Enhanced Dashboard: http://localhost:8080/enhanced"
echo "  • Combined Dashboard: http://localhost:8080/combined"
echo ""
echo "🔧 Useful Commands:"
echo "  • Check logs: kubectl logs -l app=noctipede-portal -n noctipede"
echo "  • Restart portal: kubectl rollout restart deployment/noctipede-portal -n noctipede"
echo "  • Update config: kubectl apply -f configmap.yaml"

echo ""
echo "🎉 Verification Complete!"
echo "========================="

# Final status check
RUNNING_PODS=$(kubectl get pods -n noctipede --no-headers | grep Running | wc -l)
TOTAL_PODS=$(kubectl get pods -n noctipede --no-headers | wc -l)

if [ "$RUNNING_PODS" -eq "$TOTAL_PODS" ]; then
    print_status "All pods are running successfully ($RUNNING_PODS/$TOTAL_PODS)"
else
    print_warning "Some pods may have issues ($RUNNING_PODS/$TOTAL_PODS running)"
fi

print_info "Deployment verification completed!"
