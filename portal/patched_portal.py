#!/usr/bin/env python3
"""
Patched Portal - Apply I2P optimization patch to existing metrics collector
"""
import os
import sys
import logging
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Import existing metrics collector and patch
try:
    from portal.combined_metrics_collector import CombinedMetricsCollector
    from portal.i2p_patch import patch_metrics_collector
    PATCH_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import patch: {e}")
    from portal.basic_enhanced_metrics import BasicEnhancedMetricsCollector as CombinedMetricsCollector
    PATCH_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Patched Noctipede Portal", version="1.0.0")

# Initialize and patch metrics collector
metrics_collector = CombinedMetricsCollector()
if PATCH_AVAILABLE:
    metrics_collector = patch_metrics_collector(metrics_collector)
    logger.info("✅ Applied I2P optimization patch")
else:
    logger.warning("⚠️ Patch not available, using basic metrics")

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
    """Enhanced dashboard"""
    try:
        return templates.TemplateResponse("enhanced_dashboard.html", {
            "request": request,
            "title": "Enhanced Noctipede Dashboard (Patched)"
        })
    except Exception as e:
        logger.error(f"Error loading enhanced dashboard: {e}")
        return HTMLResponse("<h1>Enhanced Dashboard</h1><p>Error loading template</p>")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": metrics_collector._get_timestamp() if hasattr(metrics_collector, '_get_timestamp') else "unknown",
        "version": "patched-portal-1.0",
        "patch_applied": PATCH_AVAILABLE,
        "dashboards": ["basic", "enhanced", "combined", "ai-reports"]
    }

@app.get("/api/metrics")
async def get_metrics():
    """Patched metrics endpoint with I2P optimization"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        logger.info("🚀 Collecting metrics with I2P patch")
        
        # Set timeout for metrics collection
        if PATCH_AVAILABLE:
            # Use patched collector with async support
            if hasattr(metrics_collector, 'collect_all_metrics') and asyncio.iscoroutinefunction(metrics_collector.collect_all_metrics):
                metrics = await asyncio.wait_for(
                    metrics_collector.collect_all_metrics(),
                    timeout=25.0  # 25-second timeout
                )
            else:
                # Sync version with network patch
                metrics = metrics_collector.collect_all_metrics()
                # Apply network patch separately if needed
                if hasattr(metrics_collector, 'collect_network_metrics'):
                    try:
                        network_metrics = await asyncio.wait_for(
                            metrics_collector.collect_network_metrics(),
                            timeout=15.0
                        )
                        metrics['network'] = network_metrics
                    except Exception as e:
                        logger.error(f"Network patch failed: {e}")
        else:
            # Fallback to basic metrics
            metrics = metrics_collector.collect_all_metrics()
        
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        metrics['collection_time'] = collection_time
        metrics['patch_applied'] = PATCH_AVAILABLE
        
        logger.info(f"✅ Metrics collected in {collection_time:.1f}ms (patch: {PATCH_AVAILABLE})")
        
        return JSONResponse(content=metrics)
        
    except asyncio.TimeoutError:
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.error(f"❌ Metrics collection timed out after {collection_time:.1f}ms")
        
        return JSONResponse(
            status_code=408,
            content={
                "error": "Metrics collection timed out",
                "timeout_ms": 25000,
                "actual_time_ms": collection_time,
                "patch_applied": PATCH_AVAILABLE,
                "timestamp": "unknown"
            }
        )
        
    except Exception as e:
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.error(f"❌ Error collecting metrics: {e}")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to collect metrics",
                "details": str(e),
                "collection_time_ms": collection_time,
                "patch_applied": PATCH_AVAILABLE,
                "timestamp": "unknown"
            }
        )

@app.get("/api/enhanced-metrics")
async def get_enhanced_metrics():
    """Alias for patched metrics"""
    return await get_metrics()

@app.get("/api/network-test")
async def test_network_only():
    """Test only network metrics with patch"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        logger.info("🔍 Testing network metrics only (patched)")
        
        if PATCH_AVAILABLE and hasattr(metrics_collector, 'collect_network_metrics'):
            network_metrics = await asyncio.wait_for(
                metrics_collector.collect_network_metrics(),
                timeout=15.0  # 15-second timeout for network only
            )
        else:
            # Fallback network test
            network_metrics = {
                'tor': {'status': 'unknown', 'note': 'Patch not available'},
                'i2p': {'status': 'unknown', 'note': 'Patch not available'},
                'overall_readiness': {'ready_for_crawling': False}
            }
        
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        return JSONResponse(content={
            "network": network_metrics,
            "collection_time_ms": collection_time,
            "patch_applied": PATCH_AVAILABLE,
            "test_type": "network_only_patched"
        })
        
    except asyncio.TimeoutError:
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        return JSONResponse(
            status_code=408,
            content={
                "error": "Network test timed out",
                "timeout_ms": 15000,
                "actual_time_ms": collection_time,
                "patch_applied": PATCH_AVAILABLE
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
                "patch_applied": PATCH_AVAILABLE
            }
        )

if __name__ == "__main__":
    # Configuration
    host = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_SERVER_PORT", "8080"))
    
    logger.info("🚀 Starting Patched Noctipede Portal...")
    logger.info(f"I2P Optimization Patch: {'✅ APPLIED' if PATCH_AVAILABLE else '❌ NOT AVAILABLE'}")
    logger.info("🎯 Target: Metrics API responds within 35 seconds")
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
