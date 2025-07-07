"""
Enhanced Portal with Extended Metrics and AI Reports
This extends the existing portal with additional metrics collection and AI reporting
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

import aiohttp
import psutil
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Import existing metrics collector
sys.path.insert(0, '/app')
from portal.metrics_collector import SystemMetricsCollector
from api.ai_reports import router as ai_reports_router, initialize_default_templates

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedMetricsCollector(SystemMetricsCollector):
    """Enhanced metrics collector that extends the base collector"""
    
    def __init__(self):
        super().__init__()
        self.ollama_config = {
            'endpoint': os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434'),
            'base_url': os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434').replace('/api/generate', '').replace('/api', '')
        }
    
    async def collect_enhanced_metrics(self) -> Dict[str, Any]:
        """Collect enhanced metrics including Ollama and detailed system info"""
        # Get base metrics
        base_metrics = await self.collect_all_metrics()
        
        # Enhance the crawler metrics with additional data
        if 'crawler' in base_metrics:
            base_metrics['crawler'] = await self.enhance_crawler_metrics(base_metrics['crawler'])
        
        # Add enhanced metrics
        enhanced = {
            **base_metrics,
            'ollama': await self.collect_ollama_metrics(),
            'detailed_system': await self.collect_detailed_system_metrics(),
            'network_connectivity': await self.collect_network_connectivity(),
            'service_pressure': await self.calculate_service_pressure()
        }
        
        # FIX: Add database metrics under 'mariadb' key for dashboard compatibility
        if 'database' in enhanced:
            enhanced['mariadb'] = enhanced['database']
        
        return enhanced
    
    async def enhance_crawler_metrics(self, base_crawler_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance crawler metrics with network breakdown and additional analysis"""
        enhanced_crawler = base_crawler_metrics.copy()
        
        try:
            # Add network breakdown
            enhanced_crawler['network_breakdown'] = await self.collect_network_breakdown()
            
            # Add log analysis
            enhanced_crawler['log_analysis'] = await self.collect_log_analysis()
            
            # Add real-time metrics
            enhanced_crawler['real_time'] = await self.collect_real_time_crawler_metrics()
            
        except Exception as e:
            logger.error(f"Error enhancing crawler metrics: {e}")
            enhanced_crawler['enhancement_error'] = str(e)
        
        return enhanced_crawler
    
    async def collect_network_breakdown(self) -> Dict[str, Any]:
        """Collect network type breakdown (Clearnet/Tor/I2P)"""
        try:
            import pymysql
            
            # Database configuration
            db_config = {
                'host': os.getenv('MARIADB_HOST', 'mariadb'),
                'port': int(os.getenv('MARIADB_PORT', 3306)),
                'user': os.getenv('MARIADB_USER', 'splinter-research'),
                'password': os.getenv('MARIADB_PASSWORD', ''),
                'database': os.getenv('MARIADB_DATABASE', 'splinter-research')
            }
            
            connection = pymysql.connect(**db_config)
            cursor = connection.cursor()
            
            # Network type breakdown using direct SQL
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN url LIKE '%.onion%' THEN 'tor'
                        WHEN url LIKE '%.i2p%' THEN 'i2p'
                        ELSE 'clearnet'
                    END as network_type,
                    COUNT(*) as count
                FROM sites 
                GROUP BY network_type
            """)
            
            breakdown = {}
            for network_type, count in cursor.fetchall():
                breakdown[network_type] = count
            
            connection.close()
            return breakdown
            
        except Exception as e:
            logger.error(f"Error collecting network breakdown: {e}")
            # Fallback: analyze from top domains if available
            try:
                from database import get_db_session, Site
                session = get_db_session()
                
                # Simple count without complex SQL
                tor_count = session.query(Site).filter(Site.url.like('%.onion%')).count()
                i2p_count = session.query(Site).filter(Site.url.like('%.i2p%')).count()
                total_count = session.query(Site).count()
                clearnet_count = total_count - tor_count - i2p_count
                
                session.close()
                
                return {
                    'tor': tor_count,
                    'i2p': i2p_count,
                    'clearnet': clearnet_count
                }
                
            except Exception as fallback_error:
                logger.error(f"Fallback network breakdown failed: {fallback_error}")
                return {'error': f'Network breakdown failed: {str(e)}', 'tor': 0, 'i2p': 0, 'clearnet': 0}
    
    async def collect_log_analysis(self) -> Dict[str, Any]:
        """Analyze recent log entries for crawler activity"""
        try:
            # Try multiple possible log locations
            log_paths = [
                '/app/logs/noctipede.log',
                '/home/celes/sources/splinterstice/noctipede/logs/noctipede.log',
                '/tmp/enhanced_portal.log',
                '/var/log/noctipede.log'
            ]
            
            log_file = None
            for path in log_paths:
                if os.path.exists(path):
                    log_file = path
                    break
            
            if not log_file:
                # No log file found, provide basic analysis from database
                return {
                    'log_file_status': 'not_found',
                    'successful_crawls': 0,
                    'failed_crawls': 0,
                    'success_rate': 0,
                    'recent_errors': [],
                    'recent_warnings': ['No log file found - using database metrics only'],
                    'log_response_codes': {},
                    'note': 'Log analysis unavailable - check log file paths'
                }
            
            # Read recent log entries (last 1000 lines)
            with open(log_file, 'r') as f:
                lines = f.readlines()[-1000:]
            
            successful_crawls = 0
            failed_crawls = 0
            recent_errors = []
            recent_warnings = []
            log_response_codes = {}
            
            for line in lines:
                if 'Successfully crawled' in line or 'SUCCESS' in line:
                    successful_crawls += 1
                elif 'Failed to crawl' in line or 'ERROR' in line:
                    failed_crawls += 1
                    if len(recent_errors) < 5:
                        recent_errors.append(line.strip())
                elif 'WARNING' in line:
                    if len(recent_warnings) < 5:
                        recent_warnings.append(line.strip())
                
                # Extract HTTP response codes from logs
                for code in ['200', '404', '403', '500', '502', '503']:
                    if code in line:
                        log_response_codes[code] = log_response_codes.get(code, 0) + 1
            
            success_rate = (successful_crawls / (successful_crawls + failed_crawls) * 100) if (successful_crawls + failed_crawls) > 0 else 0
            
            return {
                'log_file_status': 'found',
                'log_file_path': log_file,
                'successful_crawls': successful_crawls,
                'failed_crawls': failed_crawls,
                'success_rate': round(success_rate, 2),
                'recent_errors': recent_errors,
                'recent_warnings': recent_warnings,
                'log_response_codes': log_response_codes
            }
            
        except Exception as e:
            logger.error(f"Error analyzing logs: {e}")
            return {
                'error': str(e), 
                'log_file_status': 'error',
                'successful_crawls': 0, 
                'failed_crawls': 0,
                'success_rate': 0,
                'recent_errors': [],
                'recent_warnings': [f'Log analysis error: {str(e)}']
            }
    
    async def collect_real_time_crawler_metrics(self) -> Dict[str, Any]:
        """Collect real-time crawler metrics from database"""
        try:
            import pymysql
            from datetime import datetime, timedelta
            
            # Database configuration
            db_config = {
                'host': os.getenv('MARIADB_HOST', 'mariadb'),
                'port': int(os.getenv('MARIADB_PORT', 3306)),
                'user': os.getenv('MARIADB_USER', 'splinter-research'),
                'password': os.getenv('MARIADB_PASSWORD', ''),
                'database': os.getenv('MARIADB_DATABASE', 'splinter-research')
            }
            
            connection = pymysql.connect(**db_config)
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
            real_time_metrics = {}
            
            if result:
                real_time_metrics = {
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
            
            real_time_metrics['top_domains'] = top_domains
            
            connection.close()
            return real_time_metrics
            
        except Exception as e:
            logger.error(f"Error collecting real-time crawler metrics: {e}")
            return {'error': str(e)}
    
    async def collect_ollama_metrics(self) -> Dict[str, Any]:
        """Collect Ollama-specific metrics"""
        try:
            base_url = self.ollama_config['base_url']
            
            metrics = {
                'status': 'unknown',
                'models': {},
                'performance': {},
                'pressure': 0
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Test connectivity
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
                
                # Performance test
                if metrics['status'] == 'healthy':
                    try:
                        test_start = time.time()
                        test_payload = {
                            "model": "llama3.1:8b",
                            "prompt": "Hello",
                            "stream": False,
                            "options": {"num_predict": 1}
                        }
                        
                        async with session.post(f"{base_url}/api/generate", json=test_payload) as response:
                            test_time = time.time() - test_start
                            
                            if response.status == 200:
                                metrics['performance'] = {
                                    'response_time_ms': round(test_time * 1000, 2),
                                    'last_test': datetime.now().isoformat()
                                }
                                metrics['pressure'] = min((test_time / 5.0) * 100, 100)
                            else:
                                metrics['performance'] = {'error': f"Test failed: HTTP {response.status}"}
                                metrics['pressure'] = 50
                    except Exception as e:
                        metrics['performance'] = {'error': f"Performance test failed: {str(e)}"}
                        metrics['pressure'] = 75
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting Ollama metrics: {e}")
            return {'error': str(e), 'status': 'error', 'pressure': 100}
    
    async def collect_detailed_system_metrics(self) -> Dict[str, Any]:
        """Collect detailed system metrics"""
        try:
            # CPU details
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory details
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk details
            disk_usage = psutil.disk_usage('/')
            
            # Network details
            network_io = psutil.net_io_counters()
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'frequency': cpu_freq.current if cpu_freq else None
                },
                'memory': {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'percent': memory.percent,
                    'swap_percent': swap.percent
                },
                'disk': {
                    'total_gb': round(disk_usage.total / (1024**3), 2),
                    'free_gb': round(disk_usage.free / (1024**3), 2),
                    'percent': round((disk_usage.used / disk_usage.total) * 100, 1)
                },
                'network': {
                    'bytes_sent_mb': round(network_io.bytes_sent / (1024**2), 2),
                    'bytes_recv_mb': round(network_io.bytes_recv / (1024**2), 2)
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    async def collect_network_connectivity(self) -> Dict[str, Any]:
        """Test network connectivity to proxies using proper protocols"""
        connectivity = {
            'tor': {'status': 'unknown', 'connectivity': False, 'proxy_connectivity': False},
            'i2p': {'status': 'unknown', 'connectivity': False, 'proxy_connectivity': False}
        }
        
        # Test Tor SOCKS5 proxy with basic connectivity test
        try:
            # Simple connectivity test - check if we can connect to the SOCKS port (9150 in our setup)
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection('tor-proxy', 9150),
                timeout=5.0
            )
            writer.close()
            await writer.wait_closed()
            
            connectivity['tor'] = {
                'status': 'connected',
                'connectivity': True,
                'proxy_connectivity': True,
                'details': 'SOCKS5 port accessible',
                'proxy_host': 'tor-proxy',
                'proxy_port': 9150
            }
        except Exception as e:
            connectivity['tor'] = {
                'status': 'error',
                'connectivity': False,
                'proxy_connectivity': False,
                'error': f'SOCKS5 connection failed: {str(e)}'
            }
        
        # Test I2P HTTP proxy with comprehensive status checking
        try:
            # First check if I2P console is accessible
            console_accessible = False
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    async with session.get('http://i2p-proxy:7070/', timeout=aiohttp.ClientTimeout(total=3)) as console_response:
                        console_accessible = console_response.status == 200
            except:
                console_accessible = False
            
            # Test HTTP proxy functionality - this is the key test
            proxy_accessible = False
            proxy_error = None
            try:
                # Test if we can connect to the HTTP proxy port
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection('i2p-proxy', 4444),
                    timeout=3.0
                )
                writer.close()
                await writer.wait_closed()
                proxy_accessible = True
            except Exception as proxy_e:
                proxy_error = str(proxy_e)
                proxy_accessible = False
            
            # Now test if we can actually use the proxy to access I2P sites
            network_accessible = False
            network_error = None
            if proxy_accessible:
                try:
                    # Test actual I2P network access through the proxy
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                        proxy_url = 'http://i2p-proxy:4444'
                        async with session.get(
                            'http://reg.i2p/',
                            proxy=proxy_url,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            network_accessible = response.status == 200
                except Exception as net_e:
                    network_error = str(net_e)
                    network_accessible = False
            
            # Determine overall I2P status
            if proxy_accessible and network_accessible:
                connectivity['i2p'] = {
                    'status': 'connected',
                    'connectivity': True,
                    'proxy_connectivity': True,
                    'console_accessible': console_accessible,
                    'details': 'I2P proxy working, network accessible',
                    'test_site': 'reg.i2p'
                }
            elif proxy_accessible and not network_accessible:
                connectivity['i2p'] = {
                    'status': 'starting',
                    'connectivity': False,
                    'proxy_connectivity': True,
                    'console_accessible': console_accessible,
                    'details': 'I2P proxy accessible but network not ready (bootstrapping)',
                    'network_error': network_error
                }
            else:
                connectivity['i2p'] = {
                    'status': 'error',
                    'connectivity': False,
                    'proxy_connectivity': False,
                    'console_accessible': console_accessible,
                    'details': 'I2P proxy not accessible',
                    'error': proxy_error
                }
                        
        except Exception as e:
            connectivity['i2p'] = {
                'status': 'error',
                'connectivity': False,
                'proxy_connectivity': False,
                'error': f'I2P test failed: {str(e)}'
            }
        
        return connectivity
    
    async def calculate_service_pressure(self) -> Dict[str, Any]:
        """Calculate overall service pressure metrics"""
        try:
            # System pressure
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            disk_percent = (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            
            system_pressure = max(cpu_percent, memory_percent, disk_percent)
            
            # Database pressure (simplified)
            db_pressure = 0
            try:
                import pymysql
                connection = pymysql.connect(
                    host=os.getenv('MARIADB_HOST', 'mariadb'),
                    port=int(os.getenv('MARIADB_PORT', 3306)),
                    user=os.getenv('MARIADB_USER', 'splinter-research'),
                    password=os.getenv('MARIADB_PASSWORD', ''),
                    database=os.getenv('MARIADB_DATABASE', 'splinter-research')
                )
                cursor = connection.cursor()
                cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                threads_connected = int(cursor.fetchone()[1])
                cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
                max_connections = int(cursor.fetchone()[1])
                db_pressure = (threads_connected / max_connections) * 100
                connection.close()
            except:
                db_pressure = 0
            
            return {
                'system_pressure': round(system_pressure, 1),
                'database_pressure': round(db_pressure, 1),
                'overall_pressure': round(max(system_pressure, db_pressure), 1)
            }
        except Exception as e:
            return {'error': str(e)}

# Initialize FastAPI app
app = FastAPI(title="Noctipede Enhanced Portal", version="2.0.0")

# Include AI Reports router
app.include_router(ai_reports_router)

# Initialize enhanced metrics collector
enhanced_collector = EnhancedMetricsCollector()

# Setup templates
templates = Jinja2Templates(directory="/app/portal/templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Basic dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/enhanced", response_class=HTMLResponse)
async def enhanced_dashboard(request: Request):
    """Enhanced dashboard page"""
    return templates.TemplateResponse("enhanced_dashboard.html", {"request": request})

@app.get("/combined", response_class=HTMLResponse)
async def combined_dashboard(request: Request):
    """Combined dashboard page"""
    return templates.TemplateResponse("combined_dashboard.html", {"request": request})

@app.get("/ai-reports", response_class=HTMLResponse)
async def ai_reports_page(request: Request):
    """AI Reports page"""
    return templates.TemplateResponse("ai_reports.html", {"request": request})

@app.get("/api/metrics")
async def get_metrics():
    """Get comprehensive system metrics"""
    try:
        metrics = await enhanced_collector.collect_enhanced_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "noctipede-enhanced-portal",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/ollama")
async def get_ollama_metrics():
    """Get Ollama-specific metrics"""
    try:
        metrics = await enhanced_collector.collect_ollama_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/system/detailed")
async def get_detailed_system_metrics():
    """Get detailed system metrics"""
    try:
        metrics = await enhanced_collector.collect_detailed_system_metrics()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/network")
async def get_network_connectivity():
    """Get network connectivity status"""
    try:
        metrics = await enhanced_collector.collect_network_connectivity()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/pressure")
async def get_service_pressure():
    """Get service pressure metrics"""
    try:
        metrics = await enhanced_collector.calculate_service_pressure()
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# NEW: Proxy Status API Endpoints
def check_tor_proxy_status() -> Dict[str, Any]:
    """Check Tor proxy status"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('tor-proxy', 9150))
        sock.close()
        
        if result == 0:
            return {
                "ready": True,
                "status": "ready",
                "message": "Tor proxy is ready",
                "port_open": True
            }
        else:
            return {
                "ready": False,
                "status": "not_ready", 
                "message": "Tor proxy port is not accessible",
                "port_open": False
            }
    except Exception as e:
        return {
            "ready": False,
            "status": "error",
            "message": f"Error checking Tor proxy: {str(e)}",
            "port_open": False
        }

