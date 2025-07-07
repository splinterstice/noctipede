"""
Enhanced Noctipede Portal with Comprehensive Metrics
Displays system health, performance metrics, and service status
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

try:
    from portal.enhanced_metrics_collector import EnhancedMetricsCollector
except ImportError:
    # Fallback to basic metrics if enhanced collector is not available
    print("Warning: Enhanced metrics collector not available, using basic metrics")
    from portal.metrics_collector import MetricsCollector as EnhancedMetricsCollector

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Noctipede Enhanced Portal", version="2.0.0")

# Initialize metrics collector
metrics_collector = EnhancedMetricsCollector()

# Setup templates
templates = Jinja2Templates(directory="/app/portal/templates")

# Serve static files if directory exists
static_dir = Path("/app/portal/static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse)
async def basic_dashboard(request: Request):
    """Basic dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/enhanced", response_class=HTMLResponse)
async def enhanced_dashboard(request: Request):
    """Enhanced dashboard page"""
    return templates.TemplateResponse("enhanced_dashboard.html", {"request": request})

@app.get("/combined", response_class=HTMLResponse)
async def combined_dashboard(request: Request):
    """Combined dashboard page"""
    return templates.TemplateResponse("combined_dashboard.html", {"request": request})

@app.get("/ai-reports", response_class=HTMLResponse)
async def ai_reports(request: Request):
    """AI reports page"""
    return templates.TemplateResponse("ai_reports.html", {"request": request})

@app.get("/api/metrics")
async def get_metrics():
    """Get comprehensive system metrics"""
    try:
        # Check for cached metrics first
        cached_metrics = metrics_collector.get_cached_metrics()
        if cached_metrics:
            return JSONResponse(content=cached_metrics)
        
        # Collect fresh metrics
        metrics = await metrics_collector.collect_all_metrics()
        return JSONResponse(content=metrics)
    
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return JSONResponse(
            content={"error": str(e), "timestamp": datetime.now().isoformat()},
            status_code=500
        )

@app.get("/api/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/system")
async def get_system_metrics():
    """Get system-specific metrics"""
    try:
        metrics = await metrics_collector.collect_system_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/database")
async def get_database_metrics():
    """Get database-specific metrics"""
    try:
        metrics = await metrics_collector.collect_database_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/minio")
async def get_minio_metrics():
    """Get MinIO-specific metrics"""
    try:
        metrics = await metrics_collector.collect_minio_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/ollama")
async def get_ollama_metrics():
    """Get Ollama-specific metrics"""
    try:
        metrics = await metrics_collector.collect_ollama_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/crawler")
async def get_crawler_metrics():
    """Get crawler-specific metrics"""
    try:
        metrics = await metrics_collector.collect_crawler_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/network")
async def get_network_metrics():
    """Get network connectivity metrics"""
    try:
        metrics = await metrics_collector.collect_network_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/services")
async def get_service_health():
    """Get service health status"""
    try:
        metrics = await metrics_collector.collect_service_health()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import os
    
    host = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_SERVER_PORT", 8080))
    
    logger.info(f"Starting Enhanced Noctipede Portal on {host}:{port}")
    
    uvicorn.run(
        "enhanced_main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
