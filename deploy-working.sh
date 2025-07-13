#!/bin/bash

echo "🚀 Deploying Noctipede with Fixed I2P Crawling"

# Build and push the latest image with I2P fixes
echo "📦 Building and pushing latest image with I2P fixes..."
make ghcr-deploy

# Deploy to Kubernetes with the fixed image
echo "🔧 Deploying to Kubernetes..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

# Deploy core services
echo "🗄️ Deploying MariaDB..."
kubectl apply -f k8s/mariadb/

echo "📦 Deploying MinIO..."
kubectl apply -f k8s/minio/

# Wait for core services
echo "⏳ Waiting for core services to be ready..."
kubectl wait --for=condition=ready pod -l app=mariadb -n noctipede --timeout=300s
kubectl wait --for=condition=ready pod -l app=minio -n noctipede --timeout=300s

# Deploy proxy services
echo "🌐 Deploying proxy services..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tor-proxy
  namespace: noctipede
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tor-proxy
  template:
    metadata:
      labels:
        app: tor-proxy
    spec:
      containers:
      - name: tor-proxy
        image: dperson/torproxy:latest
        ports:
        - containerPort: 9150
        - containerPort: 8118
---
apiVersion: v1
kind: Service
metadata:
  name: tor-proxy
  namespace: noctipede
spec:
  selector:
    app: tor-proxy
  ports:
  - name: socks
    port: 9150
    targetPort: 9150
  - name: http
    port: 8118
    targetPort: 8118
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: i2p-proxy
  namespace: noctipede
spec:
  replicas: 1
  selector:
    matchLabels:
      app: i2p-proxy
  template:
    metadata:
      labels:
        app: i2p-proxy
    spec:
      containers:
      - name: i2p-proxy
        image: geti2p/i2p:latest
        ports:
        - containerPort: 4444
        - containerPort: 7657
        env:
        - name: JVM_XMX
          value: "512m"
---
apiVersion: v1
kind: Service
metadata:
  name: i2p-proxy
  namespace: noctipede
spec:
  selector:
    app: i2p-proxy
  ports:
  - name: http-proxy
    port: 4444
    targetPort: 4444
  - name: console
    port: 7657
    targetPort: 7657
EOF

# Wait for proxies
echo "⏳ Waiting for proxy services..."
kubectl wait --for=condition=ready pod -l app=tor-proxy -n noctipede --timeout=300s
kubectl wait --for=condition=ready pod -l app=i2p-proxy -n noctipede --timeout=300s

# Deploy main application with I2P fixes
echo "🕷️ Deploying Noctipede crawler with I2P fixes..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: noctipede-app
  namespace: noctipede
