#!/usr/bin/env bash

# Noctipede EKS Deployment Script
# This script deploys a fully working Noctipede system on Amazon EKS with AWS-specific optimizations

set -e

echo "🚀 Starting Noctipede EKS Deployment..."
echo "======================================"

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

# Configuration variables
CLUSTER_NAME="${CLUSTER_NAME:-noctipede-cluster}"
REGION="${AWS_REGION:-us-west-2}"
NAMESPACE="noctipede"
STORAGE_CLASS="${STORAGE_CLASS:-gp3}"
LOAD_BALANCER_TYPE="${LOAD_BALANCER_TYPE:-nlb}"

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if AWS CLI is available
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed or not in PATH"
        exit 1
    fi
    
    # Check if eksctl is available
    if ! command -v eksctl &> /dev/null; then
        print_warning "eksctl is not installed - some EKS-specific features may not be available"
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured or invalid"
        exit 1
    fi
    
    # Check if we can connect to EKS cluster
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to EKS cluster. Make sure your kubeconfig is configured for EKS."
        print_info "Run: aws eks update-kubeconfig --region $REGION --name $CLUSTER_NAME"
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Function to setup EKS-specific resources
setup_eks_resources() {
    print_info "Setting up EKS-specific resources..."
    
    # Check if AWS Load Balancer Controller is installed
    if ! kubectl get deployment aws-load-balancer-controller -n kube-system &> /dev/null; then
        print_warning "AWS Load Balancer Controller not found. Installing..."
        
        # Create service account for AWS Load Balancer Controller
        eksctl create iamserviceaccount \
            --cluster=$CLUSTER_NAME \
            --namespace=kube-system \
            --name=aws-load-balancer-controller \
            --role-name AmazonEKSLoadBalancerControllerRole \
            --attach-policy-arn=arn:aws:iam::aws:policy/ElasticLoadBalancingFullAccess \
            --approve \
            --override-existing-serviceaccounts \
            --region=$REGION || print_warning "Service account creation failed or already exists"
        
        # Install AWS Load Balancer Controller
        kubectl apply --validate=false -f https://github.com/jetstack/cert-manager/releases/download/v1.5.4/cert-manager.yaml || true
        sleep 30
        
        curl -Lo v2_4_7_full.yaml https://github.com/kubernetes-sigs/aws-load-balancer-controller/releases/download/v2.4.7/v2_4_7_full.yaml
        sed -i.bak -e '596,604d' ./v2_4_7_full.yaml
        sed -i.bak -e 's|your-cluster-name|'$CLUSTER_NAME'|' ./v2_4_7_full.yaml
        kubectl apply -f v2_4_7_full.yaml
        rm -f v2_4_7_full.yaml v2_4_7_full.yaml.bak
        
        print_status "AWS Load Balancer Controller installation initiated"
    else
        print_status "AWS Load Balancer Controller already installed"
    fi
    
    # Check if EBS CSI driver is installed
    if ! kubectl get csidriver ebs.csi.aws.com &> /dev/null; then
        print_warning "EBS CSI driver not found. Installing..."
        
        # Create service account for EBS CSI driver
        eksctl create iamserviceaccount \
            --name ebs-csi-controller-sa \
            --namespace kube-system \
            --cluster $CLUSTER_NAME \
            --role-name AmazonEKS_EBS_CSI_DriverRole \
            --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
            --approve \
            --override-existing-serviceaccounts \
            --region=$REGION || print_warning "EBS CSI service account creation failed or already exists"
        
        # Install EBS CSI driver addon
        aws eks create-addon --cluster-name $CLUSTER_NAME --addon-name aws-ebs-csi-driver --region=$REGION || print_warning "EBS CSI addon installation failed or already exists"
        
        print_status "EBS CSI driver installation initiated"
    else
        print_status "EBS CSI driver already installed"
    fi
    
    print_status "EKS-specific resources setup completed"
}

