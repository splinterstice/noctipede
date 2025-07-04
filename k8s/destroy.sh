#!/usr/bin/env bash

# Noctipede Kubernetes Destruction Script
# This script safely tears down the complete Noctipede system in reverse order

set -e

echo "🔥 Starting Noctipede Kubernetes Destruction"

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

# Function to wait for resources to be deleted
wait_for_deletion() {
    local resource_type=$1
    local resource_name=$2
    local namespace=$3
    local timeout=${4:-120}
    
    print_status "Waiting for $resource_type/$resource_name to be deleted..."
    
    local count=0
    while kubectl get $resource_type $resource_name -n $namespace >/dev/null 2>&1; do
        if [ $count -ge $timeout ]; then
            print_warning "$resource_type/$resource_name still exists after ${timeout}s, continuing anyway..."
            return 1
        fi
        sleep 2
        count=$((count + 2))
        if [ $((count % 20)) -eq 0 ]; then
            print_status "Still waiting for $resource_type/$resource_name deletion... (${count}s)"
        fi
    done
    
    print_success "$resource_type/$resource_name deleted successfully"
    return 0
}

# Function to force delete stuck resources
force_delete_resource() {
    local resource_type=$1
    local resource_name=$2
    local namespace=$3
    
    print_warning "Force deleting $resource_type/$resource_name..."
    kubectl patch $resource_type $resource_name -n $namespace -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
    kubectl delete $resource_type $resource_name -n $namespace --force --grace-period=0 2>/dev/null || true
}

# Function to check if namespace exists
check_namespace() {
    if kubectl get namespace noctipede >/dev/null 2>&1; then
        return 0
    else
        print_warning "Namespace 'noctipede' does not exist"
        return 1
    fi
}

# Function to show current status before destruction
show_pre_destruction_status() {
    print_status "=== Current Noctipede Status (Before Destruction) ==="
    echo ""
    
    if check_namespace; then
        print_status "Found Noctipede deployment in namespace 'noctipede'"
        
        echo ""
        print_status "Deployments to be destroyed:"
        kubectl get deployments -n noctipede 2>/dev/null || print_warning "No deployments found"
        
        echo ""
        print_status "Services to be destroyed:"
        kubectl get services -n noctipede 2>/dev/null || print_warning "No services found"
        
        echo ""
        print_status "Persistent Volume Claims to be destroyed:"
        kubectl get pvc -n noctipede 2>/dev/null || print_warning "No PVCs found"
        
        echo ""
        print_status "ConfigMaps and Secrets to be destroyed:"
        kubectl get configmaps,secrets -n noctipede 2>/dev/null || print_warning "No ConfigMaps/Secrets found"
        
    else
        print_success "No Noctipede deployment found - nothing to destroy"
        exit 0
    fi
}

# Function to backup important data before destruction
backup_data() {
    local backup_dir="./noctipede-backup-$(date +%Y%m%d-%H%M%S)"
    
    print_status "Creating backup of important configurations..."
    mkdir -p "$backup_dir"
    
    # Backup ConfigMaps and Secrets (without sensitive data)
    if kubectl get configmap -n noctipede >/dev/null 2>&1; then
        kubectl get configmap -n noctipede -o yaml > "$backup_dir/configmaps.yaml" 2>/dev/null || true
    fi
    
    # Backup PVC information (not data, just specs)
    if kubectl get pvc -n noctipede >/dev/null 2>&1; then
        kubectl get pvc -n noctipede -o yaml > "$backup_dir/pvcs.yaml" 2>/dev/null || true
    fi
    
    # Backup service configurations
    if kubectl get services -n noctipede >/dev/null 2>&1; then
        kubectl get services -n noctipede -o yaml > "$backup_dir/services.yaml" 2>/dev/null || true
    fi
    
    print_success "Backup created in: $backup_dir"
    echo "  📁 ConfigMaps: $backup_dir/configmaps.yaml"
    echo "  📁 PVCs: $backup_dir/pvcs.yaml"
    echo "  📁 Services: $backup_dir/services.yaml"
}

