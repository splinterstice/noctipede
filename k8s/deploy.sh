#!/usr/bin/env bash

# Noctipede Kubernetes Deployment Script
# This script deploys the complete Noctipede system with proxy services

set -e

echo "🚀 Starting Noctipede Kubernetes Deployment"

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

# Function to wait for deployment to be ready
wait_for_deployment() {
    local deployment=$1
    local namespace=$2
    local timeout=${3:-300}
    
    print_status "Waiting for deployment $deployment to be ready..."
    if kubectl wait --for=condition=available --timeout=${timeout}s deployment/$deployment -n $namespace; then
        print_success "Deployment $deployment is ready"
        return 0
    else
        print_error "Deployment $deployment failed to become ready within ${timeout}s"
        return 1
    fi
}

# Function to wait for I2P proxy with detailed status
wait_for_i2p_proxy() {
    local namespace=$1
    local timeout=${2:-600}
    
    print_status "Waiting for I2P proxy to be healthy (up to $((timeout/60)) minutes)..."
    
    local count=0
    local last_status=""
    
    while [ $count -lt $timeout ]; do
        # Check pod status
        local pod_status=$(kubectl get pods -n $namespace -l app=i2p-proxy -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")
        local ready_status=$(kubectl get pods -n $namespace -l app=i2p-proxy -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
        
        if [ "$ready_status" = "True" ]; then
            print_success "I2P proxy is ready and healthy"
            return 0
        fi
        
        # Provide status updates every 30 seconds
        if [ $((count % 30)) -eq 0 ]; then
            local current_status="Pod: $pod_status, Ready: $ready_status"
            if [ "$current_status" != "$last_status" ]; then
                print_status "I2P status: $current_status (${count}s elapsed, $((timeout-count))s remaining)"
                last_status="$current_status"
                
                # Show additional details if pod is running but not ready
                if [ "$pod_status" = "Running" ] && [ "$ready_status" != "True" ]; then
                    local pod_name=$(kubectl get pods -n $namespace -l app=i2p-proxy -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
                    if [ -n "$pod_name" ]; then
                        print_status "Checking if I2P HTTP proxy port 4444 is listening..."
                        if kubectl exec -n $namespace "$pod_name" -- netstat -tln 2>/dev/null | grep -q ':4444 '; then
                            print_status "✅ Port 4444 is listening - I2P HTTP proxy is active"
                        else
                            print_status "⏳ Port 4444 not ready yet - I2P still initializing"
                        fi
                    fi
                fi
            fi
        fi
        
        sleep 2
        count=$((count + 2))
    done
    
    print_error "I2P proxy failed to become ready within $((timeout/60)) minutes"
    print_error "Final status - Pod: $pod_status, Ready: $ready_status"
    
    # Show final diagnostics
    local pod_name=$(kubectl get pods -n $namespace -l app=i2p-proxy -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -n "$pod_name" ]; then
        print_error "Pod events:"
        kubectl describe pod -n $namespace "$pod_name" | tail -10
    fi
    
    return 1
}
wait_for_statefulset() {
    local statefulset=$1
    local namespace=$2
    local timeout=${3:-300}
    
    print_status "Waiting for statefulset $statefulset to be ready..."
    
    local count=0
    while [ $count -lt $timeout ]; do
        local ready_replicas=$(kubectl get statefulset $statefulset -n $namespace -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        local desired_replicas=$(kubectl get statefulset $statefulset -n $namespace -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "1")
        
        if [ "$ready_replicas" = "$desired_replicas" ] && [ "$ready_replicas" != "0" ]; then
            print_success "StatefulSet $statefulset is ready ($ready_replicas/$desired_replicas replicas)"
            return 0
        fi
        
        if [ $((count % 30)) -eq 0 ]; then
            print_status "Still waiting for $statefulset... ($ready_replicas/$desired_replicas replicas ready, ${count}s elapsed)"
        fi
        
        sleep 2
        count=$((count + 2))
    done
    
    print_error "StatefulSet $statefulset failed to become ready within ${timeout}s"
    return 1
}

# Function to check if namespace exists
check_namespace() {
    if kubectl get namespace noctipede >/dev/null 2>&1; then
        print_success "Namespace 'noctipede' already exists"
    else
        print_status "Creating namespace 'noctipede'"
        kubectl apply -f namespace.yaml
        print_success "Namespace created"
    fi
}

# Main deployment function
deploy_noctipede() {
    print_status "Starting Noctipede deployment..."
    
    # Step 1: Create namespace
    check_namespace
    
    # Step 2: Apply secrets and config
    print_status "Applying secrets and configuration..."
    kubectl apply -f secrets.yaml
    kubectl apply -f configmap.yaml
    print_success "Secrets and configuration applied"
    
    # Step 3: Deploy infrastructure services (MariaDB, MinIO)
    print_status "Deploying infrastructure services..."
    kubectl apply -f mariadb/
    kubectl apply -f minio/
    print_success "Infrastructure services deployed"
    
    # Step 4: Wait for infrastructure to be ready
    print_status "Waiting for infrastructure services..."
    wait_for_statefulset "mariadb" "noctipede" 300
    wait_for_deployment "minio" "noctipede" 300
    
    # Step 5: Deploy proxy services
    print_status "Deploying proxy services..."
    kubectl apply -f proxy/
    print_success "Proxy services deployed"
    
    # Step 6: Wait for proxy services
    print_status "Waiting for proxy services..."
    wait_for_deployment "tor-proxy" "noctipede" 180
    
    # I2P takes 5-15 minutes to start, wait up to 10 minutes with detailed status
    if wait_for_i2p_proxy "noctipede" 600; then
        print_success "All proxy services are ready"
    else
        print_error "I2P proxy failed to become ready within 10 minutes"
        print_error "This may indicate a configuration issue or resource constraints"
        return 1
    fi
    
    # Step 7: Deploy Noctipede applications
    print_status "Deploying Noctipede applications..."
    kubectl apply -f noctipede/
    print_success "Noctipede applications deployed"
    
    # Step 8: Wait for applications
    print_status "Waiting for Noctipede applications..."
    wait_for_deployment "noctipede-portal" "noctipede" 300
    wait_for_deployment "noctipede-app" "noctipede" 300
    
    print_success "🎉 Noctipede deployment completed successfully!"
    
    # Display access information
    echo ""
    print_status "=== Deployment Summary ==="
    echo ""
    
    # Get service information
    print_status "Services:"
    kubectl get services -n noctipede
    
    echo ""
    print_status "Deployments:"
    kubectl get deployments -n noctipede
    
    echo ""
    print_status "Pods:"
    kubectl get pods -n noctipede
    
    echo ""
    print_success "Access the Noctipede Portal:"
    
    # Try to get LoadBalancer IP
    EXTERNAL_IP=$(kubectl get service noctipede-portal-service -n noctipede -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    if [ -n "$EXTERNAL_IP" ]; then
        echo "  🌐 External URL: http://$EXTERNAL_IP:8080"
    else
        print_warning "LoadBalancer IP not yet assigned. Use port-forward for access:"
        echo "  kubectl port-forward -n noctipede service/noctipede-portal-service 8080:8080"
        echo "  Then access: http://localhost:8080"
    fi
    
    echo ""
    print_status "Proxy Services:"
    echo "  🧅 Tor Proxy: tor-proxy.noctipede:9050 (SOCKS5)"
    echo "  🌐 I2P Proxy: i2p-proxy.noctipede:4444 (HTTP)"
    echo "  📊 I2P Console: i2p-proxy.noctipede:7070"
    
    echo ""
    print_success "Deployment completed! 🚀"
}

# Function to clean up deployment
cleanup_noctipede() {
    print_warning "Cleaning up Noctipede deployment..."
    
    kubectl delete -f noctipede/ --ignore-not-found=true
    kubectl delete -f proxy/ --ignore-not-found=true
    kubectl delete -f minio/ --ignore-not-found=true
    kubectl delete -f mariadb/ --ignore-not-found=true
    kubectl delete -f configmap.yaml --ignore-not-found=true
    kubectl delete -f secrets.yaml --ignore-not-found=true
    kubectl delete -f namespace.yaml --ignore-not-found=true
    
    print_success "Cleanup completed"
}

# Function to show status
show_status() {
    print_status "=== Noctipede Kubernetes Status ==="
    echo ""
    
    if kubectl get namespace noctipede >/dev/null 2>&1; then
        print_status "Namespace: noctipede ✓"
        
        echo ""
        print_status "Deployments:"
        kubectl get deployments -n noctipede -o wide
        
        echo ""
        print_status "Services:"
        kubectl get services -n noctipede -o wide
        
        echo ""
        print_status "Pods:"
        kubectl get pods -n noctipede -o wide
        
        echo ""
        print_status "Persistent Volume Claims:"
        kubectl get pvc -n noctipede
        
    else
        print_warning "Noctipede namespace not found. Run 'deploy' to install."
    fi
}

# Main script logic
case "${1:-deploy}" in
    "deploy")
        deploy_noctipede
        ;;
    "cleanup"|"clean")
        cleanup_noctipede
        ;;
    "status")
        show_status
        ;;
    "help"|"-h"|"--help")
        echo "Noctipede Kubernetes Deployment Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  deploy    Deploy Noctipede to Kubernetes (default)"
        echo "  cleanup   Remove Noctipede from Kubernetes"
        echo "  status    Show deployment status"
        echo "  help      Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 deploy    # Deploy everything"
        echo "  $0 status    # Check status"
        echo "  $0 cleanup   # Remove everything"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
