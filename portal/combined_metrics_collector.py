"""
Combined Metrics Collector for Noctipede System
Merges the basic portal crawler metrics with enhanced system metrics
"""

import asyncio
import aiohttp
import psutil
import time
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

try:
    import pymysql
    from minio import Minio
    from minio.error import S3Error
    from sqlalchemy import text, func
    from core import get_logger
    from config import get_settings
    from database import get_db_session, Site, Page, MediaFile
    from storage import get_storage_client
except ImportError as e:
    logging.warning(f"Import error: {e}")

class CombinedMetricsCollector:
    """Combined metrics collector that merges basic and enhanced metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Try to use existing settings, fallback to environment variables
        try:
            self.settings = get_settings()
            self.minio_client = get_storage_client().client
        except:
            self.settings = None
            self.minio_client = None
        
        # Configuration from environment
        self.db_config = {
            'host': os.getenv('MARIADB_HOST', 'mariadb'),
            'port': int(os.getenv('MARIADB_PORT', 3306)),
            'user': os.getenv('MARIADB_USER', 'splinter-research'),
            'password': os.getenv('MARIADB_PASSWORD', ''),
            'database': os.getenv('MARIADB_DATABASE', 'splinter-research')
        }
        
        self.minio_config = {
            'endpoint': os.getenv('MINIO_ENDPOINT', 'minio:9000'),
            'access_key': os.getenv('MINIO_ACCESS_KEY', ''),
            'secret_key': os.getenv('MINIO_SECRET_KEY', ''),
            'bucket': os.getenv('MINIO_BUCKET_NAME', 'noctipede-data'),
            'secure': os.getenv('MINIO_SECURE', 'false').lower() == 'true'
        }
        
        self.ollama_config = {
            'endpoint': os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434'),
            'base_url': os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434').replace('/api/generate', '').replace('/api', '')
        }
        
        self.proxy_config = {
            'tor_host': os.getenv('TOR_PROXY_HOST', '127.0.0.1'),
            'tor_port': int(os.getenv('TOR_PROXY_PORT', 9050)),
            'i2p_host': os.getenv('I2P_PROXY_HOST', '127.0.0.1'),
            'i2p_port': int(os.getenv('I2P_PROXY_PORT', 4444))
        }
        
        # Cache for metrics
        self.metrics_cache = {}
        self.last_update = None
        self.cache_duration = 30  # seconds
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all system metrics with combined approach"""
        start_time = time.time()
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'collection_time': 0,
            'system': {},
            'database': {},
            'minio': {},
            'ollama': {},
            'crawler': {},
            'network': {},
            'services': {}
        }
        
        try:
            # Collect metrics concurrently where possible
            tasks = [
                self.collect_system_metrics(),
                self.collect_database_metrics(),
                self.collect_minio_metrics(),
                self.collect_ollama_metrics(),
                self.collect_combined_crawler_metrics(),  # This is the combined version
                self.collect_network_metrics(),
                self.collect_service_health()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Assign results
            metric_keys = ['system', 'database', 'minio', 'ollama', 'crawler', 'network', 'services']
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Error collecting {metric_keys[i]} metrics: {result}")
                    metrics[metric_keys[i]] = {'error': str(result), 'status': 'error'}
                else:
                    metrics[metric_keys[i]] = result
            
            metrics['collection_time'] = round(time.time() - start_time, 3)
            self.metrics_cache = metrics
            self.last_update = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error in collect_all_metrics: {e}")
            metrics['error'] = str(e)
        
        return metrics
    
    async def collect_combined_crawler_metrics(self) -> Dict[str, Any]:
        """Combined crawler metrics from both basic and enhanced approaches"""
        try:
            metrics = {
                'status': 'unknown',
                'response_codes': {},
                'performance': {},
                'progress': {},
                'errors': {
                    'sites_with_errors': 0,
                    'error_rate_percent': 0,
                    'recent_errors': []
                },
                'network_breakdown': {},
                'log_analysis': {},
                'real_time': {}
            }
            
            # === BASIC PORTAL METRICS (Database-driven) ===
            try:
                if self.settings:
                    session = get_db_session()
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
                    
                    # Network type breakdown
                    network_stats = session.query(
                        func.case(
                            (Site.url.like('%.onion%'), 'tor'),
                            (Site.url.like('%.i2p%'), 'i2p'),
                            else_='clearnet'
                        ).label('network_type'),
                        func.count(Site.id).label('count')
                    ).group_by('network_type').all()
                    
                    session.close()
                    
                    # Calculate hit/miss ratios
                    hit_rate = (successful_pages / total_recent_pages * 100) if total_recent_pages > 0 else 0
                    miss_rate = 100 - hit_rate
                    
                    # Populate basic metrics
                    metrics['response_codes'] = {str(code): count for code, count in response_codes}
                    metrics['performance'] = {
                        'hit_rate_percent': round(hit_rate, 2),
                        'miss_rate_percent': round(miss_rate, 2),
                        'total_requests_24h': total_recent_pages,
                        'successful_requests_24h': successful_pages,
                        'avg_response_time_ms': round(float(avg_response_time) * 1000, 2) if avg_response_time else 0
                    }
                    metrics['progress'] = {
                        'total_sites': total_sites,
                        'sites_never_crawled': sites_never_crawled,
                        'sites_crawled_today': sites_crawled_today,
                        'completion_rate_percent': round((sites_crawled_today / total_sites * 100), 2) if total_sites > 0 else 0
                    }
                    metrics['errors'] = {
                        'sites_with_errors': sites_with_errors,
                        'error_rate_percent': round((sites_with_errors / total_sites * 100), 2) if total_sites > 0 else 0,
                        'recent_errors': [
                            {
                                'url': site.url,
                                'error': site.last_error,
                                'error_count': site.error_count,
                                'last_crawled': site.last_crawled.isoformat() if site.last_crawled else None
                            }
                            for site in recent_errors
                        ]
                    }
                    metrics['network_breakdown'] = {network: count for network, count in network_stats}
                    
            except Exception as e:
                self.logger.warning(f"Could not collect basic crawler metrics: {e}")
            
            # === ENHANCED METRICS (Log-based analysis) ===
            try:
                log_file = '/app/logs/noctipede.log'
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        lines = f.readlines()[-1000:]  # Last 1000 lines
                    
                    # Parse log entries for enhanced metrics
                    log_response_codes = {}
                    log_errors = []
                    log_warnings = []
                    successful_crawls = 0
                    failed_crawls = 0
                    
                    for line in lines:
                        if 'Successfully crawled' in line:
                            successful_crawls += 1
                        elif 'Failed to crawl' in line or 'ERROR' in line:
                            failed_crawls += 1
                            if len(log_errors) < 10:
                                log_errors.append(line.strip())
                        elif 'WARNING' in line:
                            if len(log_warnings) < 10:
                                log_warnings.append(line.strip())
                        
                        # Extract HTTP response codes from logs
                        for code in ['200', '404', '403', '500', '502', '503']:
                            if code in line:
                                log_response_codes[code] = log_response_codes.get(code, 0) + 1
                    
                    metrics['log_analysis'] = {
                        'successful_crawls': successful_crawls,
                        'failed_crawls': failed_crawls,
                        'success_rate': (successful_crawls / (successful_crawls + failed_crawls) * 100) if (successful_crawls + failed_crawls) > 0 else 0,
                        'recent_errors': log_errors[-5:],
                        'recent_warnings': log_warnings[-5:],
                        'log_response_codes': log_response_codes
                    }
                    
                    # Merge log response codes with database response codes
                    for code, count in log_response_codes.items():
                        if code in metrics['response_codes']:
                            metrics['response_codes'][code] = max(metrics['response_codes'][code], count)
                        else:
                            metrics['response_codes'][code] = count
                            
            except Exception as e:
                self.logger.warning(f"Could not collect log-based crawler metrics: {e}")
            
            # === REAL-TIME METRICS (Direct database queries) ===
            try:
                connection = pymysql.connect(**self.db_config)
                cursor = connection.cursor()
                
                # Recent activity metrics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_pages,
                        COUNT(CASE WHEN crawled_at > NOW() - INTERVAL 1 HOUR THEN 1 END) as recent_pages,
                        COUNT(CASE WHEN crawled_at > NOW() - INTERVAL 24 HOUR THEN 1 END) as daily_pages,
                        AVG(response_time) as avg_response_time,
                        MAX(crawled_at) as last_crawl
                    FROM pages
                """)
                
                result = cursor.fetchone()
                if result:
                    metrics['real_time'] = {
                        'total_pages': result[0],
                        'pages_last_hour': result[1],
                        'pages_last_24h': result[2],
                        'avg_response_time': float(result[3]) if result[3] else 0,
                        'last_crawl': result[4].isoformat() if result[4] else None
                    }
                
                # Top domains by page count
                cursor.execute("""
                    SELECT 
                        SUBSTRING_INDEX(SUBSTRING_INDEX(url, '/', 3), '/', -1) as domain,
                        COUNT(*) as page_count
                    FROM pages 
                    WHERE crawled_at > NOW() - INTERVAL 24 HOUR
                    GROUP BY domain
                    ORDER BY page_count DESC
                    LIMIT 10
                """)
                
                top_domains = []
                for row in cursor.fetchall():
                    top_domains.append({'domain': row[0], 'page_count': row[1]})
                
                metrics['real_time']['top_domains'] = top_domains
                
                connection.close()
                
            except Exception as e:
                self.logger.warning(f"Could not collect real-time crawler metrics: {e}")
            
            # Determine overall status
            if metrics['performance'].get('total_requests_24h', 0) > 0:
                if metrics['performance']['hit_rate_percent'] > 70:
                    metrics['status'] = 'healthy'
                elif metrics['performance']['hit_rate_percent'] > 40:
                    metrics['status'] = 'warning'
                else:
                    metrics['status'] = 'error'
            else:
                metrics['status'] = 'idle'
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting combined crawler metrics: {e}")
            return {'error': str(e), 'status': 'error'}
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics (CPU, Memory, Disk)"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Load average (Unix-like systems)
            try:
                load_avg = os.getloadavg()
            except:
                load_avg = [0, 0, 0]
            
            return {
                'status': 'healthy' if cpu_percent < 80 and memory.percent < 80 else 'warning',
                'cpu': {
                    'usage_percent': round(cpu_percent, 2),
                    'count': cpu_count,
                    'load_avg': {
                        '1min': round(load_avg[0], 2),
                        '5min': round(load_avg[1], 2),
                        '15min': round(load_avg[2], 2)
                    }
                },
                'memory': {
                    'usage_percent': round(memory.percent, 2),
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'used_gb': round(memory.used / (1024**3), 2)
                },
                'disk': {
                    'usage_percent': round(disk.percent, 2),
                    'total_gb': round(disk.total / (1024**3), 2),
                    'free_gb': round(disk.free / (1024**3), 2),
                    'used_gb': round(disk.used / (1024**3), 2)
                }
            }
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return {'error': str(e), 'status': 'error'}
    
    async def collect_database_metrics(self) -> Dict[str, Any]:
        """Collect database metrics"""
        try:
            connection = pymysql.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Database size and table counts
            cursor.execute("SELECT COUNT(*) FROM sites")
            sites_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM pages")
            pages_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM media_files")
            media_count = cursor.fetchone()[0]
            
            # Database size
            cursor.execute(f"""
                SELECT 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'DB Size (MB)'
                FROM information_schema.tables 
                WHERE table_schema='{self.db_config['database']}'
            """)
            db_size = cursor.fetchone()[0] or 0
            
            connection.close()
            
            return {
                'status': 'healthy',
                'connection': True,
                'tables': {
                    'sites': sites_count,
                    'pages': pages_count,
                    'media_files': media_count
                },
                'size_mb': float(db_size)
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting database metrics: {e}")
            return {'error': str(e), 'status': 'error', 'connection': False}
    
    async def collect_minio_metrics(self) -> Dict[str, Any]:
        """Collect MinIO storage metrics"""
        try:
            if not self.minio_client:
                # Fallback to direct MinIO client creation
                minio_client = Minio(
                    self.minio_config['endpoint'],
                    access_key=self.minio_config['access_key'],
                    secret_key=self.minio_config['secret_key'],
                    secure=self.minio_config['secure']
                )
            else:
                minio_client = self.minio_client
            
            # Check if bucket exists
            bucket_exists = minio_client.bucket_exists(self.minio_config['bucket'])
            
            if bucket_exists:
                # Count objects in bucket
                objects = list(minio_client.list_objects(self.minio_config['bucket'], recursive=True))
                object_count = len(objects)
                total_size = sum(obj.size for obj in objects if obj.size)
            else:
                object_count = 0
                total_size = 0
            
            return {
                'status': 'healthy' if bucket_exists else 'warning',
                'connection': True,
                'bucket_exists': bucket_exists,
                'object_count': object_count,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting MinIO metrics: {e}")
            return {'error': str(e), 'status': 'error', 'connection': False}
    
    async def collect_ollama_metrics(self) -> Dict[str, Any]:
        """Collect Ollama AI service metrics"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Test basic connectivity
                async with session.get(f"{self.ollama_config['base_url']}/api/tags") as response:
                    if response.status == 200:
                        models_data = await response.json()
                        models = models_data.get('models', [])
                        
                        return {
                            'status': 'healthy',
                            'connection': True,
                            'models_available': len(models),
                            'models': [
                                {
                                    'name': model.get('name', ''),
                                    'size': model.get('size', 0),
                                    'modified_at': model.get('modified_at', '')
                                }
                                for model in models
                            ]
                        }
                    else:
                        return {
                            'status': 'error',
                            'connection': False,
                            'error': f"HTTP {response.status}"
                        }
                        
        except Exception as e:
            self.logger.error(f"Error collecting Ollama metrics: {e}")
            return {'error': str(e), 'status': 'error', 'connection': False}
    
    async def collect_network_metrics(self) -> Dict[str, Any]:
        """Collect network connectivity metrics"""
        metrics = {
            'tor': {'status': 'unknown', 'connectivity': False},
            'i2p': {'status': 'unknown', 'connectivity': False}
        }
        
        # Test Tor connectivity
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                proxy_url = f"socks5://{self.proxy_config['tor_host']}:{self.proxy_config['tor_port']}"
                
                async with session.get(
                    'https://check.torproject.org/api/ip',
                    proxy=proxy_url
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        metrics['tor'] = {
                            'status': 'healthy',
                            'connectivity': True,
                            'is_tor': data.get('IsTor', False),
                            'ip': data.get('IP', 'unknown')
                        }
                    else:
                        metrics['tor'] = {
                            'status': 'error',
                            'connectivity': False,
                            'error': f"HTTP {response.status}"
                        }
        except Exception as e:
            metrics['tor'] = {'status': 'error', 'connectivity': False, 'error': str(e)}
        
        # Test I2P connectivity (simplified)
        try:
            # Basic connectivity test to I2P proxy
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.proxy_config['i2p_host'], self.proxy_config['i2p_port']))
            sock.close()
            
            if result == 0:
                metrics['i2p'] = {'status': 'healthy', 'connectivity': True}
            else:
                metrics['i2p'] = {'status': 'error', 'connectivity': False, 'error': 'Connection refused'}
                
        except Exception as e:
            metrics['i2p'] = {'status': 'error', 'connectivity': False, 'error': str(e)}
        
        return metrics
    
    async def collect_service_health(self) -> Dict[str, Any]:
        """Collect overall service health status"""
        try:
            # This would typically check various service endpoints
            # For now, return a basic health check
            return {
                'status': 'healthy',
                'uptime_seconds': time.time(),
                'services': {
                    'web_portal': 'healthy',
                    'metrics_collector': 'healthy',
                    'crawler_engine': 'unknown'
                }
            }
        except Exception as e:
            return {'error': str(e), 'status': 'error'}
