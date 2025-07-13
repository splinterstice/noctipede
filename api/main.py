"""Main FastAPI application."""

import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from core import setup_logging, get_logger
from config import get_settings
from database import get_db_manager
from .routes import router
from .analysis_portal import router as analysis_router

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Global metrics cache
metrics_cache = {
    "last_updated": None,
    "crawler_data": {},
    "system_data": {}
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Noctipede API")
    
    # Test database connection
    db_manager = get_db_manager()
    if not db_manager.test_connection():
        logger.error("Database connection failed")
        raise Exception("Database connection failed")
    
    # Create tables if they don't exist
    db_manager.create_tables()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Noctipede API")

# Create FastAPI app
app = FastAPI(
    title="Noctipede API",
    description="Deep Web Analysis System API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates
templates = Jinja2Templates(directory="/app/api/templates")

# Include routes
app.include_router(router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api")

# Include AI Reports router
try:
    from .ai_reports_advanced import router as ai_reports_advanced_router
    app.include_router(ai_reports_advanced_router)
    logger.info("Advanced AI Reports endpoints enabled")
except ImportError as e:
    logger.warning(f"Advanced AI Reports endpoints not available: {e}")
    # Fallback to simple version
    try:
        from .simple_ai_reports import router as ai_reports_router
        app.include_router(ai_reports_router)
        logger.info("AI Reports endpoints enabled (simplified version)")
    except ImportError as e2:
        logger.warning(f"AI Reports endpoints not available: {e2}")

# Include Ollama stats router
try:
    from .ollama_stats import router as ollama_router
    app.include_router(ollama_router)
    logger.info("Ollama statistics endpoints enabled")
except ImportError as e:
    logger.warning(f"Ollama statistics endpoints not available: {e}")

@app.get("/ai-reports", response_class=HTMLResponse)
async def ai_reports_portal():
    """Serve the AI Reports portal page."""
    try:
        # Try to serve the advanced version first
        try:
            with open("/app/portal/templates/ai_reports_advanced.html", "r") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            # Fallback to basic version
            with open("/app/portal/templates/ai_reports.html", "r") as f:
                return HTMLResponse(content=f.read())
    except Exception as e:
        logger.error(f"Error serving AI Reports portal: {e}")
        raise HTTPException(status_code=500, detail="Failed to load AI Reports portal")

@app.get("/ai-reports-advanced", response_class=HTMLResponse)
async def ai_reports_advanced_portal():
    """Serve the Advanced AI Reports portal page."""
    try:
        with open("/app/portal/templates/ai_reports_advanced.html", "r") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        logger.error(f"Error serving Advanced AI Reports portal: {e}")
        raise HTTPException(status_code=500, detail="Failed to load Advanced AI Reports portal")

@app.get("/analysis", response_class=HTMLResponse)
async def analysis_portal():
    """Serve the analysis portal page."""
    try:
        with open("/app/api/templates/analysis_portal.html", "r") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        logger.error(f"Error serving analysis portal: {e}")
        raise HTTPException(status_code=500, detail="Failed to load analysis portal")

@app.get("/ollama-stats", response_class=HTMLResponse)
async def ollama_stats_dashboard():
    """Serve the Ollama statistics dashboard."""
    try:
        with open("/app/portal/templates/ollama_stats.html", "r") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        logger.error(f"Error serving Ollama stats dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to load Ollama stats dashboard")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="/app/static"), name="static")
    logger.info("Static files mounted at /static")
except Exception as e:
    logger.warning(f"Could not mount /app/static files: {e}")

try:
    app.mount("/output", StaticFiles(directory="/app/output"), name="output")
    logger.info("Output files mounted at /output")
except Exception as e:
    logger.warning(f"Could not mount /app/output files: {e}")


@app.get("/favicon.ico")
async def favicon():
    """Return a simple favicon response to avoid 404 errors."""
    # Return a simple 1x1 transparent PNG as favicon
    import base64
    # This is a 1x1 transparent PNG encoded in base64
    transparent_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77zgAAAABJRU5ErkJggg=="
    )
    from fastapi.responses import Response
    return Response(content=transparent_png, media_type="image/png")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "noctipede-api"}


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint for Kubernetes."""
    return {"status": "healthy", "service": "noctipede-api"}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check database connection
        db_manager = get_db_manager()
        if not db_manager.test_connection():
            raise HTTPException(status_code=503, detail="Database not ready")
        
        return {"status": "ready", "service": "noctipede-api"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


@app.get("/api/ready")
async def api_readiness_check():
    """API readiness check endpoint for Kubernetes."""
    try:
        # Check database connection
        db_manager = get_db_manager()
        if not db_manager.test_connection():
            raise HTTPException(status_code=503, detail="Database not ready")
        
        return {"status": "ready", "service": "noctipede-api"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Add metrics endpoints
@app.get("/api/metrics")
async def get_metrics():
    """Get comprehensive system metrics using enhanced collector."""
    try:
        # Import and use the enhanced metrics collector
        from portal.enhanced_metrics_collector import EnhancedMetricsCollector
        
        collector = EnhancedMetricsCollector()
        metrics = await collector.collect_enhanced_metrics()
        
        return {
            **metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy"
        }
        
    except Exception as e:
        logger.error(f"Error getting enhanced metrics: {e}")
        
        # Fallback to basic metrics
        try:
            from database import get_db_session, Site, Page
            
            with get_db_session() as session:
                total_sites = session.query(Site).count()
                total_pages = session.query(Page).count()
                
                onion_sites = session.query(Site).filter(Site.is_onion == True).count()
                i2p_sites = session.query(Site).filter(Site.is_i2p == True).count()
                clearnet_sites = total_sites - onion_sites - i2p_sites
                
                return {
                    "crawler": {
                        "total_sites": total_sites,
                        "total_pages": total_pages,
                        "network_breakdown": {
                            "clearnet": clearnet_sites,
                            "onion": onion_sites,
                            "i2p": i2p_sites
                        },
                        "status": "active"
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "partial",
                    "error": f"Enhanced metrics failed: {str(e)}"
                }
                
        except Exception as fallback_error:
            logger.error(f"Fallback metrics also failed: {fallback_error}")
            return {
                "error": f"All metrics collection failed: {str(e)}",
                "fallback_error": str(fallback_error),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error"
            }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "noctipede-api",
        "timestamp": datetime.utcnow().isoformat()
    }


def main():
    """Run the API server."""
    settings = get_settings()
    
    uvicorn.run(
        "api.main:app",
        host=settings.web_server_host,
        port=settings.web_server_port,
        reload=False,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
