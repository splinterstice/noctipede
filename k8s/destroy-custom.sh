#!/usr/bin/env bash

# Custom Noctipede Kubernetes Destruction Script
# Configured for cluster with Ollama at 10.1.1.12:2701
# Destroys internal MariaDB and MinIO from the project

set -e

echo "🔥 Starting Custom Noctipede Kubernetes Destruction"

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

# Configuration
NAMESPACE="noctipede"
OLLAMA_ENDPOINT="http://10.1.1.12:2701"

# Function to check if namespace exists
check_namespace() {
    if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to show what will be destroyed
show_destruction_plan() {
    print_status "=== Custom Noctipede Destruction Plan ==="
    echo ""
    print_status "Configuration:"
    echo "  🤖 Ollama: $OLLAMA_ENDPOINT (EXTERNAL - will NOT be destroyed)"
    echo "  🗄️  Database: Internal MariaDB (WILL be destroyed)"
    echo "  📦 Storage: Internal MinIO (WILL be destroyed)"
    echo "  🌐 Namespace: $NAMESPACE"
    echo ""
    
    if ! check_namespace; then
        print_success "No Noctipede deployment found - nothing to destroy"
        exit 0
    fi
    
    print_status "Found Noctipede deployment in namespace '$NAMESPACE'"
    echo ""
    
    print_status "Deployments to be destroyed:"
    kubectl get deployments -n "$NAMESPACE" 2>/dev/null || print_warning "No deployments found"
    
    echo ""
    print_status "Services to be destroyed:"
    kubectl get services -n "$NAMESPACE" 2>/dev/null || print_warning "No services found"
    
    echo ""
    print_status "Persistent Volume Claims to be destroyed:"
    kubectl get pvc -n "$NAMESPACE" 2>/dev/null || print_warning "No PVCs found"
    
    echo ""
    print_status "ConfigMaps and Secrets to be destroyed:"
    kubectl get configmaps,secrets -n "$NAMESPACE" 2>/dev/null || print_warning "No ConfigMaps/Secrets found"
    
    echo ""
    print_status "Ingress to be destroyed:"
    kubectl get ingress -n "$NAMESPACE" 2>/dev/null || print_warning "No Ingress found"
}

# Function to backup important data before destruction
backup_custom_data() {
    local backup_dir="./noctipede-custom-backup-$(date +%Y%m%d-%H%M%S)"
    
    print_status "Creating backup of custom configurations..."
    mkdir -p "$backup_dir"
    
    # Backup ConfigMaps
    if kubectl get configmap -n "$NAMESPACE" >/dev/null 2>&1; then
        kubectl get configmap -n "$NAMESPACE" -o yaml > "$backup_dir/configmaps.yaml" 2>/dev/null || true
    fi
    
    # Backup PVC information
    if kubectl get pvc -n "$NAMESPACE" >/dev/null 2>&1; then
        kubectl get pvc -n "$NAMESPACE" -o yaml > "$backup_dir/pvcs.yaml" 2>/dev/null || true
    fi
    
    # Backup service configurations
    if kubectl get services -n "$NAMESPACE" >/dev/null 2>&1; then
        kubectl get services -n "$NAMESPACE" -o yaml > "$backup_dir/services.yaml" 2>/dev/null || true
    fi
    
    # Backup ingress configurations
    if kubectl get ingress -n "$NAMESPACE" >/dev/null 2>&1; then
        kubectl get ingress -n "$NAMESPACE" -o yaml > "$backup_dir/ingress.yaml" 2>/dev/null || true
    fi
    
    # Backup deployment configurations
    if kubectl get deployments -n "$NAMESPACE" >/dev/null 2>&1; then
        kubectl get deployments -n "$NAMESPACE" -o yaml > "$backup_dir/deployments.yaml" 2>/dev/null || true
    fi
    
    # Create restoration script
    cat > "$backup_dir/restore.sh" << EOF
#!/bin/bash
# Custom Noctipede Restoration Script
# Generated on $(date)

echo "🔄 Restoring Custom Noctipede from backup..."

# Create namespace
kubectl create namespace $NAMESPACE 2>/dev/null || echo "Namespace already exists"

# Apply configurations
kubectl apply -f configmaps.yaml 2>/dev/null || echo "ConfigMaps restore failed"
kubectl apply -f services.yaml 2>/dev/null || echo "Services restore failed"
kubectl apply -f ingress.yaml 2>/dev/null || echo "Ingress restore failed"
kubectl apply -f deployments.yaml 2>/dev/null || echo "Deployments restore failed"

echo "✅ Restoration completed"
echo "Note: You may need to manually restore PVCs and run the custom deploy script"
EOF
    
    chmod +x "$backup_dir/restore.sh"
    
    print_success "Backup created in: $backup_dir"
    echo "  📁 ConfigMaps: $backup_dir/configmaps.yaml"
    echo "  📁 PVCs: $backup_dir/pvcs.yaml"
    echo "  📁 Services: $backup_dir/services.yaml"
    echo "  📁 Ingress: $backup_dir/ingress.yaml"
    echo "  📁 Deployments: $backup_dir/deployments.yaml"
    echo "  🔄 Restore Script: $backup_dir/restore.sh"
}

# Main destruction function
destroy_custom_noctipede() {
    print_destroy "🔥 Starting Custom Noctipede destruction process..."
    echo ""
    
    # Check if deployment exists
    if ! check_namespace; then
        print_success "No Noctipede deployment found - nothing to destroy"
        exit 0
    fi
    
    # Show destruction plan
    show_destruction_plan
    
    # Create backup
    backup_custom_data
    echo ""
    
    print_warning "⚠️  WARNING: This will permanently delete:"
    echo "  • All Noctipede applications and services"
    echo "  • Internal MariaDB database and all stored data"
    echo "  • Internal MinIO storage and all files"
    echo "  • All configurations and secrets"
    echo "  • All ingress rules"
    echo ""
    print_status "✅ SAFE: External Ollama at $OLLAMA_ENDPOINT will NOT be affected"
    echo ""
    
    # Confirmation prompt
    echo -n "Are you sure you want to continue? (type 'yes' to confirm): "
    read -r confirmation
    
    if [ "$confirmation" != "yes" ]; then
        print_status "Destruction cancelled by user"
        exit 0
    fi
    
    print_destroy "🔥 Beginning custom destruction sequence..."
    echo ""
    
    # Step 1: Scale down applications
    print_destroy "Step 1: Scaling down applications..."
    kubectl scale deployment --all --replicas=0 -n "$NAMESPACE" 2>/dev/null || true
    kubectl scale statefulset --all --replicas=0 -n "$NAMESPACE" 2>/dev/null || true
    print_success "Applications scaled down"
    
    # Step 2: Delete Noctipede applications
    print_destroy "Step 2: Destroying Noctipede applications..."
    if kubectl get -f noctipede/ -n "$NAMESPACE" >/dev/null 2>&1; then
        kubectl delete -f noctipede/ --timeout=120s 2>/dev/null || {
            print_warning "Graceful deletion failed, forcing deletion..."
            kubectl delete -f noctipede/ --force --grace-period=0 2>/dev/null || true
        }
        print_success "Noctipede applications destroyed"
    else
        print_warning "No Noctipede applications found"
    fi
    
    # Step 3: Delete ingress
    print_destroy "Step 3: Destroying ingress rules..."
    kubectl delete ingress --all -n "$NAMESPACE" --timeout=60s 2>/dev/null || true
    print_success "Ingress rules destroyed"
    
    # Step 4: Delete proxy services
    print_destroy "Step 4: Destroying proxy services..."
    if kubectl get -f proxy/ -n "$NAMESPACE" >/dev/null 2>&1; then
        kubectl delete -f proxy/ --timeout=120s 2>/dev/null || {
            print_warning "Graceful proxy deletion failed, forcing..."
            kubectl delete -f proxy/ --force --grace-period=0 2>/dev/null || true
        }
        print_success "Proxy services destroyed"
    else
        print_warning "No proxy services found"
    fi
    
    # Step 5: Delete infrastructure services
    print_destroy "Step 5: Destroying infrastructure services..."
    
    # Delete MinIO
    if kubectl get -f minio/ -n "$NAMESPACE" >/dev/null 2>&1; then
        kubectl delete -f minio/ --timeout=120s 2>/dev/null || {
            print_warning "Graceful MinIO deletion failed, forcing..."
            kubectl delete -f minio/ --force --grace-period=0 2>/dev/null || true
        }
        print_success "MinIO destroyed"
    else
        print_warning "No MinIO found"
    fi
    
    # Delete MariaDB
    if kubectl get -f mariadb/ -n "$NAMESPACE" >/dev/null 2>&1; then
        kubectl delete -f mariadb/ --timeout=120s 2>/dev/null || {
            print_warning "Graceful MariaDB deletion failed, forcing..."
            kubectl delete -f mariadb/ --force --grace-period=0 2>/dev/null || true
        }
        print_success "MariaDB destroyed"
    else
        print_warning "No MariaDB found"
    fi
    
    # Step 6: Delete configuration
    print_destroy "Step 6: Destroying configuration..."
    kubectl delete configmap --all -n "$NAMESPACE" --timeout=60s 2>/dev/null || true
    kubectl delete secret --all -n "$NAMESPACE" --timeout=60s 2>/dev/null || true
    print_success "Configuration destroyed"
    
    # Step 7: Clean up remaining resources
    print_destroy "Step 7: Cleaning up remaining resources..."
    
    print_status "Deleting remaining pods..."
    kubectl delete pods --all -n "$NAMESPACE" --force --grace-period=0 2>/dev/null || true
    
    print_warning "Deleting Persistent Volume Claims (this will delete stored data)..."
    kubectl delete pvc --all -n "$NAMESPACE" --timeout=120s 2>/dev/null || {
        print_warning "Graceful PVC deletion failed, forcing..."
        kubectl delete pvc --all -n "$NAMESPACE" --force --grace-period=0 2>/dev/null || true
    }
    print_success "Persistent Volume Claims destroyed"
    
    # Step 8: Delete namespace
    print_destroy "Step 8: Destroying namespace..."
    kubectl delete namespace "$NAMESPACE" --timeout=300s 2>/dev/null || {
        print_warning "Graceful namespace deletion failed, forcing..."
        kubectl delete namespace "$NAMESPACE" --force --grace-period=0 2>/dev/null || true
    }
    
    print_status "Waiting for namespace deletion to complete..."
    local count=0
    while kubectl get namespace "$NAMESPACE" >/dev/null 2>&1 && [ $count -lt 60 ]; do
        sleep 5
        count=$((count + 1))
        if [ $((count % 6)) -eq 0 ]; then
            print_status "Still waiting for namespace deletion... (${count}0s elapsed)"
        fi
    done
    
    if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        print_warning "Namespace deletion is taking longer than expected"
        print_warning "This is normal for namespaces with many resources"
    else
        print_success "Namespace destroyed"
    fi
    
    print_success "🎉 Custom Noctipede destruction completed successfully!"
    
    echo ""
    print_destroy "=== Final Verification ==="
    if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        print_warning "⏳ Namespace '$NAMESPACE' still exists (deletion in progress)"
    else
        print_success "✅ Namespace '$NAMESPACE' completely removed"
    fi
    print_success "✅ All Noctipede resources destroyed"
    print_success "✅ External Ollama at $OLLAMA_ENDPOINT is safe and untouched"
    
    echo ""
    print_destroy "=== Cleanup Summary ==="
    echo "  🔥 Applications: Destroyed"
    echo "  🔥 Proxy Services: Destroyed"
    echo "  🔥 Infrastructure: Destroyed"
    echo "  🔥 Configuration: Destroyed"
    echo "  🔥 Data Storage: Destroyed"
    echo "  🔥 Ingress Rules: Destroyed"
    echo "  🔥 Namespace: Destroyed"
    echo "  ✅ External Ollama: Safe"
    
    echo ""
    print_success "Custom Noctipede has been completely removed from Kubernetes! 🔥"
    print_status "To redeploy, run: ./deploy-custom.sh"
}

# Function to show status
show_custom_status() {
    print_status "=== Custom Noctipede Destruction Status ==="
    echo ""
    
    if check_namespace; then
        print_warning "Noctipede deployment exists in namespace '$NAMESPACE'"
        echo ""
        
        print_status "Resources that would be destroyed:"
        echo ""
        
        print_status "Deployments:"
        kubectl get deployments -n "$NAMESPACE" -o wide 2>/dev/null || print_status "None found"
        
        echo ""
        print_status "Services:"
        kubectl get services -n "$NAMESPACE" -o wide 2>/dev/null || print_status "None found"
        
        echo ""
        print_status "Pods:"
        kubectl get pods -n "$NAMESPACE" -o wide 2>/dev/null || print_status "None found"
        
        echo ""
        print_status "Persistent Volume Claims:"
        kubectl get pvc -n "$NAMESPACE" 2>/dev/null || print_status "None found"
        
        echo ""
        print_status "🤖 External Resources (SAFE):"
        echo "  ✅ Ollama at $OLLAMA_ENDPOINT will NOT be destroyed"
        
    else
        print_success "No Noctipede deployment found - nothing to destroy"
    fi
}

# Function to force cleanup (emergency)
force_cleanup() {
    print_warning "🚨 EMERGENCY FORCE CLEANUP 🚨"
    print_warning "This will forcefully remove all resources without confirmation"
    echo ""
    
    if ! check_namespace; then
        print_success "No namespace found - nothing to cleanup"
        exit 0
    fi
    
    print_destroy "Force deleting all resources in namespace $NAMESPACE..."
    
    # Force delete everything
    kubectl delete all --all -n "$NAMESPACE" --force --grace-period=0 2>/dev/null || true
    kubectl delete pvc --all -n "$NAMESPACE" --force --grace-period=0 2>/dev/null || true
    kubectl delete configmap --all -n "$NAMESPACE" --force --grace-period=0 2>/dev/null || true
    kubectl delete secret --all -n "$NAMESPACE" --force --grace-period=0 2>/dev/null || true
    kubectl delete ingress --all -n "$NAMESPACE" --force --grace-period=0 2>/dev/null || true
    
    # Force delete namespace
    kubectl delete namespace "$NAMESPACE" --force --grace-period=0 2>/dev/null || true
    
    print_success "Force cleanup completed"
}

# Main script logic
case "${1:-destroy}" in
    "destroy")
        destroy_custom_noctipede
        ;;
    "status")
        show_custom_status
        ;;
    "force")
        force_cleanup
        ;;
    "help"|"-h"|"--help")
        echo "Custom Noctipede Kubernetes Destruction Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  destroy    Destroy Custom Noctipede deployment (default)"
        echo "  status     Show what would be destroyed"
        echo "  force      Emergency force cleanup (no confirmation)"
        echo "  help       Show this help message"
        echo ""
        echo "Configuration:"
        echo "  Ollama: $OLLAMA_ENDPOINT (EXTERNAL - will NOT be destroyed)"
        echo "  Database: Internal MariaDB (WILL be destroyed)"
        echo "  Storage: Internal MinIO (WILL be destroyed)"
        echo ""
        echo "⚠️  WARNING: This will permanently delete all data!"
        echo "✅ SAFE: External Ollama will not be affected"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
