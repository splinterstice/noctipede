# AI Reports Component - Context & Implementation Guide

## Overview
The AI Reports component is a comprehensive data analysis and reporting system that integrates multiple advanced features for analyzing crawled web data. It provides dataset management, query capabilities, AI-powered analysis, and visual reporting tools.

## Component Architecture

### 1. **MemeCLIP Integration (Top Right Corner)**
- **Repository**: https://github.com/SiddhantBikram/MemeCLIP
- **Purpose**: Advanced image analysis and meme detection
- **Integration**: Embedded widget/iframe for real-time image analysis
- **Features**:
  - Image classification and similarity search
  - Meme detection and categorization
  - Visual content analysis
  - Integration with crawled media files

### 2. **Dataset Generator (Top Left)**
- **Purpose**: Create and manage datasets from crawled data
- **Features**:
  - Real-time dataset creation during crawling
  - Data filtering and selection criteria
  - Automated partitioning by website/domain
  - Snapshot creation for point-in-time analysis
  - Export to various formats (Parquet, HIVE, JSON)

### 3. **Dataset Management (Left Center)**
- **CRUD Operations**:
  - **Create**: New datasets with custom schemas
  - **Read**: Browse and preview existing datasets
  - **Update**: Modify dataset configurations and metadata
  - **Delete**: Remove datasets with confirmation
- **Features**:
  - Dataset versioning and history
  - Metadata management
  - Access control and permissions
  - Dataset sharing and collaboration

### 4. **Query Engine (Top Center)**
- **AWS Athena-like Implementation**: Presto/Trino-based query engine
- **Data Source**: S3-compatible MinIO storage
- **Features**:
  - SQL query interface
  - Query history and favorites
  - Query optimization and caching
  - Real-time query execution
  - Result export capabilities

### 5. **Results Display (Center Bottom)**
- **Query Results**: Tabular and visual data presentation
- **Report Generation**: AI-powered custom reports
- **Screenshot Integration**: Webpage screenshots for each site
- **Features**:
  - Interactive data visualization
  - Export to multiple formats
  - Drill-down capabilities
  - Real-time updates

## Technical Implementation

### Database Schema Extensions

```sql
-- Dataset Management Tables
CREATE TABLE datasets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    schema_definition JSON,
    partition_strategy VARCHAR(50), -- 'by_domain', 'by_date', 'by_network'
    storage_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'archived', 'processing'
    record_count BIGINT DEFAULT 0,
    size_bytes BIGINT DEFAULT 0
);

-- Dataset Partitions for HIVE compatibility
CREATE TABLE dataset_partitions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    dataset_id INT,
    partition_key VARCHAR(255), -- domain, date, network_type
    partition_value VARCHAR(255),
    storage_path VARCHAR(500),
    record_count BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

-- Query History and Management
CREATE TABLE query_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    query_text LONGTEXT NOT NULL,
    query_hash VARCHAR(64), -- SHA-256 for deduplication
    dataset_ids JSON, -- Array of dataset IDs used
    execution_time_ms BIGINT,
    result_count BIGINT,
    status VARCHAR(20), -- 'running', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);

-- Screenshot Management
CREATE TABLE site_screenshots (
    id INT PRIMARY KEY AUTO_INCREMENT,
    site_id INT,
    page_id INT,
    dataset_id INT,
    screenshot_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    capture_timestamp TIMESTAMP,
    viewport_width INT DEFAULT 1920,
    viewport_height INT DEFAULT 1080,
    file_size BIGINT,
    storage_path VARCHAR(500),
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (page_id) REFERENCES pages(id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
);

-- MemeCLIP Analysis Results
CREATE TABLE memeclip_analysis (
    id INT PRIMARY KEY AUTO_INCREMENT,
    media_file_id INT,
    dataset_id INT,
    classification_result JSON,
    similarity_scores JSON,
    meme_detected BOOLEAN DEFAULT FALSE,
    confidence_score FLOAT,
    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (media_file_id) REFERENCES media_files(id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
);
```

### File Structure

