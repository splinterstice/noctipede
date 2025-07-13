"""
Main Noctipede Portal - Comprehensive Multi-Dashboard System
Serves all dashboard types: Basic, Enhanced, Combined, and AI Reports
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
    from portal.combined_metrics_collector import CombinedMetricsCollector
except ImportError as e:
    logging.error(f"Failed to import metrics collectors: {e}")
    # Fallback to basic functionality
    EnhancedMetricsCollector = None
    CombinedMetricsCollector = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Noctipede Portal System",
    description="Comprehensive monitoring and metrics for Noctipede deep web crawler",
    version="3.0.0"
)

# Initialize metrics collectors
enhanced_metrics_collector = EnhancedMetricsCollector() if EnhancedMetricsCollector else None
combined_metrics_collector = CombinedMetricsCollector() if CombinedMetricsCollector else None

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Setup static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ============================================================================
# DASHBOARD ROUTES
# ============================================================================

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

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/metrics")
async def get_metrics():
    """Get comprehensive system metrics"""
    try:
        if enhanced_metrics_collector:
            # Check for cached metrics first
            cached_metrics = enhanced_metrics_collector.get_cached_metrics()
            if cached_metrics:
                logger.info("Returning cached metrics")
                return JSONResponse(content=cached_metrics)
            
            # Collect fresh metrics
            logger.info("Collecting fresh comprehensive metrics...")
            metrics = await enhanced_metrics_collector.collect_all_metrics()
            return JSONResponse(content=metrics)
        else:
            return JSONResponse(
                content={"error": "Enhanced metrics collector not available"},
                status_code=503
            )
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return JSONResponse(
            content={"error": f"Failed to collect metrics: {str(e)}"},
            status_code=500
        )

@app.get("/api/system")
async def get_system_metrics():
    """Get system-specific metrics"""
    try:
        if enhanced_metrics_collector:
            metrics = await enhanced_metrics_collector.collect_system_metrics()
            return JSONResponse(content=metrics)
        else:
            return JSONResponse(content={"error": "Metrics collector not available"}, status_code=503)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/database")
async def get_database_metrics():
    """Get database-specific metrics"""
    try:
        if enhanced_metrics_collector:
            metrics = await enhanced_metrics_collector.collect_database_metrics()
            return JSONResponse(content=metrics)
        else:
            return JSONResponse(content={"error": "Metrics collector not available"}, status_code=503)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/minio")
async def get_minio_metrics():
    """Get MinIO-specific metrics"""
    try:
        if enhanced_metrics_collector:
            metrics = await enhanced_metrics_collector.collect_minio_metrics()
            return JSONResponse(content=metrics)
        else:
            return JSONResponse(content={"error": "Metrics collector not available"}, status_code=503)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/ollama")
async def get_ollama_metrics():
    """Get Ollama-specific metrics"""
    try:
        if enhanced_metrics_collector:
            metrics = await enhanced_metrics_collector.collect_ollama_metrics()
            return JSONResponse(content=metrics)
        else:
            return JSONResponse(content={"error": "Metrics collector not available"}, status_code=503)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/crawler")
async def get_crawler_metrics():
    """Get crawler-specific metrics"""
    try:
        if enhanced_metrics_collector:
            metrics = await enhanced_metrics_collector.collect_crawler_metrics()
            return JSONResponse(content=metrics)
        else:
            return JSONResponse(content={"error": "Metrics collector not available"}, status_code=503)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/network")
async def get_network_metrics():
    """Get network connectivity metrics"""
    try:
        if enhanced_metrics_collector:
            metrics = await enhanced_metrics_collector.collect_network_metrics()
            return JSONResponse(content=metrics)
        else:
            return JSONResponse(content={"error": "Metrics collector not available"}, status_code=503)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/services")
async def get_service_health():
    """Get service health status"""
    try:
        if enhanced_metrics_collector:
            metrics = await enhanced_metrics_collector.collect_service_health()
            return JSONResponse(content=metrics)
        else:
            return JSONResponse(content={"error": "Metrics collector not available"}, status_code=503)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ============================================================================
# COMBINED DASHBOARD API ENDPOINTS
# ============================================================================

@app.get("/api/combined/metrics")
async def get_combined_metrics():
    """Get combined dashboard metrics"""
    try:
        if combined_metrics_collector:
            metrics = await combined_metrics_collector.collect_all_metrics()
            return JSONResponse(content=metrics)
        else:
            return JSONResponse(content={"error": "Combined metrics collector not available"}, status_code=503)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ============================================================================
# STARTUP AND MAIN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting Noctipede Portal System")
    logger.info("📊 Available dashboards: Basic, Enhanced, Combined, AI Reports")
    
    # Test metrics collectors
    if enhanced_metrics_collector:
        logger.info("✅ Enhanced metrics collector initialized")
    else:
        logger.warning("⚠️ Enhanced metrics collector not available")
        
    if combined_metrics_collector:
        logger.info("✅ Combined metrics collector initialized")
    else:
        logger.warning("⚠️ Combined metrics collector not available")

if __name__ == "__main__":
    uvicorn.run(
        "portal.main_portal:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )
