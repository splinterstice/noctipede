#!/usr/bin/env bash

# Enhanced Deployment Verification Script
# Verifies that the enhanced dashboard and AI reports are working after deployment

set -e

echo "🔍 Verifying Enhanced Noctipede Deployment..."
echo "=============================================="

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

# Get the service URL
NOCTIPEDE_URL=""
if kubectl get service noctipede-app-service -n noctipede &> /dev/null; then
    NODE_PORT=$(kubectl get service noctipede-app-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}')
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')
    if [ -z "$NODE_IP" ]; then
        NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
    fi
    NOCTIPEDE_URL="http://${NODE_IP}:${NODE_PORT}"
    print_info "Detected service URL: $NOCTIPEDE_URL"
else
    print_error "Noctipede service not found"
    exit 1
fi

# Test 1: Basic connectivity
echo ""
echo "🌐 Testing basic connectivity..."
if curl -s --max-time 10 "$NOCTIPEDE_URL" > /dev/null; then
    print_status "Basic dashboard is accessible"
else
    print_error "Basic dashboard is not accessible"
    exit 1
fi

# Test 2: Enhanced dashboard
echo ""
echo "⚡ Testing enhanced dashboard..."
if curl -s --max-time 10 "$NOCTIPEDE_URL/enhanced" > /dev/null; then
    print_status "Enhanced dashboard is accessible"
else
    print_error "Enhanced dashboard is not accessible"
    exit 1
fi

# Test 3: Enhanced metrics API
echo ""
echo "📊 Testing enhanced metrics API..."
ENHANCED_METRICS=$(curl -s --max-time 10 "$NOCTIPEDE_URL/api/enhanced-metrics")
if echo "$ENHANCED_METRICS" | grep -q "timestamp"; then
    print_status "Enhanced metrics API is working"
    
    # Check if we have enhanced or fallback metrics
    if echo "$ENHANCED_METRICS" | grep -q "basic_fallback"; then
        print_warning "Using basic fallback metrics (dependencies may be missing)"
    elif echo "$ENHANCED_METRICS" | grep -q "basic_enhanced"; then
        print_status "Using basic enhanced metrics (standard library only)"
    else
        print_status "Using full enhanced metrics"
    fi
else
    print_error "Enhanced metrics API is not working"
    echo "Response: $ENHANCED_METRICS"
fi

# Test 4: AI Reports dashboard
echo ""
echo "🤖 Testing AI Reports dashboard..."
if curl -s --max-time 10 "$NOCTIPEDE_URL/ai-reports" > /dev/null; then
    print_status "AI Reports dashboard is accessible"
else
    print_warning "AI Reports dashboard may not be accessible (this is expected if AI Reports API is not fully configured)"
fi

# Test 5: Combined dashboard
echo ""
echo "🔗 Testing combined dashboard..."
if curl -s --max-time 10 "$NOCTIPEDE_URL/combined" > /dev/null; then
    print_status "Combined dashboard is accessible"
else
    print_warning "Combined dashboard may not be accessible"
fi

# Test 6: Static files
echo ""
echo "📁 Testing static files..."
if curl -s --max-time 10 "$NOCTIPEDE_URL/static/ai_reports/js/ai_reports.js" > /dev/null; then
    print_status "AI Reports static files are accessible"
else
    print_warning "AI Reports static files may not be accessible"
fi

# Test 7: Database migration status
echo ""
echo "🗄️ Testing database migration status..."
DB_METRICS=$(curl -s --max-time 10 "$NOCTIPEDE_URL/api/metrics")
if echo "$DB_METRICS" | grep -q "total_sites"; then
    print_status "Database is accessible and has crawler data"
else
    print_warning "Database may not have crawler data yet"
fi

# Test 8: Pod status
echo ""
echo "🏗️ Checking pod status..."
NOCTIPEDE_POD=$(kubectl get pods -n noctipede -l app=noctipede-app -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$NOCTIPEDE_POD" ]; then
    POD_STATUS=$(kubectl get pod "$NOCTIPEDE_POD" -n noctipede -o jsonpath='{.status.phase}')
    if [ "$POD_STATUS" = "Running" ]; then
        print_status "Noctipede pod is running"
        
        # Check for any errors in logs
        echo ""
        echo "📋 Checking recent logs for errors..."
        RECENT_LOGS=$(kubectl logs "$NOCTIPEDE_POD" -n noctipede --tail=50 2>/dev/null || echo "Could not get logs")
        
        if echo "$RECENT_LOGS" | grep -i "error" | head -3; then
            print_warning "Found some errors in recent logs (shown above)"
        else
            print_status "No recent errors found in logs"
        fi
        
        # Check for enhanced metrics loading
        if echo "$RECENT_LOGS" | grep -q "Enhanced metrics collector\|Basic enhanced metrics"; then
            print_status "Enhanced metrics collector loaded successfully"
        else
            print_warning "Enhanced metrics collector may not be loaded"
        fi
        
    else
        print_error "Noctipede pod is not running (status: $POD_STATUS)"
    fi
else
    print_error "Could not find Noctipede pod"
fi

# Summary
echo ""
echo "📋 Deployment Verification Summary"
echo "=================================="
echo "Service URL: $NOCTIPEDE_URL"
echo ""
echo "Available dashboards:"
echo "  🏠 Basic Dashboard: $NOCTIPEDE_URL/"
echo "  ⚡ Enhanced Dashboard: $NOCTIPEDE_URL/enhanced"
echo "  🔗 Combined Dashboard: $NOCTIPEDE_URL/combined"
echo "  🤖 AI Reports: $NOCTIPEDE_URL/ai-reports"
echo ""
echo "API endpoints:"
echo "  📊 Basic Metrics: $NOCTIPEDE_URL/api/metrics"
echo "  ⚡ Enhanced Metrics: $NOCTIPEDE_URL/api/enhanced-metrics"
echo "  🏥 Health Check: $NOCTIPEDE_URL/api/health"
echo ""

print_status "Enhanced deployment verification completed!"
print_info "If you see warnings above, the basic functionality should still work with graceful fallbacks."