```
noctipede/
├── ai_reports/
│   ├── __init__.py
│   ├── dataset_manager.py      # Dataset CRUD operations
│   ├── query_engine.py         # Presto/Athena-like query engine
│   ├── memeclip_integration.py # MemeCLIP wrapper
│   ├── screenshot_service.py   # Website screenshot capture
│   ├── report_generator.py     # AI-powered report generation
│   ├── hive_exporter.py        # HIVE format export
│   └── partitioning.py         # Data partitioning logic
├── api/
│   └── ai_reports.py           # AI Reports API endpoints
├── portal/
│   └── templates/
│       └── ai_reports.html     # Main AI Reports interface
└── static/
    └── ai_reports/
        ├── css/
        ├── js/
        └── components/
```

## Component Layout Specification

### HTML Structure
```html
<div class="ai-reports-container">
  <!-- Top Row -->
  <div class="top-row">
    <div class="dataset-generator">
      <!-- Dataset Generation Controls -->
    </div>
    <div class="query-engine">
      <!-- SQL Query Interface -->
    </div>
    <div class="memeclip-widget">
      <!-- MemeCLIP Integration -->
    </div>
  </div>
  
  <!-- Middle Row -->
  <div class="middle-row">
    <div class="dataset-management">
      <!-- CRUD Operations Panel -->
    </div>
    <div class="results-display">
      <!-- Query Results & Reports -->
    </div>
  </div>
</div>
```

### CSS Grid Layout
```css
.ai-reports-container {
  display: grid;
  grid-template-rows: 300px 1fr;
  grid-template-columns: 300px 1fr 300px;
  height: 100vh;
  gap: 10px;
}

.top-row {
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  grid-column: 1 / -1;
}

.middle-row {
  display: grid;
  grid-template-columns: 300px 1fr;
  grid-column: 1 / -1;
}
```

## Integration Requirements

### 1. **MemeCLIP Integration**
```python
# memeclip_integration.py
import subprocess
import json
from typing import Dict, List, Optional

class MemeCLIPService:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.setup_environment()
    
    def setup_environment(self):
        """Setup MemeCLIP environment and dependencies"""
        # Clone and setup MemeCLIP repository
        # Install dependencies
        # Load pre-trained models
        pass
    
    def analyze_image(self, image_path: str) -> Dict:
        """Analyze image using MemeCLIP"""
        # Implementation for image analysis
        pass
    
    def batch_analyze(self, image_paths: List[str]) -> List[Dict]:
        """Batch analyze multiple images"""
        pass
```

### 2. **Query Engine (Presto/Trino-like)**
```python
# query_engine.py
from trino import dbapi
import pandas as pd
from typing import Dict, List, Any

class QueryEngine:
    def __init__(self, catalog_config: Dict):
        self.catalog_config = catalog_config
        self.setup_catalogs()
    
    def setup_catalogs(self):
        """Setup data catalogs for MinIO/S3 data"""
        # Configure Hive metastore
        # Setup MinIO connector
        pass
    
    def execute_query(self, sql: str) -> pd.DataFrame:
        """Execute SQL query against partitioned data"""
        pass
    
    def create_table_from_dataset(self, dataset_id: int):
        """Create external table for dataset"""
        pass
```

### 3. **Dataset Management**
```python
# dataset_manager.py
from typing import Dict, List, Optional
from database import get_db_session
from .hive_exporter import HiveExporter
from .partitioning import PartitionManager

class DatasetManager:
    def __init__(self):
        self.hive_exporter = HiveExporter()
        self.partition_manager = PartitionManager()
    
    def create_dataset(self, config: Dict) -> int:
        """Create new dataset with partitioning"""
        pass
    
    def update_dataset(self, dataset_id: int, config: Dict):
        """Update dataset configuration"""
        pass
    
    def delete_dataset(self, dataset_id: int):
        """Delete dataset and cleanup storage"""
        pass
    
    def export_to_hive(self, dataset_id: int) -> str:
        """Export dataset to HIVE format"""
        pass
```

