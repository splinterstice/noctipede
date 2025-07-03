"""Crawler management and coordination."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from queue import Queue, Empty

from core import get_logger, get_network_type
from config import get_settings
from .clearnet import ClearnetCrawler
from .tor import TorCrawler
from .i2p import I2PCrawler


class CrawlerManager:
    """Manages multiple crawlers and coordinates crawling activities."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.crawlers = {}
        self.url_queue = Queue(maxsize=self.settings.max_queue_size)
        self.results = []
        self._initialize_crawlers()
    
    def _initialize_crawlers(self):
        """Initialize crawlers for different networks."""
        self.crawlers = {
            'clearnet': ClearnetCrawler(),
            'tor': TorCrawler(),
            'i2p': I2PCrawler()
        }
        self.logger.info("Initialized all crawlers")
    
    def load_sites_from_file(self, file_path: str = None) -> List[str]:
        """Load sites from sites.txt file."""
        file_path = file_path or self.settings.sites_file_path
        
        if not os.path.exists(file_path):
            self.logger.error(f"Sites file not found: {file_path}")
            return []
        
        sites = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        sites.append(line)
            
            self.logger.info(f"Loaded {len(sites)} sites from {file_path}")
            return sites
            
        except Exception as e:
            self.logger.error(f"Error loading sites from {file_path}: {e}")
            return []
    
    def add_urls_to_queue(self, urls: List[str]):
        """Add URLs to the crawling queue."""
        for url in urls:
            try:
                self.url_queue.put(url, timeout=1)
            except:
                self.logger.warning(f"Queue full, skipping URL: {url}")
    
    def crawl_sites(self, sites: List[str] = None) -> Dict[str, Any]:
        """Crawl multiple sites using appropriate crawlers."""
        if sites is None:
            sites = self.load_sites_from_file()
        
        if not sites:
            self.logger.error("No sites to crawl")
            return {'success': False, 'message': 'No sites to crawl'}
        
        # Add sites to queue
        self.add_urls_to_queue(sites)
        
        # Start crawling with thread pool
        results = {
            'total_sites': len(sites),
            'successful': 0,
            'failed': 0,
            'results': []
        }
        
        with ThreadPoolExecutor(max_workers=self.settings.max_concurrent_crawlers) as executor:
            # Submit crawling tasks
            future_to_url = {}
            
            while not self.url_queue.empty():
                try:
                    url = self.url_queue.get(timeout=1)
                    network_type = get_network_type(url)
                    crawler = self.crawlers.get(network_type)
                    
                    if crawler:
                        future = executor.submit(crawler.crawl_site, url)
                        future_to_url[future] = url
                    else:
                        self.logger.warning(f"No crawler available for network type: {network_type}")
                        results['failed'] += 1
                        
                except Empty:
                    break
                except Exception as e:
                    self.logger.error(f"Error submitting crawl task: {e}")
                    results['failed'] += 1
            
            # Process completed tasks
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    success = future.result()
                    if success:
                        results['successful'] += 1
                        self.logger.info(f"Successfully crawled: {url}")
                    else:
                        results['failed'] += 1
                        self.logger.warning(f"Failed to crawl: {url}")
                    
                    results['results'].append({
                        'url': url,
                        'success': success,
                        'network_type': get_network_type(url)
                    })
                    
                except Exception as e:
                    results['failed'] += 1
                    self.logger.error(f"Error crawling {url}: {e}")
                    results['results'].append({
                        'url': url,
                        'success': False,
                        'error': str(e),
                        'network_type': get_network_type(url)
                    })
        
        self.logger.info(f"Crawling completed. Success: {results['successful']}, Failed: {results['failed']}")
        return results
    
    def crawl_single_site(self, url: str) -> bool:
        """Crawl a single site using the appropriate crawler."""
        network_type = get_network_type(url)
        crawler = self.crawlers.get(network_type)
        
        if not crawler:
            self.logger.error(f"No crawler available for network type: {network_type}")
            return False
        
        return crawler.crawl_site(url)
    
    def get_crawler_stats(self) -> Dict[str, Any]:
        """Get statistics about crawler performance."""
        # This would be implemented to gather stats from database
        # For now, return basic info
        return {
            'crawlers_initialized': len(self.crawlers),
            'queue_size': self.url_queue.qsize(),
            'max_queue_size': self.settings.max_queue_size,
            'max_concurrent_crawlers': self.settings.max_concurrent_crawlers
        }
    
    def shutdown(self):
        """Shutdown all crawlers and clean up resources."""
        for crawler in self.crawlers.values():
            crawler.close()
        
        self.logger.info("All crawlers shut down")
