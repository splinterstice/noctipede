"""Web crawling engines for different networks."""

from .base import BaseCrawler
from .clearnet import ClearnetCrawler
from .tor import TorCrawler
from .i2p import I2PCrawler
from .manager import CrawlerManager

__all__ = ['BaseCrawler', 'ClearnetCrawler', 'TorCrawler', 'I2PCrawler', 'CrawlerManager']
