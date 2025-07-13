# Noctipede Project Structure

## Overview
The project has been completely refactored from the original monolithic structure into a modular, maintainable architecture.

## Directory Structure

```
noctipede/
├── analysis/              # AI analysis modules
│   ├── __init__.py
│   ├── base.py           # Base analyzer class
│   ├── content_moderator.py  # Content moderation
│   ├── image_analyzer.py     # Image analysis
│   ├── manager.py           # Analysis coordination
│   └── text_analyzer.py     # Text analysis
├── api/                   # Web API
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   └── routes.py         # API endpoints
├── config/                # Configuration management
│   ├── __init__.py
│   └── settings.py       # Settings and environment variables
├── core/                  # Core utilities
│   ├── __init__.py
│   ├── logging.py        # Logging configuration
│   └── utils.py          # Utility functions
├── crawlers/              # Web crawling engines
│   ├── __init__.py
│   ├── base.py           # Base crawler class
│   ├── clearnet.py       # Regular web crawler
│   ├── i2p.py            # I2P network crawler
│   ├── main.py           # Crawler entry point
│   ├── manager.py        # Crawler coordination
│   └── tor.py            # Tor network crawler
├── database/              # Database models and management
│   ├── __init__.py
│   ├── connection.py     # Database connection management
│   ├── models.py         # SQLAlchemy models
│   └── session.py        # Session management
├── storage/               # MinIO object storage
│   ├── __init__.py
│   ├── client.py         # MinIO client wrapper
│   └── manager.py        # Storage management
├── tests/                 # Test suites
│   ├── __init__.py
│   └── test_config.py    # Configuration tests
├── k8s/                   # Kubernetes configurations
│   ├── mariadb/          # MariaDB deployment
│   ├── minio/            # MinIO deployment
│   ├── noctipede/        # Application deployment
│   ├── configmap.yaml
│   ├── namespace.yaml
│   └── secrets.yaml
├── docker/                # Docker configurations
│   └── Dockerfile
├── data/                  # Data files
│   └── sites.txt         # Sites to crawl
├── .env.example          # Environment variables template
├── docker-compose.yml    # Docker Compose configuration
├── requirements.txt      # Python dependencies
├── deploy.sh            # Kubernetes deployment script
├── Makefile             # Build and deployment targets
├── README.md            # Main documentation
├── DEPLOYMENT.md        # Deployment guide
└── PROJECT_STRUCTURE.md # This file
```

## Key Improvements

### 1. Modular Architecture
- **Separation of Concerns**: Each module has a specific responsibility
- **Loose Coupling**: Modules interact through well-defined interfaces
- **High Cohesion**: Related functionality is grouped together

### 2. Configuration Management
- **Centralized Settings**: All configuration in one place
- **Environment Variables**: Easy deployment configuration
- **Type Safety**: Pydantic models for configuration validation

### 3. Database Layer
- **Connection Management**: Proper connection pooling and retry logic
- **Session Management**: Thread-safe database sessions
- **Model Organization**: Clean SQLAlchemy models

### 4. Storage Integration
- **MinIO Integration**: Object storage for media files and content
- **Storage Management**: High-level storage operations
- **File Organization**: Hash-based directory structure

### 5. Analysis Framework
- **Pluggable Analyzers**: Easy to add new analysis types
- **Batch Processing**: Efficient processing of multiple items
- **AI Integration**: Clean integration with Ollama models

### 6. Crawler Framework
- **Network-Specific Crawlers**: Separate crawlers for different networks
- **Concurrent Processing**: Multi-threaded crawling
- **Queue Management**: Proper URL queue management

### 7. API Layer
- **RESTful API**: Clean REST endpoints
- **Documentation**: Auto-generated API documentation
- **Health Checks**: Proper health and readiness endpoints

## Migration from Original Code

The original project consisted of several large monolithic files:
- `mcp_engine.py` (214KB) - Split into crawler modules
- `ai_analysis.py` (89KB) - Split into analysis modules  
- `db_models.py` (28KB) - Refactored into database module
- Various analysis scripts - Consolidated into analysis framework

## Benefits of New Structure

1. **Maintainability**: Smaller, focused modules are easier to maintain
2. **Testability**: Each module can be tested independently
3. **Scalability**: Easy to scale individual components
4. **Deployment**: Better containerization and Kubernetes deployment
5. **Development**: Multiple developers can work on different modules
6. **Documentation**: Clear structure makes documentation easier

## Integration Points

### Database Integration
- MariaDB instead of MySQL for better performance
- Connection pooling and retry logic
- Proper transaction management

### Storage Integration  
- MinIO for object storage instead of local files
- Hash-based file organization
- Deduplication support

### AI Integration
- Clean integration with Ollama API
- Support for multiple models
- Batch processing capabilities

### Deployment Integration
- Docker Compose for development
- Kubernetes for production
- Proper secrets management
- Health checks and monitoring
