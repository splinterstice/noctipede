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
            connection = pymysql.connect(**self.db_config)
            cursor = connection.cursor()
            
            metrics = {
                'status': 'healthy',
                'connections': {},
                'performance': {},
                'storage': {},
                'pressure': 0
            }
            
            # Connection metrics
            cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
            threads_connected = int(cursor.fetchone()[1])
            
            cursor.execute("SHOW STATUS LIKE 'Max_used_connections'")
            max_used_connections = int(cursor.fetchone()[1])
            
            cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
            max_connections = int(cursor.fetchone()[1])
            
            metrics['connections'] = {
                'current': threads_connected,
                'max_used': max_used_connections,
                'max_allowed': max_connections,
                'utilization_percent': (threads_connected / max_connections) * 100
            }
            
            # Performance metrics
            cursor.execute("SHOW STATUS LIKE 'Queries'")
            total_queries = int(cursor.fetchone()[1])
            
            cursor.execute("SHOW STATUS LIKE 'Uptime'")
            uptime = int(cursor.fetchone()[1])
            
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
                
                cursor.execute("SELECT COUNT(*) FROM pages WHERE crawled_at > NOW() - INTERVAL 1 HOUR")
                recent_pages = cursor.fetchone()[0]
                
                metrics['noctipede'] = {
                    'sites': site_count,
                    'pages': page_count,
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
                'pressure': 0
            }
            
            # Check if bucket exists
            bucket_name = self.minio_config['bucket']
            if not client.bucket_exists(bucket_name):
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
        """Collect Ollama API metrics and performance data"""
        try:
            base_url = self.ollama_config['base_url']
            
            metrics = {
                'status': 'unknown',
                'models': {},
                'performance': {},
                'requests': {},
                'pressure': 0
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Test basic connectivity
                try:
                    async with session.get(f"{base_url}/api/tags") as response:
                        if response.status == 200:
                            models_data = await response.json()
                            metrics['status'] = 'healthy'
                            metrics['models'] = {
                                'available': [model['name'] for model in models_data.get('models', [])],
                                'count': len(models_data.get('models', []))
                            }
                        else:
                            metrics['status'] = 'error'
                            metrics['error'] = f"HTTP {response.status}"
                except Exception as e:
                    metrics['status'] = 'error'
                    metrics['error'] = str(e)
                
                # Try to get version info
                try:
                    async with session.get(f"{base_url}/api/version") as response:
                        if response.status == 200:
                            version_data = await response.json()
                            metrics['version'] = version_data.get('version', 'unknown')
                except:
                    pass  # Version endpoint might not exist
                
                # Performance test with a simple request
                if metrics['status'] == 'healthy':
                    try:
                        test_start = time.time()
                        test_payload = {
                            "model": "llama3.1:8b",  # Use a common model
                            "prompt": "Hello",
                            "stream": False,
                            "options": {"num_predict": 1}
                        }
                        
                        async with session.post(
                            f"{base_url}/api/generate",
                            json=test_payload
                        ) as response:
                            test_time = time.time() - test_start
                            
                            if response.status == 200:
                                metrics['performance'] = {
                                    'response_time_ms': round(test_time * 1000, 2),
                                    'last_test': datetime.now().isoformat()
                                }
                                
                                # Calculate pressure based on response time
                                # Pressure increases if response time > 5 seconds
                                metrics['pressure'] = min((test_time / 5.0) * 100, 100)
                            else:
                                metrics['performance'] = {
                                    'error': f"Test request failed: HTTP {response.status}",
                                    'response_time_ms': round(test_time * 1000, 2)
                                }
                                metrics['pressure'] = 50  # Partial failure
                    except Exception as e:
                        metrics['performance'] = {'error': f"Performance test failed: {str(e)}"}
                        metrics['pressure'] = 75  # High pressure due to performance issues
                
                # Request statistics (would need to be tracked separately in production)
                metrics['requests'] = {
                    'note': 'Request statistics would be tracked by the application',
                    'total_requests': 'N/A',
                    'successful_requests': 'N/A',
                    'failed_requests': 'N/A'
                }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting Ollama metrics: {e}")
            return {'error': str(e), 'status': 'error', 'pressure': 100}
    
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
        """Collect network connectivity metrics for Tor and I2P"""
        metrics = {
            'tor': {'status': 'unknown', 'connectivity': False},
            'i2p': {'status': 'unknown', 'connectivity': False, 'proxy_connectivity': False}
        }
        
        # Test Tor connectivity
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                # Test Tor SOCKS proxy
                proxy_url = f"socks5://{self.proxy_config['tor_host']}:{self.proxy_config['tor_port']}"
                
                try:
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
                    metrics['tor'] = {
                        'status': 'error',
                        'connectivity': False,
                        'error': str(e)
                    }
        except Exception as e:
            metrics['tor'] = {'status': 'error', 'connectivity': False, 'error': str(e)}
        
        # Test I2P connectivity
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                # Test I2P HTTP proxy connectivity
                proxy_url = f"http://{self.proxy_config['i2p_host']}:{self.proxy_config['i2p_port']}"
                
                try:
                    # Test proxy connectivity first
                    async with session.get(
                        f"http://{self.proxy_config['i2p_host']}:{self.proxy_config['i2p_port']}"
                    ) as response:
                        metrics['i2p']['proxy_connectivity'] = True
                except:
                    metrics['i2p']['proxy_connectivity'] = False
                
                # Test I2P network connectivity through proxy
                try:
                    async with session.get(
                        'http://stats.i2p',
                        proxy=proxy_url
                    ) as response:
                        if response.status == 200:
                            metrics['i2p'].update({
                                'status': 'healthy',
                                'connectivity': True,
                                'network_access': True
                            })
                        else:
                            metrics['i2p'].update({
                                'status': 'partial',
                                'connectivity': False,
                                'network_access': False,
                                'error': f"HTTP {response.status}"
                            })
                except Exception as e:
                    metrics['i2p'].update({
                        'status': 'error' if not metrics['i2p']['proxy_connectivity'] else 'partial',
                        'connectivity': False,
                        'network_access': False,
                        'error': str(e)
                    })
        except Exception as e:
            metrics['i2p'].update({
                'status': 'error',
                'connectivity': False,
                'proxy_connectivity': False,
                'error': str(e)
            })
        
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
