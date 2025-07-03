"""Clearnet (regular web) crawler."""

from .base import BaseCrawler


class ClearnetCrawler(BaseCrawler):
    """Crawler for regular clearnet websites."""
    
    def configure_proxy(self):
        """No proxy needed for clearnet."""
        # Clearnet doesn't need proxy configuration
        pass
    
    def __init__(self):
        super().__init__()
        self.configure_proxy()
        self.logger.info("ClearnetCrawler initialized")
