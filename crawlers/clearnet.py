"""Clearnet (regular web) crawler."""

from .base import BaseCrawler


class ClearnetCrawler(BaseCrawler):
    """Crawler for regular clearnet websites."""
    
    def configure_proxy(self):
        """Configure Tor proxy for clearnet requests for anonymity."""
        # Route clearnet traffic through Tor for anonymity
        self.session.proxies = {
            'http': f'socks5h://{self.settings.tor_proxy_host}:{self.settings.tor_proxy_port}',
            'https': f'socks5h://{self.settings.tor_proxy_host}:{self.settings.tor_proxy_port}'
        }
        self.logger.info(f"Configured clearnet traffic through Tor proxy: {self.settings.tor_proxy_host}:{self.settings.tor_proxy_port}")
    
    def __init__(self):
        super().__init__()
        self.configure_proxy()
        self.logger.info("ClearnetCrawler initialized with Tor proxy")
