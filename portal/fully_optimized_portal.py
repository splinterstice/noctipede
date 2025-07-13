#!/usr/bin/env python3
"""
Fully Optimized Portal - Apply comprehensive optimization patches
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

# Import existing metrics collector and patches
try:
    from portal.combined_metrics_collector import CombinedMetricsCollector
    from portal.i2p_patch import patch_metrics_collector
    from portal.comprehensive_optimization_patch import apply_comprehensive_patch
    PATCHES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import patches: {e}")
    from portal.basic_enhanced_metrics import BasicEnhancedMetricsCollector as CombinedMetricsCollector
    PATCHES_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Fully Optimized Noctipede Portal", version="1.0.0")

# Initialize and apply all patches to metrics collector
metrics_collector = CombinedMetricsCollector()
if PATCHES_AVAILABLE:
    # Apply I2P optimization patch first
    metrics_collector = patch_metrics_collector(metrics_collector)
    # Apply comprehensive optimization patch
    metrics_collector = apply_comprehensive_patch(metrics_collector)
    logger.info("✅ Applied ALL optimization patches (I2P + Comprehensive)")
else:
    logger.warning("⚠️ Patches not available, using basic metrics")

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
            "title": "Enhanced Noctipede Dashboard (Fully Optimized)"
        })
    except Exception as e:
        logger.error(f"Error loading enhanced dashboard: {e}")
        return HTMLResponse("<h1>Enhanced Dashboard</h1><p>Error loading template</p>")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "version": "fully-optimized-portal-1.0",
        "patches_applied": PATCHES_AVAILABLE,
        "optimizations": ["i2p_early_exit", "comprehensive_caching", "timeout_limits"],
        "target_response_time": "< 10 seconds",
        "dashboards": ["basic", "enhanced", "combined", "ai-reports"]
    }

@app.get("/api/metrics")
async def get_metrics():
    """Fully optimized metrics endpoint"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        logger.info("🚀 Collecting FULLY OPTIMIZED metrics")
        
        # Set aggressive timeout for fully optimized metrics
        if PATCHES_AVAILABLE and hasattr(metrics_collector, 'collect_all_metrics'):
            metrics = await asyncio.wait_for(
                metrics_collector.collect_all_metrics(),
                timeout=15.0  # 15-second timeout (well under 35s requirement)
            )
        else:
            # Fallback to basic metrics
            metrics = metrics_collector.collect_all_metrics() if hasattr(metrics_collector, 'collect_all_metrics') else {}
        
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Add optimization metadata
        metrics['optimization_info'] = {
            'patches_applied': PATCHES_AVAILABLE,
            'collection_time_ms': collection_time,
            'target_time_ms': 35000,  # Your 35-second requirement
            'performance_target_met': collection_time < 35000,
            'optimization_level': 'full' if PATCHES_AVAILABLE else 'basic',
            'optimizations_active': [
                'i2p_early_exit_at_5_sites',
                'ollama_quick_check_3s_timeout',
                'database_socket_test_2s_timeout', 
                'minio_socket_test_2s_timeout',
                'comprehensive_caching',
                'concurrent_collection'
            ] if PATCHES_AVAILABLE else []
        }
        
        logger.info(f"✅ FULLY OPTIMIZED metrics collected in {collection_time:.1f}ms (target: <35s)")
        
        return JSONResponse(content=metrics)
        
    except asyncio.TimeoutError:
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.error(f"❌ FULLY OPTIMIZED metrics timed out after {collection_time:.1f}ms")
        
        return JSONResponse(
            status_code=408,
            content={
                "error": "Fully optimized metrics collection timed out",
                "timeout_ms": 15000,
                "actual_time_ms": collection_time,
                "patches_applied": PATCHES_AVAILABLE,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
                "note": "Even with full optimization, collection exceeded 15s timeout"
            }
        )
        
    except Exception as e:
        collection_time = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.error(f"❌ Error in fully optimized metrics: {e}")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to collect fully optimized metrics",
                "details": str(e),
                "collection_time_ms": collection_time,
                "patches_applied": PATCHES_AVAILABLE,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
            }
        )

@app.get("/api/quick-test")
async def quick_performance_test():
    """Quick performance test to verify optimizations"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Test individual components with their optimizations
        if PATCHES_AVAILABLE:
            from portal.comprehensive_optimization_patch import comprehensive_patcher
            
            # Test each component individually
            component_times = {}
            
            # Test Ollama (should be ~3s max)
            comp_start = asyncio.get_event_loop().time()
            ollama_result = await comprehensive_patcher.quick_ollama_check()
            component_times['ollama'] = (asyncio.get_event_loop().time() - comp_start) * 1000
            
            # Test Database (should be ~2s max)
            comp_start = asyncio.get_event_loop().time()
            db_result = await comprehensive_patcher.quick_database_check()
            component_times['database'] = (asyncio.get_event_loop().time() - comp_start) * 1000
            
            # Test MinIO (should be ~2s max)
            comp_start = asyncio.get_event_loop().time()
            minio_result = await comprehensive_patcher.quick_minio_check()
            component_times['minio'] = (asyncio.get_event_loop().time() - comp_start) * 1000
            
            # Test I2P (should be ~0.1s with patch)
            if hasattr(metrics_collector, 'collect_network_metrics'):
                comp_start = asyncio.get_event_loop().time()
                network_result = await metrics_collector.collect_network_metrics()
                component_times['network'] = (asyncio.get_event_loop().time() - comp_start) * 1000
            
            total_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return JSONResponse(content={
                "test_type": "quick_performance_test",
                "total_time_ms": total_time,
                "component_times_ms": component_times,
                "target_time_ms": 35000,
                "performance_target_met": total_time < 35000,
                "optimization_effectiveness": {
                    "ollama": "✅ Quick check" if component_times.get('ollama', 0) < 5000 else "❌ Still slow",
                    "database": "✅ Socket test" if component_times.get('database', 0) < 3000 else "❌ Still slow", 
                    "minio": "✅ Socket test" if component_times.get('minio', 0) < 3000 else "❌ Still slow",
                    "network": "✅ I2P optimized" if component_times.get('network', 0) < 1000 else "❌ Still slow"
                },
                "patches_applied": True
            })
        else:
            return JSONResponse(content={
                "test_type": "quick_performance_test",
                "error": "Optimization patches not available",
                "patches_applied": False
            })
            
    except Exception as e:
        total_time = (asyncio.get_event_loop().time() - start_time) * 1000
        return JSONResponse(
            status_code=500,
            content={
                "test_type": "quick_performance_test",
                "error": str(e),
                "total_time_ms": total_time,
                "patches_applied": PATCHES_AVAILABLE
            }
        )

if __name__ == "__main__":
    import time
    
    # Configuration
    host = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_SERVER_PORT", "8080"))
    
    logger.info("🚀 Starting FULLY OPTIMIZED Noctipede Portal...")
    logger.info(f"Optimization Status: {'✅ ALL PATCHES APPLIED' if PATCHES_AVAILABLE else '❌ NO PATCHES'}")
    logger.info("🎯 Target: Metrics API responds within 35 seconds")
    logger.info("🏆 Goal: Achieve <10 second response time with optimizations")
    logger.info("📊 Optimizations:")
    if PATCHES_AVAILABLE:
        logger.info("   • I2P early exit at 5 successful sites")
        logger.info("   • Ollama quick check (3s timeout)")
        logger.info("   • Database socket test (2s timeout)")
        logger.info("   • MinIO socket test (2s timeout)")
        logger.info("   • Comprehensive caching (5min TTL)")
        logger.info("   • Concurrent collection")
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