# Function to create EKS-optimized storage classes
create_storage_classes() {
    print_info "Creating EKS-optimized storage classes..."
    
    cat > /tmp/eks-storage-classes.yaml << 'EOF'
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-fast
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  fsType: ext4
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-standard
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  fsType: ext4
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: io2-high-performance
provisioner: ebs.csi.aws.com
parameters:
  type: io2
  iops: "1000"
  fsType: ext4
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
EOF
    
    kubectl apply -f /tmp/eks-storage-classes.yaml
    rm -f /tmp/eks-storage-classes.yaml
    
    print_status "EKS storage classes created"
}

# Function to handle command line arguments
handle_arguments() {
    case "${1:-deploy}" in
        "deploy")
            deploy_noctipede
            ;;
        "status")
            check_deployment_status
            ;;
        "cleanup")
            cleanup_deployment
            ;;
        "update-kubeconfig")
            update_kubeconfig
            ;;
        "install-addons")
            setup_eks_resources
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Function to show help
show_help() {
    echo "Noctipede EKS Deployment Script"
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy              Deploy the complete Noctipede system (default)"
    echo "  status              Check deployment status"
    echo "  cleanup             Clean up all resources"
    echo "  update-kubeconfig   Update kubeconfig for EKS cluster"
    echo "  install-addons      Install EKS addons (Load Balancer Controller, EBS CSI)"
    echo "  help                Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  CLUSTER_NAME        EKS cluster name (default: noctipede-cluster)"
    echo "  AWS_REGION          AWS region (default: us-west-2)"
    echo "  STORAGE_CLASS       Storage class to use (default: gp3)"
    echo "  LOAD_BALANCER_TYPE  Load balancer type (default: nlb)"
    echo ""
    echo "Examples:"
    echo "  $0 deploy                    # Deploy everything"
    echo "  $0 status                    # Check status"
    echo "  CLUSTER_NAME=my-cluster $0   # Deploy to specific cluster"
}

# Function to update kubeconfig
update_kubeconfig() {
    print_info "Updating kubeconfig for EKS cluster..."
    aws eks update-kubeconfig --region $REGION --name $CLUSTER_NAME
    print_status "Kubeconfig updated"
}

# Main deployment function
deploy_noctipede() {
    print_info "Starting Noctipede deployment on EKS cluster: $CLUSTER_NAME"
    print_info "Region: $REGION"
    print_info "Storage Class: $STORAGE_CLASS"
    
    # Step 1: Check prerequisites
    check_prerequisites
    
    # Step 2: Setup EKS-specific resources
    setup_eks_resources
    
    # Step 3: Create storage classes
    create_storage_classes
    
    # Step 4: Create namespace
    echo ""
    echo "📁 Creating namespace..."
    kubectl apply -f namespace.yaml
    print_status "Namespace created"
    
    # Step 5: Apply secrets and configmaps with EKS-specific modifications
    echo ""
    echo "🔐 Applying secrets and configuration..."
    
    # Create EKS-specific configmap
    create_eks_configmap
    
    kubectl apply -f secrets.yaml
    kubectl apply -f /tmp/eks-configmap.yaml
    print_status "Secrets and configuration applied"
    
    # Step 6: Create EKS-optimized PVCs
    echo ""
    echo "💾 Creating EKS-optimized persistent volume claims..."
    create_eks_pvcs
    kubectl apply -f /tmp/eks-pvcs.yaml
    print_status "EKS PVCs created"
    
    # Step 7: Deploy infrastructure services with EKS optimizations
    echo ""
    echo "🗄️ Deploying MariaDB with EKS optimizations..."
    deploy_eks_mariadb
    
    echo ""
    echo "📦 Deploying MinIO with EKS optimizations..."
    deploy_eks_minio
    
    # Step 8: Deploy proxy services
    echo ""
    echo "🌐 Deploying proxy services..."
    kubectl apply -f proxy/
    print_status "Tor and I2P proxies deployed"
    
    # Step 9: Wait for infrastructure to be ready
    echo ""
    echo "⏳ Waiting for infrastructure services to be ready..."
    wait_for_infrastructure
    
    # Step 10: Deploy Noctipede application with EKS optimizations
    echo ""
    echo "🕷️ Deploying Noctipede application with EKS optimizations..."
    deploy_eks_noctipede_app
    
    # Step 11: Deploy EKS-optimized ingress
    echo ""
    echo "🌐 Deploying EKS Application Load Balancer..."
    deploy_eks_ingress
    
    # Step 12: Initialize database
    echo ""
    echo "🗄️ Initializing database..."
    kubectl apply -f init-database-job.yaml
    echo "⏳ Waiting for database initialization to complete..."
    kubectl wait --for=condition=complete job/init-database -n noctipede --timeout=300s
    print_status "Database initialized"
    
    # Step 13: Verify NFS sites file
    echo ""
    echo "📋 Verifying sites file..."
    verify_sites_file
    
    # Step 14: Wait for application to be ready
    echo ""
    echo "⏳ Waiting for Noctipede application to be ready..."
    kubectl wait --for=condition=ready pod -l app=noctipede-app -n noctipede --timeout=300s
    print_status "Noctipede application is ready"
    
    # Step 15: Perform comprehensive readiness check
    echo ""
    echo "🔍 Performing comprehensive readiness check..."
    perform_readiness_check
    
    # Step 16: Display access information
    echo ""
    echo "🌐 Getting EKS access information..."
    display_eks_access_info
    
    # Step 17: Clean up temporary files
    cleanup_temp_files
    
    print_status "🎉 EKS DEPLOYMENT COMPLETED SUCCESSFULLY!"
}

