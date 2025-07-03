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
from .metrics_collector import SystemMetricsCollector

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Global metrics cache
metrics_cache = {
    "last_updated": None,
    "crawler_data": {},
    "system_data": {}
}

# Initialize metrics collector
metrics_collector = SystemMetricsCollector()

def get_crawler_metrics() -> Dict[str, Any]:
    """Get current crawler metrics from database."""
    try:
        session = get_db_session()
        
        # Basic counts
        total_sites = session.query(Site).count()
        total_pages = session.query(Page).count()
        total_media = session.query(MediaFile).count()
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_pages = session.query(Page).filter(Page.crawled_at >= yesterday).count()
        recent_media = session.query(MediaFile).filter(MediaFile.downloaded_at >= yesterday).count()
        
        # Network type breakdown
        network_stats = session.query(
            Site.network_type, 
            func.count(Site.id).label('count')
        ).group_by(Site.network_type).all()
        
        # Site status breakdown
        status_stats = session.query(
            Site.status, 
            func.count(Site.id).label('count')
        ).group_by(Site.status).all()
        
        # Recent crawl activity
        recent_sites = session.query(Site).filter(
            Site.last_crawled >= yesterday
        ).order_by(desc(Site.last_crawled)).limit(10).all()
        
        # Top domains by page count
        top_domains = session.query(
            Site.domain,
            func.count(Page.id).label('page_count')
        ).join(Page).group_by(Site.domain).order_by(
            desc(func.count(Page.id))
        ).limit(10).all()
        
        session.close()
        
        return {
            "totals": {
                "sites": total_sites,
                "pages": total_pages,
                "media_files": total_media
            },
            "recent_24h": {
                "pages": recent_pages,
                "media_files": recent_media
            },
            "network_breakdown": {item.network_type: item.count for item in network_stats},
            "status_breakdown": {item.status: item.count for item in status_stats},
            "recent_activity": [
                {
                    "url": site.url,
                    "domain": site.domain,
                    "network_type": site.network_type,
                    "status": site.status,
                    "last_crawled": site.last_crawled.isoformat() if site.last_crawled else None,
                    "page_count": site.page_count or 0
                }
                for site in recent_sites
            ],
            "top_domains": [
                {"domain": item.domain, "page_count": item.page_count}
                for item in top_domains
            ]
        }
    except Exception as e:
        logger.error(f"Error getting crawler metrics: {e}")
        return {
            "totals": {"sites": 0, "pages": 0, "media_files": 0},
            "recent_24h": {"pages": 0, "media_files": 0},
            "network_breakdown": {},
            "status_breakdown": {},
            "recent_activity": [],
            "top_domains": []
        }

async def update_metrics_cache():
    """Update the metrics cache periodically."""
    while True:
        try:
            # Update crawler metrics
            metrics_cache["crawler_data"] = get_crawler_metrics()
            
            # Update system metrics
            metrics_cache["system_data"] = await metrics_collector.collect_all_metrics()
            
            metrics_cache["last_updated"] = datetime.utcnow()
            logger.debug("Metrics cache updated")
        except Exception as e:
            logger.error(f"Error updating metrics cache: {e}")
        
        await asyncio.sleep(30)  # Update every 30 seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Noctipede Web Portal")
    
    # Start metrics cache update task
    task = asyncio.create_task(update_metrics_cache())
    
    # Initial cache population
    metrics_cache["crawler_data"] = get_crawler_metrics()
    try:
        metrics_cache["system_data"] = await metrics_collector.collect_all_metrics()
    except Exception as e:
        logger.error(f"Error collecting initial system metrics: {e}")
        metrics_cache["system_data"] = {}
    
    metrics_cache["last_updated"] = datetime.utcnow()
    
    yield
    
    # Cleanup
    task.cancel()
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

@app.get("/api/metrics")
async def get_metrics():
    """Get current crawler metrics."""
    return {
        "crawler": metrics_cache["crawler_data"],
        "last_updated": metrics_cache["last_updated"].isoformat() if metrics_cache["last_updated"] else None,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/system-metrics")
async def get_system_metrics():
    """Get comprehensive system metrics."""
    return {
        "system": metrics_cache["system_data"],
        "last_updated": metrics_cache["last_updated"].isoformat() if metrics_cache["last_updated"] else None,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/all-metrics")
async def get_all_metrics():
    """Get all metrics combined."""
    return {
        "crawler": metrics_cache["crawler_data"],
        "system": metrics_cache["system_data"],
        "last_updated": metrics_cache["last_updated"].isoformat() if metrics_cache["last_updated"] else None,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "noctipede-portal",
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
