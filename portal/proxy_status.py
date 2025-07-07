"""
Proxy Status Module for Enhanced Portal
Adds proxy readiness checking capabilities to the existing portal
"""

import socket
import requests
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ProxyStatusChecker:
    """Handles proxy status checking for Tor and I2P"""
    
    def __init__(self):
        self.tor_host = "tor-proxy"
        self.tor_port = 9150
        self.i2p_host = "i2p-proxy"
        self.i2p_port = 4444
        self.i2p_console_port = 7070
    
    def check_tor_proxy_status(self) -> Dict[str, Any]:
        """Check Tor proxy status and connectivity"""
        try:
            # Check if Tor proxy port is open
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.tor_host, self.tor_port))
            sock.close()
            
            if result == 0:
                return {
                    "ready": True,
                    "status": "ready",
                    "message": "Tor proxy is ready and accessible",
                    "port_open": True,
                    "host": self.tor_host,
                    "port": self.tor_port
                }
            else:
                return {
                    "ready": False,
                    "status": "not_ready",
                    "message": "Tor proxy port is not accessible",
                    "port_open": False,
                    "host": self.tor_host,
                    "port": self.tor_port
                }
        except Exception as e:
            logger.error(f"Error checking Tor proxy: {e}")
            return {
                "ready": False,
                "status": "error",
                "message": f"Error checking Tor proxy: {str(e)}",
                "port_open": False,
                "host": self.tor_host,
                "port": self.tor_port
            }
    
    def check_i2p_proxy_status(self) -> Dict[str, Any]:
        """Check I2P proxy status and functionality"""
        try:
            # Check if I2P HTTP proxy is responding
            response = requests.get(f"http://{self.i2p_host}:{self.i2p_port}", timeout=10)
            
            if response.status_code == 200 or "I2Pd HTTP proxy" in response.text:
                # I2P proxy is responding, now check console for more details
                console_accessible = False
                tunnels_active = False
                
                try:
                    console_response = requests.get(f"http://{self.i2p_host}:{self.i2p_console_port}", timeout=5)
                    if console_response.status_code == 200:
                        console_accessible = True
                        # Check if tunnels are mentioned in console (basic check)
                        if "tunnel" in console_response.text.lower():
                            tunnels_active = True
                except Exception as console_error:
                    logger.debug(f"I2P console check failed: {console_error}")
                
                status = "fully_ready" if console_accessible and tunnels_active else "proxy_ready"
                message = "I2P proxy is ready with active tunnels" if tunnels_active else "I2P HTTP proxy is ready"
                
                return {
                    "ready": True,
                    "status": status,
                    "message": message,
                    "http_proxy": True,
                    "console_accessible": console_accessible,
                    "tunnels_active": tunnels_active,
                    "host": self.i2p_host,
                    "port": self.i2p_port,
                    "console_port": self.i2p_console_port
                }
            else:
                return {
                    "ready": False,
                    "status": "not_responding",
                    "message": "I2P proxy is not responding properly",
                    "http_proxy": False,
                    "console_accessible": False,
                    "tunnels_active": False,
                    "host": self.i2p_host,
                    "port": self.i2p_port
                }
        except Exception as e:
            logger.error(f"Error checking I2P proxy: {e}")
            return {
                "ready": False,
                "status": "error",
                "message": f"Error checking I2P proxy: {str(e)}",
                "http_proxy": False,
                "console_accessible": False,
                "tunnels_active": False,
                "host": self.i2p_host,
                "port": self.i2p_port
            }
    
    def get_proxy_status(self) -> Dict[str, Any]:
        """Get comprehensive proxy status for both Tor and I2P"""
        tor_status = self.check_tor_proxy_status()
        i2p_status = self.check_i2p_proxy_status()
        
        return {
            "tor": tor_status,
            "i2p": i2p_status,
            "both_ready": tor_status["ready"] and i2p_status["ready"],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_proxy_readiness(self) -> Dict[str, Any]:
        """Get proxy readiness status for crawler automation"""
        status = self.get_proxy_status()
        
        tor_ready = status["tor"]["ready"]
        i2p_ready = status["i2p"]["ready"]
        
        return {
            "tor_ready": tor_ready,
            "i2p_ready": i2p_ready,
            "both_ready": tor_ready and i2p_ready,
            "readiness_percentage": {
                "tor": 100 if tor_ready else 0,
                "i2p": 100 if i2p_ready else 0,
                "overall": 100 if (tor_ready and i2p_ready) else (50 if (tor_ready or i2p_ready) else 0)
            },
            "details": {
                "tor_status": status["tor"]["status"],
                "i2p_status": status["i2p"]["status"],
                "tor_message": status["tor"]["message"],
                "i2p_message": status["i2p"]["message"]
            },
            "timestamp": datetime.now().isoformat()
        }