### 4. **Screenshot Service**
```python
# screenshot_service.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import asyncio
from typing import Optional

class ScreenshotService:
    def __init__(self):
        self.setup_driver()
    
    def setup_driver(self):
        """Setup headless Chrome driver"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)
    
    async def capture_screenshot(self, url: str, output_path: str) -> Optional[str]:
        """Capture website screenshot"""
        pass
    
    def capture_batch(self, urls: List[str]) -> List[str]:
        """Batch capture screenshots"""
        pass
```

## API Endpoints

### Dataset Management
- `POST /api/ai-reports/datasets` - Create dataset
- `GET /api/ai-reports/datasets` - List datasets
- `GET /api/ai-reports/datasets/{id}` - Get dataset details
- `PUT /api/ai-reports/datasets/{id}` - Update dataset
- `DELETE /api/ai-reports/datasets/{id}` - Delete dataset
- `POST /api/ai-reports/datasets/{id}/export-hive` - Export to HIVE

### Query Engine
- `POST /api/ai-reports/query` - Execute SQL query
- `GET /api/ai-reports/query-history` - Get query history
- `GET /api/ai-reports/catalogs` - List available catalogs
- `GET /api/ai-reports/tables` - List available tables

### MemeCLIP Integration
- `POST /api/ai-reports/memeclip/analyze` - Analyze single image
- `POST /api/ai-reports/memeclip/batch-analyze` - Batch analyze images
- `GET /api/ai-reports/memeclip/results/{id}` - Get analysis results

### Screenshots
- `POST /api/ai-reports/screenshots/capture` - Capture screenshot
- `GET /api/ai-reports/screenshots/{site_id}` - Get site screenshots
- `POST /api/ai-reports/screenshots/batch` - Batch capture

## Environment Variables

```bash
# AI Reports Configuration
AI_REPORTS_ENABLED=true
MEMECLIP_MODEL_PATH=/app/models/memeclip
QUERY_ENGINE_TYPE=trino  # trino, presto, athena
HIVE_METASTORE_URI=thrift://hive-metastore:9083
SCREENSHOT_SERVICE_ENABLED=true
SCREENSHOT_STORAGE_PATH=/app/screenshots
DATASET_STORAGE_PATH=/app/datasets

# Trino/Presto Configuration
TRINO_COORDINATOR_URL=http://trino:8080
TRINO_CATALOG_CONFIG=/app/config/trino-catalogs.json

# MemeCLIP Configuration
MEMECLIP_BATCH_SIZE=32
MEMECLIP_GPU_ENABLED=false
MEMECLIP_MODEL_CACHE=/app/cache/memeclip
```

## Deployment Considerations

### Docker Extensions
```dockerfile
# Add to existing Dockerfile
RUN apt-get update && apt-get install -y \
    # Screenshot dependencies
    chromium-browser \
    chromium-chromedriver \
    # MemeCLIP dependencies
    python3-opencv \
    libgl1-mesa-glx \
    # Trino/Presto dependencies
    openjdk-11-jre-headless

# Install MemeCLIP
RUN git clone https://github.com/SiddhantBikram/MemeCLIP.git /app/memeclip && \
    cd /app/memeclip && \
    pip install -r requirements.txt
```

### Kubernetes Resources
```yaml
# Additional services needed
apiVersion: v1
kind: Service
metadata:
  name: trino-coordinator
spec:
  ports:
  - port: 8080
    targetPort: 8080
  selector:
    app: trino-coordinator

---
apiVersion: v1
kind: Service
metadata:
  name: hive-metastore
spec:
  ports:
  - port: 9083
    targetPort: 9083
  selector:
    app: hive-metastore
```

## Security & Performance

### Security Considerations
- Query execution sandboxing
- Dataset access controls
- Screenshot capture rate limiting
- MemeCLIP model security

### Performance Optimizations
- Query result caching
- Parallel screenshot capture
- Batch MemeCLIP processing
- Partitioned data storage

## Integration Points

### With Existing Components
- **Crawlers**: Automatic dataset population during crawling
- **Database**: Extended schema for AI Reports data
- **Storage**: HIVE-compatible data organization
- **Portal**: Embedded AI Reports interface
- **API**: Extended endpoints for AI Reports functionality

This context file provides a comprehensive foundation for implementing the AI Reports component with all requested features integrated into the existing Noctipede architecture.
