"""
I2P network crawler with database integration
"""
import asyncio
import aiohttp
import logging
import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse

from .base import BaseCrawler
from database import Site, Page
from database.session import get_session_manager

logger = logging.getLogger(__name__)

class I2PCrawler(BaseCrawler):
    def __init__(self, settings=None):
        super().__init__()
        # Get I2P proxy configuration from environment
        self.i2p_proxy_host = os.getenv('I2P_PROXY_HOST', 'i2p-proxy')
        self.i2p_proxy_port = os.getenv('I2P_PROXY_PORT', '4444')
        self.proxy_url = f"http://{self.i2p_proxy_host}:{self.i2p_proxy_port}"
        
        # Internal proxy configuration - comprehensive list of I2P internal proxies
        internal_proxies_str = os.getenv('I2P_INTERNAL_PROXIES', '')
        if internal_proxies_str:
            self.internal_proxies = [p.strip() for p in internal_proxies_str.split(',') if p.strip()]
        else:
            # Default comprehensive list of I2P internal proxies
            self.internal_proxies = [
                'notbob.i2p',
                'purokishi.i2p', 
                'false.i2p',
                'stormycloud.i2p',
                'reg.i2p',
                'identiguy.i2p',
                'stats.i2p',
                'i2p-projekt.i2p',
                'forum.i2p',
                'zzz.i2p',
                'echelon.i2p',
                'planet.i2p',
                'i2pwiki.i2p',
                'tracker2.postman.i2p',
                'diftracker.i2p'
            ]
        
        self.use_internal_proxies = os.getenv('USE_I2P_INTERNAL_PROXIES', 'true').lower() == 'true'
        
        logger.info(f"I2P Crawler initialized - Proxy: {self.proxy_url}, Internal proxies: {len(self.internal_proxies)}")
        
    def configure_proxy(self):
        """Configure HTTP proxy for I2P (required by base class)."""
        # This method is required by the base class but we handle proxy configuration
        # differently in our async implementation
        pass
    
    async def wait_for_i2p_readiness(self) -> bool:
        """Quick I2P network readiness check"""
        try:
            logger.info("🔄 Checking I2P network readiness...")
        except Exception:
            print("🔄 Checking I2P network readiness...")
        
        # Quick single test - if it works, we're good
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'http://reg.i2p/',
                    proxy=self.proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
                ) as response:
                    if response.status in [200, 404, 403]:
                        logger.info(f"✅ I2P network ready! (HTTP {response.status})")
                        return True
        except Exception as e:
            logger.warning(f"⚠️ I2P network not immediately ready: {str(e)[:50]}")
        
        return False  # Don't wait - proceed anyway

    async def check_site_via_notbob(self, hostname: str) -> Dict[str, Any]:
        """Quick check if site exists via notbob.i2p"""
        try:
            jump_url = f"http://notbob.i2p/cgi-bin/jump.cgi?q={hostname}"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    jump_url,
                    proxy=self.proxy_url,
                    timeout=aiohttp.ClientTimeout(total=15),
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Check if site is dead
                        if 'DEAD' in content.upper() or 'dead host' in content.lower():
                            return {'status': 'dead', 'reason': 'Confirmed dead via notbob.i2p'}
                        
                        # Look for address helper
                        import re
                        helper_match = re.search(r'i2paddresshelper=([^"&]+)', content)
                        if helper_match:
                            return {
                                'status': 'alive',
                                'address_helper': helper_match.group(1),
                                'helper_url': f"http://{hostname}/?i2paddresshelper={helper_match.group(1)}"
                            }
                        
                        # Check for redirect (alive site)
                        if 'You will be redirected' in content or 'http-equiv="Refresh"' in content:
                            return {'status': 'alive', 'method': 'redirect'}
                            
        except Exception as e:
            logger.debug(f"Notbob check failed for {hostname}: {str(e)[:50]}")
        
        return {'status': 'unknown'}



    def _crawl_i2p_site_sync(self, site: Site, db_session) -> bool:
        """Synchronous method to crawl I2P site and store results"""
        url = site.url
        parsed = urlparse(url)
        hostname = parsed.netloc
        
        try:
            # Quick network check using requests instead of aiohttp
            logger.info(f"🔍 Checking I2P network readiness...")
            if not self._check_i2p_network_sync():
                logger.error("I2P network not ready")
                return False
            
            # Step 1: Try direct access using requests
            logger.info(f"🔄 Trying direct access to {url}")
            content = self._try_direct_access_sync(url)
            
            if content:
                # Store the page content
                page = self._create_page_record(url, content, 'direct', db_session, site)
                if page:
                    logger.info(f"✅ Successfully crawled {url} directly - {len(content)} chars")
                    return True
            
            # Step 2: Try with internal proxies if enabled
            if self.use_internal_proxies and self.internal_proxies:
                logger.info(f"🔗 Trying {len(self.internal_proxies)} internal I2P proxies for {hostname}")
                for i, proxy in enumerate(self.internal_proxies, 1):
                    try:
                        # Try different proxy URL formats
                        proxy_urls = [
                            f"http://{proxy}/{hostname}/",
                            f"http://{proxy}/cgi-bin/jump.cgi?q={hostname}",
                            f"http://{proxy}/jump/{hostname}",
                            f"http://{proxy}/proxy/{hostname}"
                        ]
                        
                        for proxy_url in proxy_urls:
                            logger.info(f"🔗 [{i}/{len(self.internal_proxies)}] Trying {proxy} -> {hostname}")
                            content = self._try_direct_access_sync(proxy_url)
                            if content and len(content) > 100:  # Ensure we got actual content
                                page = self._create_page_record(proxy_url, content, f'internal_proxy_{proxy}', db_session, site)
                                if page:
                                    logger.info(f"✅ Successfully crawled {hostname} via {proxy} - {len(content)} chars")
                                    return True
                            
                    except Exception as e:
                        logger.debug(f"Proxy {proxy} failed for {hostname}: {e}")
                        continue
            
            # Step 3: Try notbob.i2p address helper as last resort
            logger.info(f"🔍 Trying notbob.i2p address helper for {hostname}")
            site_check = self.check_site_via_notbob_sync(hostname)
            if site_check.get('helper_url'):
                content = self._try_direct_access_sync(site_check['helper_url'])
                if content:
                    page = self._create_page_record(site_check['helper_url'], content, 'address_helper', db_session, site)
                    if page:
                        logger.info(f"✅ Successfully crawled {hostname} via address helper - {len(content)} chars")
                        return True
            
            # Failed to crawl
            logger.warning(f"❌ Failed to crawl {hostname} after trying direct access, {len(self.internal_proxies)} proxies, and address helper")
            site.last_error = f"Site inaccessible via direct access, {len(self.internal_proxies)} internal proxies, and address helper"
            return False
            
        except Exception as e:
            logger.error(f"Error in sync I2P crawl for {url}: {e}")
            site.last_error = str(e)
            return False

    def _check_i2p_network_sync(self) -> bool:
        """Check if I2P network is ready using synchronous requests"""
        try:
            import requests
            response = requests.get(
                "http://reg.i2p/",
                proxies={'http': self.proxy_url, 'https': self.proxy_url},
                timeout=15,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"I2P network check failed: {e}")
            return False

    def _try_direct_access_sync(self, url: str) -> Optional[str]:
        """Try to access URL directly using requests and return content"""
        try:
            import requests
            response = requests.get(
                url,
                proxies={'http': self.proxy_url, 'https': self.proxy_url},
                timeout=20,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
            )
            # Accept both 200 and 500 status codes for I2P sites (many I2P sites return 500 but have content)
            if response.status_code in [200, 500]:
                # Check if we have actual content (not just an error page)
                if len(response.text) > 100:  # Ensure we have substantial content
                    logger.info(f"✅ HTTP {response.status_code} for {url} - {len(response.text)} chars")
                    return response.text
                else:
                    logger.info(f"⚠️ HTTP {response.status_code} for {url} - insufficient content ({len(response.text)} chars)")
                    return None
            else:
                logger.info(f"⚠️ HTTP {response.status_code} for {url}")
                return None
        except requests.exceptions.Timeout:
            logger.info(f"⏰ Timeout accessing {url}")
            return None
        except Exception as e:
            logger.info(f"⚠️ Error accessing {url}: {str(e)[:50]}")
            return None



    def _try_direct_access_sync(self, url: str) -> Optional[str]:
        """Try to access URL directly and return content (synchronous version)"""
        try:
            response = requests.get(
                url,
                proxies={'http': self.proxy_url, 'https': self.proxy_url},
                timeout=20,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
            )
            if response.status_code == 200:
                logger.info(f"✅ HTTP 200 for {url}")
                return response.text
            else:
                logger.info(f"⚠️ HTTP {response.status_code} for {url}")
                return None
        except requests.exceptions.Timeout:
            logger.info(f"⏰ Timeout accessing {url}")
            return None
        except Exception as e:
            logger.info(f"⚠️ Error accessing {url}: {str(e)[:50]}")
            return None

    def wait_for_i2p_readiness_sync(self):
        """Synchronous version of wait_for_i2p_readiness"""
        logger.info("🔄 Checking I2P network readiness...")
        try:
            response = requests.get(
                'http://notbob.i2p/',
                proxies={'http': self.proxy_url, 'https': self.proxy_url},
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
            )
            if response.status_code == 200:
                logger.info("✅ I2P network ready! (HTTP 200)")
            else:
                logger.warning(f"⚠️ I2P network check returned HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ I2P network check failed: {e}")

    def check_site_via_notbob_sync(self, hostname: str) -> Dict[str, Any]:
        """Synchronous version of check_site_via_notbob with address helper support"""
        try:
            # Try to get address helper from notbob.i2p
            jump_url = f"http://notbob.i2p/cgi-bin/jump.cgi?q={hostname}"
            response = requests.get(
                jump_url,
                proxies={'http': self.proxy_url, 'https': self.proxy_url},
                timeout=15,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
            )
            
            if response.status_code == 200:
                content = response.text
                
                # Check if site is dead
                if 'DEAD' in content.upper() or 'dead host' in content.lower():
                    return {'status': 'dead', 'reason': 'Confirmed dead via notbob.i2p'}
                
                # Look for address helper
                import re
                helper_match = re.search(r'i2paddresshelper=([^"&\s]+)', content)
                if helper_match:
                    helper_url = f"http://{hostname}/?i2paddresshelper={helper_match.group(1)}"
                    return {
                        'status': 'alive',
                        'address_helper': helper_match.group(1),
                        'helper_url': helper_url
                    }
                
                # Check for redirect (alive site)
                if 'You will be redirected' in content or 'http-equiv="Refresh"' in content:
                    return {'status': 'alive', 'method': 'redirect'}
            
            # Default to unknown if we can't determine status
            return {'status': 'unknown', 'reason': 'Could not determine site status'}
            
        except Exception as e:
            logger.debug(f"Error checking site via notbob: {e}")
            return {'status': 'unknown', 'reason': f'Check failed: {str(e)[:50]}'}

    async def _crawl_i2p_site_async(self, site: Site, db_session) -> bool:
        """Async method to crawl I2P site and store results"""
        url = site.url
        parsed = urlparse(url)
        hostname = parsed.netloc
        
        # Quick network check
        await self.wait_for_i2p_readiness()
        
        # Step 1: Check if site is dead via notbob.i2p
        logger.info(f"🔍 Checking {hostname} status via notbob.i2p...")
        site_check = await self.check_site_via_notbob(hostname)
        
        if site_check['status'] == 'dead':
            logger.info(f"💀 Site {hostname} is DEAD - marking as inactive")
            site.status = 'dead'
            site.last_error = site_check['reason']
            return False
        
        # Step 2: Try direct access
        logger.info(f"🔄 Trying direct access to {url}")
        content = await self._try_direct_access(url)
        
        if content:
            # Store the page content
            page = self._create_page_record(url, content, 'direct', db_session, site)
            if page:
                logger.info(f"✅ Successfully crawled {url} directly - {len(content)} chars")
                return True
        
        # Step 3: Try with address helper if available
        if site_check['status'] == 'alive' and 'helper_url' in site_check:
            logger.info(f"🔗 Trying address helper for {hostname}")
            content = await self._try_direct_access(site_check['helper_url'])
            
            if content:
                # Store the page content with address helper URL
                page = self._create_page_record(site_check['helper_url'], content, 'address_helper', db_session, site)
                if page:
                    logger.info(f"✅ Successfully crawled {hostname} via address helper - {len(content)} chars")
                    return True
        
        # Failed to crawl
        logger.warning(f"❌ Failed to crawl {hostname}")
        site.last_error = "Site inaccessible via direct access and address helper"
        return False

    async def _try_direct_access(self, url: str) -> Optional[str]:
        """Try to access URL directly and return content"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    proxy=self.proxy_url,
                    timeout=aiohttp.ClientTimeout(total=20),
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.info(f"⚠️ HTTP {response.status} for {url}")
                        return None
        except asyncio.TimeoutError:
            logger.info(f"⏰ Timeout accessing {url}")
            return None
        except Exception as e:
            logger.info(f"⚠️ Error accessing {url}: {str(e)[:50]}")
            return None

    def _create_page_record(self, url: str, content: str, access_method: str, db_session, site: Site) -> Optional[Page]:
        """Create and store a page record"""
        try:
            # Ensure site has been committed to get ID
            if site.id is None:
                db_session.flush()  # Flush to get the site ID
            
            # Create page hash
            import hashlib
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Store content in MinIO first
            storage_result = None
            try:
                storage_result = self.storage_manager.store_page_content(url, content)
                logger.info(f"📁 Stored I2P page content: {storage_result.get('object_name')}")
            except Exception as e:
                logger.warning(f"Failed to store content in MinIO: {e}")
            
            # Create page record with site_id (no storage_path field)
            page = Page(
                site_id=site.id,
                url=url,
                content_hash=content_hash,
                content_type='text/html',
                status_code=200,
                crawled_at=datetime.utcnow(),
                content_length=len(content)
            )
            
            db_session.add(page)
            
            return page
            
        except Exception as e:
            logger.error(f"Error creating page record: {e}")
            return None

    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain from URL for storage path"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.replace(':', '_')
        except:
            return 'unknown'

    def _should_skip_site(self, url: str, db_session) -> bool:
        """Check if site should be skipped based on recent crawl."""
        if not self.settings.skip_recent_crawls:
            return False
        
        site = db_session.query(Site).filter_by(url=url).first()
        if not site or not site.last_crawled:
            return False
        
        time_threshold = datetime.utcnow() - timedelta(hours=self.settings.recent_crawl_hours)
        return site.last_crawled > time_threshold

    def _get_or_create_site(self, url: str, db_session) -> Optional[Site]:
        """Get existing site or create new one."""
        try:
            site = db_session.query(Site).filter_by(url=url).first()
            
            if not site:
                parsed_url = urlparse(url)
                site = Site(
                    url=url,
                    domain=parsed_url.netloc,
                    network_type='i2p',
                    status='pending',
                    crawl_count=0,
                    error_count=0,
                    created_at=datetime.utcnow()
                )
                db_session.add(site)
                db_session.flush()  # Ensure site gets an ID
                logger.info(f"Created new I2P site record: {url}")
            
            return site
            
        except Exception as e:
            logger.error(f"Error getting/creating site record for {url}: {e}")
            return None

    def crawl_site(self, url: str) -> Dict[str, Any]:
        """Synchronous version of crawl_site to avoid asyncio conflicts."""
        logger.info(f"🕷️ Starting I2P crawl: {url}")
        
        # Use the session manager for proper transaction handling
        session_manager = get_session_manager()
        
        try:
            with session_manager.transaction() as db_session:
                # Check if site was recently crawled
                if self._should_skip_site(url, db_session):
                    logger.info(f"Skipping recently crawled site: {url}")
                    return {
                        'url': url,
                        'pages': [],
                        'skipped': True,
                        'reason': 'recently_crawled',
                        'network_type': 'i2p'
                    }
                
                # Get or create site record
                site = self._get_or_create_site(url, db_session)
                if not site:
                    return {
                        'url': url,
                        'pages': [],
                        'errors': ['Failed to create site record'],
                        'network_type': 'i2p'
                    }
                
                # Set network type for I2P
                site.network_type = 'i2p'
                
                # Crawl the I2P site synchronously
                success = self._crawl_i2p_site_sync(site, db_session)
                
                # Update site record
                site.last_crawled = datetime.utcnow()
                if success:
                    site.crawl_count += 1
                    site.error_count = 0
                    site.last_error = None
                    site.status = 'active'
                    
                    # Return success result
                    return {
                        'url': url,
                        'pages': [{'url': url, 'content_length': 1}],  # Simplified for compatibility
                        'success': True,
                        'network_type': 'i2p'
                    }
                else:
                    site.error_count += 1
                    site.status = 'error'
                    
                    return {
                        'url': url,
                        'pages': [],
                        'errors': [site.last_error or 'Unknown error'],
                        'network_type': 'i2p'
                    }
                
        except Exception as e:
            logger.error(f"Error in I2P crawl {url}: {e}")
            return {
                'url': url,
                'pages': [],
                'errors': [str(e)],
                'network_type': 'i2p'
            }
