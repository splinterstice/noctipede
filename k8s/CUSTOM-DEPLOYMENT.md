# Custom Noctipede Kubernetes Deployment

This directory contains custom deployment scripts specifically configured for your cluster.

## Configuration

- **Ollama Endpoint**: `http://10.1.1.12:2701` (External - not managed by K8s)
- **Database**: Internal MariaDB (managed by K8s)
- **Storage**: Internal MinIO (managed by K8s)
- **Namespace**: `noctipede`

## Available Models (Confirmed)

✅ **Vision Model**: `llama3.2-vision:11b`
✅ **Text Model**: `gemma3:12b` (using instead of gemma2:9b - better model available)
✅ **Moderation Model**: `llama3.1:8b`

## Quick Start

### Deploy Everything
```bash
cd k8s/
./deploy-custom.sh
```

### Check Status
```bash
./deploy-custom.sh status
```

### Test Ollama Connection
```bash
./deploy-custom.sh test-ollama
```

### Destroy Everything
```bash
./destroy-custom.sh
```

### Emergency Cleanup
```bash
./destroy-custom.sh force
```

## Access URLs

After deployment, you can access:

### Portal
- **NodePort**: `http://10.1.1.12:PORT` (PORT shown after deployment)
- **Ingress**: `http://10.1.1.12/`
- **Hostname**: `http://noctipede.local` (add to /etc/hosts)

### MinIO Console
- **NodePort**: `http://10.1.1.12:PORT` (PORT shown after deployment)
- **Hostname**: `http://minio.local` (add to /etc/hosts)

## Features

### Custom Deploy Script (`deploy-custom.sh`)
- ✅ Tests Ollama connectivity before deployment
- ✅ Uses optimized configuration for your cluster
- ✅ Creates custom ingress rules
- ✅ Handles I2P bootstrap gracefully (non-blocking)
- ✅ Provides detailed status and health checks
- ✅ Shows all access URLs after deployment

### Custom Destroy Script (`destroy-custom.sh`)
- ✅ Creates automatic backups before destruction
- ✅ Shows detailed destruction plan
- ✅ Protects external Ollama (won't touch it)
- ✅ Provides restoration script in backups
- ✅ Supports force cleanup for emergencies
- ✅ Comprehensive cleanup verification

## Configuration Details

### AI Models
The deployment uses the best available models from your Ollama instance:
- **Vision**: `llama3.2-vision:11b` - For image analysis
- **Text**: `gemma3:12b` - For content analysis (upgraded from gemma2:9b)
- **Moderation**: `llama3.1:8b` - For content moderation

### Database
- **Type**: MariaDB (internal)
- **Storage**: Persistent volumes
- **Access**: Internal cluster only

### Object Storage
- **Type**: MinIO (internal)
- **Storage**: Persistent volumes
- **Console**: Web interface available

### Proxy Services
- **Tor**: SOCKS5 proxy for .onion sites
- **I2P**: HTTP proxy for .i2p sites (may take 10+ minutes to bootstrap)

## Backup and Recovery

The destroy script automatically creates backups in:
```
./noctipede-custom-backup-YYYYMMDD-HHMMSS/
```

Each backup contains:
- `configmaps.yaml` - All configuration
- `services.yaml` - Service definitions
- `deployments.yaml` - Deployment configurations
- `ingress.yaml` - Ingress rules
- `pvcs.yaml` - Storage claims
- `restore.sh` - Automated restoration script

## Troubleshooting

### Ollama Issues
```bash
./deploy-custom.sh test-ollama
```

### Pod Issues
```bash
kubectl get pods -n noctipede
kubectl logs <pod-name> -n noctipede
```

### Service Issues
```bash
kubectl get services -n noctipede
kubectl describe service <service-name> -n noctipede
```

### I2P Bootstrap Issues
I2P can take 10-30 minutes to bootstrap. This is normal and won't block the deployment.

## Security Notes

- Ollama endpoint is external and not managed by these scripts
- Internal services are only accessible within the cluster
- Ingress provides controlled external access
- All data is stored in persistent volumes

## Support

For issues with:
- **Deployment**: Check the deploy script output
- **Ollama**: Verify the endpoint is accessible
- **Storage**: Check PVC status
- **Networking**: Verify ingress and services

The scripts provide detailed logging and status information to help with troubleshooting.
