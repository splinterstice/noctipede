"""Main FastAPI application for the Noctipede Web Portal."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, desc
import json
from contextlib import asynccontextmanager

from core import setup_logging, get_logger
from config import get_settings
from database import get_db_session, Site, Page, MediaFile
from .cached_metrics_collector import CachedMetricsCollector

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Global metrics cache
metrics_cache = {
    "last_updated": None,
    "crawler_data": {},
    "system_data": {}
}

# Initialize cached metrics collector
metrics_collector = CachedMetricsCollector()

def get_crawler_metrics() -> Dict[str, Any]:
    """Get current crawler metrics from database (legacy function - now using cached collector)."""
    # This function is kept for compatibility but the cached collector is preferred
    try:
        session = get_db_session()
        
        # Basic counts
        total_sites = session.query(Site).count()
        total_pages = session.query(Page).count()
        total_media = session.query(MediaFile).count()
        
        session.close()
        
        return {
            "totals": {
                "sites": total_sites,
                "pages": total_pages,
                "media_files": total_media
            },
            "recent_24h": {
                "pages": 0,
                "media_files": 0
            },
            "network_breakdown": {},
            "status_breakdown": {},
            "recent_activity": [],
            "top_domains": []
        }
    except Exception as e:
        logger.error(f"Error getting legacy crawler metrics: {e}")
        return {
            "totals": {"sites": 0, "pages": 0, "media_files": 0},
            "recent_24h": {"pages": 0, "media_files": 0},
            "network_breakdown": {},
            "status_breakdown": {},
            "recent_activity": [],
            "top_domains": []
        }

async def update_metrics_cache():
    """Legacy function - now using on-demand caching instead."""
    # This function is no longer used but kept for compatibility
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Noctipede Web Portal with cached metrics")
    
    # No background tasks needed - using on-demand caching
    logger.info("Cached metrics collector initialized")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Noctipede Web Portal")

# Create FastAPI app
app = FastAPI(
    title="Noctipede Crawler Dashboard",
    description="Live metrics and monitoring for the Noctipede crawler system",
    version="1.0.0",
    lifespan=lifespan
)

# Setup templates
templates = Jinja2Templates(directory="/app/portal/templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Noctipede Crawler Dashboard"
    })

@app.get("/basic", response_class=HTMLResponse)
async def basic_dashboard(request: Request):
    """Basic dashboard page (same as main)."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Noctipede Basic Dashboard"
    })

@app.get("/api/metrics")
async def get_metrics():
    """Get current crawler metrics with smart caching."""
    try:
        # Use the cached metrics collector for fast response
        all_metrics = await metrics_collector.collect_all_metrics()
        
        return {
            "crawler": all_metrics.get("crawler", {}),
            "last_updated": all_metrics.get("timestamp"),
            "timestamp": datetime.utcnow().isoformat(),
            "cache_info": all_metrics.get("cache_info", {}),
            "collection_time": all_metrics.get("collection_time", "0.0s")
        }
    except Exception as e:
        logger.error(f"Error in /api/metrics: {e}")
        return {
            "error": f"Metrics collection failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error"
        }

@app.get("/api/system-metrics")
async def get_system_metrics():
    """Get comprehensive system metrics with caching."""
    try:
        all_metrics = await metrics_collector.collect_all_metrics()
        
        return {
            "system": all_metrics.get("system", {}),
            "network": all_metrics.get("network", {}),
            "last_updated": all_metrics.get("timestamp"),
            "timestamp": datetime.utcnow().isoformat(),
            "cache_info": all_metrics.get("cache_info", {}),
            "collection_time": all_metrics.get("collection_time", "0.0s")
        }
    except Exception as e:
        logger.error(f"Error in /api/system-metrics: {e}")
        return {
            "error": f"System metrics collection failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error"
        }

@app.get("/api/all-metrics")
async def get_all_metrics():
    """Get all metrics combined with smart caching."""
    try:
        all_metrics = await metrics_collector.collect_all_metrics()
        return all_metrics
    except Exception as e:
        logger.error(f"Error in /api/all-metrics: {e}")
        return {
            "error": f"All metrics collection failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error"
        }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "noctipede-portal",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/cache-status")
async def get_cache_status():
    """Get cache status information."""
    try:
        cache_status = metrics_collector.get_cache_status()
        return {
            "cache_status": cache_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/api/clear-cache")
async def clear_cache():
    """Clear all caches (useful for testing)."""
    try:
        metrics_collector.clear_cache()
        return {
            "message": "All caches cleared successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api/system-info")
async def system_info():
    """Get system information."""
    settings = get_settings()
    return {
        "crawler_settings": {
            "max_links_per_page": settings.max_links_per_page,
            "max_queue_size": settings.max_queue_size,
            "crawl_delay_seconds": settings.crawl_delay_seconds,
            "max_concurrent_crawlers": settings.max_concurrent_crawlers,
            "content_analysis_enabled": settings.content_analysis_enabled,
            "image_analysis_enabled": settings.image_analysis_enabled
        },
        "network_settings": {
            "tor_proxy": f"{settings.tor_proxy_host}:{settings.tor_proxy_port}",
            "i2p_proxy": f"{settings.i2p_proxy_host}:{settings.i2p_proxy_port}"
        }
    }

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "portal.main:app",
        host=settings.web_server_host,
        port=settings.web_server_port,
        reload=False,
        log_level=settings.log_level.lower()
    )
