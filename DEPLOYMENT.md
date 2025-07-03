# Noctipede Deployment Guide

## Quick Start

### Docker Compose (Recommended for Development)

1. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Ollama endpoint and other settings
   ```

2. **Deploy**
   ```bash
   docker-compose up -d
   ```

3. **Access**
   - Web Interface: http://localhost:8080
   - MinIO Console: http://localhost:9001
   - MariaDB: localhost:3306

### Kubernetes (Production)

1. **Prerequisites**
   - Kubernetes cluster with MariaDB Operator
   - MinIO Operator
   - Longhorn or similar storage provider

2. **Deploy**
   ```bash
   ./deploy.sh
   ```

3. **Access**
   ```bash
   kubectl port-forward service/noctipede-web-service 8080:8080 -n noctipede
   ```

## Configuration

### Required Environment Variables

- `MARIADB_PASSWORD` - Database password
- `MINIO_ACCESS_KEY` - MinIO access key  
- `MINIO_SECRET_KEY` - MinIO secret key
- `OLLAMA_ENDPOINT` - Your Ollama API endpoint

### Image Format Support

Noctipede has enhanced support for image formats commonly used on Tor and I2P networks:

- **WebP** (prioritized - very common on dark web)
- **JPEG/JPG** (standard format)
- **PNG** (with transparency support)
- **GIF** (including animated GIFs)
- **BMP, TIFF** (legacy formats)
- **SVG** (vector graphics)

The system automatically:
- Validates image integrity and safety
- Converts formats for optimal AI analysis
- Handles animated WebP and GIF files
- Extracts metadata for forensic analysis

### Sites Configuration

Create `/app/data/sites.txt` with URLs to crawl:
```
http://example.com
https://httpbin.org
# Add your .onion and .i2p sites here
```

## Usage

### Running the Crawler
```bash
# Docker
docker exec -it noctipede-app python -m noctipede.crawlers.main

# Kubernetes  
kubectl exec -it deployment/noctipede-app -n noctipede -- python -m noctipede.crawlers.main
```

### Running Analysis
```bash
# Image analysis
docker exec -it noctipede-app python -m noctipede.analysis.image_analyzer

# Content moderation
docker exec -it noctipede-app python -m noctipede.analysis.content_moderator
```

## Monitoring

### Logs
```bash
# Docker
docker logs noctipede-app
docker logs noctipede-web

# Kubernetes
kubectl logs -f deployment/noctipede-app -n noctipede
kubectl logs -f deployment/noctipede-web -n noctipede
```

### Health Checks
- Health: http://localhost:8080/health
- Readiness: http://localhost:8080/ready

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check MariaDB is running
   - Verify credentials in secrets
   - Check network connectivity

2. **MinIO Connection Failed**
   - Verify MinIO is running
   - Check access keys
   - Ensure bucket exists

3. **Ollama Connection Failed**
   - Verify Ollama endpoint is accessible
   - Check required models are installed
   - Test with curl: `curl -X POST http://your-ollama:11434/api/generate`

### Reset Database
```bash
# Docker
docker exec -it noctipede-app python -c "from database import get_db_manager; get_db_manager().create_tables()"

# Kubernetes
kubectl exec -it deployment/noctipede-app -n noctipede -- python -c "from database import get_db_manager; get_db_manager().create_tables()"
```

## Security Notes

- Change default passwords in production
- Use proper network policies in Kubernetes
- Restrict access to MinIO and MariaDB
- Monitor for flagged content regularly
- Keep Ollama service isolated and secure
