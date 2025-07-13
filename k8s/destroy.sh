#!/usr/bin/env bash

# Noctipede Kubernetes Destruction Script
# This script safely removes all Noctipede components from Kubernetes

set -e

echo "🗑️  Starting Noctipede Destruction..."
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

# Check if namespace exists
if ! kubectl get namespace noctipede &> /dev/null; then
    print_warning "Noctipede namespace does not exist, nothing to destroy"
    exit 0
fi

# Confirmation prompt
echo ""
print_warning "This will permanently delete ALL Noctipede resources including:"
echo "  • All applications and services"
echo "  • All databases and stored data"
echo "  • All persistent volumes and claims"
echo "  • All configuration and secrets"
echo "  • The entire noctipede namespace"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    print_info "Destruction cancelled"
    exit 0
fi

echo ""
print_info "Starting destruction process..."

# Step 1: Delete all jobs and cronjobs first to prevent new pods
echo ""
echo "🔄 Stopping all jobs and scheduled tasks..."
kubectl delete jobs --all -n noctipede --ignore-not-found=true --timeout=60s
kubectl delete cronjobs --all -n noctipede --ignore-not-found=true --timeout=60s
print_status "Jobs and cronjobs deleted"

# Step 2: Delete all deployments and statefulsets
echo ""
echo "🛑 Stopping all applications..."
kubectl delete deployments --all -n noctipede --ignore-not-found=true --timeout=120s
kubectl delete statefulsets --all -n noctipede --ignore-not-found=true --timeout=120s
print_status "Applications stopped"

# Step 3: Delete all services
echo ""
echo "🌐 Removing all services..."
kubectl delete services --all -n noctipede --ignore-not-found=true --timeout=60s
print_status "Services removed"

# Step 4: Delete all pods (in case any are stuck)
echo ""
echo "🧹 Cleaning up remaining pods..."
kubectl delete pods --all -n noctipede --ignore-not-found=true --timeout=120s --force --grace-period=0 2>/dev/null || true
print_status "Pods cleaned up"

# Step 5: Delete MariaDB operator resources if they exist
echo ""
echo "🗄️  Removing MariaDB operator resources..."
kubectl delete mariadb --all -n noctipede --ignore-not-found=true --timeout=60s 2>/dev/null || true
kubectl delete backups --all -n noctipede --ignore-not-found=true --timeout=60s 2>/dev/null || true
kubectl delete restores --all -n noctipede --ignore-not-found=true --timeout=60s 2>/dev/null || true
print_status "MariaDB operator resources removed"

# Step 6: Delete all persistent volume claims
echo ""
echo "💾 Removing persistent storage..."
kubectl delete pvc --all -n noctipede --ignore-not-found=true --timeout=120s
print_status "Persistent storage removed"

# Step 7: Delete all configmaps and secrets
echo ""
echo "🔐 Removing configuration and secrets..."
kubectl delete configmaps --all -n noctipede --ignore-not-found=true --timeout=60s
kubectl delete secrets --all -n noctipede --ignore-not-found=true --timeout=60s
print_status "Configuration and secrets removed"

# Step 8: Delete any remaining resources
echo ""
echo "🧽 Cleaning up remaining resources..."
kubectl delete ingress --all -n noctipede --ignore-not-found=true --timeout=60s 2>/dev/null || true
kubectl delete networkpolicies --all -n noctipede --ignore-not-found=true --timeout=60s 2>/dev/null || true
kubectl delete serviceaccounts --all -n noctipede --ignore-not-found=true --timeout=60s 2>/dev/null || true
kubectl delete rolebindings --all -n noctipede --ignore-not-found=true --timeout=60s 2>/dev/null || true
kubectl delete roles --all -n noctipede --ignore-not-found=true --timeout=60s 2>/dev/null || true
print_status "Remaining resources cleaned up"

# Step 9: Wait for all pods to be terminated
echo ""
echo "⏳ Waiting for all pods to terminate..."
timeout=120
while [[ $timeout -gt 0 ]]; do
    pod_count=$(kubectl get pods -n noctipede --no-headers 2>/dev/null | wc -l)
    if [[ $pod_count -eq 0 ]]; then
        break
    fi
    echo "   Waiting for $pod_count pods to terminate..."
    sleep 5
    ((timeout-=5))
done

if [[ $timeout -le 0 ]]; then
    print_warning "Some pods may still be terminating"
    kubectl get pods -n noctipede 2>/dev/null || true
else
    print_status "All pods terminated"
fi

# Step 10: Delete the namespace
echo ""
echo "📁 Removing namespace..."
kubectl delete namespace noctipede --ignore-not-found=true --timeout=180s
print_status "Namespace removed"

# Step 11: Clean up any orphaned persistent volumes
echo ""
echo "🧹 Checking for orphaned persistent volumes..."
orphaned_pvs=$(kubectl get pv --no-headers 2>/dev/null | grep "noctipede" | awk '{print $1}' || true)
if [[ -n "$orphaned_pvs" ]]; then
    print_warning "Found orphaned persistent volumes:"
    echo "$orphaned_pvs"
    echo ""
    read -p "Delete orphaned persistent volumes? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "$orphaned_pvs" | xargs kubectl delete pv --ignore-not-found=true 2>/dev/null || true
        print_status "Orphaned persistent volumes deleted"
    else
        print_info "Orphaned persistent volumes left intact"
    fi
else
    print_status "No orphaned persistent volumes found"
fi

# Step 12: Verify destruction
echo ""
echo "🔍 Verifying destruction..."
if kubectl get namespace noctipede &> /dev/null; then
    print_warning "Namespace still exists (may be in terminating state)"
    kubectl get namespace noctipede
else
    print_status "Namespace successfully removed"
fi

# Check for any remaining resources
remaining_resources=$(kubectl api-resources --verbs=list --namespaced -o name | xargs -n 1 kubectl get --show-kind --ignore-not-found -n noctipede 2>/dev/null | grep -v "No resources found" || true)
if [[ -n "$remaining_resources" ]]; then
    print_warning "Some resources may still exist:"
    echo "$remaining_resources"
else
    print_status "All resources successfully removed"
fi

echo ""
echo "🎉 DESTRUCTION COMPLETED!"
echo "========================"
echo ""
print_status "Noctipede has been completely removed from the cluster"
echo ""
echo "📋 WHAT WAS REMOVED:"
echo "==================="
echo "✅ All applications and services"
echo "✅ All databases and stored data"
echo "✅ All persistent volumes and claims"
echo "✅ All configuration and secrets"
echo "✅ All network policies and ingress rules"
echo "✅ The noctipede namespace"
echo ""
echo "🔧 USEFUL COMMANDS:"
echo "=================="
echo "• Verify removal: kubectl get all -n noctipede"
echo "• Check PVs: kubectl get pv | grep noctipede"
echo "• Redeploy: ./deploy.sh"
echo ""
print_info "Destruction script completed successfully!"
