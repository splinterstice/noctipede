"""System metrics collector for all services."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import text, func
import json

from core import get_logger
from config import get_settings
from database import get_db_session, Site, Page, MediaFile

logger = get_logger(__name__)


class SystemMetricsCollector:
    """Collects basic system metrics."""
    
    def __init__(self):
        self.settings = get_settings()
        
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect basic system metrics."""
        try:
            start_time = time.time()
            
            # Collect basic metrics
            system_metrics = await self._collect_basic_system_metrics()
            database_metrics = await self._collect_database_metrics()
            
            collection_time = time.time() - start_time
            
            return {
                "system": system_metrics,
                "database": database_metrics,
                "timestamp": datetime.utcnow().isoformat(),
                "collection_time": f"{collection_time:.2f}s",
                "status": "healthy"
            }
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {
                "system": {"status": "error", "error": str(e)},
                "database": {"status": "error"},
                "timestamp": datetime.utcnow().isoformat(),
                "collection_time": "0.0s",
                "status": "error",
                "error": str(e)
            }
    
    async def _collect_basic_system_metrics(self) -> Dict[str, Any]:
        """Collect basic system information."""
        try:
            # Try to get system metrics if psutil is available
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                return {
                    "cpu": {
                        "usage_percent": cpu_percent,
                        "cores": psutil.cpu_count()
                    },
                    "memory": {
                        "total_gb": round(memory.total / (1024**3), 2),
                        "used_gb": round(memory.used / (1024**3), 2),
                        "usage_percent": memory.percent
                    },
                    "disk": {
                        "total_gb": round(disk.total / (1024**3), 2),
                        "used_gb": round(disk.used / (1024**3), 2),
                        "usage_percent": round((disk.used / disk.total) * 100, 1)
                    },
                    "status": "healthy"
                }
            except ImportError:
                # Fallback to basic info without psutil
                return {
                    "cpu": {"usage_percent": 0, "cores": 1},
                    "memory": {"total_gb": 0, "used_gb": 0, "usage_percent": 0},
                    "disk": {"total_gb": 0, "used_gb": 0, "usage_percent": 0},
                    "status": "basic_mode"
                }
                
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _collect_database_metrics(self) -> Dict[str, Any]:
        """Collect database metrics."""
        try:
            session = get_db_session()
            
            # Basic table counts
            sites_count = session.query(Site).count()
            pages_count = session.query(Page).count()
            media_count = session.query(MediaFile).count()
            
            # Recent activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(hours=24)
            recent_pages = session.query(Page).filter(Page.crawled_at >= yesterday).count()
            
            session.close()
            
            return {
                "tables": {
                    "sites": sites_count,
                    "pages": pages_count,
                    "media_files": media_count
                },
                "recent_activity": {
                    "pages_last_24h": recent_pages
                },
                "status": "healthy"
            }
            
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
            return {"status": "error", "error": str(e)}
