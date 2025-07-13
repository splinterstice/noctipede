# Noctipede Kubernetes Quick Reference

## 🚀 One-Command Deployment
```bash
cd k8s/ && ./deploy.sh
```

## 🧪 Test Everything
```bash
./test-deployment.sh
```

## 🗑️ Complete Removal
```bash
./destroy.sh
```

## 📊 Status Checks
```bash
# All pods
kubectl get pods -n noctipede

# Services
kubectl get services -n noctipede

# Storage
kubectl get pvc -n noctipede
```

## 🌐 Access Applications
```bash
# Get NodePort
kubectl get service noctipede-app-service -n noctipede

# Port forward (local access)
kubectl port-forward service/noctipede-app-service 8080:8080 -n noctipede

# MinIO console
kubectl port-forward service/minio-console 9001:9001 -n noctipede
```

## 🕷️ Run Crawler
```bash
# Manual crawler job
kubectl create job --from=cronjob/noctipede-crawler noctipede-crawler-manual -n noctipede

# Check crawler logs
kubectl logs -l job-name=noctipede-crawler-manual -n noctipede
```

## 🔍 Debugging
```bash
# Pod logs
kubectl logs -l app=noctipede-app -n noctipede

# Describe pod
kubectl describe pod <pod-name> -n noctipede

# Events
kubectl get events -n noctipede --sort-by='.lastTimestamp'

# Shell into pod
kubectl exec -it <pod-name> -n noctipede -- /bin/bash
```

## 🧪 Test Connectivity
```bash
# I2P test
kubectl run i2p-test --image=curlimages/curl --rm -it --restart=Never -n noctipede -- curl -x http://i2p-proxy:4444 -m 30 http://reg.i2p/ --head

# Database test
kubectl exec -n noctipede deployment/mariadb -- mysql -u root -p$MYSQL_ROOT_PASSWORD -e "SHOW DATABASES;"
```

## 📋 Key Ports
- **App**: 8080 (NodePort varies)
- **MariaDB**: 3306
- **MinIO**: 9000 (API), 9001 (Console)
- **Tor**: 9150
- **I2P**: 4444

## 🔧 Fixed Issues
- ✅ UTF-8 database charset
- ✅ Secret references
- ✅ Python module paths
- ✅ Init container dependencies
- ✅ Health check endpoints
- ✅ Service exposure
