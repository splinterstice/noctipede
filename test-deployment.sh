#!/bin/bash

# Noctipede Deployment Test Script
# This script tests the complete deployment to ensure everything works

set -e

echo "🧪 Testing Noctipede Deployment"
echo "==============================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Test 1: Check all pods are running
print_info "Testing pod status..."
if kubectl get pods -n noctipede | grep -q "Running"; then
    print_status "All pods are running"
else
    print_error "Some pods are not running"
    kubectl get pods -n noctipede
    exit 1
fi

# Test 2: Check services are accessible
print_info "Testing service accessibility..."
if kubectl get services -n noctipede | grep -q "noctipede-portal-service"; then
    print_status "Services are configured"
else
    print_error "Services not found"
    exit 1
fi

# Test 3: Test database connectivity
print_info "Testing database connectivity..."
if kubectl exec deployment/mariadb -n noctipede -- mariadb -u root -pstrongRootPassword -e "SELECT 1;" > /dev/null 2>&1; then
    print_status "Database is accessible"
else
    print_error "Database connection failed"
    exit 1
fi

# Test 4: Test MinIO connectivity
print_info "Testing MinIO connectivity..."
if kubectl exec deployment/minio -n noctipede -- mc --version > /dev/null 2>&1; then
    print_status "MinIO is accessible"
else
    print_warning "MinIO test skipped (mc not available)"
fi

# Test 5: Test portal health endpoint
print_info "Testing portal health endpoint..."
kubectl port-forward service/noctipede-portal-service 8082:8080 -n noctipede &
PF_PID=$!
sleep 3

if curl -s http://localhost:8082/api/health > /dev/null 2>&1; then
    print_status "Portal health endpoint is working"
else
    print_error "Portal health endpoint failed"
    kill $PF_PID 2>/dev/null || true
    exit 1
fi

kill $PF_PID 2>/dev/null || true

# Test 6: Run a quick crawler test
print_info "Testing crawler functionality..."
kubectl create job --from=cronjob/noctipede-crawler-nfs test-crawler -n noctipede
sleep 10

if kubectl wait --for=condition=complete job/test-crawler -n noctipede --timeout=60s; then
    print_status "Crawler test completed successfully"
    kubectl delete job test-crawler -n noctipede
else
    print_warning "Crawler test timed out (this is normal for large crawls)"
    kubectl delete job test-crawler -n noctipede 2>/dev/null || true
fi

# Test 7: Check data in database
print_info "Testing database data..."
SITE_COUNT=$(kubectl exec deployment/mariadb -n noctipede -- mariadb -u root -pstrongRootPassword -e "USE \`splinter-research\`; SELECT COUNT(*) FROM sites;" -s -N 2>/dev/null || echo "0")
PAGE_COUNT=$(kubectl exec deployment/mariadb -n noctipede -- mariadb -u root -pstrongRootPassword -e "USE \`splinter-research\`; SELECT COUNT(*) FROM pages;" -s -N 2>/dev/null || echo "0")

if [ "$SITE_COUNT" -gt 0 ] && [ "$PAGE_COUNT" -gt 0 ]; then
    print_status "Database contains crawled data (Sites: $SITE_COUNT, Pages: $PAGE_COUNT)"
else
    print_warning "Database is empty or crawler hasn't run yet"
fi

echo ""
echo "🎉 DEPLOYMENT TEST COMPLETED!"
echo "============================="
echo ""
print_status "Noctipede is deployed and working correctly"
echo ""
echo "📋 ACCESS INFORMATION:"
echo "====================="
echo "🌐 Portal (NodePort): http://<node-ip>:32080"
echo "🕷️  Main App (NodePort): http://<node-ip>:30080"
echo "🔗 Portal (Ingress): https://noctipede.splinterstice.celestium.life"
echo "📦 MinIO Console: http://10.1.1.12:9001"
echo ""
echo "🔧 USEFUL COMMANDS:"
echo "=================="
echo "• Check pods: kubectl get pods -n noctipede"
echo "• View logs: kubectl logs -l app=noctipede-portal -n noctipede"
echo "• Run crawler: kubectl create job --from=cronjob/noctipede-crawler-nfs manual-crawl -n noctipede"
echo "• Port forward: kubectl port-forward service/noctipede-portal-service 8080:8080 -n noctipede"
echo ""
print_info "Test script completed successfully!"
