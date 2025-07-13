#!/usr/bin/env bash

# Improved Noctipede Kubernetes Destruction Script
# Handles stuck resources and hanging pods more gracefully

set -e

echo "🔥 Starting Improved Noctipede Kubernetes Destruction"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_destroy() {
    echo -e "${PURPLE}[DESTROY]${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace noctipede >/dev/null 2>&1; then
    print_warning "Namespace 'noctipede' does not exist or already deleted"
    exit 0
fi

print_status "Found noctipede namespace, proceeding with destruction..."

# Step 1: Delete CronJobs first to prevent new pods
print_destroy "Deleting CronJobs..."
kubectl delete cronjobs --all -n noctipede --ignore-not-found=true
print_success "CronJobs deleted"

# Step 2: Delete Jobs
print_destroy "Deleting Jobs..."
kubectl delete jobs --all -n noctipede --ignore-not-found=true
print_success "Jobs deleted"

# Step 3: Force delete any stuck pods
print_destroy "Force deleting any stuck pods..."
kubectl delete pods --all -n noctipede --force --grace-period=0 --ignore-not-found=true
print_success "Stuck pods deleted"

# Step 4: Delete applications in reverse order
print_destroy "Deleting Noctipede applications..."
kubectl delete -f noctipede/ --ignore-not-found=true
print_success "Applications deleted"

# Step 5: Delete proxy services
print_destroy "Deleting proxy services..."
kubectl delete -f proxy/ --ignore-not-found=true
print_success "Proxy services deleted"

# Step 6: Delete storage services
print_destroy "Deleting storage services..."
kubectl delete -f minio/ --ignore-not-found=true
kubectl delete -f mariadb/ --ignore-not-found=true
print_success "Storage services deleted"

# Step 7: Delete ConfigMap and Secrets
print_destroy "Deleting ConfigMap and Secrets..."
kubectl delete -f configmap.yaml --ignore-not-found=true
kubectl delete -f secrets.yaml --ignore-not-found=true
print_success "ConfigMap and Secrets deleted"

# Step 8: Force delete any remaining PVCs
print_destroy "Force deleting any remaining PVCs..."
kubectl delete pvc --all -n noctipede --force --grace-period=0 --ignore-not-found=true
print_success "PVCs deleted"

# Step 9: Wait a moment for resources to clean up
print_status "Waiting for resources to clean up..."
sleep 10

# Step 10: Delete namespace (with timeout)
print_destroy "Deleting namespace..."
kubectl delete namespace noctipede --ignore-not-found=true &
NAMESPACE_PID=$!

# Wait for namespace deletion with timeout
TIMEOUT=120
COUNT=0
while kubectl get namespace noctipede >/dev/null 2>&1; do
    if [ $COUNT -ge $TIMEOUT ]; then
        print_warning "Namespace deletion timed out after ${TIMEOUT}s"
        print_status "Attempting to force delete namespace..."
        
        # Remove finalizers if stuck
        kubectl patch namespace noctipede -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
        break
    fi
    
    sleep 2
    COUNT=$((COUNT + 2))
    
    if [ $((COUNT % 20)) -eq 0 ]; then
        print_status "Still waiting for namespace deletion... (${COUNT}s/${TIMEOUT}s)"
    fi
done

# Check final status
if kubectl get namespace noctipede >/dev/null 2>&1; then
    print_error "Namespace still exists after cleanup attempts"
    print_status "You may need to manually investigate stuck resources:"
    echo "kubectl get all -n noctipede"
    echo "kubectl describe namespace noctipede"
    exit 1
else
    print_success "Namespace successfully deleted"
fi

print_success "🎉 Noctipede Destruction Complete!"
print_status "All resources have been cleaned up successfully"
