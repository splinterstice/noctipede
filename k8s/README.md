# Noctipede Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the complete Noctipede deep web analysis system with proxy infrastructure.

## 🚀 Quick Start

### Standard Kubernetes Deployment
```bash
# Deploy everything
./deploy.sh

# Check status
./deploy.sh status

# Clean up
./deploy.sh cleanup
```

### Amazon EKS Deployment
```bash
# Deploy to EKS with AWS optimizations
./deploy-eks.sh

# Check EKS deployment status
./deploy-eks.sh status

# Update kubeconfig for EKS
./deploy-eks.sh update-kubeconfig

# Install EKS addons
./deploy-eks.sh install-addons

# Clean up EKS deployment
./deploy-eks.sh cleanup
```

## 📋 What's Included

### Core Services
- **MariaDB**: Database for storing crawl data and metadata
- **MinIO**: Object storage for page content and media files
- **Noctipede App**: Main crawler application
- **Noctipede Portal**: Web dashboard with live metrics

### Proxy Services (NEW!)
- **Tor Proxy**: SOCKS5 proxy for .onion sites (`dperson/torproxy`)
- **I2P Proxy**: HTTP proxy for .i2p sites (`geti2p/i2p`)

## 🔧 Architecture Updates

Based on successful Docker implementation, the K8s deployment now includes:

### ✅ **Fixed Issues**
1. **Database Session Management**: Implemented session-per-operation pattern
2. **Proxy Infrastructure**: Added dedicated Tor and I2P proxy services
3. **Service Dependencies**: Proper init containers and service ordering
4. **Portal vs API**: Updated from API to Portal with live metrics

### 🌐 **Network Capabilities**
- **Clearnet**: Direct HTTP/HTTPS crawling
- **Tor Network**: .onion site crawling via SOCKS5 proxy
- **I2P Network**: .i2p site crawling via HTTP proxy

## 📁 Directory Structure

```
k8s/
├── deploy.sh              # Main deployment script
├── namespace.yaml          # Kubernetes namespace
├── secrets.yaml           # Sensitive configuration
├── configmap.yaml         # Application configuration
├── mariadb/               # Database deployment
├── minio/                 # Object storage deployment
├── proxy/                 # NEW: Proxy services
│   ├── tor-proxy.yaml     # Tor SOCKS5 proxy
│   └── i2p-proxy.yaml     # I2P HTTP proxy
└── noctipede/             # Application deployments
    ├── deployment.yaml    # App and Portal deployments
    ├── service.yaml       # Kubernetes services
    └── pvc.yaml          # Persistent volume claims
```

## 🔧 Configuration Changes

### Updated ConfigMap
```yaml
# Network Configuration - Updated for K8s proxy services
TOR_PROXY_HOST: "tor-proxy"      # Was: 127.0.0.1
TOR_PROXY_PORT: "9150"
I2P_PROXY_HOST: "i2p-proxy"     # Was: 127.0.0.1
I2P_PROXY_PORT: "4444"
```

### New Proxy Services
```yaml
# Tor Proxy Service
apiVersion: v1
kind: Service
metadata:
  name: tor-proxy
spec:
  ports:
  - port: 9150
    name: socks-proxy

# I2P Proxy Service  
apiVersion: v1
kind: Service
metadata:
  name: i2p-proxy
spec:
  ports:
  - port: 4444
    name: http-proxy
  - port: 7070
    name: web-console
```

## 🚀 Deployment Process

The deployment script follows this order:

1. **Namespace Creation**: Create `noctipede` namespace
2. **Configuration**: Apply secrets and config maps
3. **Infrastructure**: Deploy MariaDB and MinIO
4. **Proxy Services**: Deploy Tor and I2P proxies
5. **Applications**: Deploy crawler and portal
6. **Health Checks**: Wait for all services to be ready

### Init Containers
Each application pod includes init containers that wait for proxy services:

```yaml
initContainers:
- name: wait-for-tor-proxy
  image: busybox:1.35
  command: ['sh', '-c']
  args: ['until nc -z tor-proxy 9150; do sleep 5; done']
  
- name: wait-for-i2p-proxy
  image: busybox:1.35
  command: ['sh', '-c']
  args: ['until nc -z i2p-proxy 4444; do sleep 10; done']
```

