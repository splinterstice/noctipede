"""
Enhanced Portal with Extended Metrics, AI Reports, and Proxy Status
This extends the existing portal with proxy status API endpoints
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

import aiohttp
import psutil
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Import existing components
sys.path.insert(0, '/app')
from portal.metrics_collector import SystemMetricsCollector
from portal.proxy_status import ProxyStatusChecker
from api.ai_reports import router as ai_reports_router, initialize_default_templates

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedMetricsCollector(SystemMetricsCollector):
    """Enhanced metrics collector that extends the base collector"""
    
    def __init__(self):
        super().__init__()
        self.ollama_config = {
            'endpoint': os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434'),
            'base_url': os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434').replace('/api/generate', '').replace('/api', '')
        }
    
    async def collect_enhanced_metrics(self) -> Dict[str, Any]:
        """Collect enhanced metrics including Ollama and detailed system info"""
        # Get base metrics
        base_metrics = await self.collect_all_metrics()
        
        # Enhance the crawler metrics with additional data
        if 'crawler' in base_metrics:
            base_metrics['crawler'] = await self.enhance_crawler_metrics(base_metrics['crawler'])
        
        # Add Ollama metrics
        base_metrics['ollama'] = await self.collect_ollama_metrics()
        
        # Add detailed system metrics
        base_metrics['system_detailed'] = await self.collect_detailed_system_metrics()
        
        # Add network connectivity
        base_metrics['network'] = await self.collect_network_connectivity()
        
        # Add service pressure metrics
        base_metrics['service_pressure'] = await self.calculate_service_pressure()
        
        return base_metrics
    
    async def enhance_crawler_metrics(self, crawler_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance crawler metrics with additional insights"""
        enhanced = crawler_metrics.copy()
        
        # Add crawl efficiency metrics
        if 'total_pages' in enhanced and 'total_sites' in enhanced:
            enhanced['pages_per_site'] = enhanced['total_pages'] / max(enhanced['total_sites'], 1)
        
        # Add recent activity indicators
        enhanced['last_updated'] = datetime.now().isoformat()
        
        return enhanced
    
    async def collect_ollama_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive Ollama metrics"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get list of models
                try:
                    async with session.get(f"{self.ollama_config['base_url']}/api/tags", timeout=10) as response:
                        if response.status == 200:
                            models_data = await response.json()
                            models = models_data.get('models', [])
                        else:
                            models = []
                except Exception as e:
                    logger.debug(f"Failed to get Ollama models: {e}")
                    models = []
                
                # Get running processes
                try:
                    async with session.get(f"{self.ollama_config['base_url']}/api/ps", timeout=10) as response:
                        if response.status == 200:
                            ps_data = await response.json()
                            running_models = ps_data.get('models', [])
                        else:
                            running_models = []
                except Exception as e:
                    logger.debug(f"Failed to get Ollama processes: {e}")
                    running_models = []
                
                return {
                    "available": True,
                    "endpoint": self.ollama_config['base_url'],
                    "models_count": len(models),
                    "models": [
                        {
                            "name": model.get("name", "unknown"),
                            "size": model.get("size", 0),
                            "modified_at": model.get("modified_at", "")
                        } for model in models
                    ],
                    "running_models_count": len(running_models),
                    "running_models": [
                        {
                            "name": model.get("name", "unknown"),
                            "size": model.get("size", 0),
                            "size_vram": model.get("size_vram", 0)
                        } for model in running_models
                    ],
                    "status": "healthy",
                    "last_checked": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Failed to collect Ollama metrics: {e}")
            return {
                "available": False,
                "endpoint": self.ollama_config['base_url'],
                "error": str(e),
                "status": "error",
                "last_checked": datetime.now().isoformat()
            }
    
    async def collect_detailed_system_metrics(self) -> Dict[str, Any]:
        """Collect detailed system metrics"""
        try:
            # CPU details
            cpu_info = {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "current_freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
                "per_cpu_usage": psutil.cpu_percent(percpu=True, interval=1)
            }
            
            # Memory details
            memory = psutil.virtual_memory()
            memory_info = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percentage": memory.percent,
                "buffers_gb": round(getattr(memory, 'buffers', 0) / (1024**3), 2),
                "cached_gb": round(getattr(memory, 'cached', 0) / (1024**3), 2)
            }
            
            # Disk details
            disk_info = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percentage": round((usage.used / usage.total) * 100, 1)
                    })
                except PermissionError:
                    continue
            
            return {
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to collect detailed system metrics: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    async def collect_network_connectivity(self) -> Dict[str, Any]:
        """Test network connectivity to various services"""
        connectivity_tests = {
            "database": {"host": "mariadb", "port": 3306},
            "minio": {"host": "minio", "port": 9000},
            "tor_proxy": {"host": "tor-proxy", "port": 9150},
            "i2p_proxy": {"host": "i2p-proxy", "port": 4444},
            "ollama": {"host": "ollama.ollama-service.svc.cluster.local", "port": 11434}
        }
        
        results = {}
        for service, config in connectivity_tests.items():
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((config["host"], config["port"]))
                sock.close()
                
                results[service] = {
                    "reachable": result == 0,
                    "host": config["host"],
                    "port": config["port"],
                    "status": "connected" if result == 0 else "unreachable"
                }
            except Exception as e:
                results[service] = {
                    "reachable": False,
                    "host": config["host"],
                    "port": config["port"],
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "services": results,
            "timestamp": datetime.now().isoformat()
        }
    
    async def calculate_service_pressure(self) -> Dict[str, Any]:
        """Calculate service pressure based on resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            # Calculate pressure levels
            cpu_pressure = "high" if cpu_percent > 80 else "medium" if cpu_percent > 60 else "low"
            memory_pressure = "high" if memory_percent > 80 else "medium" if memory_percent > 60 else "low"
            
            # Overall pressure
            overall_pressure = "high" if cpu_pressure == "high" or memory_pressure == "high" else \
                             "medium" if cpu_pressure == "medium" or memory_pressure == "medium" else "low"
            
            return {
                "overall": overall_pressure,
                "cpu": {
                    "usage_percent": cpu_percent,
                    "pressure": cpu_pressure
                },
                "memory": {
                    "usage_percent": memory_percent,
                    "pressure": memory_pressure
                },
                "recommendations": self._get_pressure_recommendations(overall_pressure),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def _get_pressure_recommendations(self, pressure_level: str) -> list:
        """Get recommendations based on pressure level"""
        if pressure_level == "high":
            return [
                "Consider scaling up resources",
                "Check for resource-intensive processes",
                "Monitor for memory leaks",
                "Consider load balancing"
            ]
        elif pressure_level == "medium":
            return [
                "Monitor resource usage trends",
                "Consider optimizing queries",
                "Review crawler concurrency settings"
            ]
        else:
            return ["System resources are operating normally"]

# Initialize components
enhanced_collector = EnhancedMetricsCollector()
proxy_checker = ProxyStatusChecker()

# Create FastAPI app
app = FastAPI(title="Enhanced Noctipede Portal with Proxy Status", version="2.1.0")

# Mount static files and templates
try:
    app.mount("/static", StaticFiles(directory="/app/portal/static"), name="static")
except Exception:
    logger.warning("Static files directory not found")

try:
    templates = Jinja2Templates(directory="/app/portal/templates")
except Exception:
    logger.warning("Templates directory not found")
    templates = None

# Include AI reports router
app.include_router(ai_reports_router, prefix="/api/ai-reports", tags=["ai-reports"])

# Existing API endpoints
@app.get("/")
async def dashboard(request: Request):
    """Main dashboard"""
    if templates:
        return templates.TemplateResponse("dashboard.html", {"request": request})
    else:
        return HTMLResponse("""
        <html>
        <head><title>Enhanced Noctipede Portal</title></head>
        <body>
        <h1>🕷️ Enhanced Noctipede Portal</h1>
        <p>Portal is running. API endpoints available at:</p>
        <ul>
        <li><a href="/api/health">/api/health</a> - Health check</li>
        <li><a href="/api/metrics">/api/metrics</a> - System metrics</li>
        <li><a href="/api/proxy-status">/api/proxy-status</a> - Proxy status</li>
        <li><a href="/api/proxy-readiness">/api/proxy-readiness</a> - Proxy readiness</li>
        <li><a href="/docs">/docs</a> - API documentation</li>
        </ul>
        </body>
        </html>
        """)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.1.0",
        "features": ["metrics", "ai-reports", "proxy-status"]
    }

@app.get("/api/metrics")
async def get_metrics():
    """Get comprehensive system metrics"""
    try:
        metrics = await enhanced_collector.collect_enhanced_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# NEW: Proxy Status API Endpoints
@app.get("/api/proxy-status")
async def get_proxy_status():
    """Get current proxy status for both Tor and I2P"""
    try:
        status = proxy_checker.get_proxy_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Error getting proxy status: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/proxy-readiness")
async def check_proxy_readiness():
    """Check if both proxies are ready for crawling (used by crawler automation)"""
    try:
        readiness = proxy_checker.get_proxy_readiness()
        return JSONResponse(content=readiness)
    except Exception as e:
        logger.error(f"Error checking proxy readiness: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Additional enhanced endpoints
@app.get("/api/ollama")
async def get_ollama_metrics():
    """Get Ollama-specific metrics"""
    try:
        metrics = await enhanced_collector.collect_ollama_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/system-detailed")
async def get_detailed_system_metrics():
    """Get detailed system metrics"""
    try:
        metrics = await enhanced_collector.collect_detailed_system_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/network")
async def get_network_connectivity():
    """Get network connectivity status"""
    try:
        metrics = await enhanced_collector.collect_network_connectivity()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/pressure")
async def get_service_pressure():
    """Get service pressure metrics"""
    try:
        metrics = await enhanced_collector.calculate_service_pressure()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Initializing Enhanced Portal with Proxy Status...")
    
    # Initialize default AI report templates
    try:
        await initialize_default_templates()
        logger.info("AI report templates initialized")
    except Exception as e:
        logger.error(f"Failed to initialize AI report templates: {e}")
    
    # Test proxy connectivity on startup
    try:
        proxy_status = proxy_checker.get_proxy_status()
        logger.info(f"Proxy status on startup: Tor={proxy_status['tor']['ready']}, I2P={proxy_status['i2p']['ready']}")
    except Exception as e:
        logger.error(f"Failed to check proxy status on startup: {e}")

if __name__ == "__main__":
    import os
    
    host = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_SERVER_PORT", 8080))
    
    logger.info(f"Starting Enhanced Noctipede Portal with Proxy Status on {host}:{port}")
    
    uvicorn.run(
        "portal.enhanced_portal_with_proxy:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
