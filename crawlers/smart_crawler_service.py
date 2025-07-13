#!/usr/bin/env python3
"""
Smart Crawler Service - Event-driven crawler that starts when proxies are ready
"""

import asyncio
import aiohttp
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from core import get_logger
from config import get_settings
from .manager import CrawlerManager


class SmartCrawlerService:
    """Event-driven crawler service that monitors proxy availability."""
    
    def __init__(self, portal_url: str = "http://noctipede-portal-service:8080"):
        self.portal_url = portal_url
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.crawler_manager = CrawlerManager()
        self.last_crawl_time: Optional[datetime] = None
        self.min_crawl_interval = timedelta(minutes=30)  # Minimum time between crawls
        self.check_interval = 60  # Check proxy status every 60 seconds
        self.running = False
        
    async def check_proxy_status(self) -> Dict[str, Any]:
        """Check proxy status via portal API."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"{self.portal_url}/api/network") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"Portal API returned status {response.status}")
                        return {}
        except Exception as e:
            self.logger.error(f"Failed to check proxy status: {e}")
            return {}
    
    def are_proxies_ready(self, status: Dict[str, Any]) -> bool:
        """Check if both Tor and I2P proxies are ready for crawling."""
        if not status:
            return False
            
        tor_ready = (
            status.get('tor', {}).get('status') == 'connected' and
            status.get('tor', {}).get('connectivity', False) and
            status.get('tor', {}).get('proxy_connectivity', False)
        )
        
        i2p_ready = (
            status.get('i2p', {}).get('status') == 'connected' and
            status.get('i2p', {}).get('connectivity', False) and
            status.get('i2p', {}).get('proxy_connectivity', False)
        )
        
        return tor_ready and i2p_ready
    
    def should_start_crawl(self) -> bool:
        """Check if enough time has passed since last crawl."""
        if self.last_crawl_time is None:
            return True
            
        time_since_last = datetime.utcnow() - self.last_crawl_time
        return time_since_last >= self.min_crawl_interval
    
    async def start_crawl_session(self) -> Dict[str, Any]:
        """Start a crawling session."""
        self.logger.info("🚀 Starting smart crawl session...")
        
        try:
            # Load sites and start crawling
            sites = self.crawler_manager.load_sites_from_file()
            if not sites:
                self.logger.warning("No sites found to crawl")
                return {"success": False, "message": "No sites to crawl"}
            
            self.logger.info(f"🕷️ Starting crawl of {len(sites)} sites...")
            result = await self.crawler_manager.crawl_sites_async(sites)
            
            # Update last crawl time
            self.last_crawl_time = datetime.utcnow()
            
            self.logger.info(f"✅ Crawl completed: {result['successful']} successful, {result['failed']} failed")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Crawl session failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def monitor_and_crawl(self):
        """Main monitoring loop."""
        self.logger.info("🔍 Starting smart crawler monitoring service...")
        self.running = True
        
        consecutive_ready_checks = 0
        required_consecutive_checks = 3  # Require 3 consecutive "ready" checks before starting
        
        while self.running:
            try:
                # Check proxy status
                status = await self.check_proxy_status()
                proxies_ready = self.are_proxies_ready(status)
                
                if proxies_ready:
                    consecutive_ready_checks += 1
                    self.logger.info(f"✅ Proxies ready ({consecutive_ready_checks}/{required_consecutive_checks})")
                    
                    if consecutive_ready_checks >= required_consecutive_checks:
                        if self.should_start_crawl():
                            self.logger.info("🎯 All conditions met - starting crawl!")
                            await self.start_crawl_session()
                            consecutive_ready_checks = 0  # Reset counter after crawl
                        else:
                            time_until_next = self.min_crawl_interval - (datetime.utcnow() - self.last_crawl_time)
                            self.logger.info(f"⏳ Proxies ready but waiting {time_until_next} until next crawl")
                else:
                    if consecutive_ready_checks > 0:
                        self.logger.warning("⚠️ Proxies not ready, resetting ready counter")
                    consecutive_ready_checks = 0
                    
                    # Log specific proxy issues
                    tor_status = status.get('tor', {}).get('status', 'unknown')
                    i2p_status = status.get('i2p', {}).get('status', 'unknown')
                    self.logger.info(f"🔄 Waiting for proxies - Tor: {tor_status}, I2P: {i2p_status}")
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the monitoring service."""
        self.logger.info("🛑 Stopping smart crawler service...")
        self.running = False


async def main():
    """Main entry point for the smart crawler service."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start the service
    service = SmartCrawlerService()
    
    try:
        await service.monitor_and_crawl()
    except KeyboardInterrupt:
        service.stop()
        print("\n🛑 Smart crawler service stopped by user")
    except Exception as e:
        print(f"❌ Smart crawler service failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
