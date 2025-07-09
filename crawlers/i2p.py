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
        # Use settings object for consistent configuration
        self.i2p_proxy_host = self.settings.i2p_proxy_host
        self.i2p_proxy_port = self.settings.i2p_proxy_port
        self.proxy_url = f"http://{self.i2p_proxy_host}:{self.i2p_proxy_port}"
        
        # Internal proxy configuration - use settings object
        self.internal_proxies = self.settings.i2p_internal_proxies_list
        
        # If no proxies configured in settings, use comprehensive default list
        if not self.internal_proxies:
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
        
        # Use settings for internal proxy configuration
        self.use_internal_proxies = self.settings.use_i2p_internal_proxies
        
        logger.info(f"I2P Crawler initialized - Proxy: {self.proxy_url}, Internal proxies: {len(self.internal_proxies)}")
        
    def configure_proxy(self):
        """Configure HTTP proxy for I2P (required by base class)."""
        # This method is required by the base class but we handle proxy configuration
        # differently in our async implementation
        pass
    
    def wait_for_i2p_readiness(self) -> bool:
        """Check I2P readiness via unified metrics API"""
        try:
            logger.info("🔄 Checking I2P network readiness via metrics API...")
        except Exception:
            print("🔄 Checking I2P network readiness via metrics API...")
        
        try:
            import requests
            
            # Check the unified metrics API for I2P readiness
            response = requests.get(
                'http://noctipede-portal-service:8080/api/metrics',
                timeout=30,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede-I2P-Crawler/1.0)'}
            )
            
            if response.status_code == 200:
                metrics_data = response.json()
                network_data = metrics_data.get('network', {})
                overall_readiness = network_data.get('overall_readiness', {})
                i2p_data = network_data.get('i2p', {})
                
                # Check comprehensive I2P readiness
                i2p_ready = i2p_data.get('ready_for_crawling', False)
                i2p_proxy_working = i2p_data.get('proxy_working', False)
                i2p_connectivity = i2p_data.get('connectivity', False)
                proxies_sufficient = i2p_data.get('internal_proxies', {}).get('sufficient', False)
                active_proxies = i2p_data.get('internal_proxies', {}).get('active_count', 0)
                
                if i2p_ready and i2p_proxy_working and i2p_connectivity and proxies_sufficient:
                    logger.info(f"✅ I2P network fully ready! ({active_proxies}/5+ internal proxies active)")
                    return True
                else:
                    # Log specific issues
                    issues = []
                    if not i2p_proxy_working:
                        issues.append("proxy not working")
                    if not i2p_connectivity:
                        issues.append("no connectivity")
                    if not proxies_sufficient:
                        issues.append(f"insufficient proxies ({active_proxies}/5)")
                    
                    logger.warning(f"⚠️ I2P not ready: {', '.join(issues)}")
                    return False
            else:
                logger.warning(f"⚠️ Could not check I2P readiness: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ I2P readiness check failed: {str(e)[:100]}")
            return False

    def check_site_via_notbob(self, hostname: str) -> Dict[str, Any]:
        """Synchronous check if site exists via notbob.i2p and extract address helper"""
        try:
            import requests
            jump_url = f"http://notbob.i2p/cgi-bin/jump.cgi?q={hostname}"
            response = requests.get(
                jump_url,
                proxies={'http': self.proxy_url, 'https': self.proxy_url},
                timeout=15,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
            )
            if response.status_code == 200:
                content = response.text
                
                # Check if site is explicitly marked as dead (be more specific)
                dead_indicators = [
                    'DEAD HOST',
                    'HOST IS DEAD', 
                    'Site is dead',
                    'dead host',
                    'host is dead',
                    'site is dead'
                ]
                
                # Only mark as dead if explicitly stated, not just containing "DEAD"
                for indicator in dead_indicators:
                    if indicator in content:
                        return {'status': 'dead', 'reason': f'Confirmed dead via notbob.i2p: {indicator}'}
                
                # Look for address helper with more comprehensive regex
                import re
                helper_patterns = [
                    r'i2paddresshelper=([^"&\s\']+)',
                    r'addresshelper=([^"&\s\']+)',
                    r'helper=([^"&\s\']+)'
                ]
                
                for pattern in helper_patterns:
                    helper_match = re.search(pattern, content, re.IGNORECASE)
                    if helper_match:
                        helper_key = helper_match.group(1)
                        helper_url = f"http://{hostname}/?i2paddresshelper={helper_key}"
                        logger.info(f"🎯 Found address helper for {hostname}: {helper_key[:20]}...")
                        return {
                            'status': 'alive',
                            'address_helper': helper_key,
                            'helper_url': helper_url
                        }
                
                # Check for redirect (alive site) - more specific patterns
                redirect_indicators = [
                    'You will be redirected',
                    'http-equiv="Refresh"',
                    'meta.*refresh',
                    'window.location',
                    'Redirecting to'
                ]
                
                for indicator in redirect_indicators:
                    if re.search(indicator, content, re.IGNORECASE):
                        # Try to extract redirect URL
                        redirect_patterns = [
                            r'url=([^"\'>\s]+)',
                            r'href="([^"]+)"',
                            r"href='([^']+)'"
                        ]
                        
                        for pattern in redirect_patterns:
                            redirect_match = re.search(pattern, content, re.IGNORECASE)
                            if redirect_match:
                                redirect_url = redirect_match.group(1)
                                if redirect_url.startswith('http'):
                                    return {
                                        'status': 'alive', 
                                        'method': 'redirect',
                                        'helper_url': redirect_url
                                    }
                        
                        return {'status': 'alive', 'method': 'redirect'}
                
                # Check if site appears to be accessible (has monitoring data)
                if any(indicator in content.lower() for indicator in [
                    'first seen', 'ping average', 'server:', 'encryption:', 
                    'address helper', 'b32 link', hostname.lower()
                ]):
                    return {'status': 'alive', 'method': 'monitored'}
                    
        except Exception as e:
            logger.debug(f"Notbob check failed for {hostname}: {str(e)[:50]}")
        
        # Default to unknown instead of dead
        return {'status': 'unknown'}



    def _crawl_i2p_site(self, site: Site, db_session) -> bool:
        """Main method to crawl I2P site and store results"""
        url = site.url
        parsed = urlparse(url)
        hostname = parsed.netloc
        
        try:
            # Quick network check using requests
            logger.info(f"🔍 Checking I2P network readiness...")
            if not self._check_i2p_network_sync():
                logger.error("I2P network not ready")
                return False
            
            # Step 1: Try to get address helper from notbob.i2p first
            logger.info(f"🔍 Getting address helper for {hostname} from notbob.i2p")
            site_check = self.check_site_via_notbob(hostname)
            
            # Only skip if explicitly marked as dead
            if site_check.get('status') == 'dead':
                logger.info(f"💀 Site {hostname} is marked as DEAD by notbob.i2p")
                site.last_error = site_check.get('reason', 'Site marked as dead')
                return False
            
            # Step 2: Try address helper if available
            if site_check.get('helper_url'):
                logger.info(f"🔗 Trying address helper URL: {site_check['helper_url']}")
                content = self._try_direct_access_sync(site_check['helper_url'])
                if content and len(content) > 1000 and not self._is_proxy_error_page(content):
                    page = self._create_page_record(url, content, 'address_helper', db_session, site)
                    if page:
                        logger.info(f"✅ Successfully crawled {hostname} via address helper - {len(content)} chars")
                        # Start deep crawling from this successful page
                        self._deep_crawl_i2p_site(site, db_session, content, url)
                        return True
                else:
                    logger.info(f"⚠️ Address helper returned insufficient content for {hostname}")
            
            # Step 3: Try direct access to original URL
            logger.info(f"🔄 Trying direct access to {url}")
            content = self._try_direct_access_sync(url)
            
            if content and len(content) > 1000 and not self._is_proxy_error_page(content):
                page = self._create_page_record(url, content, 'direct', db_session, site)
                if page:
                    logger.info(f"✅ Successfully crawled {url} directly - {len(content)} chars")
                    # Start deep crawling from this successful page
                    self._deep_crawl_i2p_site(site, db_session, content, url)
                    return True
            
            # Step 4: If site status is alive/unknown, try internal I2P proxies as fallback
            if site_check.get('status') in ['alive', 'unknown'] and self.use_internal_proxies and self.internal_proxies:
                logger.info(f"🔗 Site appears accessible, trying {len(self.internal_proxies)} internal I2P proxies for {hostname}")
                for i, proxy in enumerate(self.internal_proxies, 1):
                    try:
                        # Try to get the actual site content through the proxy
                        success = self._try_proxy_chain_access(hostname, proxy, i, db_session, site)
                        if success:
                            return True
                            
                    except Exception as e:
                        logger.debug(f"Proxy {proxy} failed for {hostname}: {e}")
                        continue
            
            # Failed to crawl
            if site_check.get('status') == 'dead':
                logger.info(f"❌ Site {hostname} confirmed dead by notbob.i2p")
                site.last_error = "Site confirmed dead by notbob.i2p"
            else:
                logger.warning(f"❌ Failed to crawl {hostname} after trying address helper, direct access, and {len(self.internal_proxies)} internal proxies")
                site.last_error = f"Site inaccessible via all methods (status: {site_check.get('status', 'unknown')})"
            return False
            
        except Exception as e:
            logger.error(f"Error in I2P crawl for {url}: {e}")
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
            # Only accept HTTP 200 - no more accepting 500 errors
            if response.status_code == 200:
                if len(response.text) > 2000:  # Ensure we have substantial content
                    logger.info(f"✅ HTTP 200 for {url} - {len(response.text)} chars")
                    return response.text
                else:
                    logger.info(f"⚠️ HTTP 200 for {url} - insufficient content ({len(response.text)} chars)")
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

    def _try_proxy_access_sync(self, proxy_url: str, proxy_name: str) -> Optional[str]:
        """Try to access URL via internal I2P proxy and return content"""
        try:
            import requests
            response = requests.get(
                proxy_url,
                proxies={'http': self.proxy_url, 'https': self.proxy_url},
                timeout=25,  # Longer timeout for proxy chains
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
            )
            
            if response.status_code == 200:
                content = response.text
                # Check if this is a real page or a proxy error/redirect page
                if len(content) > 2000 and not self._is_proxy_error_page(content):
                    logger.info(f"✅ HTTP 200 via {proxy_name} for {proxy_url} - {len(content)} chars")
                    return content
                else:
                    logger.info(f"⚠️ HTTP 200 via {proxy_name} but content appears to be error/redirect page ({len(content)} chars)")
                    return None
            else:
                logger.debug(f"⚠️ HTTP {response.status_code} via {proxy_name} for {proxy_url}")
                return None
                
        except requests.exceptions.Timeout:
            logger.debug(f"⏰ Timeout via {proxy_name} for {proxy_url}")
            return None
        except Exception as e:
            logger.debug(f"⚠️ Error via {proxy_name} for {proxy_url}: {str(e)[:50]}")
            return None

    def _try_proxy_chain_access(self, hostname: str, proxy: str, proxy_index: int, db_session, site: Site) -> bool:
        """Try to access I2P site through proxy chain and get actual content"""
        try:
            import requests
            # First, try to get address helper from the proxy
            jump_url = f"http://{proxy}/cgi-bin/jump.cgi?q={hostname}"
            logger.info(f"🔗 [{proxy_index}/{len(self.internal_proxies)}] Getting address helper from {proxy}")
            
            response = requests.get(
                jump_url,
                proxies={'http': self.proxy_url, 'https': self.proxy_url},
                timeout=20,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede/1.0)'}
            )
            
            if response.status_code == 200:
                jump_content = response.text
                
                # Look for address helper in the response
                import re
                helper_match = re.search(r'i2paddresshelper=([^"&\s]+)', jump_content)
                if helper_match:
                    # Found address helper, now try to access the actual site
                    helper_url = f"http://{hostname}/?i2paddresshelper={helper_match.group(1)}"
                    logger.info(f"🎯 Found address helper for {hostname}, trying: {helper_url}")
                    
                    actual_content = self._try_direct_access_sync(helper_url)
                    if actual_content and len(actual_content) > 2000 and not self._is_proxy_error_page(actual_content):
                        # Store the actual site content
                        page = self._create_page_record(site.url, actual_content, f'proxy_chain_{proxy}', db_session, site)
                        if page:
                            logger.info(f"✅ Successfully crawled {hostname} via {proxy} proxy chain - {len(actual_content)} chars")
                            # Start deep crawling from this successful page
                            self._deep_crawl_i2p_site(site, db_session, actual_content, site.url)
                            return True
                
                # Check if the jump page indicates the site is accessible via redirect
                if 'You will be redirected' in jump_content or 'http-equiv="Refresh"' in jump_content:
                    # Try to extract redirect URL
                    redirect_match = re.search(r'url=([^"\'>\s]+)', jump_content, re.IGNORECASE)
                    if redirect_match:
                        redirect_url = redirect_match.group(1)
                        logger.info(f"🔄 Found redirect for {hostname}: {redirect_url}")
                        
                        actual_content = self._try_direct_access_sync(redirect_url)
                        if actual_content and len(actual_content) > 2000 and not self._is_proxy_error_page(actual_content):
                            page = self._create_page_record(site.url, actual_content, f'proxy_redirect_{proxy}', db_session, site)
                            if page:
                                logger.info(f"✅ Successfully crawled {hostname} via {proxy} redirect - {len(actual_content)} chars")
                                # Start deep crawling from this successful page
                                self._deep_crawl_i2p_site(site, db_session, actual_content, site.url)
                                return True
                
                # If no address helper found, try direct proxy access
                direct_proxy_urls = [
                    f"http://{proxy}/{hostname}/",
                    f"http://{proxy}/jump/{hostname}",
                    f"http://{proxy}/proxy/{hostname}"
                ]
                
                for proxy_url in direct_proxy_urls:
                    logger.info(f"🔗 Trying direct proxy access: {proxy_url}")
                    content = self._try_proxy_access_sync(proxy_url, proxy)
                    if content and len(content) > 2000 and not self._is_proxy_error_page(content):
                        # Make sure this isn't just another proxy page
                        if not self._is_proxy_jump_page(content):
                            page = self._create_page_record(site.url, content, f'direct_proxy_{proxy}', db_session, site)
                            if page:
                                logger.info(f"✅ Successfully crawled {hostname} via direct proxy {proxy} - {len(content)} chars")
                                # Start deep crawling from this successful page
                                self._deep_crawl_i2p_site(site, db_session, content, site.url)
                                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Proxy chain access failed for {hostname} via {proxy}: {e}")
            return False

    def _is_proxy_jump_page(self, content: str) -> bool:
        """Check if content is a proxy jump/directory page rather than actual site content"""
        content_lower = content.lower()
        jump_indicators = [
            'jump service',
            'address helper',
            'i2paddresshelper',
            'you will be redirected',
            'jump.cgi',
            'site directory',
            'proxy jump',
            'eepsite',
            'i2p site list'
        ]
        
        # If content contains multiple jump indicators, it's likely a proxy page
        indicator_count = sum(1 for indicator in jump_indicators if indicator in content_lower)
        return indicator_count >= 2

    def _is_proxy_error_page(self, content: str) -> bool:
        """Check if content appears to be a proxy error page rather than real content"""
        content_lower = content.lower()
        error_indicators = [
            'error 404',
            'not found',
            'site not found',
            'destination not found',
            'tunnel not found',
            'proxy error',
            'connection failed',
            'unable to connect',
            'service unavailable',
            'internal server error',
            'bad gateway'
        ]
        
        # If content is very short, it's likely an error
        if len(content) < 1000:
            return True
            
        # Check for common error indicators
        for indicator in error_indicators:
            if indicator in content_lower:
                return True
                
        return False

    def wait_for_i2p_readiness_sync(self):
        """Synchronous version of wait_for_i2p_readiness - uses unified metrics API"""
        logger.info("🔄 Checking I2P network readiness via metrics API...")
        try:
            import requests
            
            # Check the unified metrics API for comprehensive I2P readiness
            response = requests.get(
                'http://noctipede-portal-service:8080/api/readiness',
                timeout=30,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Noctipede-I2P-Crawler/1.0)'}
            )
            
            if response.status_code == 200:
                readiness_data = response.json()
                if readiness_data.get('ready_for_crawling', False):
                    network_status = readiness_data.get('network_status', {})
                    i2p_status = network_status.get('i2p', {})
                    active_proxies = i2p_status.get('internal_proxies', {}).get('active_count', 0)
                    
                    logger.info(f"✅ I2P network fully ready! ({active_proxies}/5+ internal proxies active)")
                    return True
                else:
                    readiness_summary = readiness_data.get('readiness_details', {}).get('readiness_summary', 'Not ready')
                    logger.warning(f"⚠️ I2P not ready: {readiness_summary}")
                    return False
            elif response.status_code == 503:
                # Service unavailable - system not ready
                readiness_data = response.json()
                readiness_summary = readiness_data.get('readiness_details', {}).get('readiness_summary', 'System not ready')
                logger.warning(f"⚠️ System not ready for crawling: {readiness_summary}")
                return False
            else:
                logger.warning(f"⚠️ Could not check readiness: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ I2P readiness check failed: {e}")
            return False



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

    def _deep_crawl_i2p_site(self, site: Site, db_session, initial_content: str, base_url: str) -> None:
        """Perform deep crawling of I2P site starting from successful homepage"""
        try:
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin
            from core.utils import extract_domain
            import time
            
            logger.info(f"🔍 Starting deep crawl for {site.url}")
            
            # Parse the initial content to extract links
            soup = BeautifulSoup(initial_content, 'html.parser')
            links = self._extract_links(soup, base_url)
            
            if not links:
                logger.info(f"No links found on {base_url} for deep crawling")
                return
            
            # Start with extracted links at depth 1
            pages_to_crawl = [(link, 1, False) for link in links[:50]]  # Limit initial links
            crawled_pages = {base_url}  # Already crawled the homepage
            site_domain = extract_domain(base_url)
            
            logger.info(f"Found {len(links)} links, queuing {len(pages_to_crawl)} for deep crawling")
            
            while pages_to_crawl and len(crawled_pages) < 20:  # Limit to 20 pages per I2P site
                current_url, current_depth, is_offsite = pages_to_crawl.pop(0)
                
                if current_url in crawled_pages:
                    continue
                
                # Check depth limits
                if current_depth > self.settings.max_crawl_depth:
                    logger.debug(f"Skipping {current_url} - exceeds crawl depth limit ({current_depth} > {self.settings.max_crawl_depth})")
                    continue
                
                logger.info(f"Deep crawling page {len(crawled_pages)+1}: {current_url} (depth: {current_depth})")
                
                # Try to crawl this page using I2P methods
                content = self._try_direct_access_sync(current_url)
                
                if content and len(content) > 500 and not self._is_proxy_error_page(content):
                    # Create page record
                    page = self._create_page_record(current_url, content, f'deep_crawl_d{current_depth}', db_session, site)
                    if page:
                        crawled_pages.add(current_url)
                        logger.info(f"✅ Deep crawled: {current_url} - {len(content)} chars")
                        
                        # Extract more links if we haven't reached depth limit
                        if current_depth < self.settings.max_crawl_depth:
                            try:
                                page_soup = BeautifulSoup(content, 'html.parser')
                                page_links = self._extract_links(page_soup, current_url)
                                
                                # Add new links to queue (limit to 10 per page)
                                new_links = 0
                                for link in page_links[:10]:
                                    if link not in crawled_pages and not any(url == link for url, _, _ in pages_to_crawl):
                                        link_domain = extract_domain(link)
                                        link_is_offsite = (link_domain != site_domain)
                                        pages_to_crawl.append((link, current_depth + 1, link_is_offsite))
                                        new_links += 1
                                
                                if new_links > 0:
                                    logger.debug(f"Added {new_links} new links from {current_url}")
                                    
                            except Exception as e:
                                logger.debug(f"Error extracting links from {current_url}: {e}")
                else:
                    logger.debug(f"Failed to crawl or insufficient content: {current_url}")
                
                # Respect crawl delay
                time.sleep(self.settings.crawl_delay_seconds)
            
            logger.info(f"🎯 Deep crawling completed for {site.url}: {len(crawled_pages)} total pages")
            
        except Exception as e:
            logger.error(f"Error during deep crawling of {site.url}: {e}")

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
                success = self._crawl_i2p_site(site, db_session)
                
                # Update site record
                site.last_crawled = datetime.utcnow()
                if success:
                    site.crawl_count = (site.crawl_count or 0) + 1
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
                    site.error_count = (site.error_count or 0) + 1
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
