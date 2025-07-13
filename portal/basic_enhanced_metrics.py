"""
Basic Enhanced Metrics Collector for Noctipede System
No external dependencies required - uses only standard library
"""

import time
import os
import platform
from datetime import datetime
from typing import Dict, Any

class BasicEnhancedMetricsCollector:
    """Basic enhanced metrics collector using only standard library"""
    
    def __init__(self):
        pass
        
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect basic enhanced metrics using standard library only"""
        start_time = time.time()
        
        try:
            # Basic system info using standard library
            system_metrics = self.get_basic_system_metrics()
            
            # Mock enhanced structure for compatibility
            metrics = {
                "system": system_metrics,
                "database": self.get_mock_database_metrics(),
                "minio": self.get_mock_minio_metrics(),
                "ollama": self.get_mock_ollama_metrics(),
                "crawler": self.get_mock_crawler_metrics(),
                "network": self.get_mock_network_metrics(),
                "services": self.get_mock_services_metrics(),
                "timestamp": datetime.utcnow().isoformat(),
                "collection_time": round(time.time() - start_time, 2),
                "status": "basic_enhanced",
                "message": "Using standard library only - install psutil/aiohttp for full metrics"
            }
            
            return metrics
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "collection_time": round(time.time() - start_time, 2),
                "status": "error"
            }
    
    def get_basic_system_metrics(self) -> Dict[str, Any]:
        """Get basic system metrics using standard library"""
        try:
            # Basic system info
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            
            # Try to get some basic info from /proc if available (Linux)
            cpu_count = os.cpu_count() or 1
            
            # Basic disk info
            try:
                stat = os.statvfs('/')
                total_space = stat.f_frsize * stat.f_blocks
                free_space = stat.f_frsize * stat.f_bavail
                used_space = total_space - free_space
                disk_usage_percent = (used_space / total_space) * 100 if total_space > 0 else 0
            except:
                total_space = free_space = disk_usage_percent = 0
            
            return {
                "cpu": {
                    "usage_percent": 0,  # Can't get without psutil
                    "count": cpu_count,
                    "load_avg": {
                        "1min": load_avg[0],
                        "5min": load_avg[1],
                        "15min": load_avg[2]
                    }
                },
                "memory": {
                    "total_gb": 0,  # Can't get without psutil
                    "available_gb": 0,  # Can't get without psutil
                    "usage_percent": 0  # Can't get without psutil
                },
                "disk": {
                    "total_gb": round(total_space / (1024**3), 2),
                    "free_gb": round(free_space / (1024**3), 2),
                    "usage_percent": round(disk_usage_percent, 1)
                },
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "machine": platform.machine(),
                    "python_version": platform.python_version()
                },
                "status": "basic"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_mock_database_metrics(self) -> Dict[str, Any]:
        """Mock database metrics for compatibility"""
        return {
            "status": "unknown",
            "connections": {"current": 0, "max": 100, "usage_percent": 0},
            "size": {"total_mb": 0, "tables": []},
            "performance": {
                "buffer_hit_ratio_percent": 95,
                "total_queries": 0,
                "slow_queries": 0
            },
            "pressure": {"buffer_pressure": 5}
        }
    
    def get_mock_minio_metrics(self) -> Dict[str, Any]:
        """Mock MinIO metrics for compatibility"""
        return {
            "status": "unknown",
            "connection": False,
            "bucket_exists": False,
            "storage": {
                "object_count": 0,
                "total_size_mb": 0,
                "bucket_name": "noctipede-data",
                "file_types": {},
                "largest_files": []
            },
            "pressure": {"storage_usage_gb": 0}
        }
    
    def get_mock_ollama_metrics(self) -> Dict[str, Any]:
        """Mock Ollama metrics for compatibility"""
        return {
            "status": "unknown",
            "connection": False,
            "models_available": 0,
            "models_running": 0,
            "total_requests": 0,
            "performance": {"response_time_ms": 0},
            "usage_stats": {
                "requests_last_24h": 0,
                "active_sessions": 0,
                "average_response_time_ms": 0
            },
            "models": []
        }
    
    def get_mock_crawler_metrics(self) -> Dict[str, Any]:
        """Mock crawler metrics for compatibility"""
        return {
            "status": "unknown",
            "performance": {
                "hit_rate_percent": 0,
                "error_rate_percent": 0
            },
            "progress": {
                "total_sites": 0,
                "sites_crawled_today": 0,
                "completion_rate_percent": 0
            },
            "real_time": {
                "total_pages": 0,
                "pages_last_24h": 0,
                "avg_response_time": 0,
                "last_crawl": None
            },
            "errors": {"error_rate_percent": 0}
        }
    
    def get_mock_network_metrics(self) -> Dict[str, Any]:
        """Mock network metrics for compatibility"""
        return {
            "tor": {
                "status": "unknown",
                "connectivity": False,
                "is_tor": False,
                "error": "Not tested in basic mode"
            },
            "i2p": {
                "status": "unknown",
                "connectivity": False,
                "proxy_working": False,
                "error": "Not tested in basic mode"
            }
        }
    
    def get_mock_services_metrics(self) -> Dict[str, Any]:
        """Mock services metrics for compatibility"""
        return {
            "database": {"status": "unknown"},
            "minio": {"status": "unknown"},
            "ollama": {"status": "unknown"},
            "crawler": {"status": "unknown"}
        }
