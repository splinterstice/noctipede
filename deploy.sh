#!/bin/bash

# Noctipede Kubernetes Deployment Script

set -e

echo "🚀 Deploying Noctipede to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster"
    exit 1
fi

echo "✅ Kubernetes cluster connection verified"

# Create namespace
echo "📦 Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Apply secrets
echo "🔐 Applying secrets..."
kubectl apply -f k8s/secrets.yaml

# Apply configmap
echo "⚙️  Applying configuration..."
kubectl apply -f k8s/configmap.yaml

# Deploy MariaDB
echo "🗄️  Deploying MariaDB..."
kubectl apply -f k8s/mariadb/

# Wait for MariaDB to be ready
echo "⏳ Waiting for MariaDB to be ready..."
kubectl wait --for=condition=Ready mariadb/mariadb -n noctipede --timeout=300s

# Deploy MinIO
echo "📦 Deploying MinIO..."
kubectl apply -f k8s/minio/

# Wait for MinIO to be ready
echo "⏳ Waiting for MinIO to be ready..."
kubectl wait --for=condition=Ready tenant/minio-crawler -n noctipede --timeout=300s

# Create MinIO bucket
echo "🪣 Creating MinIO bucket..."
kubectl apply -f k8s/minio/bucket-job.yaml

# Deploy PVCs
echo "💾 Creating Persistent Volume Claims..."
kubectl apply -f k8s/noctipede/pvc.yaml

# Deploy Noctipede application
echo "🕷️  Deploying Noctipede application..."
kubectl apply -f k8s/noctipede/deployment.yaml

# Deploy services
echo "🌐 Creating services..."
kubectl apply -f k8s/noctipede/service.yaml

# Wait for deployments to be ready
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=Available deployment/noctipede-app -n noctipede --timeout=300s
kubectl wait --for=condition=Available deployment/noctipede-web -n noctipede --timeout=300s

echo "✅ Deployment completed successfully!"

# Show status
echo ""
echo "📊 Deployment Status:"
kubectl get pods -n noctipede
echo ""
kubectl get services -n noctipede

echo ""
echo "🎉 Noctipede has been deployed to Kubernetes!"
echo ""
echo "To access the web interface:"
echo "  kubectl port-forward service/noctipede-web-service 8080:8080 -n noctipede"
echo "  Then open http://localhost:8080"
echo ""
echo "To check logs:"
echo "  kubectl logs -f deployment/noctipede-app -n noctipede"
echo "  kubectl logs -f deployment/noctipede-web -n noctipede"
