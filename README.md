# Noctipede - Deep Web Analysis System

A modular, scalable system for crawling, analyzing, and reporting on deep web content with advanced AI-powered content moderation capabilities.

## Overview

Noctipede is a comprehensive solution for accessing, storing, and analyzing content from various web sources, including deep web .onion and .i2p sites. The system has been refactored into modular components for better maintainability and scalability.

### Key Features

- **Multi-Network Crawling**: Support for standard web, Tor (.onion), and I2P networks
- **Modular Architecture**: Clean separation of concerns across multiple modules
- **Content Storage**: Structured database storage with MariaDB and object storage with MinIO
- **AI-Powered Analysis**: Multi-model AI analysis of text and images
- **Content Moderation**: Detection of potentially illicit content with multi-stage filtering
- **Scalable Deployment**: Docker Compose and Kubernetes deployment options

## Architecture

### Core Modules

- `core/` - Core functionality and shared utilities
- `crawlers/` - Web crawling engines for different networks
- `database/` - Database models and connection management
- `storage/` - MinIO object storage integration
- `analysis/` - AI analysis and content moderation
- `portal/` - Web portal for live metrics and monitoring
- `config/` - Configuration management

## Prerequisites

- Docker and Docker Compose (for containerized deployment)
- Kubernetes cluster (for K8s deployment)
- Ollama service with required AI models (external requirement)
- MariaDB database (included in deployments)
- MinIO object storage (included in deployments)

## AI Models

The system uses multiple AI models for different tasks:

1. **llama3.2-vision:11b** - Multimodal model for image description generation
2. **gemma3:12b** - Text model for content analysis and understanding
3. **llama3.1:8b** - Efficient model for content moderation and illicit content detection

All models are served via an external Ollama instance that must be configured separately.

## Environment Variables

### Database Configuration
- `MARIADB_HOST` - MariaDB server hostname (default: `mariadb`)
- `MARIADB_PORT` - MariaDB server port (default: `3306`)
- `MARIADB_USER` - Database username (default: `splinter-research`)
- `MARIADB_PASSWORD` - Database password (required)
- `MARIADB_DATABASE` - Database name (default: `splinter-research`)
- `MARIADB_ROOT_PASSWORD` - Root password for MariaDB (required for setup)

### MinIO Configuration
- `MINIO_ENDPOINT` - MinIO server endpoint (default: `minio:9000`)
- `MINIO_ACCESS_KEY` - MinIO access key (required)
- `MINIO_SECRET_KEY` - MinIO secret key (required)
- `MINIO_BUCKET_NAME` - Default bucket name (default: `noctipede-data`)
- `MINIO_SECURE` - Use HTTPS for MinIO connection (default: `false`)

### AI/Ollama Configuration
- `OLLAMA_ENDPOINT` - Ollama API endpoint (required)
- `OLLAMA_VISION_MODEL` - Vision model name (default: `llama3.2-vision:11b`)
- `OLLAMA_TEXT_MODEL` - Text analysis model (default: `gemma3:12b`)
- `OLLAMA_MODERATION_MODEL` - Content moderation model (default: `llama3.1:8b`)

### Crawler Configuration
- `MAX_LINKS_PER_PAGE` - Maximum links to extract per page (default: `50`)
- `MAX_QUEUE_SIZE` - Maximum crawler queue size (default: `500`)
- `CRAWL_DELAY_SECONDS` - Delay between requests in seconds (default: `3`)
- `SKIP_RECENT_CRAWLS` - Skip recently crawled sites (default: `true`)
- `RECENT_CRAWL_HOURS` - Hours to consider "recent" (default: `24`)
- `MAX_CONCURRENT_CRAWLERS` - Maximum concurrent crawler threads (default: `10`)

### Network Configuration
- `TOR_PROXY_HOST` - Tor SOCKS proxy host (default: `127.0.0.1`)
- `TOR_PROXY_PORT` - Tor SOCKS proxy port (default: `9050`)
- `I2P_PROXY_HOST` - I2P HTTP proxy host (default: `127.0.0.1`)
- `I2P_PROXY_PORT` - I2P HTTP proxy port (default: `4444`)
- `I2P_INTERNAL_PROXIES` - Comma-separated list of I2P internal proxies

### Application Configuration
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `OUTPUT_DIR` - Output directory for reports (default: `/app/output`)
- `SITES_FILE_PATH` - Path to sites.txt file (default: `/app/data/sites.txt`)
- `WEB_SERVER_PORT` - Web server port (default: `8080`)
- `WEB_SERVER_HOST` - Web server host (default: `0.0.0.0`)

### Content Analysis Configuration
- `CONTENT_ANALYSIS_ENABLED` - Enable content analysis (default: `true`)
- `IMAGE_ANALYSIS_ENABLED` - Enable image analysis (default: `true`)
- `MODERATION_THRESHOLD` - Content moderation threshold (default: `30`)
- `MAX_IMAGE_SIZE_MB` - Maximum image size for analysis in MB (default: `10`)
- `SUPPORTED_IMAGE_FORMATS` - Comma-separated list of supported formats (default: `webp,jpg,jpeg,png,gif,bmp,tiff,svg`)

