"""Tor (.onion) network crawler."""

import socks
import socket
from .base import BaseCrawler


class TorCrawler(BaseCrawler):
    """Crawler for Tor .onion sites."""
    
    def configure_proxy(self):
        """Configure SOCKS proxy for Tor."""
        # Set up SOCKS proxy for Tor - only for requests session, not globally
        self.session.proxies = {
            'http': f'socks5h://{self.settings.tor_proxy_host}:{self.settings.tor_proxy_port}',
            'https': f'socks5h://{self.settings.tor_proxy_host}:{self.settings.tor_proxy_port}'
        }
        
        # FIXED: Remove global socket proxy setting that breaks database connections
        # socket.socket = socks.socksocket  # This line was causing issues
        
        self.logger.info(f"Configured Tor proxy: {self.settings.tor_proxy_host}:{self.settings.tor_proxy_port}")
    
    def __init__(self):
        super().__init__()
        self.configure_proxy()
        self.logger.info("TorCrawler initialized")
