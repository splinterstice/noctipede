#!/usr/bin/env bash

# Test script to verify deploy.sh works with all the fixes
# This script tests the deployment and verifies the I2P proxy fixes

set -e

echo "🧪 Testing deploy.sh with I2P proxy fixes"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Step 1: Check if we have the latest image
echo ""
print_info "Checking if latest image is available..."
if docker pull ghcr.io/splinterstice/noctipede:latest; then
    print_status "Latest image available"
else
    print_warning "Latest image not found, building..."
    make ghcr-deploy
fi

# Step 2: Verify ConfigMap has correct I2P proxies
echo ""
print_info "Verifying ConfigMap has correct I2P proxy configuration..."
if grep -q "stats.i2p\|i2p-projekt.i2p\|forum.i2p\|zzz.i2p" k8s/configmap.yaml; then
    print_error "ConfigMap still contains non-proxy I2P sites!"
    echo "Found problematic entries in k8s/configmap.yaml:"
    grep -n "stats.i2p\|i2p-projekt.i2p\|forum.i2p\|zzz.i2p" k8s/configmap.yaml || true
    exit 1
else
    print_status "ConfigMap has correct I2P proxy configuration"
fi

# Step 3: Count expected proxies
PROXY_LIST=$(grep "I2P_INTERNAL_PROXIES:" k8s/configmap.yaml | cut -d'"' -f2)
EXPECTED_PROXIES=$(echo "$PROXY_LIST" | tr ',' '\n' | wc -l)
print_info "Expected I2P internal proxies: $EXPECTED_PROXIES"

# Step 4: Verify CronJob uses latest image and readiness
echo ""
print_info "Verifying CronJob configuration..."
if grep -q "ghcr.io/splinterstice/noctipede:latest" k8s/crawler-nfs.yaml; then
    print_status "CronJob uses latest image"
else
    print_error "CronJob not using latest image!"
    grep -n "image:" k8s/crawler-nfs.yaml
    exit 1
fi

if grep -q "ready_for_crawling" k8s/crawler-nfs.yaml; then
    print_status "CronJob has readiness integration"
else
    print_error "CronJob missing readiness integration!"
    exit 1
fi

if grep -A 1 "CONTENT_ANALYSIS_ENABLED" k8s/crawler-nfs.yaml | grep -q '"true"'; then
    print_status "CronJob has content analysis enabled"
else
    print_warning "CronJob has content analysis disabled"
fi
# Step 6: Verify Ollama data persistence configuration
echo ""
print_info "Verifying Ollama data persistence..."
if grep -q "noctipede-data-pvc" k8s/noctipede/pvc.yaml; then
    print_status "Data PVC defined"
else
    print_error "Data PVC missing!"
    exit 1
fi

if grep -q "data-storage" k8s/noctipede/enhanced-portal-deployment-with-data.yaml; then
    print_status "Portal deployment has data volume mount"
else
    print_error "Portal deployment missing data volume mount!"
    exit 1
fi

if grep -q "enhanced-portal-deployment-with-data.yaml" k8s/deploy.sh; then
    print_status "deploy.sh uses enhanced portal deployment"
else
    print_error "deploy.sh not using enhanced portal deployment!"
    exit 1
fi
# Step 8: Verify bootstrap-aware caching implementation
echo ""
print_info "Verifying bootstrap-aware caching..."
if grep -q "_is_bootstrap_mode" portal/combined_metrics_collector.py; then
    print_status "Bootstrap mode detection implemented"
else
    print_error "Bootstrap mode detection missing!"
    exit 1
fi

if grep -q "BOOTSTRAP_DURATION.*1800" portal/combined_metrics_collector.py; then
    print_status "Bootstrap duration set to 30 minutes"
else
    print_error "Bootstrap duration not configured!"
    exit 1
fi

if grep -q "bootstrap_info" portal/combined_metrics_collector.py; then
    print_status "Bootstrap info included in readiness API"
else
    print_error "Bootstrap info missing from readiness API!"
    exit 1
fi
# Step 9: Verify deploy.sh uses latest image
echo ""
print_info "Verifying deploy.sh uses latest image..."
if grep -q "ghcr.io/splinterstice/noctipede:latest" k8s/deploy.sh; then
    print_status "deploy.sh uses latest image"
else
    print_error "deploy.sh not using latest image!"
    exit 1
fi

# Step 5: Test deployment (if requested)
if [ "$1" = "--deploy" ]; then
    echo ""
    print_info "Running full deployment test..."
    
    # Destroy existing
    if [ -f "k8s/destroy.sh" ]; then
        print_info "Destroying existing deployment..."
        cd k8s && ./destroy.sh && cd ..
    fi
    
    # Deploy fresh
    print_info "Deploying with fixes..."
    cd k8s && ./deploy.sh && cd ..
    
    # Wait for readiness
    print_info "Waiting for system to be ready..."
    sleep 60
    
    # Test readiness
    print_info "Testing readiness endpoint..."
    kubectl run readiness-test --image=curlimages/curl --rm -it --restart=Never -n noctipede --timeout=30s -- curl -s http://noctipede-portal-service:8080/api/readiness > /tmp/readiness_test.json
    
    if [ -f /tmp/readiness_test.json ]; then
        ACTIVE_PROXIES=$(cat /tmp/readiness_test.json | grep -o '"active_i2p_proxies":[0-9]*' | cut -d':' -f2)
        TOTAL_PROXIES=$(cat /tmp/readiness_test.json | grep -o '"total_configured":[0-9]*' | cut -d':' -f2)
        
        print_info "I2P Proxy Status: $ACTIVE_PROXIES/$TOTAL_PROXIES active"
        
        if [ "$TOTAL_PROXIES" = "$EXPECTED_PROXIES" ]; then
            print_status "Correct number of I2P proxies configured"
        else
            print_warning "Expected $EXPECTED_PROXIES proxies, got $TOTAL_PROXIES"
        fi
        
        if [ "$ACTIVE_PROXIES" -ge 2 ]; then
            print_status "Good I2P proxy connectivity ($ACTIVE_PROXIES active)"
        else
            print_warning "Limited I2P proxy connectivity ($ACTIVE_PROXIES active)"
        fi
    fi
    
    rm -f /tmp/readiness_test.json
fi

echo ""
print_status "🎯 Deploy readiness test completed!"
echo ""
echo "📋 Summary:"
echo "==========="
echo "✅ ConfigMap has correct I2P proxy configuration (no destination sites)"
echo "✅ deploy.sh uses latest image with syntax fixes"
echo "✅ Expected $EXPECTED_PROXIES I2P internal proxies configured"
echo ""
echo "🚀 Ready to deploy with: cd k8s && ./deploy.sh"
echo ""
echo "💡 To run full deployment test: $0 --deploy"