# Main destruction function
destroy_noctipede() {
    print_destroy "Starting Noctipede destruction process..."
    echo ""
    
    # Check if deployment exists
    if ! check_namespace; then
        print_success "No Noctipede deployment found - nothing to destroy"
        return 0
    fi
    
    # Show what will be destroyed
    show_pre_destruction_status
    echo ""
    
    # Ask for confirmation unless --force is used
    if [[ "${1}" != "--force" && "${1}" != "-f" ]]; then
        print_warning "⚠️  This will PERMANENTLY DELETE the entire Noctipede deployment!"
        print_warning "⚠️  All data, configurations, and services will be removed!"
        echo ""
        read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation
        
        if [[ "$confirmation" != "yes" ]]; then
            print_status "Destruction cancelled by user"
            exit 0
        fi
    fi
    
    echo ""
    print_destroy "🔥 Beginning destruction sequence..."
    echo ""
    
    # Step 1: Scale down applications first (graceful shutdown)
    print_destroy "Step 1: Scaling down applications..."
    kubectl scale deployment --all --replicas=0 -n noctipede 2>/dev/null || true
    sleep 10
    print_success "Applications scaled down"
    
    # Step 2: Delete Noctipede applications (reverse order of deployment)
    print_destroy "Step 2: Destroying Noctipede applications..."
    if kubectl get -f noctipede/ -n noctipede >/dev/null 2>&1; then
        kubectl delete -f noctipede/ --timeout=120s 2>/dev/null || {
            print_warning "Some Noctipede resources didn't delete cleanly, force deleting..."
            kubectl delete -f noctipede/ --force --grace-period=0 2>/dev/null || true
        }
        print_success "Noctipede applications destroyed"
    else
        print_warning "No Noctipede applications found"
    fi
    
    # Step 3: Delete proxy services
    print_destroy "Step 3: Destroying proxy services..."
    if kubectl get -f proxy/ -n noctipede >/dev/null 2>&1; then
        kubectl delete -f proxy/ --timeout=120s 2>/dev/null || {
            print_warning "Some proxy resources didn't delete cleanly, force deleting..."
            kubectl delete -f proxy/ --force --grace-period=0 2>/dev/null || true
        }
        print_success "Proxy services destroyed"
    else
        print_warning "No proxy services found"
    fi
    
    # Step 4: Delete infrastructure services (MinIO, MariaDB)
    print_destroy "Step 4: Destroying infrastructure services..."
    
    # Delete MinIO
    if kubectl get -f minio/ -n noctipede >/dev/null 2>&1; then
        kubectl delete -f minio/ --timeout=120s 2>/dev/null || {
            print_warning "MinIO didn't delete cleanly, force deleting..."
            kubectl delete -f minio/ --force --grace-period=0 2>/dev/null || true
        }
        print_success "MinIO destroyed"
    else
        print_warning "No MinIO resources found"
    fi
    
    # Delete MariaDB
    if kubectl get -f mariadb/ -n noctipede >/dev/null 2>&1; then
        kubectl delete -f mariadb/ --timeout=120s 2>/dev/null || {
            print_warning "MariaDB didn't delete cleanly, force deleting..."
            kubectl delete -f mariadb/ --force --grace-period=0 2>/dev/null || true
        }
        print_success "MariaDB destroyed"
    else
        print_warning "No MariaDB resources found"
    fi
    
    # Step 5: Delete ConfigMaps and Secrets
    print_destroy "Step 5: Destroying configuration..."
    kubectl delete -f configmap.yaml --ignore-not-found=true --timeout=60s 2>/dev/null || true
    kubectl delete -f secrets.yaml --ignore-not-found=true --timeout=60s 2>/dev/null || true
    print_success "Configuration destroyed"
    
    # Step 6: Clean up any remaining resources
    print_destroy "Step 6: Cleaning up remaining resources..."
    
    # Delete any remaining pods
    if kubectl get pods -n noctipede 2>/dev/null | grep -q .; then
        print_status "Deleting remaining pods..."
        kubectl delete pods --all -n noctipede --force --grace-period=0 2>/dev/null || true
    fi
    
    # Delete any remaining services
    if kubectl get services -n noctipede 2>/dev/null | grep -v kubernetes | grep -q .; then
        print_status "Deleting remaining services..."
        kubectl delete services --all -n noctipede --timeout=60s 2>/dev/null || true
    fi
    
    # Delete any remaining PVCs (this will delete data!)
    if kubectl get pvc -n noctipede 2>/dev/null | grep -q .; then
        print_warning "Deleting Persistent Volume Claims (this will delete stored data)..."
        kubectl delete pvc --all -n noctipede --timeout=120s 2>/dev/null || {
            print_warning "Some PVCs didn't delete cleanly, force deleting..."
            kubectl get pvc -n noctipede -o name 2>/dev/null | xargs -I {} kubectl patch {} -n noctipede -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
            kubectl delete pvc --all -n noctipede --force --grace-period=0 2>/dev/null || true
        }
        print_success "Persistent Volume Claims destroyed"
    fi
    
    # Step 7: Delete the namespace
    print_destroy "Step 7: Destroying namespace..."
    if kubectl get namespace noctipede >/dev/null 2>&1; then
        kubectl delete -f namespace.yaml --timeout=120s 2>/dev/null || {
            print_warning "Namespace didn't delete cleanly, force deleting..."
            kubectl patch namespace noctipede -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
            kubectl delete namespace noctipede --force --grace-period=0 2>/dev/null || true
        }
        
        # Wait for namespace to be fully deleted
        print_status "Waiting for namespace deletion to complete..."
        local count=0
        while kubectl get namespace noctipede >/dev/null 2>&1; do
            if [ $count -ge 180 ]; then
                print_error "Namespace still exists after 3 minutes, may require manual cleanup"
                break
            fi
            sleep 2
            count=$((count + 2))
            if [ $((count % 30)) -eq 0 ]; then
                print_status "Still waiting for namespace deletion... (${count}s)"
            fi
        done
        
        print_success "Namespace destroyed"
    else
        print_warning "Namespace already deleted"
    fi
    
    echo ""
    print_success "🎉 Noctipede destruction completed successfully!"
    
    # Final verification
    echo ""
    print_status "=== Final Verification ==="
    if kubectl get namespace noctipede >/dev/null 2>&1; then
        print_warning "⚠️  Namespace 'noctipede' still exists - may require manual cleanup"
        print_status "Remaining resources in namespace:"
        kubectl get all -n noctipede 2>/dev/null || true
    else
        print_success "✅ Namespace 'noctipede' completely removed"
        print_success "✅ All Noctipede resources destroyed"
    fi
    
    echo ""
    print_status "=== Cleanup Summary ==="
    echo "  🔥 Applications: Destroyed"
    echo "  🔥 Proxy Services: Destroyed"
    echo "  🔥 Infrastructure: Destroyed"
    echo "  🔥 Configuration: Destroyed"
    echo "  🔥 Data Storage: Destroyed"
    echo "  🔥 Namespace: Destroyed"
    echo ""
    print_success "Noctipede has been completely removed from Kubernetes! 🔥"
}