## 📊 Monitoring & Access

### Web Portal
- **URL**: `http://<LoadBalancer-IP>:8080`
- **Local Access**: `kubectl port-forward -n noctipede service/noctipede-portal-service 8080:8080`

### Proxy Services
- **Tor Proxy**: `tor-proxy.noctipede:9150` (SOCKS5)
- **I2P Proxy**: `i2p-proxy.noctipede:4444` (HTTP)
- **I2P Console**: `i2p-proxy.noctipede:7070` (Web UI)

### Monitoring Commands
```bash
# Check all pods
kubectl get pods -n noctipede

# Check services
kubectl get services -n noctipede

# View logs
kubectl logs -n noctipede deployment/noctipede-portal
kubectl logs -n noctipede deployment/noctipede-app
kubectl logs -n noctipede deployment/tor-proxy
kubectl logs -n noctipede deployment/i2p-proxy

# Check proxy connectivity
kubectl exec -n noctipede deployment/noctipede-portal -- curl -s http://i2p-proxy:4444
kubectl exec -n noctipede deployment/noctipede-portal -- nc -z tor-proxy 9150
```

## 🔒 Security Considerations

### Network Policies
Consider implementing network policies to restrict traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: noctipede-network-policy
  namespace: noctipede
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: noctipede
  egress:
  - to: []  # Allow all egress for web crawling
```

### Resource Limits
All deployments include resource requests and limits:

```yaml
resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 2Gi
```

## 🔧 Troubleshooting

### Common Issues

1. **Proxy Services Not Ready**
   ```bash
   kubectl logs -n noctipede deployment/tor-proxy
   kubectl logs -n noctipede deployment/i2p-proxy
   ```

2. **Database Connection Issues**
   ```bash
   kubectl exec -n noctipede deployment/noctipede-app -- nc -z mariadb 3306
   ```

3. **Storage Issues**
   ```bash
   kubectl get pvc -n noctipede
   kubectl describe pvc -n noctipede
   ```

### Health Checks
```bash
# Check all deployments
kubectl get deployments -n noctipede

# Check pod status
kubectl get pods -n noctipede -o wide

# Test proxy connectivity
kubectl exec -n noctipede deployment/noctipede-portal -- \
  curl -s http://localhost:8080/api/system-metrics | jq '.system.network'
```

## 📈 Scaling

### Horizontal Scaling
```bash
# Scale portal replicas
kubectl scale deployment noctipede-portal --replicas=3 -n noctipede

# Scale crawler replicas (be careful with database connections)
kubectl scale deployment noctipede-app --replicas=2 -n noctipede
```

### Vertical Scaling
Update resource limits in deployment manifests and apply:
```bash
kubectl apply -f noctipede/deployment.yaml
```

## 🔄 Updates

### Rolling Updates
```bash
# Update image
kubectl set image deployment/noctipede-portal noctipede-portal=noctipede:v2.0 -n noctipede

# Check rollout status
kubectl rollout status deployment/noctipede-portal -n noctipede

# Rollback if needed
kubectl rollout undo deployment/noctipede-portal -n noctipede
```

## 📝 Notes

- **I2P Bootstrap**: I2P proxy may take 5-10 minutes to fully bootstrap on first run
- **Persistent Storage**: All data is stored in PVCs and survives pod restarts
- **Proxy Dependencies**: Applications wait for proxy services via init containers
- **Database Sessions**: Fixed concurrent session issues with per-operation sessions
- **Health Checks**: Comprehensive liveness and readiness probes for all services

## 🆘 Support

For issues or questions:
1. Check the deployment logs: `kubectl logs -n noctipede deployment/<service-name>`
2. Verify service connectivity: `kubectl exec -n noctipede deployment/<pod> -- nc -z <service> <port>`
3. Check resource usage: `kubectl top pods -n noctipede`
4. Review events: `kubectl get events -n noctipede --sort-by='.lastTimestamp'`

---

## ☁️ Amazon EKS Deployment Guide

The `deploy-eks.sh` script provides a comprehensive EKS-optimized deployment with AWS-specific features and optimizations.

### 🔧 Prerequisites for EKS

Before deploying to EKS, ensure you have:

1. **AWS CLI configured**:
   ```bash
   aws configure
   # or use AWS profiles
   export AWS_PROFILE=your-profile
   ```

2. **EKS cluster created**:
   ```bash
   # Create EKS cluster (example)
   eksctl create cluster \
     --name noctipede-cluster \
     --region us-west-2 \
     --nodegroup-name standard-workers \
     --node-type m5.large \
     --nodes 3 \
     --nodes-min 1 \
     --nodes-max 4 \
     --managed
   ```

3. **kubectl configured for EKS**:
   ```bash
   aws eks update-kubeconfig --region us-west-2 --name noctipede-cluster
   ```

4. **Required tools installed**:
   - `kubectl` (Kubernetes CLI)
   - `aws` (AWS CLI v2)
   - `eksctl` (optional, for cluster management)

### 🚀 EKS Deployment Commands

```bash
# Basic deployment
./deploy-eks.sh

