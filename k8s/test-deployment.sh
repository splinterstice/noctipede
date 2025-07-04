#!/bin/bash

# Noctipede Kubernetes Deployment Test Script
# This script validates that all services are working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    print_test "$test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        print_pass "$test_name"
        return 0
    else
        print_fail "$test_name"
        return 1
    fi
}

# Main test function
test_deployment() {
    echo "🧪 Testing Noctipede Kubernetes Deployment"
    echo ""
    
    local total_tests=0
    local passed_tests=0
    
    # Test 1: Namespace exists
    total_tests=$((total_tests + 1))
    if run_test "Namespace 'noctipede' exists" "kubectl get namespace noctipede"; then
        passed_tests=$((passed_tests + 1))
    fi
    
    # Test 2: All deployments are ready
    local deployments=("mariadb" "minio-crawler" "tor-proxy" "i2p-proxy" "noctipede-portal" "noctipede-app")
    
    for deployment in "${deployments[@]}"; do
        total_tests=$((total_tests + 1))
        if run_test "Deployment '$deployment' is ready" "kubectl get deployment $deployment -n noctipede -o jsonpath='{.status.readyReplicas}' | grep -q '^[1-9]'"; then
            passed_tests=$((passed_tests + 1))
        fi
    done
    
    # Test 3: All services are accessible
    local services=("mariadb:3306" "minio-crawler-hl:9000" "tor-proxy:9050" "i2p-proxy:4444" "noctipede-portal-service:8080")
    
    for service in "${services[@]}"; do
        total_tests=$((total_tests + 1))
        local service_name=$(echo $service | cut -d: -f1)
        local service_port=$(echo $service | cut -d: -f2)
        
        if run_test "Service '$service_name' is accessible on port $service_port" \
           "kubectl exec -n noctipede deployment/noctipede-portal -- nc -z $service_name $service_port"; then
            passed_tests=$((passed_tests + 1))
        fi
    done
    
    # Test 4: Portal API is responding
    total_tests=$((total_tests + 1))
    if run_test "Portal API health check" \
       "kubectl exec -n noctipede deployment/noctipede-portal -- curl -s http://localhost:8080/api/health | grep -q 'status'"; then
        passed_tests=$((passed_tests + 1))
    fi
    
    # Test 5: Database connectivity
    total_tests=$((total_tests + 1))
    if run_test "Database connectivity from portal" \
       "kubectl exec -n noctipede deployment/noctipede-portal -- nc -z mariadb 3306"; then
        passed_tests=$((passed_tests + 1))
    fi
    
    # Test 6: MinIO connectivity
    total_tests=$((total_tests + 1))
    if run_test "MinIO connectivity from portal" \
       "kubectl exec -n noctipede deployment/noctipede-portal -- nc -z minio-crawler-hl 9000"; then
        passed_tests=$((passed_tests + 1))
    fi
    
    # Test 7: Proxy network metrics (if portal is responding)
    total_tests=$((total_tests + 1))
    if run_test "Proxy network metrics available" \
       "kubectl exec -n noctipede deployment/noctipede-portal -- curl -s http://localhost:8080/api/system-metrics | grep -q 'network'"; then
        passed_tests=$((passed_tests + 1))
    fi
    
    # Summary
    echo ""
    echo "📊 Test Results:"
    echo "  Total Tests: $total_tests"
    echo "  Passed: $passed_tests"
    echo "  Failed: $((total_tests - passed_tests))"
    
    if [ $passed_tests -eq $total_tests ]; then
        print_pass "All tests passed! 🎉"
        echo ""
        echo "🌐 Access Information:"
        
        # Try to get external IP
        EXTERNAL_IP=$(kubectl get service noctipede-portal-service -n noctipede -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        
        if [ -n "$EXTERNAL_IP" ]; then
            echo "  Portal URL: http://$EXTERNAL_IP:8080"
        else
            echo "  Use port-forward: kubectl port-forward -n noctipede service/noctipede-portal-service 8080:8080"
            echo "  Then access: http://localhost:8080"
        fi
        
        return 0
    else
        print_fail "Some tests failed. Check the deployment."
        echo ""
        echo "🔍 Debugging commands:"
        echo "  kubectl get pods -n noctipede"
        echo "  kubectl logs -n noctipede deployment/noctipede-portal"
        echo "  kubectl describe pods -n noctipede"
        
        return 1
    fi
}

# Detailed status function
show_detailed_status() {
    echo "📋 Detailed Deployment Status"
    echo ""
    
    print_test "Checking pods..."
    kubectl get pods -n noctipede -o wide
    
    echo ""
    print_test "Checking services..."
    kubectl get services -n noctipede
    
    echo ""
    print_test "Checking deployments..."
    kubectl get deployments -n noctipede
    
    echo ""
    print_test "Checking PVCs..."
    kubectl get pvc -n noctipede
    
    echo ""
    print_test "Recent events..."
    kubectl get events -n noctipede --sort-by='.lastTimestamp' | tail -10
}

# Network connectivity test
test_network_connectivity() {
    echo "🌐 Testing Network Connectivity"
    echo ""
    
    print_test "Testing proxy connectivity from portal..."
    
    # Test if we can get system metrics
    if kubectl exec -n noctipede deployment/noctipede-portal -- \
       curl -s http://localhost:8080/api/system-metrics >/tmp/metrics.json 2>/dev/null; then
        
        print_pass "Portal API responding"
        
        # Check network metrics
        if grep -q '"network"' /tmp/metrics.json; then
            print_pass "Network metrics available"
            
            # Show network status
            echo ""
            echo "🔌 Network Status:"
            kubectl exec -n noctipede deployment/noctipede-portal -- \
                curl -s http://localhost:8080/api/system-metrics | \
                jq '.system.network' 2>/dev/null || echo "Could not parse network metrics"
        else
            print_warn "Network metrics not found in response"
        fi
        
        rm -f /tmp/metrics.json
    else
        print_fail "Portal API not responding"
    fi
}

# Main script logic
case "${1:-test}" in
    "test")
        test_deployment
        ;;
    "status")
        show_detailed_status
        ;;
    "network")
        test_network_connectivity
        ;;
    "all")
        test_deployment
        echo ""
        show_detailed_status
        echo ""
        test_network_connectivity
        ;;
    "help"|"-h"|"--help")
        echo "Noctipede Kubernetes Test Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  test      Run basic deployment tests (default)"
        echo "  status    Show detailed deployment status"
        echo "  network   Test network connectivity and proxy status"
        echo "  all       Run all tests and show detailed status"
        echo "  help      Show this help message"
        ;;
    *)
        print_fail "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
