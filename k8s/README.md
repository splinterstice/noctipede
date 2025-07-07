# Noctipede Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the complete Noctipede deep web analysis system with proxy infrastructure.

## 🚀 Quick Start

```bash
# Deploy everything
./deploy.sh

# Check status
./deploy.sh status

# Clean up
./deploy.sh cleanup
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
