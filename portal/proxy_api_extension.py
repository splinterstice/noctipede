"""
Simple Proxy Status API Extension
Adds proxy status endpoints to existing enhanced_portal.py
"""

import socket
import requests
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

def check_tor_proxy_status() -> Dict[str, Any]:
    """Check Tor proxy status"""
    try:
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

def add_proxy_endpoints(app):
    """Add proxy status endpoints to existing FastAPI app"""
    
    @app.get("/api/proxy-status")
    async def get_proxy_status():
        """Get current proxy status"""
        tor_status = check_tor_proxy_status()
        i2p_status = check_i2p_proxy_status()
        
        return {
            "tor": tor_status,
            "i2p": i2p_status,
            "both_ready": tor_status["ready"] and i2p_status["ready"],
            "timestamp": datetime.now().isoformat()
        }
    
    @app.get("/api/proxy-readiness")
    async def check_proxy_readiness():
        """Check if both proxies are ready for crawling"""
        tor_status = check_tor_proxy_status()
        i2p_status = check_i2p_proxy_status()
        
        tor_ready = tor_status["ready"]
        i2p_ready = i2p_status["ready"]
        
        return {
            "tor_ready": tor_ready,
            "i2p_ready": i2p_ready,
            "both_ready": tor_ready and i2p_ready,
            "readiness_percentage": {
                "tor": 100 if tor_ready else 0,
                "i2p": 100 if i2p_ready else 0,
                "overall": 100 if (tor_ready and i2p_ready) else (50 if (tor_ready or i2p_ready) else 0)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    logger.info("✅ Proxy status API endpoints added to portal")
    return app
