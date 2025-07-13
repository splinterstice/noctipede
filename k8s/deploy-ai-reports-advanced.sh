#!/bin/bash

# Deploy Advanced AI Reports System to Kubernetes
# This script deploys the comprehensive AI Reports system with MemeCLIP integration

set -e

echo "🚀 Deploying Advanced AI Reports System to Kubernetes"
echo "=================================================="

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

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

# Check if noctipede namespace exists
if ! kubectl get namespace noctipede &> /dev/null; then
    print_error "noctipede namespace does not exist"
    exit 1
fi

print_status "Kubernetes cluster connection verified"

# Deploy ConfigMaps
print_status "Deploying AI Reports ConfigMaps..."

print_status "Creating AI Reports Advanced Templates ConfigMap..."
kubectl apply -f ai-reports-advanced-configmap.yaml

print_status "Creating AI Reports JavaScript Files ConfigMap..."
kubectl apply -f ai-reports-js-configmap.yaml

print_status "Creating AI Reports API Files ConfigMap..."
kubectl apply -f ai-reports-api-configmap.yaml

print_success "ConfigMaps deployed successfully"

# Deploy the Advanced AI Reports application
print_status "Deploying Advanced AI Reports Application..."
kubectl apply -f noctipede-ai-reports-deployment.yaml

print_success "Advanced AI Reports deployment created"

# Wait for deployment to be ready
print_status "Waiting for Advanced AI Reports deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/noctipede-app-ai-reports -n noctipede

print_success "Advanced AI Reports deployment is ready"

# Get service information
print_status "Getting service information..."
kubectl get services -n noctipede | grep ai-reports

# Get pod status
print_status "Getting pod status..."
kubectl get pods -n noctipede -l component=ai-reports

# Get deployment status
print_status "Getting deployment status..."
kubectl get deployments -n noctipede -l component=ai-reports

# Check if ingress exists and update it
print_status "Checking ingress configuration..."
if kubectl get ingress noctipede-ingress -n noctipede &> /dev/null; then
    print_status "Ingress exists, you may need to update it to include AI Reports routes"
    kubectl get ingress noctipede-ingress -n noctipede -o yaml
else
    print_warning "No ingress found, AI Reports will be accessible via NodePort only"
fi

# Display access information
echo ""
echo "🎉 Advanced AI Reports System Deployment Complete!"
echo "=================================================="
echo ""
echo "📊 Access Information:"
echo "  • NodePort Service: Available on port 31080"
echo "  • Internal Service: noctipede-ai-reports-service.noctipede.svc.cluster.local:8080"
echo ""
echo "🌐 URLs (if ingress is configured):"
echo "  • Basic AI Reports: https://noctipede.splinterstice.celestium.life/ai-reports"
echo "  • Advanced AI Reports: https://noctipede.splinterstice.celestium.life/ai-reports-advanced"
echo ""
echo "🔧 Features Available:"
echo "  ✅ AWS Athena-like Query Engine with SQL syntax highlighting"
echo "  ✅ MemeCLIP Integration for image analysis"
echo "  ✅ Dataset Management with CRUD operations"
echo "  ✅ Screenshot Service for website capture"
echo "  ✅ AI-Powered Report Generation"
echo "  ✅ HIVE Export functionality"
echo "  ✅ Responsive modern UI with Bootstrap 5"
echo ""
echo "📋 Next Steps:"
echo "  1. Verify the deployment is working: kubectl logs -f deployment/noctipede-app-ai-reports -n noctipede"
echo "  2. Test the AI Reports interface in your browser"
echo "  3. Configure MemeCLIP repository if needed"
echo "  4. Set up screenshot service dependencies"
echo ""

# Show logs from the deployment
print_status "Showing recent logs from AI Reports deployment..."
kubectl logs --tail=20 deployment/noctipede-app-ai-reports -n noctipede || print_warning "Could not retrieve logs"

echo ""
print_success "Advanced AI Reports System is now deployed and ready to use! 🚀"
