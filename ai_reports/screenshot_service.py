"""Screenshot service for capturing website screenshots."""

import os
import asyncio
import tempfile
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import hashlib

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from core import get_logger
from config import get_settings
from database import get_db_session
from storage import get_storage_manager
from sqlalchemy import text

logger = get_logger(__name__)


class ScreenshotService:
    """Service for capturing website screenshots with various configurations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.storage_manager = get_storage_manager()
        
        # Configuration
        self.screenshot_enabled = getattr(self.settings, 'screenshot_service_enabled', True)
        self.storage_path = getattr(self.settings, 'screenshot_storage_path', '/app/screenshots')
        self.viewport_width = getattr(self.settings, 'screenshot_viewport_width', 1920)
        self.viewport_height = getattr(self.settings, 'screenshot_viewport_height', 1080)
        self.page_load_timeout = getattr(self.settings, 'screenshot_page_load_timeout', 30)
        self.max_concurrent = getattr(self.settings, 'screenshot_max_concurrent', 5)
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        self.driver_pool = []
        self.setup_driver_pool()
    
    def setup_driver_pool(self) -> None:
        """Setup pool of Chrome drivers for concurrent screenshot capture."""
        try:
            if not self.screenshot_enabled:
                logger.info("Screenshot service disabled")
                return
            
            for i in range(self.max_concurrent):
                driver = self._create_driver()
                if driver:
                    self.driver_pool.append(driver)
            
            logger.info(f"Screenshot service initialized with {len(self.driver_pool)} drivers")
            
        except Exception as e:
            logger.error(f"Failed to setup driver pool: {e}")
    
    def capture_screenshot(self, url: str, site_id: int, page_id: Optional[int] = None, 
                          dataset_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Capture screenshot of a single website.
        
        Args:
            url: Website URL to capture
            site_id: Site ID from database
            page_id: Optional page ID
            dataset_id: Optional dataset ID for organization
            
        Returns:
            Screenshot information dictionary or None if failed
        """
        try:
            if not self.screenshot_enabled or not self.driver_pool:
                logger.warning("Screenshot service not available")
                return None
            
            # Get available driver
            driver = self._get_available_driver()
            if not driver:
                logger.warning("No available drivers for screenshot capture")
                return None
            
            try:
                # Navigate to URL
                driver.get(url)
                
                # Wait for page to load
                WebDriverWait(driver, self.page_load_timeout).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Additional wait for dynamic content
                time.sleep(2)
                
                # Generate filename
                filename = self._generate_filename(url, site_id)
                screenshot_path = os.path.join(self.storage_path, filename)
                
                # Capture screenshot
                success = driver.save_screenshot(screenshot_path)
                
                if success and os.path.exists(screenshot_path):
                    # Get file size
                    file_size = os.path.getsize(screenshot_path)
                    
                    # Upload to MinIO if available
                    minio_path = None
                    if self.storage_manager:
                        minio_path = self._upload_to_minio(screenshot_path, filename)
                    
                    # Generate thumbnail
                    thumbnail_path = self._generate_thumbnail(screenshot_path)
                    
                    # Store in database
                    screenshot_info = {
                        'site_id': site_id,
                        'page_id': page_id,
                        'dataset_id': dataset_id,
                        'screenshot_url': minio_path or screenshot_path,
                        'thumbnail_url': thumbnail_path,
                        'capture_timestamp': datetime.now(),
                        'viewport_width': self.viewport_width,
                        'viewport_height': self.viewport_height,
                        'file_size': file_size,
                        'storage_path': screenshot_path
                    }
                    
                    screenshot_id = self._store_screenshot_info(screenshot_info)
                    screenshot_info['id'] = screenshot_id
                    
                    logger.info(f"Screenshot captured for {url}")
                    return screenshot_info
                else:
                    logger.error(f"Failed to save screenshot for {url}")
                    return None
                    
            finally:
                # Return driver to pool
                self._return_driver(driver)
                
        except Exception as e:
            logger.error(f"Failed to capture screenshot for {url}: {e}")
            return None
    
    def capture_batch(self, urls_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch capture screenshots for multiple URLs.
        
        Args:
            urls_info: List of dictionaries with url, site_id, page_id, dataset_id
            
        Returns:
            List of screenshot information dictionaries
        """
        try:
            results = []
            
            # Process in batches based on available drivers
            batch_size = min(len(self.driver_pool), self.max_concurrent)
            
            for i in range(0, len(urls_info), batch_size):
                batch = urls_info[i:i + batch_size]
                
                # Execute batch synchronously
                batch_results = []
                for url_info in batch:
                    try:
                        result = self.capture_screenshot(
                            url_info['url'],
                            url_info['site_id'],
                            url_info.get('page_id'),
                            url_info.get('dataset_id')
                        )
                        batch_results.append(result)
                    except Exception as e:
                        logger.error(f"Batch screenshot error: {e}")
                        batch_results.append(None)
                
                results.extend(batch_results)
                
                # Small delay between batches
                time.sleep(1)
            
            successful_captures = len([r for r in results if r is not None])
            logger.info(f"Batch screenshot capture completed: {successful_captures}/{len(urls_info)} successful")
            
            return results
            
        except Exception as e:
            logger.error(f"Batch screenshot capture failed: {e}")
            return [None] * len(urls_info)
    
    def get_site_screenshots(self, site_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get screenshots for a specific site."""
        try:
            with get_db_session() as session:
                query = text("""
                    SELECT * FROM site_screenshots
                    WHERE site_id = :site_id
                    ORDER BY capture_timestamp DESC
                    LIMIT :limit
                """)
                
                result = session.execute(query, {
                    'site_id': site_id,
                    'limit': limit
                })
                
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get screenshots for site {site_id}: {e}")
            return []
    
    def get_dataset_screenshots(self, dataset_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get screenshots for a specific dataset."""
        try:
            with get_db_session() as session:
                query = text("""
                    SELECT ss.*, s.url, s.domain
                    FROM site_screenshots ss
                    JOIN sites s ON ss.site_id = s.id
                    WHERE ss.dataset_id = :dataset_id
                    ORDER BY ss.capture_timestamp DESC
                    LIMIT :limit
                """)
                
                result = session.execute(query, {
                    'dataset_id': dataset_id,
                    'limit': limit
                })
                
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get screenshots for dataset {dataset_id}: {e}")
            return []
    
    def cleanup_old_screenshots(self, days_old: int = 30) -> int:
        """Cleanup screenshots older than specified days."""
        try:
            with get_db_session() as session:
                # Get old screenshots
                query = text("""
                    SELECT * FROM site_screenshots
                    WHERE capture_timestamp < DATE_SUB(NOW(), INTERVAL :days DAY)
                """)
                
                old_screenshots = session.execute(query, {'days': days_old}).fetchall()
                
                cleaned_count = 0
                for screenshot in old_screenshots:
                    # Delete files
                    if screenshot.storage_path and os.path.exists(screenshot.storage_path):
                        os.unlink(screenshot.storage_path)
                    
                    if screenshot.thumbnail_url and os.path.exists(screenshot.thumbnail_url):
                        os.unlink(screenshot.thumbnail_url)
                    
                    # Delete from MinIO if applicable
                    if self.storage_manager and screenshot.screenshot_url:
                        try:
                            # Extract object name from URL
                            object_name = screenshot.screenshot_url.split('/')[-1]
                            self.storage_manager.delete_object(object_name)
                        except Exception as e:
                            logger.warning(f"Failed to delete from MinIO: {e}")
                    
                    cleaned_count += 1
                
                # Delete database records
                delete_query = text("""
                    DELETE FROM site_screenshots
                    WHERE capture_timestamp < DATE_SUB(NOW(), INTERVAL :days DAY)
                """)
                
                session.execute(delete_query, {'days': days_old})
                session.commit()
                
                logger.info(f"Cleaned up {cleaned_count} old screenshots")
                return cleaned_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old screenshots: {e}")
            return 0
    
    def _create_driver(self) -> Optional[webdriver.Chrome]:
        """Create a new Chrome driver instance."""
        try:
            options = Options()
            
            # Headless mode
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # Faster loading
            options.add_argument('--disable-javascript')  # Optional: disable JS for faster loading
            
            # Set viewport size
            options.add_argument(f'--window-size={self.viewport_width},{self.viewport_height}')
            
            # User agent
            options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Proxy settings for Tor/I2P if needed
            tor_proxy = getattr(self.settings, 'tor_proxy_host', None)
            if tor_proxy:
                proxy_port = getattr(self.settings, 'tor_proxy_port', 9050)
                options.add_argument(f'--proxy-server=socks5://{tor_proxy}:{proxy_port}')
            
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.page_load_timeout)
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            return None
    
    def _get_available_driver(self) -> Optional[webdriver.Chrome]:
        """Get an available driver from the pool."""
        if self.driver_pool:
            return self.driver_pool.pop(0)
        return None
    
    def _return_driver(self, driver: webdriver.Chrome) -> None:
        """Return driver to the pool."""
        try:
            # Clear cookies and cache
            driver.delete_all_cookies()
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            
            self.driver_pool.append(driver)
            
        except Exception as e:
            logger.warning(f"Failed to return driver to pool: {e}")
            # Create new driver to replace the problematic one
            new_driver = self._create_driver()
            if new_driver:
                self.driver_pool.append(new_driver)
    
    def _generate_filename(self, url: str, site_id: int) -> str:
        """Generate unique filename for screenshot."""
        # Create hash from URL for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"screenshot_{site_id}_{url_hash}_{timestamp}.png"
    
    def _upload_to_minio(self, local_path: str, filename: str) -> Optional[str]:
        """Upload screenshot to MinIO storage."""
        try:
            if not self.storage_manager:
                return None
            
            object_name = f"screenshots/{filename}"
            
            # Upload file
            self.storage_manager.upload_file(local_path, object_name)
            
            # Return MinIO URL
            bucket_name = getattr(self.settings, 'minio_bucket_name', 'noctipede-data')
            minio_endpoint = getattr(self.settings, 'minio_endpoint', 'minio:9000')
            
            return f"http://{minio_endpoint}/{bucket_name}/{object_name}"
            
        except Exception as e:
            logger.error(f"Failed to upload screenshot to MinIO: {e}")
            return None
    
    def _generate_thumbnail(self, screenshot_path: str) -> Optional[str]:
        """Generate thumbnail from screenshot."""
        try:
            from PIL import Image
            
            # Open screenshot
            with Image.open(screenshot_path) as img:
                # Create thumbnail
                thumbnail_size = (300, 200)
                img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                thumbnail_path = screenshot_path.replace('.png', '_thumb.png')
                img.save(thumbnail_path, 'PNG')
                
                return thumbnail_path
                
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return None
    
    def _store_screenshot_info(self, screenshot_info: Dict[str, Any]) -> Optional[int]:
        """Store screenshot information in database."""
        try:
            with get_db_session() as session:
                query = text("""
                    INSERT INTO site_screenshots (
                        site_id, page_id, dataset_id, screenshot_url, thumbnail_url,
                        capture_timestamp, viewport_width, viewport_height, file_size, storage_path
                    ) VALUES (
                        :site_id, :page_id, :dataset_id, :screenshot_url, :thumbnail_url,
                        :capture_timestamp, :viewport_width, :viewport_height, :file_size, :storage_path
                    )
                """)
                
                result = session.execute(query, screenshot_info)
                session.commit()
                
                return result.lastrowid
                
        except Exception as e:
            logger.error(f"Failed to store screenshot info: {e}")
            return None
    
    def __del__(self):
        """Cleanup drivers when service is destroyed."""
        try:
            for driver in self.driver_pool:
                driver.quit()
        except Exception:
            pass
