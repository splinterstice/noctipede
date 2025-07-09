"""
Enhanced Metrics Collector for Noctipede System
Collects comprehensive metrics from all system components
"""

import asyncio
import aiohttp
import psutil
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, '/app')

try:
    import pymysql
    from minio import Minio
    from minio.error import S3Error
except ImportError as e:
    logging.warning(f"Import error: {e}")

class EnhancedMetricsCollector:
    """Comprehensive metrics collector for all Noctipede components"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
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
            'tor_host': os.getenv('TOR_PROXY_HOST', 'tor-proxy'),
            'tor_port': int(os.getenv('TOR_PROXY_PORT', 9050)),
            'i2p_host': os.getenv('I2P_PROXY_HOST', 'i2p-proxy'),
            'i2p_port': int(os.getenv('I2P_PROXY_PORT', 4444))
        }
        
        # Metrics cache
        self.metrics_cache = {}
        self.last_update = None
        
        # Ollama usage tracking - Use persistent directory
        self.ollama_stats_file = '/app/data/ollama_usage_stats.json'
        self.ollama_stats = self._load_ollama_stats()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all system metrics"""
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
                self.collect_crawler_metrics(),
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
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics (CPU, Memory, Disk)"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network metrics
            network_io = psutil.net_io_counters()
            
            # Process metrics
            process_count = len(psutil.pids())
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'frequency': cpu_freq.current if cpu_freq else None
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free,
                    'swap_total': swap.total,
                    'swap_used': swap.used,
                    'swap_percent': swap.percent
                },
                'disk': {
                    'total': disk_usage.total,
                    'used': disk_usage.used,
                    'free': disk_usage.free,
                    'percent': (disk_usage.used / disk_usage.total) * 100,
                    'read_bytes': disk_io.read_bytes if disk_io else 0,
                    'write_bytes': disk_io.write_bytes if disk_io else 0
                },
                'network': {
                    'bytes_sent': network_io.bytes_sent,
                    'bytes_recv': network_io.bytes_recv,
                    'packets_sent': network_io.packets_sent,
                    'packets_recv': network_io.packets_recv
                },
                'processes': process_count,
                'status': 'healthy'
            }
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return {'error': str(e), 'status': 'error'}
    
    async def collect_database_metrics(self) -> Dict[str, Any]:
        """Collect database metrics and pressure indicators"""
        try:
            # Enhanced connection with better timeout and error handling
            db_config = self.db_config.copy()
            db_config.update({
                'connect_timeout': 5,
                'read_timeout': 5,
                'write_timeout': 5,
                'autocommit': True
            })
            
            connection = pymysql.connect(**db_config)
            cursor = connection.cursor()
            
            metrics = {
                'status': 'healthy',
                'connections': {},
                'performance': {},
                'storage': {},
                'pressure': 0
            }
            
            # Connection metrics with error handling
            try:
                cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                result = cursor.fetchone()
                threads_connected = int(result[1]) if result else 0
                
                cursor.execute("SHOW STATUS LIKE 'Max_used_connections'")
                result = cursor.fetchone()
                max_used_connections = int(result[1]) if result else 0
                
                cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
                result = cursor.fetchone()
                max_connections = int(result[1]) if result else 100
                
                metrics['connections'] = {
                    'current': threads_connected,
                    'max_used': max_used_connections,
                    'max_allowed': max_connections,
                    'utilization_percent': round((threads_connected / max_connections) * 100, 2) if max_connections > 0 else 0
                }
            except Exception as e:
                self.logger.warning(f"Could not collect connection metrics: {e}")
                metrics['connections'] = {'error': str(e)}
            
            # Performance metrics with error handling
            try:
                cursor.execute("SHOW STATUS LIKE 'Queries'")
                result = cursor.fetchone()
                total_queries = int(result[1]) if result else 0
                
                cursor.execute("SHOW STATUS LIKE 'Uptime'")
                result = cursor.fetchone()
                uptime = int(result[1]) if result else 1
                
                cursor.execute("SHOW STATUS LIKE 'Slow_queries'")
                slow_queries = int(cursor.fetchone()[1])
                
                # Buffer pool metrics
                cursor.execute("SHOW STATUS LIKE 'Innodb_buffer_pool_read_requests'")
                buffer_read_requests = int(cursor.fetchone()[1])
                
                cursor.execute("SHOW STATUS LIKE 'Innodb_buffer_pool_reads'")
                buffer_reads = int(cursor.fetchone()[1])
                
                buffer_hit_ratio = ((buffer_read_requests - buffer_reads) / buffer_read_requests * 100) if buffer_read_requests > 0 else 0
                
                metrics['performance'] = {
                    'queries_per_second': total_queries / uptime if uptime > 0 else 0,
                    'slow_queries': slow_queries,
                    'buffer_hit_ratio': buffer_hit_ratio,
                    'uptime_seconds': uptime
                }
            except Exception as e:
                self.logger.warning(f"Could not collect performance metrics: {e}")
                metrics['performance'] = {'error': str(e)}
            
            # Storage metrics
            cursor.execute("""
                SELECT 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS total_mb,
                    COUNT(*) as table_count
                FROM information_schema.tables 
                WHERE table_schema = %s
            """, (self.db_config['database'],))
            
            result = cursor.fetchone()
            total_size_mb = float(result[0]) if result[0] else 0
            table_count = int(result[1])
            
            # Noctipede-specific metrics
            try:
                cursor.execute("SELECT COUNT(*) FROM sites")
                site_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM pages")
                page_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM media_files")
                media_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM pages WHERE crawled_at > NOW() - INTERVAL 1 HOUR")
                recent_pages = cursor.fetchone()[0]
                
                metrics['noctipede'] = {
                    'sites': site_count,
                    'pages': page_count,
                    'media_files': media_count,
                    'recent_pages_1h': recent_pages
                }
            except Exception as e:
                self.logger.warning(f"Could not collect Noctipede-specific DB metrics: {e}")
                metrics['noctipede'] = {'error': str(e)}
            
            metrics['storage'] = {
                'total_size_mb': total_size_mb,
                'table_count': table_count
            }
            
            # Calculate database pressure (0-100)
            connection_pressure = (threads_connected / max_connections) * 100
            buffer_pressure = 100 - buffer_hit_ratio
            slow_query_pressure = min((slow_queries / total_queries) * 1000, 100) if total_queries > 0 else 0
            
            metrics['pressure'] = min(max(connection_pressure, buffer_pressure, slow_query_pressure), 100)
            
            connection.close()
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting database metrics: {e}")
            return {'error': str(e), 'status': 'error', 'pressure': 100}
    
    async def collect_minio_metrics(self) -> Dict[str, Any]:
        """Collect MinIO metrics and storage information"""
        try:
            # Enhanced MinIO client with better error handling
            client = Minio(
                self.minio_config['endpoint'],
                access_key=self.minio_config['access_key'],
                secret_key=self.minio_config['secret_key'],
                secure=self.minio_config['secure']
            )
            
            metrics = {
                'status': 'healthy',
                'storage': {},
                'objects': {},
                'pressure': 0,
                'endpoint': self.minio_config['endpoint']
            }
            
            # Test basic connectivity first
            try:
                # Check if bucket exists (this tests connectivity)
                bucket_name = self.minio_config['bucket']
                bucket_exists = client.bucket_exists(bucket_name)
                
                if not bucket_exists:
                    return {
                        'error': f'Bucket {bucket_name} does not exist', 
                        'status': 'error', 
                        'pressure': 100,
                        'endpoint': self.minio_config['endpoint']
                    }
                    
                metrics['bucket_name'] = bucket_name
                metrics['bucket_exists'] = True
                
            except Exception as e:
                return {
                    'error': f'MinIO connection failed: {str(e)}', 
                    'status': 'error', 
                    'pressure': 100,
                    'endpoint': self.minio_config['endpoint']
                }
                return {'error': f'Bucket {bucket_name} does not exist', 'status': 'error', 'pressure': 100}
            
            # Collect object statistics
            total_objects = 0
            total_size = 0
            object_types = {}
            
            try:
                objects = client.list_objects(bucket_name, recursive=True)
                for obj in objects:
                    total_objects += 1
                    total_size += obj.size
                    
                    # Categorize by type
                    if obj.object_name.startswith('pages/'):
                        object_types['pages'] = object_types.get('pages', 0) + 1
                    elif obj.object_name.startswith('media/'):
                        object_types['media'] = object_types.get('media', 0) + 1
                    else:
                        object_types['other'] = object_types.get('other', 0) + 1
            except Exception as e:
                self.logger.warning(f"Could not list MinIO objects: {e}")
                object_types = {'error': str(e)}
            
            metrics['storage'] = {
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2)
            }
            
            metrics['objects'] = {
                'total_count': total_objects,
                'by_type': object_types
            }
            
            # Calculate MinIO pressure based on object count and size
            # This is a simple heuristic - adjust based on your needs
            object_pressure = min((total_objects / 100000) * 100, 100)  # Pressure increases with object count
            size_pressure = min((total_size / (10 * 1024 * 1024 * 1024)) * 100, 100)  # Pressure at 10GB
            
            metrics['pressure'] = max(object_pressure, size_pressure)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting MinIO metrics: {e}")
            return {'error': str(e), 'status': 'error', 'pressure': 100}
    
    async def collect_ollama_metrics(self) -> Dict[str, Any]:
        """Collect Ollama metrics from the unified metrics API"""
        try:
            # Fetch metrics from the unified API endpoint to avoid duplicate stats management
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                try:
                    async with session.get("http://localhost:8080/api/metrics") as response:
                        if response.status == 200:
                            unified_metrics = await response.json()
                            ollama_data = unified_metrics.get('ollama', {})
                            
                            # Transform the unified metrics format to enhanced format
                            if ollama_data.get('status') == 'healthy':
                                # Calculate pressure based on usage and performance
                                total_requests = ollama_data.get('total_requests', 0)
                                models_running = ollama_data.get('models_running', 0)
                                
                                # Pressure calculation: higher usage = higher pressure
                                pressure = min(100, (models_running * 25) + (total_requests / 100))
                                
                                return {
                                    'status': 'healthy',
                                    'connection': True,
                                    'models': {
                                        'available': [model['name'] for model in ollama_data.get('models', [])],
                                        'count': ollama_data.get('models_available', 0),
                                        'running': models_running,
                                        'details': ollama_data.get('models', [])
                                    },
                                    'performance': {
                                        'total_requests': total_requests,
                                        'requests_last_hour': ollama_data.get('usage_stats', {}).get('requests_last_hour', 0),
                                        'requests_last_24h': ollama_data.get('usage_stats', {}).get('requests_last_24h', 0),
                                        'average_response_time_ms': ollama_data.get('usage_stats', {}).get('average_response_time_ms', 0),
                                        'active_sessions': ollama_data.get('usage_stats', {}).get('active_sessions', 0),
                                        'uptime_hours': ollama_data.get('usage_stats', {}).get('uptime_hours', 0)
                                    },
                                    'usage_stats': ollama_data.get('usage_stats', {}),
                                    'model_usage': ollama_data.get('usage_stats', {}).get('model_usage', {}),
                                    'most_used_model': ollama_data.get('most_used_model'),
                                    'total_model_size_mb': ollama_data.get('total_model_size_mb', 0),
                                    'pressure': round(pressure, 1)
                                }
                            else:
                                # Return error state from unified metrics
                                return {
                                    'status': ollama_data.get('status', 'error'),
                                    'connection': ollama_data.get('connection', False),
                                    'error': ollama_data.get('error', 'Unknown error'),
                                    'models': {'available': [], 'count': 0, 'running': 0},
                                    'performance': {'total_requests': 0},
                                    'pressure': 100
                                }
                        else:
                            # Fallback to direct Ollama API if unified metrics unavailable
                            return await self._collect_direct_ollama_metrics()
                            
                except Exception as e:
                    self.logger.warning(f"Could not fetch from unified metrics API: {e}")
                    # Fallback to direct Ollama API
                    return await self._collect_direct_ollama_metrics()
                    
        except Exception as e:
            self.logger.error(f"Error collecting Ollama metrics: {e}")
            return {'error': str(e), 'status': 'error', 'pressure': 100}
    
    async def _collect_direct_ollama_metrics(self) -> Dict[str, Any]:
        """Fallback method to collect basic Ollama metrics directly"""
        try:
            base_url = self.ollama_config['base_url']
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"{base_url}/api/tags") as response:
                    if response.status == 200:
                        models_data = await response.json()
                        models = models_data.get('models', [])
                        
                        return {
                            'status': 'healthy',
                            'connection': True,
                            'models': {
                                'available': [model['name'] for model in models],
                                'count': len(models),
                                'running': 0,  # Can't determine without /api/ps
                                'details': models
                            },
                            'performance': {
                                'total_requests': 0,  # No persistent tracking in fallback
                                'note': 'Limited metrics - unified API unavailable'
                            },
                            'pressure': 25  # Moderate pressure due to limited data
                        }
                    else:
                        return {
                            'status': 'error',
                            'connection': False,
                            'error': f"HTTP {response.status}",
                            'models': {'available': [], 'count': 0, 'running': 0},
                            'performance': {'total_requests': 0},
                            'pressure': 100
                        }
        except Exception as e:
            return {
                'status': 'error',
                'connection': False,
                'error': str(e),
                'models': {'available': [], 'count': 0, 'running': 0},
                'performance': {'total_requests': 0},
                'pressure': 100
            }
    
    async def collect_crawler_metrics(self) -> Dict[str, Any]:
        """Collect crawler performance and status metrics"""
        try:
            metrics = {
                'status': 'unknown',
                'http_responses': {},
                'performance': {},
                'progress': {},
                'errors': [],
                'warnings': []
            }
            
            # Try to read crawler logs for metrics
            log_file = '/app/logs/noctipede.log'
            if os.path.exists(log_file):
                try:
                    # Read recent log entries (last 1000 lines)
                    with open(log_file, 'r') as f:
                        lines = f.readlines()[-1000:]
                    
                    # Parse log entries for metrics
                    response_codes = {}
                    errors = []
                    warnings = []
                    successful_crawls = 0
                    failed_crawls = 0
                    
                    for line in lines:
                        if 'Successfully crawled' in line:
                            successful_crawls += 1
                        elif 'Failed to crawl' in line or 'ERROR' in line:
                            failed_crawls += 1
                            if len(errors) < 10:  # Keep last 10 errors
                                errors.append(line.strip())
                        elif 'WARNING' in line:
                            if len(warnings) < 10:  # Keep last 10 warnings
                                warnings.append(line.strip())
                        
                        # Extract HTTP response codes
                        if 'status' in line.lower() and any(code in line for code in ['200', '404', '403', '500', '502', '503']):
                            for code in ['200', '404', '403', '500', '502', '503']:
                                if code in line:
                                    response_codes[code] = response_codes.get(code, 0) + 1
                    
                    metrics['http_responses'] = response_codes
                    metrics['performance'] = {
                        'successful_crawls': successful_crawls,
                        'failed_crawls': failed_crawls,
                        'success_rate': (successful_crawls / (successful_crawls + failed_crawls) * 100) if (successful_crawls + failed_crawls) > 0 else 0
                    }
                    metrics['errors'] = errors[-5:]  # Last 5 errors
                    metrics['warnings'] = warnings[-5:]  # Last 5 warnings
                    metrics['status'] = 'active' if successful_crawls > 0 or failed_crawls > 0 else 'idle'
                    
                except Exception as e:
                    metrics['log_error'] = str(e)
            
            # Try to get database-based crawler metrics
            try:
                connection = pymysql.connect(**self.db_config)
                cursor = connection.cursor()
                
                # Recent crawling activity
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_pages,
                        COUNT(CASE WHEN crawled_at > NOW() - INTERVAL 1 HOUR THEN 1 END) as recent_pages,
                        COUNT(CASE WHEN crawled_at > NOW() - INTERVAL 24 HOUR THEN 1 END) as daily_pages,
                        AVG(response_time) as avg_response_time
                    FROM pages
                """)
                
                result = cursor.fetchone()
                if result:
                    metrics['progress'] = {
                        'total_pages': result[0],
                        'pages_last_hour': result[1],
                        'pages_last_24h': result[2],
                        'avg_response_time': float(result[3]) if result[3] else 0
                    }
                
                # Response code distribution from database
                cursor.execute("""
                    SELECT status_code, COUNT(*) as count
                    FROM pages 
                    WHERE crawled_at > NOW() - INTERVAL 24 HOUR
                    GROUP BY status_code
                    ORDER BY count DESC
                """)
                
                db_response_codes = {}
                for row in cursor.fetchall():
                    db_response_codes[str(row[0])] = row[1]
                
                if db_response_codes:
                    metrics['http_responses'].update(db_response_codes)
                
                connection.close()
                
            except Exception as e:
                self.logger.warning(f"Could not collect database crawler metrics: {e}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting crawler metrics: {e}")
            return {'error': str(e), 'status': 'error'}
    
    async def collect_network_metrics(self) -> Dict[str, Any]:
        """Collect network connectivity metrics from unified API"""
        try:
            # Fetch network metrics from the unified API endpoint
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                try:
                    async with session.get("http://localhost:8080/api/metrics") as response:
                        if response.status == 200:
                            unified_metrics = await response.json()
                            network_data = unified_metrics.get('network', {})
                            
                            # Transform unified network metrics to enhanced format
                            return {
                                'tor': {
                                    'status': network_data.get('tor', {}).get('status', 'unknown'),
                                    'connectivity': network_data.get('tor', {}).get('connectivity', False),
                                    'ready_for_crawling': network_data.get('tor', {}).get('ready_for_crawling', False),
                                    'proxy_working': network_data.get('tor', {}).get('proxy_working', False),
                                    'details': network_data.get('tor', {})
                                },
                                'i2p': {
                                    'status': network_data.get('i2p', {}).get('status', 'unknown'),
                                    'connectivity': network_data.get('i2p', {}).get('connectivity', False),
                                    'ready_for_crawling': network_data.get('i2p', {}).get('ready_for_crawling', False),
                                    'proxy_working': network_data.get('i2p', {}).get('proxy_working', False),
                                    'internal_proxies': network_data.get('i2p', {}).get('internal_proxies', {}),
                                    'stats_accessible': network_data.get('i2p', {}).get('stats_accessible', False),
                                    'successful_sites': network_data.get('i2p', {}).get('successful_sites', []),
                                    'details': network_data.get('i2p', {})
                                },
                                'overall_readiness': network_data.get('overall_readiness', {
                                    'ready_for_crawling': False,
                                    'tor_ready': False,
                                    'i2p_ready': False,
                                    'i2p_proxies_sufficient': False,
                                    'minimum_i2p_proxies_required': 5,
                                    'active_i2p_proxies': 0,
                                    'readiness_summary': '❌ Network metrics unavailable'
                                })
                            }
                        else:
                            # Fallback to direct testing if unified API unavailable
                            return await self._collect_direct_network_metrics()
                            
                except Exception as e:
                    self.logger.warning(f"Could not fetch from unified metrics API: {e}")
                    # Fallback to direct testing
                    return await self._collect_direct_network_metrics()
                    
        except Exception as e:
            self.logger.error(f"Error collecting network metrics: {e}")
            return {
                'tor': {'status': 'error', 'connectivity': False, 'ready_for_crawling': False, 'error': str(e)},
                'i2p': {'status': 'error', 'connectivity': False, 'ready_for_crawling': False, 'error': str(e)},
                'overall_readiness': {
                    'ready_for_crawling': False,
                    'tor_ready': False,
                    'i2p_ready': False,
                    'i2p_proxies_sufficient': False,
                    'minimum_i2p_proxies_required': 5,
                    'active_i2p_proxies': 0,
                    'readiness_summary': f'❌ Network testing failed: {str(e)}'
                }
            }
    
    async def _collect_direct_network_metrics(self) -> Dict[str, Any]:
        """Fallback method for direct network testing when unified API unavailable"""
        metrics = {
            'tor': {'status': 'unknown', 'connectivity': False, 'ready_for_crawling': False},
            'i2p': {'status': 'unknown', 'connectivity': False, 'ready_for_crawling': False},
            'overall_readiness': {
                'ready_for_crawling': False,
                'tor_ready': False,
                'i2p_ready': False,
                'i2p_proxies_sufficient': False,
                'minimum_i2p_proxies_required': 5,
                'active_i2p_proxies': 0,
                'readiness_summary': '⚠️ Using fallback network testing'
            }
        }
        
        # Basic Tor connectivity test
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.proxy_config['tor_host'], self.proxy_config['tor_port']))
            sock.close()
            
            if result == 0:
                metrics['tor'] = {
                    'status': 'warning',
                    'connectivity': True,
                    'ready_for_crawling': True,  # Assume ready if proxy accessible
                    'proxy_working': True,
                    'note': 'Basic socket test only - limited verification'
                }
            else:
                metrics['tor'] = {
                    'status': 'error',
                    'connectivity': False,
                    'ready_for_crawling': False,
                    'proxy_working': False,
                    'error': 'SOCKS5 proxy not accessible'
                }
        except Exception as e:
            metrics['tor'] = {
                'status': 'error',
                'connectivity': False,
                'ready_for_crawling': False,
                'error': str(e)
            }
        
        # Basic I2P connectivity test
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.proxy_config['i2p_host'], self.proxy_config['i2p_port']))
            sock.close()
            
            if result == 0:
                metrics['i2p'] = {
                    'status': 'warning',
                    'connectivity': True,
                    'ready_for_crawling': False,  # Can't verify internal proxies in fallback
                    'proxy_working': True,
                    'internal_proxies': {
                        'total_configured': 0,
                        'active_count': 0,
                        'minimum_required': 5,
                        'sufficient': False,
                        'note': 'Cannot test internal proxies in fallback mode'
                    },
                    'note': 'Basic socket test only - cannot verify internal proxies'
                }
            else:
                metrics['i2p'] = {
                    'status': 'error',
                    'connectivity': False,
                    'ready_for_crawling': False,
                    'proxy_working': False,
                    'error': 'HTTP proxy not accessible',
                    'internal_proxies': {
                        'total_configured': 0,
                        'active_count': 0,
                        'minimum_required': 5,
                        'sufficient': False,
                        'error': 'Proxy not accessible'
                    }
                }
        except Exception as e:
            metrics['i2p'] = {
                'status': 'error',
                'connectivity': False,
                'ready_for_crawling': False,
                'error': str(e),
                'internal_proxies': {
                    'total_configured': 0,
                    'active_count': 0,
                    'minimum_required': 5,
                    'sufficient': False,
                    'error': str(e)
                }
            }
        
        # Update overall readiness
        tor_ready = metrics['tor'].get('ready_for_crawling', False)
        i2p_ready = metrics['i2p'].get('ready_for_crawling', False)
        
        metrics['overall_readiness'] = {
            'ready_for_crawling': tor_ready and i2p_ready,
            'tor_ready': tor_ready,
            'i2p_ready': i2p_ready,
            'i2p_proxies_sufficient': False,  # Cannot verify in fallback
            'minimum_i2p_proxies_required': 5,
            'active_i2p_proxies': 0,
            'readiness_summary': f'⚠️ Fallback mode - Tor: {"OK" if tor_ready else "Failed"}, I2P: {"OK" if i2p_ready else "Failed"} (proxy verification limited)'
        }
        
        return metrics
    
    async def collect_service_health(self) -> Dict[str, Any]:
        """Collect health status of all services"""
        services = {
            'database': {'status': 'unknown'},
            'minio': {'status': 'unknown'},
            'ollama': {'status': 'unknown'},
            'tor_proxy': {'status': 'unknown'},
            'i2p_proxy': {'status': 'unknown'}
        }
        
        # Database health
        try:
            connection = pymysql.connect(**self.db_config)
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            connection.close()
            services['database'] = {'status': 'healthy', 'last_check': datetime.now().isoformat()}
        except Exception as e:
            services['database'] = {'status': 'error', 'error': str(e)}
        
        # MinIO health
        try:
            client = Minio(
                self.minio_config['endpoint'],
                access_key=self.minio_config['access_key'],
                secret_key=self.minio_config['secret_key'],
                secure=self.minio_config['secure']
            )
            # Simple bucket check
            client.bucket_exists(self.minio_config['bucket'])
            services['minio'] = {'status': 'healthy', 'last_check': datetime.now().isoformat()}
        except Exception as e:
            services['minio'] = {'status': 'error', 'error': str(e)}
        
        # Ollama health
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.ollama_config['base_url']}/api/tags") as response:
                    if response.status == 200:
                        services['ollama'] = {'status': 'healthy', 'last_check': datetime.now().isoformat()}
                    else:
                        services['ollama'] = {'status': 'error', 'error': f"HTTP {response.status}"}
        except Exception as e:
            services['ollama'] = {'status': 'error', 'error': str(e)}
        
        # Tor proxy health
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                proxy_url = f"socks5://{self.proxy_config['tor_host']}:{self.proxy_config['tor_port']}"
                async with session.get('http://httpbin.org/ip', proxy=proxy_url) as response:
                    if response.status == 200:
                        services['tor_proxy'] = {'status': 'healthy', 'last_check': datetime.now().isoformat()}
                    else:
                        services['tor_proxy'] = {'status': 'error', 'error': f"HTTP {response.status}"}
        except Exception as e:
            services['tor_proxy'] = {'status': 'error', 'error': str(e)}
        
        # I2P proxy health
        try:
            # Simple TCP connection test to I2P proxy port
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.proxy_config['i2p_host'], self.proxy_config['i2p_port']))
            sock.close()
            
            if result == 0:
                services['i2p_proxy'] = {'status': 'healthy', 'last_check': datetime.now().isoformat()}
            else:
                services['i2p_proxy'] = {'status': 'error', 'error': 'Connection refused'}
        except Exception as e:
            services['i2p_proxy'] = {'status': 'error', 'error': str(e)}
        
        return services
    
    def get_cached_metrics(self) -> Optional[Dict[str, Any]]:
        """Get cached metrics if available and recent"""
        if self.metrics_cache and self.last_update:
            age = datetime.now() - self.last_update
            if age.total_seconds() < 30:  # Cache for 30 seconds
                return self.metrics_cache
        return None

# Example usage
async def main():
    """Example usage of the enhanced metrics collector"""
    collector = EnhancedMetricsCollector()
    metrics = await collector.collect_all_metrics()
    print(json.dumps(metrics, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())
