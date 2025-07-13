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
            # All crawlers are now synchronous, so we run them in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crawler.crawl_site, url)
            
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
    
    async def check_crawler_readiness(self, timeout: int = 30) -> Dict[str, Any]:
        """Check if the system is ready for crawling by testing network connectivity"""
        import aiohttp
        
        self.logger.info("🔍 Checking crawler readiness...")
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                # Check readiness endpoint
                try:
                    async with session.get("http://noctipede-portal-service:8080/api/readiness") as response:
                        readiness_data = await response.json()
                        
                        if response.status == 200 and readiness_data.get('ready_for_crawling', False):
                            self.logger.info("✅ System ready for crawling!")
                            self.logger.info(f"📊 {readiness_data.get('readiness_details', {}).get('readiness_summary', 'Ready')}")
                            return {
                                'ready': True,
                                'details': readiness_data
                            }
                        else:
                            readiness_summary = readiness_data.get('readiness_details', {}).get('readiness_summary', 'Not ready')
                            self.logger.warning(f"⚠️ System not ready for crawling: {readiness_summary}")
                            
                            # Log specific issues
                            network_status = readiness_data.get('network_status', {})
                            if not network_status.get('tor', {}).get('ready', False):
                                self.logger.warning("🧅 Tor network not ready")
                            if not network_status.get('i2p', {}).get('ready', False):
                                i2p_proxies = network_status.get('i2p', {}).get('internal_proxies', {})
                                active_proxies = i2p_proxies.get('active_count', 0)
                                required_proxies = i2p_proxies.get('minimum_required', 5)
                                self.logger.warning(f"🌐 I2P network not ready - Active proxies: {active_proxies}/{required_proxies}")
                            
                            return {
                                'ready': False,
                                'details': readiness_data,
                                'reason': readiness_summary
                            }
                            
                except aiohttp.ClientError as e:
                    self.logger.error(f"❌ Could not check readiness endpoint: {e}")
                    return {
                        'ready': False,
                        'error': f"Readiness endpoint unavailable: {str(e)}",
                        'reason': 'Cannot verify system readiness'
                    }
                    
        except Exception as e:
            self.logger.error(f"❌ Error checking crawler readiness: {e}")
            return {
                'ready': False,
                'error': str(e),
                'reason': 'Readiness check failed'
            }
    
    async def wait_for_readiness(self, max_wait_minutes: int = 10) -> bool:
        """Wait for the system to become ready for crawling"""
        import asyncio
        
        max_wait_seconds = max_wait_minutes * 60
        check_interval = 30  # Check every 30 seconds
        elapsed = 0
        
        self.logger.info(f"⏳ Waiting up to {max_wait_minutes} minutes for system readiness...")
        
        while elapsed < max_wait_seconds:
            readiness = await self.check_crawler_readiness()
            
            if readiness.get('ready', False):
                self.logger.info(f"✅ System ready after {elapsed // 60}m {elapsed % 60}s")
                return True
            
            self.logger.info(f"⏳ Not ready yet ({readiness.get('reason', 'Unknown')}), waiting {check_interval}s... ({elapsed}s/{max_wait_seconds}s)")
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        self.logger.error(f"❌ System not ready after {max_wait_minutes} minutes, giving up")
        return False
    
    async def crawl_sites_async(self, sites: List[str] = None) -> Dict[str, Any]:
        """Crawl multiple sites using appropriate crawlers with retry logic (async version)."""
        # Check system readiness before starting
        self.logger.info("🚀 Starting crawler with readiness checks...")
        
        readiness = await self.check_crawler_readiness()
        if not readiness.get('ready', False):
            self.logger.warning("⚠️ System not ready, waiting for readiness...")
            if not await self.wait_for_readiness(max_wait_minutes=5):
                error_msg = f"System not ready for crawling: {readiness.get('reason', 'Unknown')}"
                self.logger.error(f"❌ {error_msg}")
                return {
                    'success': False, 
                    'message': error_msg,
                    'readiness_details': readiness.get('details', {})
                }
        
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
        
        # Initialize retry tracking
        retry_counts = {site: 0 for site in sites}
        sites_to_crawl = sites.copy()
        max_retries = 3
        
        while sites_to_crawl:
            self.logger.info(f"🔄 Crawling {len(sites_to_crawl)} sites (some may be retries)")
            
            # Create tasks for current batch of sites
            tasks = []
            current_batch = sites_to_crawl.copy()
            
            for site in current_batch:
                network_type = get_network_type(site)
                crawler = self.crawlers.get(network_type)
                
                if crawler:
                    task = self._crawl_site_async(site, crawler)
                    tasks.append(task)
                else:
                    self.logger.warning(f"No crawler available for network type: {network_type}")
                    results['failed'] += 1
                    sites_to_crawl.remove(site)
            
            # Execute tasks with concurrency limit
            if tasks:
                # Respect MAX_CONCURRENT_CRAWLERS setting
                max_concurrent = self.settings.max_concurrent_crawlers
                self.logger.info(f"🔄 Running {len(tasks)} crawl tasks with max concurrency: {max_concurrent}")
                
                # Use semaphore to limit concurrent tasks
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def limited_task(task):
                    async with semaphore:
                        return await task
                
                # Wrap all tasks with semaphore
                limited_tasks = [limited_task(task) for task in tasks]
                completed_results = await asyncio.gather(*limited_tasks, return_exceptions=True)
                
                # Process results and determine retries
                sites_to_retry = []
                
                for i, result in enumerate(completed_results):
                    site = current_batch[i] if i < len(current_batch) else None
                    
                    if isinstance(result, Exception):
                        self.logger.error(f"Task failed with exception: {result}")
                        if site and retry_counts[site] < max_retries - 1:
                            retry_counts[site] += 1
                            sites_to_retry.append(site)
                            self.logger.info(f"🔄 Will retry {site} (attempt {retry_counts[site] + 1}/{max_retries})")
                        else:
                            if site:
                                self.logger.error(f"❌ {site} failed {max_retries} times, marking as recently crawled")
                                self._mark_site_as_recently_crawled(site)
                            results['failed'] += 1
                    else:
                        if result['success']:
                            results['successful'] += 1
                            self.logger.info(f"✅ Successfully crawled: {result['url']}")
                        else:
                            # Check if this is a temporary failure that should be retried
                            should_retry = self._should_retry_failure(result)
                            
                            if should_retry and site and retry_counts[site] < max_retries - 1:
                                retry_counts[site] += 1
                                sites_to_retry.append(site)
                                self.logger.info(f"🔄 Will retry {site} due to: {result.get('result', {}).get('reason', 'unknown')} (attempt {retry_counts[site] + 1}/{max_retries})")
                            else:
                                if site and retry_counts[site] >= max_retries - 1:
                                    self.logger.error(f"❌ {site} failed {max_retries} times, marking as recently crawled")
                                    self._mark_site_as_recently_crawled(site)
                                results['failed'] += 1
                                self.logger.warning(f"❌ Failed to crawl: {result['url']}")
                        
                        results['results'].append(result)
                
                # Update sites_to_crawl for next iteration
                sites_to_crawl = sites_to_retry
                
                # Add delay between retry batches
                if sites_to_crawl:
                    retry_delay = 30  # 30 seconds between retry batches
                    self.logger.info(f"⏳ Waiting {retry_delay} seconds before retrying {len(sites_to_crawl)} sites...")
                    await asyncio.sleep(retry_delay)
            else:
                break
        
        self.logger.info(f"🎯 Crawling completed. Success: {results['successful']}, Failed: {results['failed']}")
        return results
    
    def _should_retry_failure(self, result: Dict[str, Any]) -> bool:
        """Determine if a failed crawl should be retried."""
        # Handle case where result might be a boolean
        if not isinstance(result, dict):
            return False
            
        if result.get('success', False):
            return False
        
        # Safely get the reason from nested result
        result_data = result.get('result', {})
        if not isinstance(result_data, dict):
            return True  # Retry if we can't determine the reason
            
        reason = result_data.get('reason', '')
        
        # Don't retry if already marked as recently crawled
        if reason == 'recently_crawled':
            return False
        
        # Don't retry if site is permanently unreachable
        if reason in ['invalid_url', 'dns_resolution_failed']:
            return False
        
        # Retry for temporary failures
        retry_reasons = [
            'connection_timeout',
            'connection_refused', 
            'network_error',
            'proxy_error',
            'http_error',
            'ssl_error',
            'unknown_error'
        ]
        
        return any(retry_reason in reason for retry_reason in retry_reasons)
    
    def _mark_site_as_recently_crawled(self, site_url: str):
        """Mark a site as recently crawled to prevent further attempts."""
        try:
            from database.connection import get_db_session
            from database.models import Site
            from datetime import datetime, timedelta
            
            with get_db_session() as session:
                # Find or create site record
                site = session.query(Site).filter(Site.url == site_url).first()
                if not site:
                    site = Site(url=site_url, network_type=get_network_type(site_url))
                    session.add(site)
                
                # Mark as recently crawled (24 hours from now)
                site.last_crawled = datetime.utcnow()
                session.commit()
                
                self.logger.info(f"🚫 Marked {site_url} as recently crawled")
                
        except Exception as e:
            self.logger.error(f"Failed to mark site as recently crawled: {e}")
    
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


if __name__ == "__main__":
    """Main execution when run as a module."""
    import sys
    
    # Create and run crawler manager
    manager = CrawlerManager()
    
    try:
        # Load sites and start crawling
        sites = manager.load_sites_from_file()
        
        if not sites:
            print("❌ No sites found to crawl")
            sys.exit(1)
        
        print(f"🚀 Starting crawler with {len(sites)} sites...")
        
        # Run the crawler
        results = manager.crawl_sites(sites)
        
        # Print results
        print(f"✅ Crawling completed!")
        print(f"📊 Results: {results['successful']} successful, {results['failed']} failed out of {results['total_sites']} total")
        
        # Exit with appropriate code
        if results['successful'] > 0:
            sys.exit(0)
        else:
            print("❌ No sites were successfully crawled")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Crawler interrupted by user")
        manager.shutdown()
        sys.exit(130)
    except Exception as e:
        print(f"❌ Crawler failed with error: {e}")
        manager.shutdown()
        sys.exit(1)
    finally:
        manager.shutdown()