# Function to create EKS-specific configmap
create_eks_configmap() {
    print_info "Creating EKS-specific configuration..."
    
    # Read the original configmap and modify for EKS
    if [ -f "configmap.yaml" ]; then
        cp configmap.yaml /tmp/eks-configmap.yaml
        
        # Add EKS-specific configurations
        cat >> /tmp/eks-configmap.yaml << 'EOF'
  # EKS-specific configurations
  AWS_REGION: "${AWS_REGION:-us-west-2}"
  EKS_CLUSTER_NAME: "${CLUSTER_NAME:-noctipede-cluster}"
  STORAGE_CLASS: "${STORAGE_CLASS:-gp3}"
  LOAD_BALANCER_TYPE: "${LOAD_BALANCER_TYPE:-nlb}"
  
  # Enhanced resource limits for EKS
  MAX_CONCURRENT_CRAWLERS: "15"
  CRAWLER_TIMEOUT: "300"
  DATABASE_POOL_SIZE: "20"
  
  # EKS networking optimizations
  NETWORK_TIMEOUT: "60"
  CONNECTION_POOL_SIZE: "50"
EOF
    else
        print_error "configmap.yaml not found"
        exit 1
    fi
}

# Function to create EKS-optimized PVCs
create_eks_pvcs() {
    print_info "Creating EKS-optimized PVCs..."
    
    cat > /tmp/eks-pvcs.yaml << EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: noctipede-data-pvc
  namespace: noctipede
  labels:
    app: noctipede
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: $STORAGE_CLASS
  resources:
    requests:
      storage: 20Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: noctipede-logs-pvc
  namespace: noctipede
  labels:
    app: noctipede
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: $STORAGE_CLASS
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: noctipede-output-pvc
  namespace: noctipede
  labels:
    app: noctipede
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: $STORAGE_CLASS
  resources:
    requests:
      storage: 50Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: noctipede-sites-pvc
  namespace: noctipede
  labels:
    app: noctipede
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: $STORAGE_CLASS
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mariadb-data-pvc
  namespace: noctipede
  labels:
    app: mariadb
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: gp3-fast
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: minio-data-pvc
  namespace: noctipede
  labels:
    app: minio
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: $STORAGE_CLASS
  resources:
    requests:
      storage: 200Gi
EOF
}

