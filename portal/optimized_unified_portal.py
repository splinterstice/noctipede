#!/usr/bin/env python3
"""
Optimized Unified Noctipede Portal - Early exit I2P tests
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

# Import the optimized metrics collector
from portal.optimized_metrics_collector import OptimizedMetricsCollector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Optimized Noctipede Portal", version="1.0.0")

# Initialize metrics collector
metrics_collector = OptimizedMetricsCollector()

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
    """Enhanced dashboard with optimized metrics"""
    try:
        return templates.TemplateResponse("enhanced_dashboard.html", {
            "request": request,
            "title": "Enhanced Noctipede Dashboard (Optimized)"
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
        "version": "optimized-portal-1.0",
        "mode": "optimized",
        "early_exit_threshold": 5,
        "dashboards": ["basic", "enhanced", "combined", "ai-reports"]
    }

@app.get("/api/metrics")
async def get_metrics():
    """Optimized metrics endpoint with early exit I2P tests"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        logger.info("🚀 Starting optimized metrics collection (early exit at 5 successful I2P proxies)")
        
        # Set a timeout for the entire metrics collection
        metrics = await asyncio.wait_for(
            metrics_collector.collect_all_metrics(),
            timeout=30.0  # 30-second timeout
        )
        
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        metrics['collection_time'] = collection_time
        metrics['optimization'] = {
            'early_exit_enabled': True,
            'i2p_proxy_threshold': 5,
            'max_collection_time_ms': 30000,
            'actual_collection_time_ms': collection_time
        }
        
        logger.info(f"✅ Optimized metrics collected in {collection_time:.1f}ms")
        
        return JSONResponse(content=metrics)
        
    except asyncio.TimeoutError:
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.error(f"❌ Metrics collection timed out after {collection_time:.1f}ms")
        
        return JSONResponse(
            status_code=408,
            content={
                "error": "Metrics collection timed out",
                "timeout_ms": 30000,
                "actual_time_ms": collection_time,
                "timestamp": metrics_collector._get_timestamp(),
                "mode": "optimized_timeout",
                "suggestion": "I2P network tests may be taking too long despite optimization"
            }
        )
        
    except Exception as e:
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.error(f"❌ Error collecting optimized metrics: {e}")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to collect metrics",
                "details": str(e),
                "collection_time_ms": collection_time,
                "timestamp": metrics_collector._get_timestamp(),
                "mode": "optimized_error"
            }
        )

@app.get("/api/enhanced-metrics")
async def get_enhanced_metrics():
    """Alias for optimized metrics"""
    return await get_metrics()

@app.get("/api/network-test")
async def test_network_only():
    """Test only network metrics with optimization"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        logger.info("🔍 Testing network metrics only (optimized)")
        
        network_metrics = await asyncio.wait_for(
            metrics_collector.collect_network_metrics(),
            timeout=20.0  # 20-second timeout for network only
        )
        
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        return JSONResponse(content={
            "network": network_metrics,
            "collection_time_ms": collection_time,
            "timestamp": metrics_collector._get_timestamp(),
            "test_type": "network_only_optimized"
        })
        
    except asyncio.TimeoutError:
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        return JSONResponse(
            status_code=408,
            content={
                "error": "Network test timed out",
                "timeout_ms": 20000,
                "actual_time_ms": collection_time,
                "timestamp": metrics_collector._get_timestamp()
            }
        )
        
    except Exception as e:
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        return JSONResponse(
            status_code=500,
            content={
                "error": "Network test failed",
                "details": str(e),
                "collection_time_ms": collection_time,
                "timestamp": metrics_collector._get_timestamp()
            }
        )

if __name__ == "__main__":
    # Configuration
    host = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_SERVER_PORT", "8080"))
    
    logger.info("🚀 Starting Optimized Unified Noctipede Portal...")
    logger.info(f"Available dashboards: /enhanced, /combined, /ai-reports")
    logger.info("🎯 Optimization: Early exit I2P tests at 5 successful proxies")
    logger.info("⏱️  Timeout: 30s for full metrics, 20s for network-only")
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
