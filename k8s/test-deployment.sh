#!/bin/bash

# Noctipede Deployment Test Script
# This script tests all components of the deployed Noctipede system

set -e

echo "🧪 Testing Noctipede Deployment..."
echo "================================="

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

# Test counter
tests_passed=0
tests_failed=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo ""
    print_info "Testing: $test_name"
    
    if eval "$test_command" &> /dev/null; then
        print_status "$test_name - PASSED"
        ((tests_passed++))
        return 0
    else
        print_error "$test_name - FAILED"
        ((tests_failed++))
        return 1
    fi
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

# Test 1: Namespace exists
run_test "Namespace exists" "kubectl get namespace noctipede"

# Test 2: All pods are running
echo ""
print_info "Checking pod status..."
kubectl get pods -n noctipede

# Test core services
run_test "MariaDB pod running" "kubectl get pod -l app=mariadb -n noctipede | grep Running"
run_test "MinIO pod running" "kubectl get pod -l app=minio -n noctipede | grep Running"
run_test "Tor proxy running" "kubectl get pod -l app=tor-proxy -n noctipede | grep Running"
run_test "I2P proxy running" "kubectl get pod -l app=i2p-proxy -n noctipede | grep Running"
run_test "Noctipede app running" "kubectl get pod -l app=noctipede-app -n noctipede | grep Running"

# Test 3: Services are accessible
run_test "MariaDB service accessible" "kubectl get service mariadb -n noctipede"
run_test "MinIO service accessible" "kubectl get service minio -n noctipede"
run_test "App service accessible" "kubectl get service noctipede-app-service -n noctipede"

# Test 4: Database connectivity
echo ""
print_info "Testing database connectivity..."
if kubectl exec -n noctipede deployment/mariadb -- mysql -u root -p\$MYSQL_ROOT_PASSWORD -e "SHOW DATABASES;" &> /dev/null; then
    print_status "Database connectivity - PASSED"
    ((tests_passed++))
else
    print_error "Database connectivity - FAILED"
    ((tests_failed++))
fi

# Test 5: MinIO connectivity
echo ""
print_info "Testing MinIO connectivity..."
if kubectl exec -n noctipede deployment/minio -- mc --version &> /dev/null; then
    print_status "MinIO connectivity - PASSED"
    ((tests_passed++))
else
    print_error "MinIO connectivity - FAILED"
    ((tests_failed++))
fi

# Test 6: Proxy connectivity
echo ""
print_info "Testing Tor proxy connectivity..."
if kubectl exec -n noctipede deployment/tor-proxy -- nc -z localhost 9150 &> /dev/null; then
    print_status "Tor proxy connectivity - PASSED"
    ((tests_passed++))
else
    print_error "Tor proxy connectivity - FAILED"
    ((tests_failed++))
fi

echo ""
print_info "Testing I2P proxy connectivity..."
if kubectl exec -n noctipede deployment/i2p-proxy -- nc -z localhost 4444 &> /dev/null; then
    print_status "I2P proxy connectivity - PASSED"
    ((tests_passed++))
else
    print_error "I2P proxy connectivity - FAILED"
    ((tests_failed++))
fi

# Test 7: Web application
echo ""
print_info "Testing web application..."
APP_PORT=$(kubectl get service noctipede-app-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}')

# Port forward in background for testing
kubectl port-forward service/noctipede-app-service 8080:8080 -n noctipede &
PF_PID=$!
sleep 5

if curl -s http://localhost:8080 | grep -q "html"; then
    print_status "Web application - PASSED"
    ((tests_passed++))
else
    print_error "Web application - FAILED"
    ((tests_failed++))
fi

# Clean up port forward
kill $PF_PID 2>/dev/null || true

# Test 8: I2P network test
echo ""
print_info "Testing I2P network access..."
if kubectl run i2p-network-test --image=curlimages/curl --rm --restart=Never -n noctipede --timeout=60s -- curl -x http://i2p-proxy:4444 -m 30 http://reg.i2p/ --head &> /dev/null; then
    print_status "I2P network access - PASSED"
    ((tests_passed++))
else
    print_warning "I2P network access - FAILED (may be normal if I2P is bootstrapping)"
    ((tests_failed++))
fi

# Test 9: Storage volumes
run_test "Output PVC exists" "kubectl get pvc noctipede-output-pvc -n noctipede"
run_test "Logs PVC exists" "kubectl get pvc noctipede-logs-pvc -n noctipede"

# Test 10: Configuration
run_test "ConfigMap exists" "kubectl get configmap noctipede-config -n noctipede"
run_test "Secrets exist" "kubectl get secret noctipede-secrets -n noctipede"

# Summary
echo ""
echo "🏁 TEST SUMMARY"
echo "==============="
echo "Tests Passed: $tests_passed"
echo "Tests Failed: $tests_failed"
echo "Total Tests: $((tests_passed + tests_failed))"

if [[ $tests_failed -eq 0 ]]; then
    echo ""
    print_status "ALL TESTS PASSED! 🎉"
    echo ""
    echo "📋 ACCESS INFORMATION:"
    echo "====================="
    echo "🌐 Main Application: http://<node-ip>:${APP_PORT}"
    echo "📊 Portal: kubectl port-forward service/noctipede-portal-service 8080:8080 -n noctipede"
    echo "📦 MinIO: kubectl port-forward service/minio-console 9001:9001 -n noctipede"
    echo ""
    echo "🔧 USEFUL COMMANDS:"
    echo "=================="
    echo "• View all pods: kubectl get pods -n noctipede"
    echo "• Check app logs: kubectl logs -l app=noctipede-app -n noctipede"
    echo "• Access app: kubectl port-forward service/noctipede-app-service 8080:8080 -n noctipede"
    exit 0
else
    echo ""
    print_error "SOME TESTS FAILED!"
    echo ""
    echo "🔧 TROUBLESHOOTING:"
    echo "=================="
    echo "• Check pod status: kubectl get pods -n noctipede"
    echo "• View pod logs: kubectl logs <pod-name> -n noctipede"
    echo "• Describe pod: kubectl describe pod <pod-name> -n noctipede"
    echo "• Check events: kubectl get events -n noctipede --sort-by='.lastTimestamp'"
    exit 1
fi