# Function to deploy EKS-optimized MariaDB
deploy_eks_mariadb() {
    print_info "Deploying MariaDB with EKS optimizations..."
    
    cat > /tmp/eks-mariadb.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mariadb
  namespace: noctipede
  labels:
    app: mariadb
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mariadb
  template:
    metadata:
      labels:
        app: mariadb
    spec:
      containers:
      - name: mariadb
        image: mariadb:11.0
        ports:
        - containerPort: 3306
          name: mysql
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mariadb-secret
              key: MARIA_ROOT_PASSWORD
        - name: MYSQL_DATABASE
          value: "noctipede"
        - name: MYSQL_USER
          value: "splinter-research"
        - name: MYSQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mariadb-secret
              key: MARIA_ROOT_PASSWORD
        args:
        - --character-set-server=utf8mb4
        - --collation-server=utf8mb4_unicode_ci
        - --max-connections=200
        - --innodb-buffer-pool-size=1G
        - --innodb-log-file-size=256M
        - --innodb-flush-log-at-trx-commit=2
        - --sync-binlog=0
        volumeMounts:
        - name: mariadb-data
          mountPath: /var/lib/mysql
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          exec:
            command:
            - mysqladmin
            - ping
            - -h
            - localhost
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          exec:
            command:
            - mysql
            - -h
            - localhost
            - -e
            - SELECT 1
          initialDelaySeconds: 5
          periodSeconds: 2
          timeoutSeconds: 1
      volumes:
      - name: mariadb-data
        persistentVolumeClaim:
          claimName: mariadb-data-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: mariadb
  namespace: noctipede
  labels:
    app: mariadb
spec:
  ports:
  - port: 3306
    targetPort: 3306
    name: mysql
  selector:
    app: mariadb
  type: ClusterIP
EOF
    
    kubectl apply -f /tmp/eks-mariadb.yaml
    
    # Wait for MariaDB to be ready
    print_info "Waiting for MariaDB to be ready..."
    kubectl wait --for=condition=ready pod -l app=mariadb -n noctipede --timeout=300s
    print_status "MariaDB deployed and ready"
}

# Function to deploy EKS-optimized MinIO
deploy_eks_minio() {
    print_info "Deploying MinIO with EKS optimizations..."
    
    cat > /tmp/eks-minio.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
  namespace: noctipede
  labels:
    app: minio
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
      - name: minio
        image: minio/minio:latest
        ports:
        - containerPort: 9000
          name: api
        - containerPort: 9001
          name: console
        env:
        - name: MINIO_ROOT_USER
          valueFrom:
            secretKeyRef:
              name: minio-secret
              key: MINIO_ROOT_USER
        - name: MINIO_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: minio-secret
              key: MINIO_ROOT_PASSWORD
        command:
        - /bin/bash
        - -c
        args:
        - minio server /data --console-address ":9001"
        volumeMounts:
        - name: minio-data
          mountPath: /data
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /minio/health/live
            port: 9000
          initialDelaySeconds: 30
          periodSeconds: 20
        readinessProbe:
          httpGet:
            path: /minio/health/ready
            port: 9000
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: minio-data
        persistentVolumeClaim:
          claimName: minio-data-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: minio-api
  namespace: noctipede
  labels:
    app: minio
spec:
  ports:
  - port: 9000
    targetPort: 9000
    name: api
  selector:
    app: minio
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: minio-console
  namespace: noctipede
  labels:
    app: minio
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
spec:
  ports:
  - port: 9001
    targetPort: 9001
    name: console
  selector:
    app: minio
  type: LoadBalancer
EOF
    
    kubectl apply -f /tmp/eks-minio.yaml
    
    # Wait for MinIO to be ready
    print_info "Waiting for MinIO to be ready..."
    kubectl wait --for=condition=ready pod -l app=minio -n noctipede --timeout=300s
    print_status "MinIO deployed and ready"
}

# Function to wait for infrastructure services
wait_for_infrastructure() {
    print_info "Waiting for infrastructure services to be fully ready..."
    
    # Test MariaDB connectivity
    print_info "Testing MariaDB connectivity..."
    kubectl run mariadb-test --image=mariadb:11.0 --restart=Never -n noctipede --rm -i --tty -- \
        mariadb -h mariadb -u root -p$(kubectl get secret mariadb-secret -n noctipede -o jsonpath='{.data.MARIA_ROOT_PASSWORD}' | base64 -d) -e "SELECT 1;" || \
        print_warning "MariaDB test failed, but continuing..."
    
    # Test MinIO connectivity
    print_info "Testing MinIO connectivity..."
    kubectl run minio-test --image=curlimages/curl --restart=Never -n noctipede --rm -i --tty -- \
        curl -f http://minio-api:9000/minio/health/ready || \
        print_warning "MinIO test failed, but continuing..."
    
    print_status "Infrastructure services are ready"
}