spec:
  replicas: 1
  selector:
    matchLabels:
      app: noctipede-app
  template:
    metadata:
      labels:
        app: noctipede-app
    spec:
      initContainers:
      - name: wait-for-services
        image: busybox:1.35
        command: ['sh', '-c']
        args:
        - |
          echo "🔍 Waiting for services to be ready..."
          until nc -z mariadb 3306; do echo "⏳ MariaDB not ready..."; sleep 5; done
          until nc -z minio 9000; do echo "⏳ MinIO not ready..."; sleep 5; done
          until nc -z tor-proxy 9150; do echo "⏳ Tor proxy not ready..."; sleep 5; done
          until nc -z i2p-proxy 4444; do echo "⏳ I2P proxy not ready..."; sleep 5; done
          echo "✅ All services ready!"
      containers:
      - name: noctipede-app
        image: ghcr.io/splinterstice/noctipede:latest
        command: ["python", "-m", "noctipede.crawlers.main"]
        env:
        - name: MARIADB_HOST
          value: "mariadb"
        - name: MARIADB_PORT
          value: "3306"
        - name: MARIADB_USER
          value: "splinter-research"
        - name: MARIADB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mariadb-secret
              key: MARIA_USER_PASSWORD
        - name: MARIADB_DATABASE
          value: "splinter-research"
        - name: MINIO_ENDPOINT
          value: "minio:9000"
        - name: MINIO_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: minio-secrets
              key: MINIO_ACCESS_KEY
        - name: MINIO_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: minio-secrets
              key: MINIO_SECRET_KEY
        - name: MINIO_BUCKET_NAME
          value: "noctipede-data"
        - name: MINIO_SECURE
          value: "false"
        - name: TOR_PROXY_HOST
          value: "tor-proxy"
        - name: TOR_PROXY_PORT
          value: "9150"
        - name: I2P_PROXY_HOST
          value: "i2p-proxy"
        - name: I2P_PROXY_PORT
          value: "4444"
        - name: I2P_INTERNAL_PROXIES
          value: "notbob.i2p,purokishi.i2p,false.i2p,stormycloud.i2p"
        - name: USE_I2P_INTERNAL_PROXIES
          value: "true"
        - name: MAX_CONCURRENT_CRAWLERS
          value: "20"
        - name: CRAWL_DELAY_SECONDS
          value: "1"
        - name: LOG_LEVEL
          value: "INFO"
        - name: CONTENT_ANALYSIS_ENABLED
          value: "false"
        - name: IMAGE_ANALYSIS_ENABLED
          value: "false"
        ports:
        - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: noctipede-app
  namespace: noctipede
spec:
  selector:
    app: noctipede-app
  ports:
  - port: 8080
    targetPort: 8080
EOF

# Deploy crawler cronjob
echo "⏰ Deploying crawler cronjob..."
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: noctipede-crawler
  namespace: noctipede
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: noctipede-crawler
            image: ghcr.io/splinterstice/noctipede:latest
            command: ["python", "-m", "noctipede.crawlers.main"]
            env:
            - name: MARIADB_HOST
              value: "mariadb"
            - name: MARIADB_PORT
              value: "3306"
            - name: MARIADB_USER
              value: "splinter-research"
            - name: MARIADB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mariadb-secret
                  key: MARIA_USER_PASSWORD
            - name: MARIADB_DATABASE
              value: "splinter-research"
            - name: MINIO_ENDPOINT
              value: "minio:9000"
            - name: MINIO_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: minio-secrets
                  key: MINIO_ACCESS_KEY
            - name: MINIO_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: minio-secrets
                  key: MINIO_SECRET_KEY
            - name: MINIO_BUCKET_NAME
              value: "noctipede-data"
            - name: MINIO_SECURE
              value: "false"
            - name: TOR_PROXY_HOST
              value: "tor-proxy"
            - name: TOR_PROXY_PORT
              value: "9150"
            - name: I2P_PROXY_HOST
              value: "i2p-proxy"
            - name: I2P_PROXY_PORT
              value: "4444"
            - name: I2P_INTERNAL_PROXIES
              value: "notbob.i2p,purokishi.i2p,false.i2p,stormycloud.i2p"
            - name: USE_I2P_INTERNAL_PROXIES
              value: "true"
            - name: MAX_CONCURRENT_CRAWLERS
              value: "20"
            - name: CRAWL_DELAY_SECONDS
              value: "1"
            - name: LOG_LEVEL
              value: "INFO"
            - name: CONTENT_ANALYSIS_ENABLED
              value: "false"
            - name: IMAGE_ANALYSIS_ENABLED
              value: "false"
EOF

echo "✅ Deployment complete!"
echo ""
echo "🔍 Checking deployment status..."
kubectl get pods -n noctipede

echo ""
echo "🧪 To test I2P crawling, run:"
echo "kubectl create job --from=cronjob/noctipede-crawler test-i2p -n noctipede"
echo ""
echo "📊 To check results:"
echo "kubectl exec -it deployment/mariadb -n noctipede -- mysql -u splinter-research -p -e 'SELECT COUNT(*) FROM splinter-research.pages WHERE url LIKE \"%.i2p%\";'"
