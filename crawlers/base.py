"""Base crawler class with common functionality."""

import time
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core import (
    get_logger, is_valid_url, extract_domain, get_network_type,
    is_supported_image_format, validate_and_process_image, is_image_safe_to_process
)
from config import get_settings
from database import get_db_session, Site, Page, MediaFile
from storage import StorageManager


class BaseCrawler(ABC):
    """Base class for all web crawlers."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(self.__class__.__name__)
        self.session = self._create_session()
        self.storage_manager = StorageManager()
        # Remove the shared db_session - we'll create one per operation instead
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set common headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        return session
    
    @abstractmethod
    def configure_proxy(self):
        """Configure proxy settings for the specific network."""
        pass
    
    def crawl_site(self, url: str) -> bool:
        """Crawl a single site."""
        # Create a new database session for this operation
        db_session = get_db_session()
        
        try:
            # Check if site was recently crawled
            if self._should_skip_site(url, db_session):
                self.logger.info(f"Skipping recently crawled site: {url}")
                return True
            
            # Get or create site record
            site = self._get_or_create_site(url, db_session)
            if not site:
                return False
            
            # Crawl the site
            success = self._crawl_site_pages(site, db_session)
            
            # Update site record
            site.last_crawled = datetime.utcnow()
            if success:
                site.crawl_count += 1
                site.error_count = 0
                site.last_error = None
            else:
                site.error_count += 1
            
            db_session.commit()
            return success
            
        except Exception as e:
            self.logger.error(f"Error crawling site {url}: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.close()
            return False
    
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
                # Determine network type and domain
                network_type = get_network_type(url)
                domain = extract_domain(url)
                
                site = Site(
                    url=url,
                    domain=domain,
                    network_type=network_type,
                    is_onion=network_type == 'tor',  # Backward compatibility
                    is_i2p=network_type == 'i2p',   # Backward compatibility
                    created_at=datetime.utcnow()
                )
                db_session.add(site)
                db_session.commit()
            
            return site
            
        except Exception as e:
            self.logger.error(f"Error getting/creating site {url}: {e}")
            return None
    
    def _crawl_site_pages(self, site: Site, db_session) -> bool:
        """Crawl pages for a site."""
        try:
            # Start with the main page
            pages_to_crawl = [site.url]
            crawled_pages = set()
            
            while pages_to_crawl and len(crawled_pages) < self.settings.max_links_per_page:
                current_url = pages_to_crawl.pop(0)
                
                if current_url in crawled_pages:
                    continue
                
                # Crawl the page
                page_data = self._crawl_page(current_url, site.id, db_session)
                if page_data:
                    crawled_pages.add(current_url)
                    
                    # Extract links for further crawling
                    if page_data.get('links'):
                        for link in page_data['links'][:10]:  # Limit links per page
                            if link not in crawled_pages and link not in pages_to_crawl:
                                pages_to_crawl.append(link)
                
                # Respect crawl delay
                time.sleep(self.settings.crawl_delay_seconds)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error crawling site pages for {site.url}: {e}")
            return False
    
    def _crawl_page(self, url: str, site_id: int, db_session) -> Optional[Dict[str, Any]]:
        """Crawl a single page."""
        try:
            start_time = time.time()
            
            # Make request
            response = self.session.get(url, timeout=30)
            response_time = time.time() - start_time
            
            if response.status_code != 200:
                self.logger.warning(f"Non-200 status for {url}: {response.status_code}")
                return None
            
            # Parse content
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string.strip() if soup.title else None
            content = soup.get_text(strip=True)
            
            # Calculate content hash
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Check if page already exists with same content
            existing_page = db_session.query(Page).filter_by(
                url=url, content_hash=content_hash
            ).first()
            
            if existing_page:
                self.logger.debug(f"Page content unchanged: {url}")
                return {'links': self._extract_links(soup, url)}
            
            # Store page content in MinIO
            storage_result = self.storage_manager.store_page_content(
                url=url,
                content=content,
                content_type=response.headers.get('content-type', 'text/html')
            )
            
            # Create page record
            page = Page(
                site_id=site_id,
                url=url,
                title=title,
                content=content[:10000],  # Store first 10k chars in DB
                content_hash=content_hash,
                status_code=response.status_code,
                crawled_at=datetime.utcnow(),
                content_type=response.headers.get('content-type'),
                content_length=len(content),
                response_time=response_time
            )
            
            db_session.add(page)
            
            # Update site page count
            site = db_session.query(Site).filter_by(id=site_id).first()
            if site:
                site.page_count = (site.page_count or 0) + 1
            
            db_session.commit()
            
            # Extract and store media files
            media_files = self._extract_media_files(soup, url, page.id, db_session)
            
            # Extract links
            links = self._extract_links(soup, url)
            
            self.logger.info(f"Successfully crawled page: {url}")
            
            return {
                'page': page,
                'media_files': media_files,
                'links': links,
                'storage_result': storage_result
            }
            
        except Exception as e:
            self.logger.error(f"Error crawling page {url}: {e}")
            return None
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract links from page."""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            if is_valid_url(full_url) and self._is_same_network(full_url, base_url):
                links.append(full_url)
        
        return list(set(links))  # Remove duplicates
    
    def _extract_media_files(self, soup: BeautifulSoup, base_url: str, page_id: int, db_session) -> List[MediaFile]:
        """Extract and store media files from page."""
        media_files = []
        
        # Extract images
        for img in soup.find_all('img', src=True):
            src = img['src']
            full_url = urljoin(base_url, src)
            
            if is_valid_url(full_url):
                media_file = self._download_and_store_media(full_url, 'image', page_id, db_session)
                if media_file:
                    media_files.append(media_file)
        
        # Extract other media types (videos, audio, etc.)
        media_tags = [
            ('video', 'src'),
            ('audio', 'src'),
            ('source', 'src'),
            ('embed', 'src'),
            ('object', 'data')
        ]
        
        for tag, attr in media_tags:
            for element in soup.find_all(tag, **{attr: True}):
                src = element[attr]
                full_url = urljoin(base_url, src)
                
                if is_valid_url(full_url):
                    media_file = self._download_and_store_media(full_url, tag, page_id, db_session)
                    if media_file:
                        media_files.append(media_file)
        
        return media_files
    
    def _download_and_store_media(self, url: str, file_type: str, page_id: int, db_session) -> Optional[MediaFile]:
        """Download and store a media file with enhanced WebP and dark web format support."""
        try:
            # Check if media file already exists
            existing_media = db_session.query(MediaFile).filter_by(url=url).first()
            if existing_media:
                return existing_media
            
            # Download the file
            response = self.session.get(url, timeout=30, stream=True)
            if response.status_code != 200:
                return None
            
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.settings.max_image_size_mb * 1024 * 1024:
                self.logger.warning(f"File too large, skipping: {url}")
                return None
            
            # Read content
            content = response.content
            if len(content) > self.settings.max_image_size_mb * 1024 * 1024:
                self.logger.warning(f"Downloaded file too large, skipping: {url}")
                return None
            
            # For images, perform additional validation
            if file_type == 'image':
                filename = urlparse(url).path.split('/')[-1] or 'unnamed'
                content_type = response.headers.get('content-type', '')
                
                # Check if format is supported
                if not is_supported_image_format(filename, content_type):
                    self.logger.debug(f"Unsupported image format, skipping: {url}")
                    return None
                
                # Validate image safety and integrity
                if not is_image_safe_to_process(content):
                    self.logger.warning(f"Image failed safety check, skipping: {url}")
                    return None
                
                # Process and validate image
                image_info = validate_and_process_image(content)
                if not image_info:
                    self.logger.warning(f"Image validation failed, skipping: {url}")
                    return None
                
                self.logger.info(f"Processing {image_info['format']} image: {image_info['width']}x{image_info['height']} from {url}")
            
            # Store in MinIO
            storage_result = self.storage_manager.store_media_file(
                url=url,
                content=content,
                content_type=response.headers.get('content-type')
            )
            
            # Create media file record
            media_file = MediaFile(
                page_id=page_id,
                url=url,
                filename=urlparse(url).path.split('/')[-1] or 'unnamed',
                file_type=file_type,
                mime_type=response.headers.get('content-type'),
                file_size=len(content),
                file_hash=storage_result['file_hash'],
                downloaded_at=datetime.utcnow(),
                minio_bucket=storage_result['bucket'],
                minio_object_name=storage_result['object_name']
            )
            
            db_session.add(media_file)
            db_session.commit()
            
            self.logger.debug(f"Downloaded and stored media: {url}")
            return media_file
            
        except Exception as e:
            self.logger.error(f"Error downloading media {url}: {e}")
            return None
    
    def _is_same_network(self, url1: str, url2: str) -> bool:
        """Check if two URLs are on the same network type."""
        return get_network_type(url1) == get_network_type(url2)
    
    def close(self):
        """Clean up resources."""
        if self.session:
            self.session.close()
        # db_session is now created per-operation, so no cleanup needed here
