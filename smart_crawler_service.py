#!/usr/bin/env python3
"""Smart Crawler Service - Actually Smart Edition!"""

import asyncio
import aiohttp
import time
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

sys.path.insert(0, '/app')

from core import get_logger
from config import get_settings
from crawlers.manager import CrawlerManager
from database.connection import get_db_manager
from database.models import Site

class SmartCrawlerService:
    def __init__(self, portal_url='http://noctipede-portal-service:8080'):
        self.portal_url = portal_url
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.crawler_manager = CrawlerManager()
        self.last_crawl_times = {
            'tor': None,
            'i2p': None,
            'clearnet': None
        }
        self.min_crawl_interval = timedelta(minutes=10)  # More frequent crawling
        self.check_interval = 30  # Check every 30 seconds
        self.running = False
        
        # Initialize database
        self.db_manager = get_db_manager()
        
    async def check_proxy_status(self):
        """Check proxy status from portal API."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f'{self.portal_url}/api/network') as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f'Portal API returned status {response.status}')
                        return {}
        except Exception as e:
            self.logger.error(f'Failed to check proxy status: {e}')
            return {}
    
    def is_network_ready(self, status: dict, network: str) -> bool:
        """Check if a specific network is ready."""
        if not status:
            return False
            
        network_status = status.get(network, {})
        return (
            network_status.get('status') == 'connected' and
            network_status.get('connectivity', False) and
            network_status.get('proxy_connectivity', False)
        )
    
    def should_crawl_network(self, network: str) -> bool:
        """Check if we should crawl a specific network."""
        last_crawl = self.last_crawl_times.get(network)
        if last_crawl is None:
            return True
            
        time_since_last = datetime.utcnow() - last_crawl
        return time_since_last >= self.min_crawl_interval
    
    async def get_sites_for_network(self, network: str) -> List[str]:
        """Get site URLs to crawl for a specific network."""
        try:
            with self.db_manager.get_session() as session:
                sites = session.query(Site).filter(
                    Site.network_type == network,
                    Site.status == 'active'
                ).all()
                # Return URLs instead of Site objects to avoid session binding issues
                return [site.url for site in sites]
        except Exception as e:
            self.logger.error(f'Failed to get sites for {network}: {e}')
            return []
    
    async def crawl_network_sites(self, network: str, site_urls: List[str]) -> dict:
        """Crawl sites for a specific network."""
        if not site_urls:
            self.logger.warning(f'No {network} sites to crawl')
            return {'success': False, 'message': f'No {network} sites found'}
        
        self.logger.info(f'🕷️ Starting {network} crawl of {len(site_urls)} sites...')
        
        try:
            # Use the appropriate crawler based on network type
            if network == 'tor':
                result = await self.crawler_manager.tor_crawler.crawl_sites_async(site_urls)
            elif network == 'i2p':
                result = await self.crawler_manager.i2p_crawler.crawl_sites_async(site_urls)
            elif network == 'clearnet':
                result = await self.crawler_manager.clearnet_crawler.crawl_sites_async(site_urls)
            else:
                return {'success': False, 'error': f'Unknown network type: {network}'}
            
            self.last_crawl_times[network] = datetime.utcnow()
            
            self.logger.info(f'✅ {network.upper()} crawl completed: {result.get("successful", 0)} successful, {result.get("failed", 0)} failed')
            return result
            
        except Exception as e:
            self.logger.error(f'❌ {network.upper()} crawl failed: {e}')
            return {'success': False, 'error': str(e)}
    
    async def monitor_and_crawl(self):
        """Main monitoring loop - actually smart this time!"""
        self.logger.info('🧠 Starting SMART crawler monitoring service...')
        self.running = True
        
        # Initialize database on startup
        try:
            self.db_manager.create_tables()
            self.logger.info('✅ Database tables initialized')
        except Exception as e:
            self.logger.error(f'❌ Database initialization failed: {e}')
        
        while self.running:
            try:
                status = await self.check_proxy_status()
                
                # Check each network independently and crawl when ready
                networks_to_check = ['tor', 'i2p', 'clearnet']
                
                for network in networks_to_check:
                    if self.is_network_ready(status, network) and self.should_crawl_network(network):
                        self.logger.info(f'🎯 {network.upper()} is ready and due for crawling!')
                        
                        site_urls = await self.get_sites_for_network(network)
                        if site_urls:
                            await self.crawl_network_sites(network, site_urls)
                        else:
                            self.logger.warning(f'No {network} sites found in database')
                    elif self.is_network_ready(status, network):
                        time_until_next = self.min_crawl_interval - (datetime.utcnow() - (self.last_crawl_times[network] or datetime.utcnow()))
                        if time_until_next.total_seconds() > 0:
                            self.logger.debug(f'⏳ {network.upper()} ready but waiting {time_until_next} until next crawl')
                    else:
                        self.logger.debug(f'⚠️ {network.upper()} not ready')
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info('🛑 Smart crawler stopped by user')
                break
            except Exception as e:
                self.logger.error(f'❌ Error in monitoring loop: {e}')
                await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the monitoring service."""
        self.running = False

async def main():
    """Main entry point."""
    service = SmartCrawlerService()
    
    try:
        await service.monitor_and_crawl()
    except KeyboardInterrupt:
        service.stop()
        print('🛑 Smart crawler service stopped by user')
    except Exception as e:
        print(f'❌ Smart crawler service failed: {e}')

if __name__ == "__main__":
    asyncio.run(main())