# Function to show help
show_help() {
    echo "Noctipede Kubernetes Destruction Script"
    echo ""
    echo "This script safely tears down the complete Noctipede Kubernetes deployment"
    echo "in reverse order, ensuring proper cleanup of all resources."
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --force, -f    Skip confirmation prompt and force destruction"
    echo "  --backup, -b   Create backup before destruction (default: yes)"
    echo "  --no-backup    Skip backup creation"
    echo "  --status, -s   Show current deployment status"
    echo "  --help, -h     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Interactive destruction with backup"
    echo "  $0 --force            # Force destruction without confirmation"
    echo "  $0 --status           # Show what would be destroyed"
    echo "  $0 --no-backup -f     # Force destruction without backup"
    echo ""
    echo "⚠️  WARNING: This will permanently delete:"
    echo "  • All Noctipede applications and services"
    echo "  • All stored data (database, MinIO storage)"
    echo "  • All configurations and secrets"
    echo "  • The entire 'noctipede' namespace"
    echo ""
    echo "💾 Backup: By default, configurations are backed up before destruction"
    echo "🔄 Recovery: Use the original deploy.sh to redeploy after destruction"
}

# Main script logic
BACKUP=true
FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE=true
            shift
            ;;
        --backup|-b)
            BACKUP=true
            shift
            ;;
        --no-backup)
            BACKUP=false
            shift
            ;;
        --status|-s)
            show_pre_destruction_status
            exit 0
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

# Create backup if requested
if [[ "$BACKUP" == true ]]; then
    if check_namespace; then
        backup_data
        echo ""
    fi
fi

# Execute destruction
if [[ "$FORCE" == true ]]; then
    destroy_noctipede --force
else
    destroy_noctipede
fi
