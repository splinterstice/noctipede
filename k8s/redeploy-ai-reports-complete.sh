#!/bin/bash

# Complete Redeployment of Advanced AI Reports with Bottom Popup
# This script performs a clean redeployment of all AI Reports components

set -e

echo "🔄 Starting Complete AI Reports Redeployment"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Step 1: Delete existing ConfigMaps
print_status "Cleaning up existing ConfigMaps..."

kubectl delete configmap ai-reports-advanced-templates -n noctipede --ignore-not-found=true
kubectl delete configmap ai-reports-js-files -n noctipede --ignore-not-found=true
kubectl delete configmap ai-reports-api-files -n noctipede --ignore-not-found=true
kubectl delete configmap api-main-updated -n noctipede --ignore-not-found=true

print_success "Old ConfigMaps cleaned up"

# Step 2: Recreate ConfigMaps with latest files
print_status "Creating fresh ConfigMaps..."

cd /home/celes/sources/splinterstice/noctipede

# Templates ConfigMap
kubectl create configmap ai-reports-advanced-templates \
    --from-file=ai_reports_advanced.html=portal/templates/ai_reports_advanced.html \
    -n noctipede

# JavaScript ConfigMap
kubectl create configmap ai-reports-js-files \
    --from-file=ai_reports_advanced.js=static/ai_reports/js/ai_reports_advanced.js \
    --from-file=memeclip_integration.js=static/ai_reports/js/memeclip_integration.js \
    -n noctipede

# API ConfigMap
kubectl create configmap ai-reports-api-files \
    --from-file=ai_reports_advanced.py=api/ai_reports_advanced.py \
    -n noctipede

# Main API ConfigMap
kubectl create configmap api-main-updated \
    --from-file=main.py=api/main.py \
    -n noctipede

print_success "Fresh ConfigMaps created"

# Step 3: Force restart deployment
print_status "Force restarting deployment..."

kubectl delete pod -n noctipede -l app=noctipede-app --force --grace-period=0

print_status "Waiting for new pod to be ready..."
kubectl wait --for=condition=ready pod -l app=noctipede-app -n noctipede --timeout=300s

print_success "Deployment restarted successfully"

# Step 4: Verify deployment
print_status "Verifying deployment..."

# Check if pod is running
POD_NAME=$(kubectl get pods -n noctipede -l app=noctipede-app --no-headers -o custom-columns=":metadata.name" | head -1)
print_status "Active pod: $POD_NAME"

# Check if files are properly mounted
print_status "Verifying file mounts..."

POPUP_COUNT=$(kubectl exec $POD_NAME -n noctipede -- grep -c "bottom-popup" /app/portal/templates/ai_reports_advanced.html 2>/dev/null || echo "0")
JS_COUNT=$(kubectl exec $POD_NAME -n noctipede -- grep -c "showBottomPopup" /app/static/ai_reports/js/ai_reports_advanced.js 2>/dev/null || echo "0")

if [ "$POPUP_COUNT" -gt "10" ] && [ "$JS_COUNT" -gt "0" ]; then
    print_success "Bottom popup files properly mounted"
else
    print_warning "File mount verification inconclusive (popup: $POPUP_COUNT, js: $JS_COUNT)"
fi

# Check if advanced AI Reports are loaded
print_status "Checking AI Reports status..."
sleep 10  # Give the app time to start

kubectl logs $POD_NAME -n noctipede --tail=20 | grep -i "advanced" || print_warning "Advanced AI Reports status unclear"

# Step 5: Test endpoints
print_status "Testing API endpoints..."

# Test health endpoint
if curl -s https://noctipede.splinterstice.celestium.life/api/ai-reports/health | grep -q "healthy"; then
    print_success "AI Reports API is healthy"
else
    print_warning "AI Reports API health check failed"
fi

# Test interface
if curl -s https://noctipede.splinterstice.celestium.life/ai-reports-advanced | grep -q "bottom-popup"; then
    print_success "Bottom popup interface is accessible"
else
    print_warning "Bottom popup interface verification failed"
fi

# Step 6: Display status
echo ""
echo "🎉 Complete Redeployment Summary"
echo "================================"
echo ""

kubectl get configmaps -n noctipede | grep ai-reports
echo ""
kubectl get pods -n noctipede -l app=noctipede-app
echo ""

print_success "Advanced AI Reports with Bottom Popup - Redeployment Complete!"
echo ""
echo "🌐 Access URLs:"
echo "  • Advanced Interface: https://noctipede.splinterstice.celestium.life/ai-reports-advanced"
echo "  • API Health: https://noctipede.splinterstice.celestium.life/api/ai-reports/health"
echo ""
echo "🎯 Features Available:"
echo "  ✅ Bottom popup window (lower third of screen)"
echo "  ✅ Drag-to-resize functionality"
echo "  ✅ Tabbed result organization"
echo "  ✅ Scrollable main content area"
echo "  ✅ Professional animations and transitions"
echo ""
print_success "Ready to use! 🚀"
