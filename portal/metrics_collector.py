"""System metrics collector for all services."""

import asyncio
import aiohttp
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import text, func
import pymysql

from core import get_logger
from config import get_settings
from database import get_db_session, Site, Page, MediaFile
from storage import get_storage_client

logger = get_logger(__name__)


class SystemMetricsCollector:
    """Collects metrics from all system components."""
    
    def __init__(self):
        self.settings = get_settings()
        self.minio_client = get_storage_client().client
        
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect metrics from all services."""
        try:
            # Collect metrics concurrently
            tasks = [
                self._collect_system_metrics(),
                self._collect_database_metrics(),
                self._collect_minio_metrics(),
                self._collect_ollama_metrics(),
                self._collect_crawler_metrics(),
                self._collect_network_connectivity(),
                self._collect_service_health()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine all metrics
            all_metrics = {}
            metric_names = [
                'system', 'database', 'minio', 'ollama', 
                'crawler', 'network', 'services'
            ]
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error collecting {metric_names[i]} metrics: {result}")
                    all_metrics[metric_names[i]] = {"error": str(result)}
                else:
                    all_metrics[metric_names[i]] = result
            
            all_metrics['timestamp'] = datetime.utcnow().isoformat()
            return all_metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system CPU and memory metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "frequency_mhz": cpu_freq.current if cpu_freq else None
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent
                },
                "swap": {
                    "total_gb": round(swap.total / (1024**3), 2),
                    "used_gb": round(swap.used / (1024**3), 2),
                    "percent": swap.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": round((disk.used / disk.total) * 100, 2)
                }
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {"error": str(e)}
    
    async def _collect_database_metrics(self) -> Dict[str, Any]:
        """Collect database metrics and pressure indicators."""
        try:
            session = get_db_session()
            
            # Connection metrics
            connection_info = session.execute(text("SHOW STATUS LIKE 'Threads_connected'")).fetchone()
            max_connections = session.execute(text("SHOW VARIABLES LIKE 'max_connections'")).fetchone()
            
            # Database size
            db_size_query = text("""
                SELECT 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS db_size_mb
                FROM information_schema.tables 
                WHERE table_schema = :db_name
            """)
            db_size = session.execute(db_size_query, {"db_name": self.settings.mariadb_database}).fetchone()
            
            # Table sizes
            table_sizes_query = text("""
                SELECT 
                    table_name,
                    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb,
                    table_rows
                FROM information_schema.TABLES 
                WHERE table_schema = :db_name
                ORDER BY (data_length + index_length) DESC
            """)
            table_sizes = session.execute(table_sizes_query, {"db_name": self.settings.mariadb_database}).fetchall()
            
            # Performance metrics
            slow_queries = session.execute(text("SHOW STATUS LIKE 'Slow_queries'")).fetchone()
            queries_per_sec = session.execute(text("SHOW STATUS LIKE 'Queries'")).fetchone()
            
            # Database pressure indicators
            innodb_buffer_pool = session.execute(text("SHOW STATUS LIKE 'Innodb_buffer_pool_read_requests'")).fetchone()
            innodb_buffer_misses = session.execute(text("SHOW STATUS LIKE 'Innodb_buffer_pool_reads'")).fetchone()
            
            buffer_hit_ratio = 0
            if innodb_buffer_pool and innodb_buffer_misses:
                total_reads = float(innodb_buffer_pool[1])
                disk_reads = float(innodb_buffer_misses[1])
                if total_reads > 0:
                    buffer_hit_ratio = ((total_reads - disk_reads) / total_reads) * 100
            
            session.close()
            
            return {
                "connections": {
                    "current": int(connection_info[1]) if connection_info else 0,
                    "max": int(max_connections[1]) if max_connections else 0,
                    "usage_percent": round((int(connection_info[1]) / int(max_connections[1])) * 100, 2) if connection_info and max_connections else 0
                },
                "size": {
                    "total_mb": float(db_size[0]) if db_size and db_size[0] else 0,
                    "tables": [
                        {
                            "name": row[0],
                            "size_mb": float(row[1]) if row[1] else 0,
                            "rows": int(row[2]) if row[2] else 0
                        }
                        for row in table_sizes
                    ]
                },
                "performance": {
                    "slow_queries": int(slow_queries[1]) if slow_queries else 0,
                    "total_queries": int(queries_per_sec[1]) if queries_per_sec else 0,
                    "buffer_hit_ratio_percent": round(buffer_hit_ratio, 2)
                },
                "pressure": {
                    "connection_pressure": round((int(connection_info[1]) / int(max_connections[1])) * 100, 2) if connection_info and max_connections else 0,
                    "buffer_pressure": round(100 - buffer_hit_ratio, 2),
                    "status": "high" if buffer_hit_ratio < 95 else "normal"
                }
            }
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
            return {"error": str(e)}
    
    async def _collect_minio_metrics(self) -> Dict[str, Any]:
        """Collect MinIO metrics and storage information."""
        try:
            # Get bucket statistics
            bucket_name = self.settings.minio_bucket_name
            
            # List objects and calculate total size
            total_size = 0
            object_count = 0
            
            try:
                objects = self.minio_client.list_objects(bucket_name, recursive=True)
                for obj in objects:
                    total_size += obj.size
                    object_count += 1
            except Exception as e:
                logger.warning(f"Could not list MinIO objects: {e}")
            
            # Try to get MinIO server info via API
            minio_info = {}
            try:
                async with aiohttp.ClientSession() as session:
                    minio_url = f"http://{self.settings.minio_endpoint}/minio/health/live"
                    async with session.get(minio_url, timeout=5) as response:
                        minio_info["health"] = response.status == 200
            except Exception as e:
                logger.warning(f"Could not get MinIO health: {e}")
                minio_info["health"] = False
            
            return {
                "storage": {
                    "total_size_gb": round(total_size / (1024**3), 2),
                    "total_size_mb": round(total_size / (1024**2), 2),
                    "object_count": object_count,
                    "bucket_name": bucket_name
                },
                "health": minio_info.get("health", False),
                "pressure": {
                    "storage_usage_gb": round(total_size / (1024**3), 2),
                    "status": "normal"  # Could add more sophisticated pressure detection
                }
            }
        except Exception as e:
            logger.error(f"Error collecting MinIO metrics: {e}")
            return {"error": str(e)}
    
    async def _collect_ollama_metrics(self) -> Dict[str, Any]:
        """Collect Ollama API metrics and performance data."""
        try:
            if not self.settings.ollama_endpoint:
                return {"error": "Ollama endpoint not configured"}
            
            async with aiohttp.ClientSession() as session:
                # Health check
                health_url = f"{self.settings.ollama_endpoint}/api/tags"
                start_time = time.time()
                
                try:
                    async with session.get(health_url, timeout=10) as response:
                        response_time = time.time() - start_time
                        health_status = response.status == 200
                        
                        if health_status:
                            models_data = await response.json()
                            models = models_data.get('models', [])
                        else:
                            models = []
                except Exception as e:
                    logger.warning(f"Ollama health check failed: {e}")
                    health_status = False
                    response_time = 0
                    models = []
                
                # Try to get version info
                version_info = {}
                try:
                    version_url = f"{self.settings.ollama_endpoint}/api/version"
                    async with session.get(version_url, timeout=5) as response:
                        if response.status == 200:
                            version_info = await response.json()
                except Exception as e:
                    logger.warning(f"Could not get Ollama version: {e}")
                
                return {
                    "health": health_status,
                    "response_time_ms": round(response_time * 1000, 2),
                    "models": [
                        {
                            "name": model.get("name", "unknown"),
                            "size": model.get("size", 0),
                            "modified_at": model.get("modified_at", "")
                        }
                        for model in models
                    ],
                    "version": version_info,
                    "configured_models": {
                        "vision": self.settings.ollama_vision_model,
                        "text": self.settings.ollama_text_model,
                        "moderation": self.settings.ollama_moderation_model
                    },
                    "pressure": {
                        "response_time_ms": round(response_time * 1000, 2),
                        "status": "slow" if response_time > 2 else "normal"
                    }
                }
        except Exception as e:
            logger.error(f"Error collecting Ollama metrics: {e}")
            return {"error": str(e)}
    
    async def _collect_crawler_metrics(self) -> Dict[str, Any]:
        """Collect crawler performance and status metrics."""
        try:
            session = get_db_session()
            
            # Recent crawl activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(hours=24)
            
            # HTTP response codes from recent crawls
            response_codes = session.query(
                Page.status_code,
                func.count(Page.id).label('count')
            ).filter(
                Page.crawled_at >= yesterday
            ).group_by(Page.status_code).all()
            
            # Crawler success/failure rates
            total_recent_pages = session.query(Page).filter(Page.crawled_at >= yesterday).count()
            successful_pages = session.query(Page).filter(
                Page.crawled_at >= yesterday,
                Page.status_code.between(200, 299)
            ).count()
            
            # Site crawl statistics
            sites_with_errors = session.query(Site).filter(Site.error_count > 0).count()
            total_sites = session.query(Site).count()
            
            # Recent errors (last 24 hours)
            recent_errors = session.query(Site).filter(
                Site.last_crawled >= yesterday,
                Site.last_error.isnot(None)
            ).limit(10).all()
            
            # Crawler progress metrics
            sites_never_crawled = session.query(Site).filter(Site.last_crawled.is_(None)).count()
            sites_crawled_today = session.query(Site).filter(Site.last_crawled >= yesterday).count()
            
            # Average response times
            avg_response_time = session.query(func.avg(Page.response_time)).filter(
                Page.crawled_at >= yesterday,
                Page.response_time.isnot(None)
            ).scalar()
            
            session.close()
            
            # Calculate hit/miss ratios
            hit_rate = (successful_pages / total_recent_pages * 100) if total_recent_pages > 0 else 0
            miss_rate = 100 - hit_rate
            
            return {
                "response_codes": {
                    str(code): count for code, count in response_codes
                },
                "performance": {
                    "hit_rate_percent": round(hit_rate, 2),
                    "miss_rate_percent": round(miss_rate, 2),
                    "total_requests_24h": total_recent_pages,
                    "successful_requests_24h": successful_pages,
                    "avg_response_time_ms": round(float(avg_response_time) * 1000, 2) if avg_response_time else 0
                },
                "progress": {
                    "total_sites": total_sites,
                    "sites_never_crawled": sites_never_crawled,
                    "sites_crawled_today": sites_crawled_today,
                    "completion_rate_percent": round((sites_crawled_today / total_sites * 100), 2) if total_sites > 0 else 0
                },
                "errors": {
                    "sites_with_errors": sites_with_errors,
                    "error_rate_percent": round((sites_with_errors / total_sites * 100), 2) if total_sites > 0 else 0,
                    "recent_errors": [
                        {
                            "url": site.url,
                            "error": site.last_error,
                            "error_count": site.error_count,
                            "last_crawled": site.last_crawled.isoformat() if site.last_crawled else None
                        }
                        for site in recent_errors
                    ]
                }
            }
        except Exception as e:
            logger.error(f"Error collecting crawler metrics: {e}")
            return {"error": str(e)}
    
    async def _collect_network_connectivity(self) -> Dict[str, Any]:
        """Test network connectivity for Tor and I2P."""
        try:
            connectivity = {}
            
            # Test Tor connectivity
            try:
                # Test Tor proxy by checking if the SOCKS5 port is accessible
                import socket
                start_time = time.time()
                
                # Test if Tor proxy port is accessible
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((self.settings.tor_proxy_host, self.settings.tor_proxy_port))
                sock.close()
                
                tor_response_time = time.time() - start_time
                
                if result == 0:
                    connectivity["tor"] = {
                        "status": "connected",
                        "response_time_ms": round(tor_response_time * 1000, 2),
                        "proxy_host": self.settings.tor_proxy_host,
                        "proxy_port": self.settings.tor_proxy_port
                    }
                else:
                    connectivity["tor"] = {
                        "status": "error",
                        "error": f"Cannot connect to Tor proxy port {self.settings.tor_proxy_port}",
                        "response_time_ms": round(tor_response_time * 1000, 2)
                    }
            except Exception as e:
                connectivity["tor"] = {
                    "status": "error",
                    "error": str(e),
                    "response_time_ms": 0
                }
            
            # Test I2P connectivity
            try:
                proxy_url = f"http://{self.settings.i2p_proxy_host}:{self.settings.i2p_proxy_port}"
                start_time = time.time()
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "http://notbob.i2p", 
                        proxy=proxy_url, 
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        i2p_response_time = time.time() - start_time
                        connectivity["i2p"] = {
                            "status": "connected" if response.status == 200 else "error",
                            "response_time_ms": round(i2p_response_time * 1000, 2),
                            "proxy_host": self.settings.i2p_proxy_host,
                            "proxy_port": self.settings.i2p_proxy_port
                        }
            except Exception as e:
                connectivity["i2p"] = {
                    "status": "error",
                    "error": str(e),
                    "response_time_ms": 0
                }
            
            # Test I2P proxy connectivity (separate from I2P network)
            try:
                proxy_health_url = f"http://{self.settings.i2p_proxy_host}:{self.settings.i2p_proxy_port}"
                start_time = time.time()
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        proxy_health_url, 
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        proxy_response_time = time.time() - start_time
                        connectivity["i2p_proxy"] = {
                            "status": "running",
                            "response_time_ms": round(proxy_response_time * 1000, 2)
                        }
            except Exception as e:
                connectivity["i2p_proxy"] = {
                    "status": "error",
                    "error": str(e),
                    "response_time_ms": 0
                }
            
            return connectivity
        except Exception as e:
            logger.error(f"Error collecting network connectivity: {e}")
            return {"error": str(e)}
    
    async def _collect_service_health(self) -> Dict[str, Any]:
        """Check health status of all services."""
        try:
            services = {}
            
            # Database health
            try:
                session = get_db_session()
                session.execute(text("SELECT 1"))
                session.close()
                services["database"] = {"status": "healthy", "type": "mariadb"}
            except Exception as e:
                services["database"] = {"status": "unhealthy", "error": str(e), "type": "mariadb"}
            
            # MinIO health
            try:
                buckets = self.minio_client.list_buckets()
                services["minio"] = {"status": "healthy", "type": "object_storage"}
            except Exception as e:
                services["minio"] = {"status": "unhealthy", "error": str(e), "type": "object_storage"}
            
            # Ollama health (already collected above, but simplified here)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.settings.ollama_endpoint}/api/tags", timeout=5) as response:
                        services["ollama"] = {
                            "status": "healthy" if response.status == 200 else "unhealthy",
                            "type": "ai_service"
                        }
            except Exception as e:
                services["ollama"] = {"status": "unhealthy", "error": str(e), "type": "ai_service"}
            
            return services
        except Exception as e:
            logger.error(f"Error collecting service health: {e}")
            return {"error": str(e)}