# Deploy with custom settings
CLUSTER_NAME=my-cluster AWS_REGION=us-east-1 ./deploy-eks.sh

# Check deployment status
./deploy-eks.sh status

# Update kubeconfig
./deploy-eks.sh update-kubeconfig

# Install EKS addons only
./deploy-eks.sh install-addons

# Clean up everything
./deploy-eks.sh cleanup

# Show help
./deploy-eks.sh help
```

### 🔧 EKS-Specific Features

#### **AWS Load Balancer Controller**
- Automatically installs and configures AWS Load Balancer Controller
- Creates Application Load Balancer (ALB) for web traffic
- Creates Network Load Balancer (NLB) for direct access
- Supports SSL termination with ACM certificates

#### **EBS CSI Driver**
- Automatically installs EBS CSI driver for persistent storage
- Creates optimized storage classes:
  - `gp3-standard`: General purpose SSD
  - `gp3-fast`: High IOPS SSD (3000 IOPS)
  - `io2-high-performance`: Provisioned IOPS SSD

#### **Enhanced Resource Management**
- Increased replica count (2 replicas for high availability)
- Optimized resource requests and limits for EKS
- Enhanced health checks and readiness probes
- Cross-zone load balancing enabled

#### **AWS-Specific Configurations**
- EKS cluster name and region detection
- AWS service integration ready
- CloudWatch logging compatible
- VPC and security group optimized

### 📊 EKS Storage Classes

The deployment creates several storage classes optimized for different workloads:

```yaml
# High-performance database storage
gp3-fast:
  - Type: gp3 SSD
  - IOPS: 3000
  - Throughput: 125 MB/s
  - Use: MariaDB data

# Standard application storage  
gp3-standard:
  - Type: gp3 SSD
  - IOPS: 3000 (baseline)
  - Use: Application data, logs

# High-performance storage
io2-high-performance:
  - Type: io2 SSD
  - IOPS: 1000 (provisioned)
  - Use: High-performance workloads
```

### 🌐 EKS Networking

#### **Load Balancers**
```bash
# Application Load Balancer (ALB)
# - HTTPS termination
# - Path-based routing
# - Health checks
# - Auto-scaling integration

# Network Load Balancer (NLB)  
# - TCP load balancing
# - Static IP addresses
# - Cross-zone load balancing
# - High performance
```

#### **Ingress Configuration**
```yaml
# ALB Ingress with SSL
annotations:
  kubernetes.io/ingress.class: alb
  alb.ingress.kubernetes.io/scheme: internet-facing
  alb.ingress.kubernetes.io/target-type: ip
  alb.ingress.kubernetes.io/ssl-redirect: '443'
  alb.ingress.kubernetes.io/certificate-arn: "${SSL_CERT_ARN}"
