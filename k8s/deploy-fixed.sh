#!/usr/bin/env bash

# Noctipede Kubernetes Deployment Script - FIXED VERSION
# This script deploys the complete Noctipede system with proper error handling

set -e

echo "🚀 Starting Noctipede Kubernetes Deployment (Fixed Version)"

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
    
    # Step 6: Wait for Tor proxy (required) but be lenient with I2P
    print_status "Waiting for proxy services..."
    wait_for_deployment "tor-proxy" "noctipede" 180
    
    # Check I2P but don't fail if it's not ready
    print_status "Checking I2P proxy status (non-blocking)..."
    if kubectl get deployment i2p-proxy -n noctipede >/dev/null 2>&1; then
        local i2p_ready=$(kubectl get deployment i2p-proxy -n noctipede -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        if [ "$i2p_ready" = "1" ]; then
            print_success "I2P proxy is ready"
        else
            print_warning "I2P proxy is still bootstrapping (this can take 10+ minutes)"
            print_warning "Continuing deployment - I2P will be available when ready"
        fi
    fi
    
    # Step 7: Deploy Noctipede applications (FIXED - ensure this actually happens)
    print_status "Deploying Noctipede applications..."
    
    # Apply PVCs first
    kubectl apply -f noctipede/pvc.yaml
    print_success "PVCs created"
    
    # Apply deployments
    kubectl apply -f noctipede/deployment.yaml
    print_success "Deployments created"
    
    # Apply services
    kubectl apply -f noctipede/service.yaml
    print_success "Services created"
    
    # Apply cronjob
    kubectl apply -f noctipede/cronjob-fixed.yaml
    print_success "CronJob created"
    
    # Apply ingress
    kubectl apply -f noctipede/ingress-final.yaml 2>/dev/null || {
        print_warning "Ingress creation had warnings (middleware not supported)"
        print_status "Creating simple ingress instead..."
        kubectl apply -f noctipede/ingress-fixed.yaml 2>/dev/null || true
    }
    
    print_success "Noctipede applications deployed"
    
    # Step 8: Wait for applications (with reasonable timeouts)
    print_status "Waiting for Noctipede applications..."
    
    # Wait for portal first (it's more critical)
    if wait_for_deployment "noctipede-portal" "noctipede" 300; then
        print_success "Portal is ready!"
    else
        print_warning "Portal deployment taking longer than expected"
        print_status "Checking portal pod status..."
        kubectl describe pods -l app=noctipede-portal -n noctipede | tail -10
    fi
    
    # Check app deployment (it might take longer due to init containers)
    print_status "Checking noctipede-app status..."
    local app_ready=$(kubectl get deployment noctipede-app -n noctipede -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    if [ "$app_ready" = "1" ]; then
        print_success "Noctipede app is ready!"
    else
        print_warning "Noctipede app is still initializing (init containers may be waiting for proxies)"
        print_status "This is normal - the app will start once proxy health checks complete"
    fi
    
    print_success "🎉 Noctipede deployment completed!"
    
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
    
    # Get NodePort for portal service
    local nodeport=$(kubectl get service noctipede-portal-service -n noctipede -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")
    
    if [ -n "$nodeport" ]; then
        echo "  🌐 NodePort Access: http://10.1.1.12:$nodeport"
        echo "  🌐 Alternative IPs: http://10.1.1.13:$nodeport or http://10.1.1.14:$nodeport"
    fi
    
    # Check for ingress
    if kubectl get ingress -n noctipede >/dev/null 2>&1; then
        echo "  🌐 Ingress Access: http://10.1.1.12/ (via Traefik)"
        echo "  🌐 Hostname Access: http://noctipede.local (add to /etc/hosts)"
    fi
    
    echo ""
    print_status "Proxy Services:"
    echo "  🧅 Tor Proxy: tor-proxy.noctipede:9150 (SOCKS5)"
    echo "  🌐 I2P Proxy: i2p-proxy.noctipede:4444 (HTTP)"
    echo "  📊 I2P Console: i2p-proxy.noctipede:7070"
    
    echo ""
    print_success "Deployment completed! 🚀"
    
    # Final health check
    echo ""
    print_status "=== Quick Health Check ==="
    
    # Test portal health
    local portal_pod=$(kubectl get pods -l app=noctipede-portal -n noctipede -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ -n "$portal_pod" ]; then
        if kubectl get pod "$portal_pod" -n noctipede -o jsonpath='{.status.phase}' 2>/dev/null | grep -q "Running"; then
            print_success "✅ Portal pod is running"
            # Test health endpoint if possible
            if [ -n "$nodeport" ]; then
                if curl -s --connect-timeout 5 "http://10.1.1.12:$nodeport/api/health" >/dev/null 2>&1; then
                    print_success "✅ Portal health endpoint responding"
                else
                    print_warning "⏳ Portal health endpoint not ready yet"
                fi
            fi
        else
            print_warning "⏳ Portal pod still starting"
        fi
    fi
}

# Run the deployment
deploy_noctipede
