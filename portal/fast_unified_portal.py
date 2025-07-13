#!/usr/bin/env python3
"""
Fast Unified Noctipede Portal - No expensive I2P tests
"""
import os
import sys
import logging
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Import the fast metrics collector
from portal.fast_metrics_collector import FastMetricsCollector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Fast Noctipede Portal", version="1.0.0")

# Initialize metrics collector
metrics_collector = FastMetricsCollector()

# Mount static files
static_path = project_root / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Templates
templates_path = project_root / "portal" / "templates"
templates = Jinja2Templates(directory=str(templates_path))

@app.get("/", response_class=HTMLResponse)
async def dashboard_selection(request: Request):
    """Dashboard selection page"""
    try:
        return templates.TemplateResponse("dashboard_selection.html", {
            "request": request,
            "title": "Noctipede Portal - Dashboard Selection"
        })
    except Exception as e:
        logger.error(f"Error loading dashboard selection: {e}")
        return HTMLResponse("<h1>Dashboard Selection</h1><p>Error loading template</p>")

@app.get("/enhanced", response_class=HTMLResponse)
async def enhanced_dashboard(request: Request):
    """Enhanced dashboard with fast metrics"""
    try:
        return templates.TemplateResponse("enhanced_dashboard.html", {
            "request": request,
            "title": "Enhanced Noctipede Dashboard (Fast Mode)"
        })
    except Exception as e:
        logger.error(f"Error loading enhanced dashboard: {e}")
        return HTMLResponse("<h1>Enhanced Dashboard</h1><p>Error loading template</p>")

@app.get("/combined", response_class=HTMLResponse)
async def combined_dashboard(request: Request):
    """Combined dashboard"""
    try:
        return templates.TemplateResponse("combined_dashboard.html", {
            "request": request,
            "title": "Combined Noctipede Dashboard"
        })
    except Exception as e:
        logger.error(f"Error loading combined dashboard: {e}")
        return HTMLResponse("<h1>Combined Dashboard</h1><p>Error loading template</p>")

@app.get("/ai-reports", response_class=HTMLResponse)
async def ai_reports_dashboard(request: Request):
    """AI Reports dashboard"""
    try:
        return templates.TemplateResponse("ai_reports.html", {
            "request": request,
            "title": "AI Reports Dashboard"
        })
    except Exception as e:
        logger.error(f"Error loading AI reports: {e}")
        return HTMLResponse("<h1>AI Reports</h1><p>Error loading template</p>")

@app.get("/api/health")
async def health_check():
    """Fast health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": metrics_collector._get_timestamp(),
        "version": "fast-portal-1.0",
        "mode": "fast",
        "dashboards": ["basic", "enhanced", "combined", "ai-reports"]
    }

@app.get("/api/metrics")
async def get_metrics():
    """Fast metrics endpoint - no expensive I2P tests"""
    try:
        logger.info("Collecting fast metrics (no I2P tests)")
        metrics = metrics_collector.collect_all_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        logger.error(f"Error collecting fast metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to collect metrics",
                "details": str(e),
                "timestamp": metrics_collector._get_timestamp(),
                "mode": "fast_error"
            }
        )

@app.get("/api/enhanced-metrics")
async def get_enhanced_metrics():
    """Alias for fast metrics"""
    return await get_metrics()

if __name__ == "__main__":
    # Configuration
    host = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_SERVER_PORT", "8080"))
    
    logger.info("🚀 Starting Fast Unified Noctipede Portal...")
    logger.info(f"Available dashboards: /enhanced, /combined, /ai-reports")
    logger.info("Fast mode: Expensive I2P network tests disabled")
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
