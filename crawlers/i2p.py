"""
I2P network crawler with enhanced connectivity and internal proxy support
"""
import asyncio
import aiohttp
import logging
import os
from typing import Dict, List, Any, Optional
from .base import BaseCrawler

logger = logging.getLogger(__name__)

class I2PCrawler(BaseCrawler):
    def __init__(self):
        super().__init__()
        # Get I2P proxy configuration from environment
        self.i2p_proxy_host = os.getenv('I2P_PROXY_HOST', 'i2p-proxy')
        self.i2p_proxy_port = os.getenv('I2P_PROXY_PORT', '4444')
        self.proxy_url = f"http://{self.i2p_proxy_host}:{self.i2p_proxy_port}"
        
        # Internal proxy configuration
        internal_proxies_str = os.getenv('I2P_INTERNAL_PROXIES', '')
        self.internal_proxies = [p.strip() for p in internal_proxies_str.split(',') if p.strip()] if internal_proxies_str else []
        self.use_internal_proxies = os.getenv('USE_I2P_INTERNAL_PROXIES', 'false').lower() == 'true'
        
        self.max_wait_minutes = 10  # Maximum wait for I2P network readiness
        logger.info(f"I2P Crawler initialized - Proxy: {self.proxy_url}, Internal proxies: {len(self.internal_proxies)}")
        
    def configure_proxy(self):
        """Configure HTTP proxy for I2P (required by base class)."""
        # This method is required by the base class but we handle proxy configuration
        # differently in our async implementation
        pass
    
    async def wait_for_i2p_readiness(self) -> bool:
        """Wait for I2P network to be ready for crawling"""
        logger.info("🔄 Waiting for I2P network readiness...")
        
        # Test sites to check I2P connectivity
        test_sites = [
            'http://reg.i2p/',
            'http://notbob.i2p/',
            'http://stats.i2p/'
        ]
        
        for attempt in range(self.max_wait_minutes * 2):  # Check every 30 seconds
            try:
                async with aiohttp.ClientSession() as session:
                    for test_site in test_sites:
                        try:
                            async with session.get(
                                test_site,
                                proxy=self.proxy_url,
                                timeout=aiohttp.ClientTimeout(total=15),
                                headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
                            ) as response:
                                if response.status == 200:
                                    logger.info(f"✅ I2P network ready! Test site {test_site} returned HTTP 200")
                                    return True
                                elif response.status in [404, 403]:  # Site exists but content not found
                                    logger.info(f"✅ I2P network ready! Test site {test_site} returned HTTP {response.status}")
                                    return True
                        except Exception as e:
                            logger.debug(f"Test site {test_site} failed: {str(e)[:50]}...")
                            continue
                            
                logger.info(f"⏳ I2P network not ready yet (attempt {attempt + 1}/{self.max_wait_minutes * 2}), waiting 30s...")
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.debug(f"I2P readiness check error: {e}")
                await asyncio.sleep(30)
        
        logger.warning("⚠️ I2P network readiness timeout - proceeding with internal proxies")
        return False
    
    async def test_internal_proxies(self) -> List[str]:
        """Test which internal I2P proxies are accessible"""
        working_proxies = []
        
        if not self.use_internal_proxies or not self.internal_proxies:
            logger.info("Internal I2P proxies disabled or not configured")
            return working_proxies
            
        logger.info(f"🧪 Testing {len(self.internal_proxies)} internal I2P proxies...")
        
        async with aiohttp.ClientSession() as session:
            for proxy in self.internal_proxies:
                try:
                    proxy_url = f"http://{proxy.strip()}/"
                    async with session.get(
                        proxy_url,
                        proxy=self.proxy_url,
                        timeout=aiohttp.ClientTimeout(total=20),
                        headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
                    ) as response:
                        if response.status in [200, 404, 403]:  # Any response means proxy is reachable
                            working_proxies.append(proxy.strip())
                            logger.info(f"✅ Internal proxy working: {proxy.strip()} (HTTP {response.status})")
                        else:
                            logger.debug(f"Internal proxy {proxy.strip()} returned HTTP {response.status}")
                except Exception as e:
                    logger.debug(f"Internal proxy {proxy.strip()} failed: {str(e)[:50]}...")
        
        logger.info(f"🎯 Found {len(working_proxies)} working internal I2P proxies")
        return working_proxies
    
    async def crawl_site(self, url: str) -> Dict[str, Any]:
        """Crawl an I2P site with enhanced error handling and retry logic"""
        logger.info(f"🕷️ Starting I2P crawl: {url}")
        
        # Wait for I2P network readiness
        if not await self.wait_for_i2p_readiness():
            logger.warning("Proceeding without confirmed I2P network readiness")
        
        # Test internal proxies
        working_proxies = await self.test_internal_proxies()
        if working_proxies:
            logger.info(f"Internal proxies available: {', '.join(working_proxies)}")
        
        result = {
            'url': url,
            'pages': [],
            'errors': [],
            'network_type': 'i2p',
            'proxy_status': 'connected',
            'internal_proxies': working_proxies
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Enhanced retry logic for I2P
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        async with session.get(
                            url,
                            proxy=self.proxy_url,
                            timeout=aiohttp.ClientTimeout(total=30),
                            headers={
                                'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)',
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                            }
                        ) as response:
                            if response.status == 200:
                                content = await response.text()
                                page_data = {
                                    'url': url,
                                    'content': content,
                                    'status_code': response.status,
                                    'content_type': response.headers.get('content-type', ''),
                                    'timestamp': self.get_timestamp(),
                                    'network_type': 'i2p'
                                }
                                result['pages'].append(page_data)
                                logger.info(f"✅ Successfully crawled {url} - {len(content)} chars")
                                break
                            elif response.status in [404, 403, 410]:
                                logger.info(f"⚠️ Site {url} returned HTTP {response.status} - site may not exist")
                                result['errors'].append(f"HTTP {response.status}")
                                break
                            else:
                                logger.warning(f"⚠️ Site {url} returned HTTP {response.status} (attempt {attempt + 1})")
                                if attempt == max_retries - 1:
                                    result['errors'].append(f"HTTP {response.status} after {max_retries} attempts")
                                else:
                                    await asyncio.sleep(10)  # Wait before retry
                                    
                    except aiohttp.ClientError as e:
                        logger.warning(f"⚠️ Connection error for {url} (attempt {attempt + 1}): {str(e)[:100]}")
                        if attempt == max_retries - 1:
                            result['errors'].append(f"Connection error: {str(e)[:100]}")
                        else:
                            await asyncio.sleep(10)
                            
        except Exception as e:
            error_msg = f"Crawl error: {str(e)[:100]}"
            logger.error(f"❌ {error_msg}")
            result['errors'].append(error_msg)
            result['proxy_status'] = 'error'
        
        return result
    
    def get_timestamp(self):
        """Get current timestamp"""
        import datetime
        return datetime.datetime.now().isoformat()
