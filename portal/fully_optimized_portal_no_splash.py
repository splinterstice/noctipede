#!/usr/bin/env python3
"""
Fully Optimized Portal - No splash page for basic dashboard
"""
import os
import sys
import logging
import asyncio
import time
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

@app.get("/basic", response_class=HTMLResponse)
async def basic_dashboard(request: Request):
    """Basic dashboard - Direct to dashboard, no splash page"""
    try:
        # Go directly to the dashboard template
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Basic Noctipede Dashboard"
        })
    except Exception as e:
        logger.error(f"Error loading basic dashboard: {e}")
        # Fallback to a simple HTML dashboard if template fails
        return HTMLResponse("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Basic Noctipede Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; }
                .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
                .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .metric-value { font-size: 2em; font-weight: bold; color: #3498db; }
                .metric-label { color: #7f8c8d; margin-top: 5px; }
                .status { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
                .status.healthy { background: #d4edda; color: #155724; }
                .status.error { background: #f8d7da; color: #721c24; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🕷️ Basic Noctipede Dashboard</h1>
                    <p>Real-time crawler metrics and system status</p>
                </div>
                <div class="metrics" id="metrics">
                    <div class="metric-card">
                        <div class="metric-value" id="total-sites">Loading...</div>
                        <div class="metric-label">Total Sites</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="total-pages">Loading...</div>
                        <div class="metric-label">Total Pages</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="system-status">Loading...</div>
                        <div class="metric-label">System Status</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="response-time">Loading...</div>
                        <div class="metric-label">API Response Time</div>
                    </div>
                </div>
            </div>
            <script>
                async function loadMetrics() {
                    try {
                        const start = Date.now();
                        const response = await fetch('/api/metrics');
                        const responseTime = Date.now() - start;
                        const data = await response.json();
                        
                        document.getElementById('total-sites').textContent = data.crawler?.total_sites || '0';
                        document.getElementById('total-pages').textContent = data.crawler?.total_pages || '0';
                        document.getElementById('system-status').innerHTML = 
                            `<span class="status ${data.system?.status === 'healthy' ? 'healthy' : 'error'}">${data.system?.status || 'Unknown'}</span>`;
                        document.getElementById('response-time').textContent = responseTime + 'ms';
                    } catch (error) {
                        console.error('Error loading metrics:', error);
                        document.getElementById('system-status').innerHTML = '<span class="status error">Error</span>';
                    }
                }
                
                // Load metrics immediately and then every 30 seconds
                loadMetrics();
                setInterval(loadMetrics, 30000);
            </script>
        </body>
        </html>
        """)

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

@app.get("/combined", response_class=HTMLResponse)
async def combined_dashboard(request: Request):
    """Combined dashboard"""
    try:
        return templates.TemplateResponse("combined_dashboard.html", {
            "request": request,
            "title": "Combined Noctipede Dashboard (Optimized)"
        })
    except Exception as e:
        logger.error(f"Error loading combined dashboard: {e}")
        # Fallback to enhanced dashboard if combined template doesn't exist
        try:
            return templates.TemplateResponse("enhanced_dashboard.html", {
                "request": request,
                "title": "Combined Noctipede Dashboard (Fallback to Enhanced)"
            })
        except:
            return HTMLResponse("<h1>Combined Dashboard</h1><p>Template not found, using enhanced dashboard features</p>")

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
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        "version": "fully-optimized-portal-1.0-no-splash",
        "patches_applied": PATCHES_AVAILABLE,
        "optimizations": ["i2p_early_exit", "comprehensive_caching", "timeout_limits"],
        "target_response_time": "< 10 seconds",
        "service_connections": {
            "ollama": "10.1.1.12:2701",
            "minio": "minio-crawler-hl.minio-service:9000",
            "database": "mariadb.mariadb-service:3306"
        },
        "dashboards": ["basic", "enhanced", "combined", "ai-reports"],
        "note": "Basic dashboard bypasses splash page"
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
            'service_connections': {
                'ollama_endpoint': '10.1.1.12:2701',
                'minio_endpoint': 'minio-crawler-hl.minio-service:9000',
                'database_endpoint': 'mariadb.mariadb-service:3306'
            },
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

@app.get("/api/enhanced-metrics")
async def get_enhanced_metrics():
    """Alias for fully optimized metrics"""
    return await get_metrics()

if __name__ == "__main__":
    # Configuration
    host = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_SERVER_PORT", "8080"))
    
    logger.info("🚀 Starting FULLY OPTIMIZED Noctipede Portal (NO SPLASH PAGE)...")
    logger.info(f"Optimization Status: {'✅ ALL PATCHES APPLIED' if PATCHES_AVAILABLE else '❌ NO PATCHES'}")
    logger.info("🎯 Target: Metrics API responds within 35 seconds")
    logger.info("🏆 Goal: Achieve <10 second response time with optimizations")
    logger.info("🔗 Service Connections:")
    logger.info("   • Ollama: 10.1.1.12:2701")
    logger.info("   • MinIO: minio-crawler-hl.minio-service:9000")
    logger.info("   • Database: mariadb.mariadb-service:3306")
    logger.info("📊 Dashboard Changes:")
    logger.info("   • Basic Dashboard: Direct access, no splash page")
    logger.info("   • Enhanced/Combined: Full featured dashboards")
    logger.info("   • AI Reports: Advanced analytics interface")
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
