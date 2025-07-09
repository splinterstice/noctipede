#!/usr/bin/env bash

# Complete update and deployment script for Noctipede
# This script builds the latest image and deploys with readiness checks

set -e

echo "🚀 Noctipede Complete Update & Deployment"
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

# Step 1: Build and push latest image
echo ""
echo "🔨 Building and pushing latest image..."
print_info "This includes all the latest readiness system improvements"

if ! make ghcr-deploy; then
    print_error "Failed to build and push image"
    exit 1
fi

print_status "Latest image built and pushed to GHCR"

# Step 2: Destroy existing deployment
echo ""
echo "💥 Destroying existing deployment..."
if [ -f "k8s/destroy.sh" ]; then
    cd k8s
    ./destroy.sh
    cd ..
    print_status "Existing deployment destroyed"
else
    print_warning "destroy.sh not found, skipping destruction"
fi

# Step 3: Deploy with latest image
echo ""
echo "🚀 Deploying with latest image and readiness checks..."
if [ -f "k8s/deploy.sh" ]; then
    cd k8s
    ./deploy.sh
    cd ..
    print_status "Deployment completed"
else
    print_error "deploy.sh not found"
    exit 1
fi

echo ""
echo "🎉 COMPLETE UPDATE & DEPLOYMENT FINISHED!"
echo "========================================"
print_status "Noctipede is now running with the latest readiness system"
echo ""
echo "🔍 The system will automatically:"
echo "   • Check Tor network connectivity"
echo "   • Verify I2P network with 5+ internal proxies"
echo "   • Test walker.i2p accessibility"
echo "   • Only start crawling when fully ready"
echo ""
echo "📊 Monitor readiness at: http://<node-ip>:30080/api/readiness"