def check_i2p_proxy_status() -> Dict[str, Any]:
    """Check I2P proxy status"""
    try:
        import requests
        response = requests.get("http://i2p-proxy:4444", timeout=10)
        
        if response.status_code == 200 or "I2Pd HTTP proxy" in response.text:
            return {
                "ready": True,
                "status": "proxy_ready",
                "message": "I2P HTTP proxy is ready",
                "http_proxy": True,
                "console_accessible": False
            }
        else:
            return {
                "ready": False,
                "status": "not_ready",
                "message": "I2P proxy is not responding",
                "http_proxy": False,
                "console_accessible": False
            }
    except Exception as e:
        return {
            "ready": False,
            "status": "error",
            "message": f"Error checking I2P proxy: {str(e)}",
            "http_proxy": False,
            "console_accessible": False
        }

@app.get("/api/proxy-status")
async def get_proxy_status():
    """Get current proxy status for both Tor and I2P"""
    try:
        tor_status = check_tor_proxy_status()
        i2p_status = check_i2p_proxy_status()
        
        return JSONResponse(content={
            "tor": tor_status,
            "i2p": i2p_status,
            "both_ready": tor_status["ready"] and i2p_status["ready"],
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting proxy status: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/proxy-readiness")
async def check_proxy_readiness():
    """Check if both proxies are ready for crawling (used by crawler automation)"""
    try:
        tor_status = check_tor_proxy_status()
        i2p_status = check_i2p_proxy_status()
        
        tor_ready = tor_status["ready"]
        i2p_ready = i2p_status["ready"]
        
        return JSONResponse(content={
            "tor_ready": tor_ready,
            "i2p_ready": i2p_ready,
            "both_ready": tor_ready and i2p_ready,
            "readiness_percentage": {
                "tor": 100 if tor_ready else 0,
                "i2p": 100 if i2p_ready else 0,
                "overall": 100 if (tor_ready and i2p_ready) else (50 if (tor_ready or i2p_ready) else 0)
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error checking proxy readiness: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Initializing Enhanced Portal...")
    
    # Initialize default AI report templates
    try:
        await initialize_default_templates()
        logger.info("AI report templates initialized")
    except Exception as e:
        logger.error(f"Failed to initialize AI report templates: {e}")

if __name__ == "__main__":
    import os
    
    host = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_SERVER_PORT", 8080))
    
    logger.info(f"Starting Enhanced Noctipede Portal on {host}:{port}")
    
    uvicorn.run(
        "portal.enhanced_portal:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
