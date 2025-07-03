"""I2P (.i2p) network crawler."""

from .base import BaseCrawler


class I2PCrawler(BaseCrawler):
    """Crawler for I2P .i2p sites."""
    
    def configure_proxy(self):
        """Configure HTTP proxy for I2P."""
        # Set up HTTP proxy for I2P
        self.session.proxies = {
            'http': f'http://{self.settings.i2p_proxy_host}:{self.settings.i2p_proxy_port}',
            'https': f'http://{self.settings.i2p_proxy_host}:{self.settings.i2p_proxy_port}'
        }
        
        self.logger.info(f"Configured I2P proxy: {self.settings.i2p_proxy_host}:{self.settings.i2p_proxy_port}")
    
    def __init__(self):
        super().__init__()
        self.configure_proxy()
        self.logger.info("I2PCrawler initialized")