**Note**: WebP format is prioritized as it's commonly used on Tor and I2P networks. The system includes enhanced WebP processing with support for animated WebP files.

### Performance Configuration
- `DB_POOL_SIZE` - Database connection pool size (default: `20`)
- `DB_MAX_OVERFLOW` - Database connection pool overflow (default: `30`)
- `WORKER_THREADS` - Number of worker threads (default: `4`)
- `BATCH_SIZE` - Batch processing size (default: `100`)

## Deployment Options

![Noctipede System Overview](imgs/docker-1.png)

### 1. Docker Compose Deployment

#### Quick Start
```bash
# Clone and setup
git clone <repository-url> noctipede
cd noctipede

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Start services
docker-compose up -d
```

#### Services Included
- **noctipede-app**: Main application container
- **mariadb**: Database server
- **minio**: Object storage server
- **noctipede-portal**: Web dashboard for live metrics

![Docker Compose Services](imgs/docker-2.png)

### 2. Kubernetes Deployment

#### Prerequisites
- Kubernetes cluster with kubectl configured
- External Ollama service accessible via network
- Storage provisioner for PersistentVolumes

#### Deployment Steps
```bash
# Quick deployment with automated script
cd k8s/
./deploy.sh

# Or manual step-by-step deployment
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/mariadb/
kubectl apply -f k8s/minio/
kubectl apply -f k8s/proxy/          # NEW: Proxy services
kubectl apply -f k8s/noctipede/

# Test the deployment
./test-deployment.sh
```

#### New Features in K8s Deployment
- **🧅 Tor Proxy Service**: Dedicated SOCKS5 proxy for .onion sites
- **🌐 I2P Proxy Service**: HTTP proxy for .i2p network access  
- **🔄 Init Containers**: Automatic service dependency management
- **📊 Live Metrics Portal**: Real-time system monitoring dashboard
- **🔒 Fixed Session Management**: Resolved database concurrency issues
- **🚀 Automated Deployment**: One-command deployment with health checks

![Kubernetes Deployment](imgs/kube.png)

### 3. GitHub Container Registry Deployment

The project supports automated building and publishing of Docker images to GitHub Container Registry (GHCR) for easy distribution and deployment.

#### Prerequisites
- GitHub Personal Access Token with `write:packages` scope
- Docker installed locally
- Access to the GitHub repository

#### Manual Build and Push
```bash
# Show repository and image information
make ghcr-info

# Login to GitHub Container Registry
make ghcr-login

# Build, tag, and push image to GHCR
make ghcr-deploy
```

#### Using Pre-built Images
```bash
# Pull the latest image
docker pull ghcr.io/splinterstice/noctipede:latest

# Run with Docker Compose using GHCR image
make run-ghcr

# Deploy to Kubernetes using GHCR image
make k8s-deploy-ghcr
```

#### Automated CI/CD
The repository includes a GitHub Actions workflow that automatically:
- Builds Docker images on push to main/develop branches
- Tags images with version numbers for releases
- Publishes to GitHub Container Registry
- Provides deployment summaries

Images are available at: `ghcr.io/splinterstice/noctipede`

## Usage

### Running the Crawler
```bash
# Docker
docker exec -it noctipede-app python -m noctipede.crawlers.main

# Kubernetes
kubectl exec -it deployment/noctipede-app -- python -m noctipede.crawlers.main
```

### Running Analysis
```bash
# Image analysis
docker exec -it noctipede-app python -m noctipede.analysis.image_analyzer

# Content moderation
docker exec -it noctipede-app python -m noctipede.analysis.content_moderator --threshold 30
```

### Web Portal
- Docker: http://localhost:8080
- Kubernetes: Use Service IP or configured Ingress

The web portal provides live metrics and monitoring including:
- Real-time crawler statistics
- Network type breakdown (clearnet, tor, i2p)
- Site status monitoring
- Recent crawl activity
- Top domains by page count
- System health indicators
- **AI-Powered Reports**: Natural language querying of crawled data

![Web Portal Dashboard](imgs/docker-3.png)

## Sites Configuration

The system expects a `sites.txt` file containing URLs to crawl, one per line. This file should be mounted as a volume or stored in a PersistentVolume.

Example `sites.txt`:
```
http://example.com
http://3g2upl4pq6kufc4m.onion
http://example.i2p
```

## Security Considerations

- Ensure proper access controls on all deployment platforms
- Regularly rotate database and MinIO credentials
- Restrict network access to the Ollama service
- Review generated reports regularly for moderation
- Use secure and isolated environments for AI services
- Monitor resource usage and set appropriate limits

## Development

### Local Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with local configuration

# Run tests
pytest tests/
```

### Code Structure
```
noctipede/
├── core/           # Core utilities and shared code
├── crawlers/       # Web crawling engines
├── database/       # Database models and management
├── storage/        # MinIO integration
├── analysis/       # AI analysis modules
├── api/           # Web API and interfaces
├── config/        # Configuration management
└── tests/         # Test suites
```

## License

This project is proprietary and confidential.

## Support

For support and questions, please contact the development team.