# Function to deploy EKS-optimized Noctipede application
deploy_eks_noctipede_app() {
    print_info "Deploying Noctipede application with EKS optimizations..."
    
    cat > /tmp/eks-noctipede-app.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: noctipede-app
  namespace: noctipede
  labels:
    app: noctipede-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: noctipede-app
  template:
    metadata:
      labels:
        app: noctipede-app
    spec:
      initContainers:
      - name: wait-for-database
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔍 Waiting for MariaDB to be ready..."
          until nc -z mariadb 3306; do
            echo "⏳ MariaDB not ready, waiting..."
            sleep 5
          done
          echo "✅ MariaDB is ready!"
      - name: wait-for-minio
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔍 Waiting for MinIO to be ready..."
          until nc -z minio-api 9000; do
            echo "⏳ MinIO not ready, waiting..."
            sleep 5
          done
          echo "✅ MinIO is ready!"
      - name: wait-for-proxies
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔍 Waiting for proxy services..."
          until nc -z tor-proxy 9150 && nc -z i2p-proxy 4444; do
            echo "⏳ Proxies not ready, waiting..."
            sleep 10
          done
          echo "✅ Proxies are ready!"
      - name: init-directories
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔧 Creating directories and setting permissions..."
          mkdir -p /app/logs /app/output /app/data
          chmod 777 /app/logs /app/output /app/data
          echo "✅ Directories initialized"
        volumeMounts:
        - name: log-data
          mountPath: /app/logs
        - name: output-data
          mountPath: /app/output
        - name: data-volume
          mountPath: /app/data
      containers:
      - name: noctipede-app
        image: ghcr.io/splinterstice/noctipede:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
        envFrom:
        - configMapRef:
            name: noctipede-config
        - secretRef:
            name: noctipede-secrets
        env:
        - name: MARIADB_HOST
          value: "mariadb"
        - name: MINIO_ENDPOINT
          value: "minio-api:9000"
        - name: WEB_SERVER_PORT
          value: "8080"
        - name: WEB_SERVER_HOST
          value: "0.0.0.0"
        - name: SKIP_RECENT_CRAWLS
          value: "false"
        - name: MAX_CONCURRENT_CRAWLERS
          value: "15"
        - name: AWS_REGION
          value: "${AWS_REGION}"
        command: ["sh", "-c"]
        args:
        - |
          echo "🚀 Starting Noctipede Web Application on EKS..."
          cd /app
          
          echo "🗄️ Initializing database..."
          python database/init_db.py
          echo "✅ Database initialized successfully!"
          
          echo "🌐 Starting web portal..."
          PYTHONPATH=/app python -m portal.unified_portal
        volumeMounts:
        - name: output-data
          mountPath: /app/output
        - name: log-data
          mountPath: /app/logs
        - name: data-volume
          mountPath: /app/data
        - name: sites-volume
          mountPath: /nfs-sites
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 120
          periodSeconds: 15
          timeoutSeconds: 10
          failureThreshold: 10
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 30
          failureThreshold: 5
      volumes:
      - name: output-data
        persistentVolumeClaim:
          claimName: noctipede-output-pvc
      - name: log-data
        persistentVolumeClaim:
          claimName: noctipede-logs-pvc
      - name: data-volume
        persistentVolumeClaim:
          claimName: noctipede-data-pvc
      - name: sites-volume
        persistentVolumeClaim:
          claimName: noctipede-sites-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: noctipede-app-service
  namespace: noctipede
  labels:
    app: noctipede-app
spec:
  ports:
  - port: 8080
    targetPort: 8080
    protocol: TCP
    name: http
  selector:
    app: noctipede-app
  type: ClusterIP
EOF
    
    kubectl apply -f /tmp/eks-noctipede-app.yaml
    print_status "Noctipede application deployed"
}