```

### 🔒 EKS Security Features

#### **IAM Integration**
- Service accounts with IAM roles (IRSA)
- Least privilege access policies
- AWS Load Balancer Controller permissions
- EBS CSI driver permissions

#### **Network Security**
- VPC-native networking
- Security group integration
- Private subnet deployment ready
- Network policies support

### 📈 EKS Monitoring & Scaling

#### **Horizontal Pod Autoscaling**
```bash
# Enable HPA for Noctipede app
kubectl autoscale deployment noctipede-app \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n noctipede
```

#### **Cluster Autoscaling**
```bash
# EKS cluster autoscaler (if using managed node groups)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml
```

#### **CloudWatch Integration**
```bash
# Install CloudWatch agent (optional)
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cloudwatch-namespace.yaml
```

### 🔧 EKS Troubleshooting

#### **Common Issues**

1. **Load Balancer Controller Issues**:
   ```bash
   # Check controller logs
   kubectl logs -n kube-system deployment/aws-load-balancer-controller
   
   # Verify service account
   kubectl describe sa aws-load-balancer-controller -n kube-system
   ```

2. **EBS CSI Driver Issues**:
   ```bash
   # Check CSI driver
   kubectl get csidriver
   
   # Check CSI pods
   kubectl get pods -n kube-system | grep ebs-csi
   ```

3. **Storage Issues**:
   ```bash
   # Check storage classes
   kubectl get storageclass
   
   # Check PVC status
   kubectl get pvc -n noctipede
   
   # Describe problematic PVC
   kubectl describe pvc <pvc-name> -n noctipede
   ```

4. **Networking Issues**:
   ```bash
   # Check ingress status
   kubectl describe ingress noctipede-ingress -n noctipede
   
   # Check load balancer services
   kubectl get svc -n noctipede
   
   # Test internal connectivity
   kubectl run test --image=curlimages/curl --rm -it --restart=Never -n noctipede -- curl http://noctipede-app-service:8080/api/health
   ```

### 🔄 EKS Updates and Maintenance

#### **Rolling Updates**
```bash
# Update application image
kubectl set image deployment/noctipede-app noctipede-app=ghcr.io/splinterstice/noctipede:v2.0 -n noctipede

# Check rollout status
kubectl rollout status deployment/noctipede-app -n noctipede

# Rollback if needed
kubectl rollout undo deployment/noctipede-app -n noctipede
```

#### **Cluster Maintenance**
```bash
# Update EKS cluster version
eksctl update cluster --name noctipede-cluster --region us-west-2

# Update node groups
eksctl update nodegroup --cluster noctipede-cluster --name standard-workers --region us-west-2
```

### 💰 EKS Cost Optimization

#### **Resource Optimization**
- Use Spot instances for non-critical workloads
- Right-size your node groups
- Enable cluster autoscaler
- Use gp3 storage instead of gp2

#### **Cost Monitoring**
```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n noctipede

# Analyze costs with AWS Cost Explorer
# Monitor EBS volume usage
# Review Load Balancer costs
```

### 🌍 Multi-Region EKS Deployment

For multi-region deployments:

```bash
# Deploy to multiple regions
AWS_REGION=us-west-2 CLUSTER_NAME=noctipede-west ./deploy-eks.sh
AWS_REGION=us-east-1 CLUSTER_NAME=noctipede-east ./deploy-eks.sh

# Cross-region replication setup
# Database replication configuration
# Cross-region load balancing
```

### 📝 EKS Environment Variables

The EKS deployment script supports these environment variables:

```bash
# Required/Recommended
export CLUSTER_NAME="noctipede-cluster"      # EKS cluster name
export AWS_REGION="us-west-2"                # AWS region
export STORAGE_CLASS="gp3"                   # Storage class
export LOAD_BALANCER_TYPE="nlb"              # LB type

# Optional
export SSL_CERT_ARN="arn:aws:acm:..."        # SSL certificate ARN
export DOMAIN_NAME="noctipede.example.com"   # Custom domain
export NODE_GROUP_NAME="standard-workers"    # Node group name
```

### 🎯 EKS Best Practices

1. **Security**:
   - Use private subnets for worker nodes
   - Enable EKS cluster logging
   - Implement network policies
   - Use AWS Secrets Manager integration

2. **Performance**:
   - Use appropriate instance types
   - Enable cluster autoscaler
   - Optimize storage classes
   - Configure resource requests/limits

3. **Reliability**:
   - Deploy across multiple AZs
   - Use managed node groups
   - Implement proper health checks
   - Set up monitoring and alerting

4. **Cost Management**:
   - Use Spot instances where appropriate
   - Right-size resources
   - Monitor and optimize storage
   - Review load balancer usage

---
