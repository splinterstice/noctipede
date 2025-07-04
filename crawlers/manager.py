"""Crawler management and coordination with async support."""

import os
import asyncio
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
    
    async def _crawl_site_async(self, url: str, crawler) -> Dict[str, Any]:
        """Async wrapper for crawling a single site."""
        try:
            if hasattr(crawler, 'crawl_site') and asyncio.iscoroutinefunction(crawler.crawl_site):
                # Async crawler (like I2P)
                result = await crawler.crawl_site(url)
            else:
                # Sync crawler (like Tor, Clearnet)
                result = crawler.crawl_site(url)
            
            return {
                'url': url,
                'success': len(result.get('pages', [])) > 0 if isinstance(result, dict) else bool(result),
                'result': result,
                'network_type': get_network_type(url)
            }
        except Exception as e:
            self.logger.error(f"Error crawling {url}: {e}")
            return {
                'url': url,
                'success': False,
                'error': str(e),
                'network_type': get_network_type(url)
            }
    
    async def crawl_sites_async(self, sites: List[str] = None) -> Dict[str, Any]:
        """Crawl multiple sites using appropriate crawlers (async version)."""
        if sites is None:
            sites = self.load_sites_from_file()
        
        if not sites:
            self.logger.error("No sites to crawl")
            return {'success': False, 'message': 'No sites to crawl'}
        
        results = {
            'total_sites': len(sites),
            'successful': 0,
            'failed': 0,
            'results': []
        }
        
        # Group sites by network type for better handling
        sites_by_network = {}
        for site in sites:
            network_type = get_network_type(site)
            if network_type not in sites_by_network:
                sites_by_network[network_type] = []
            sites_by_network[network_type].append(site)
        
        self.logger.info(f"Sites by network: {[(k, len(v)) for k, v in sites_by_network.items()]}")
        
        # Handle I2P sites first with readiness check
        if 'i2p' in sites_by_network:
            i2p_crawler = self.crawlers.get('i2p')
            if i2p_crawler:
                self.logger.info(f"🔄 Pre-checking I2P network readiness for {len(sites_by_network['i2p'])} sites...")
                # Wait for I2P readiness once for all I2P sites
                await i2p_crawler.wait_for_i2p_readiness()
        
        # Create tasks for all sites
        tasks = []
        for site in sites:
            network_type = get_network_type(site)
            crawler = self.crawlers.get(network_type)
            
            if crawler:
                task = self._crawl_site_async(site, crawler)
                tasks.append(task)
            else:
                self.logger.warning(f"No crawler available for network type: {network_type}")
                results['failed'] += 1
        
        # Execute all tasks concurrently
        if tasks:
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in completed_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Task failed with exception: {result}")
                    results['failed'] += 1
                else:
                    if result['success']:
                        results['successful'] += 1
                        self.logger.info(f"✅ Successfully crawled: {result['url']}")
                    else:
                        results['failed'] += 1
                        self.logger.warning(f"❌ Failed to crawl: {result['url']}")
                    
                    results['results'].append(result)
        
        self.logger.info(f"🎯 Crawling completed. Success: {results['successful']}, Failed: {results['failed']}")
        return results
    
    def crawl_sites(self, sites: List[str] = None) -> Dict[str, Any]:
        """Crawl multiple sites using appropriate crawlers (sync wrapper)."""
        return asyncio.run(self.crawl_sites_async(sites))
    
    async def crawl_single_site_async(self, url: str) -> Dict[str, Any]:
        """Crawl a single site using the appropriate crawler (async)."""
        network_type = get_network_type(url)
        crawler = self.crawlers.get(network_type)
        
        if not crawler:
            self.logger.error(f"No crawler available for network type: {network_type}")
            return {'success': False, 'error': f'No crawler for {network_type}'}
        
        return await self._crawl_site_async(url, crawler)
    
    def crawl_single_site(self, url: str) -> bool:
        """Crawl a single site using the appropriate crawler (sync wrapper)."""
        result = asyncio.run(self.crawl_single_site_async(url))
        return result.get('success', False)
    
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
