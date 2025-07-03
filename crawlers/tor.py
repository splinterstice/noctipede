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
        
        # DO NOT set global socket proxy - this affects database connections too
        # socks.set_default_proxy() is removed to prevent database connection issues
        socket.socket = socks.socksocket
        
        self.logger.info(f"Configured Tor proxy: {self.settings.tor_proxy_host}:{self.settings.tor_proxy_port}")
    
    def __init__(self):
        super().__init__()
        self.configure_proxy()
        self.logger.info("TorCrawler initialized")
