"""Enhanced Noctipede Portal with comprehensive metrics."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from portal.metrics_collector_enhanced import get_comprehensive_metrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Noctipede Enhanced Portal",
    description="Comprehensive monitoring and metrics for Noctipede deep web crawler",
    version="2.0.0"
)

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the enhanced dashboard."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Noctipede Enhanced Portal</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; 
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .header p { font-size: 1.2em; opacity: 0.9; }
        
        .metrics-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        
        .metric-card { 
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; 
            padding: 20px; 
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease;
        }
        .metric-card:hover { transform: translateY(-5px); }
        
        .metric-card h3 { 
            font-size: 1.3em; 
            margin-bottom: 15px; 
            color: #ffd700;
            border-bottom: 2px solid rgba(255,215,0,0.3);
            padding-bottom: 8px;
        }
        
        .metric-row { 
            display: flex; 
            justify-content: space-between; 
            margin: 8px 0; 
            padding: 5px 0;
        }
        .metric-label { font-weight: 500; }
        .metric-value { 
            font-weight: bold; 
            color: #4ade80;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-connected { background-color: #22c55e; }
        .status-error { background-color: #ef4444; }
        .status-warning { background-color: #f59e0b; }
        .status-timeout { background-color: #6b7280; }
        
        .pressure-normal { color: #22c55e; }
        .pressure-low { color: #84cc16; }
        .pressure-medium { color: #f59e0b; }
        .pressure-high { color: #ef4444; }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: rgba(255,255,255,0.2);
            border-radius: 10px;
            overflow: hidden;
            margin: 5px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #22c55e, #16a34a);
            transition: width 0.3s ease;
        }
        
        .update-info { 
            text-align: center; 
            margin-top: 20px; 
            opacity: 0.8; 
            font-size: 0.9em;
        }
        
        .error-message {
            background-color: rgba(239, 68, 68, 0.2);
            border: 1px solid #ef4444;
            border-radius: 8px;
            padding: 10px;
            margin: 10px 0;
            color: #fecaca;
        }
        
        .loading {
            text-align: center;
            font-size: 1.2em;
            margin: 50px 0;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .loading { animation: pulse 2s infinite; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕷️ Noctipede Enhanced Portal</h1>
            <p>Comprehensive Deep Web Crawler Monitoring System</p>
        </div>
        
        <div id="loading" class="loading">
            🔄 Loading comprehensive metrics...
        </div>
        
        <div id="metrics-container" style="display: none;">
            <div class="metrics-grid" id="metrics-grid">
                <!-- Metrics will be populated here -->
            </div>
        </div>
        
        <div class="update-info">
            <p>Last updated: <span id="last-update">Never</span></p>
            <p>Collection time: <span id="collection-time">0</span>s | Auto-refresh: 30s</p>
        </div>
    </div>

    <script>
        let metricsData = {};
        
        async function fetchMetrics() {
            try {
                const response = await fetch('/api/comprehensive-metrics');
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                metricsData = await response.json();
                updateDashboard();
                
                document.getElementById('loading').style.display = 'none';
                document.getElementById('metrics-container').style.display = 'block';
                
            } catch (error) {
                console.error('Error fetching metrics:', error);
                showError('Failed to fetch metrics: ' + error.message);
            }
        }
        
        function updateDashboard() {
            const grid = document.getElementById('metrics-grid');
            grid.innerHTML = '';
            
            // System Metrics
            if (metricsData.system) {
                grid.appendChild(createSystemCard(metricsData.system));
            }
            
            // Health Overview
            if (metricsData.health) {
                grid.appendChild(createHealthCard(metricsData.health));
            }
            
            // Database Metrics
            if (metricsData.database) {
                grid.appendChild(createDatabaseCard(metricsData.database));
            }
            
            // MinIO Metrics
            if (metricsData.minio) {
                grid.appendChild(createMinIOCard(metricsData.minio));
            }
            
            // Ollama Metrics
            if (metricsData.ollama) {
                grid.appendChild(createOllamaCard(metricsData.ollama));
            }
            
            // Crawler Metrics
            if (metricsData.crawler) {
                grid.appendChild(createCrawlerCard(metricsData.crawler));
            }
            
            // Network Metrics
            if (metricsData.network) {
                grid.appendChild(createNetworkCard(metricsData.network));
            }
            
            // Update timestamp
            document.getElementById('last-update').textContent = new Date().toLocaleString();
            document.getElementById('collection-time').textContent = metricsData.collection_time || 0;
        }
        
        function createSystemCard(system) {
            const card = document.createElement('div');
            card.className = 'metric-card';
            card.innerHTML = `
                <h3>🖥️ System Resources</h3>
                <div class="metric-row">
                    <span class="metric-label">CPU Usage:</span>
                    <span class="metric-value">${system.cpu?.usage_percent || 0}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${system.cpu?.usage_percent || 0}%"></div>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Memory Usage:</span>
                    <span class="metric-value">${system.memory?.usage_percent || 0}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${system.memory?.usage_percent || 0}%"></div>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Disk Usage:</span>
                    <span class="metric-value">${system.disk?.usage_percent || 0}%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Processes:</span>
                    <span class="metric-value">${system.processes || 0}</span>
                </div>
            `;
            return card;
        }
        
        function createHealthCard(health) {
            const card = document.createElement('div');
            card.className = 'metric-card';
            
            let servicesHtml = '';
            for (const [service, status] of Object.entries(health.services || {})) {
                const statusClass = `status-${status}`;
                servicesHtml += `
                    <div class="metric-row">
                        <span class="metric-label">
                            <span class="status-indicator ${statusClass}"></span>
                            ${service}:
                        </span>
                        <span class="metric-value">${status}</span>
                    </div>
                `;
            }
            
            card.innerHTML = `
                <h3>🏥 System Health</h3>
                <div class="metric-row">
                    <span class="metric-label">Overall Status:</span>
                    <span class="metric-value">${health.overall_status || 'unknown'}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Health Score:</span>
                    <span class="metric-value">${health.health_percentage || 0}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${health.health_percentage || 0}%"></div>
                </div>
                ${servicesHtml}
            `;
            return card;
        }
        
        function createDatabaseCard(database) {
            const card = document.createElement('div');
            card.className = 'metric-card';
            
            if (database.error) {
                card.innerHTML = `
                    <h3>🗄️ Database</h3>
                    <div class="error-message">Error: ${database.error}</div>
                `;
                return card;
            }
            
            const pressureClass = `pressure-${database.database_pressure || 'normal'}`;
            
            card.innerHTML = `
                <h3>🗄️ Database</h3>
                <div class="metric-row">
                    <span class="metric-label">Status:</span>
                    <span class="metric-value">${database.status || 'unknown'}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Connections:</span>
                    <span class="metric-value">${database.connections || 0}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Database Size:</span>
                    <span class="metric-value">${database.database_size_mb || 0} MB</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Pressure:</span>
                    <span class="metric-value ${pressureClass}">${database.database_pressure || 'normal'}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Buffer Hit Ratio:</span>
                    <span class="metric-value">${database.pressure?.buffer_pool_hit_ratio || 0}%</span>
                </div>
            `;
            return card;
        }
        
        function createMinIOCard(minio) {
            const card = document.createElement('div');
            card.className = 'metric-card';
            
            if (minio.error) {
                card.innerHTML = `
                    <h3>🗂️ MinIO Storage</h3>
                    <div class="error-message">Error: ${minio.error}</div>
                `;
                return card;
            }
            
            const pressureClass = `pressure-${minio.minio_pressure || 'normal'}`;
            
            card.innerHTML = `
                <h3>🗂️ MinIO Storage</h3>
                <div class="metric-row">
                    <span class="metric-label">Status:</span>
                    <span class="metric-value">${minio.status || 'unknown'}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Total Objects:</span>
                    <span class="metric-value">${minio.total_objects || 0}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Total Size:</span>
                    <span class="metric-value">${minio.total_size_mb || 0} MB</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Buckets:</span>
                    <span class="metric-value">${minio.buckets || 0}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Pressure:</span>
                    <span class="metric-value ${pressureClass}">${minio.minio_pressure || 'normal'}</span>
                </div>
            `;
            return card;
        }
        
        function createOllamaCard(ollama) {
            const card = document.createElement('div');
            card.className = 'metric-card';
            
            if (ollama.error) {
                card.innerHTML = `
                    <h3>🤖 Ollama AI</h3>
                    <div class="error-message">Error: ${ollama.error}</div>
                `;
                return card;
            }
            
            const pressureClass = `pressure-${ollama.ollama_pressure || 'normal'}`;
            
            card.innerHTML = `
                <h3>🤖 Ollama AI</h3>
                <div class="metric-row">
                    <span class="metric-label">Status:</span>
                    <span class="metric-value">${ollama.status || 'unknown'}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Available Models:</span>
                    <span class="metric-value">${ollama.model_count || 0}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Running Models:</span>
                    <span class="metric-value">${ollama.running_models || 0}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Pressure:</span>
                    <span class="metric-value ${pressureClass}">${ollama.ollama_pressure || 'normal'}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Version:</span>
                    <span class="metric-value">${ollama.version || 'unknown'}</span>
                </div>
            `;
            return card;
        }
        
        function createCrawlerCard(crawler) {
            const card = document.createElement('div');
            card.className = 'metric-card';
            
            if (crawler.error) {
                card.innerHTML = `
                    <h3>🕷️ Crawler Status</h3>
                    <div class="error-message">Error: ${crawler.error}</div>
                `;
                return card;
            }
            
            const progress = crawler.progress || {};
            const performance = crawler.performance || {};
            
            card.innerHTML = `
                <h3>🕷️ Crawler Status</h3>
                <div class="metric-row">
                    <span class="metric-label">Total Sites:</span>
                    <span class="metric-value">${progress.total_sites || 0}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Total Pages:</span>
                    <span class="metric-value">${progress.total_pages || 0}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Success Rate:</span>
                    <span class="metric-value">${performance.success_rate || 0}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${performance.success_rate || 0}%"></div>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Recent Errors:</span>
                    <span class="metric-value">${crawler.errors || 0}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Hits vs Misses:</span>
                    <span class="metric-value">${performance.hits || 0} / ${performance.misses || 0}</span>
                </div>
            `;
            return card;
        }
        
        function createNetworkCard(network) {
            const card = document.createElement('div');
            card.className = 'metric-card';
            
            const tor = network.tor || {};
            const i2p = network.i2p || {};
            const i2pProxy = network.i2p_proxy || {};
            
            card.innerHTML = `
                <h3>🌐 Network Connectivity</h3>
                <div class="metric-row">
                    <span class="metric-label">
                        <span class="status-indicator status-${tor.status || 'error'}"></span>
                        Tor Network:
                    </span>
                    <span class="metric-value">${tor.status || 'unknown'}</span>
                </div>
                ${tor.response_time_ms ? `
                <div class="metric-row">
                    <span class="metric-label">Tor Response Time:</span>
                    <span class="metric-value">${tor.response_time_ms}ms</span>
                </div>` : ''}
                <div class="metric-row">
                    <span class="metric-label">
                        <span class="status-indicator status-${i2p.status || 'error'}"></span>
                        I2P Network:
                    </span>
                    <span class="metric-value">${i2p.status || 'unknown'}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">
                        <span class="status-indicator status-${i2pProxy.status || 'error'}"></span>
                        I2P Proxy:
                    </span>
                    <span class="metric-value">${i2pProxy.status || 'unknown'}</span>
                </div>
            `;
            return card;
        }
        
        function showError(message) {
            const container = document.getElementById('metrics-container');
            container.innerHTML = `<div class="error-message">${message}</div>`;
            container.style.display = 'block';
            document.getElementById('loading').style.display = 'none';
        }
        
        // Initial load and auto-refresh
        fetchMetrics();
        setInterval(fetchMetrics, 30000); // Refresh every 30 seconds
    </script>
</body>
</html>
    """

@app.get("/api/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "noctipede-enhanced-portal", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/comprehensive-metrics")
async def get_metrics():
    """Get comprehensive system metrics."""
    try:
        metrics = await get_comprehensive_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect metrics: {str(e)}")

@app.get("/api/system-metrics")
async def get_system_metrics():
    """Get system-level metrics only."""
    try:
        metrics = await get_comprehensive_metrics()
        return JSONResponse(content={
            "timestamp": metrics.get("timestamp"),
            "system": metrics.get("system", {}),
            "health": metrics.get("health", {})
        })
    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect system metrics: {str(e)}")

@app.get("/api/crawler-metrics")
async def get_crawler_metrics():
    """Get crawler-specific metrics."""
    try:
        metrics = await get_comprehensive_metrics()
        return JSONResponse(content={
            "timestamp": metrics.get("timestamp"),
            "crawler": metrics.get("crawler", {}),
            "network": metrics.get("network", {})
        })
    except Exception as e:
        logger.error(f"Error collecting crawler metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect crawler metrics: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "portal.main_enhanced:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )
