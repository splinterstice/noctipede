"""Storage management utilities."""

import os
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from core import get_logger, sanitize_filename, get_file_hash
from .client import get_storage_client

logger = get_logger(__name__)


class StorageManager:
    """High-level storage management."""
    
    def __init__(self):
        self.client = get_storage_client()
    
    def store_media_file(
        self,
        url: str,
        content: bytes,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store a media file with organized naming."""
        # Generate object name based on URL and content hash
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path) or 'unnamed_file'
        filename = sanitize_filename(filename)
        
        # Create hash-based directory structure
        content_hash = get_file_hash(content)
        hash_prefix = content_hash[:2]  # First 2 chars for directory
        
        object_name = f"media/{hash_prefix}/{content_hash}_{filename}"
        
        # Check if file already exists
        if self.client.file_exists(object_name):
            logger.info(f"File already exists in storage: {object_name}")
            return {
                'bucket': self.client.settings.minio_bucket_name,
                'object_name': object_name,
                'file_hash': content_hash,
                'size': len(content),
                'already_exists': True
            }
        
        # Upload the file
        result = self.client.upload_file(
            object_name=object_name,
            data=content,
            content_type=content_type
        )
        
        result['already_exists'] = False
        return result
    
    def store_page_content(
        self,
        url: str,
        content: str,
        content_type: str = 'text/html'
    ) -> Dict[str, Any]:
        """Store page content."""
        content_bytes = content.encode('utf-8')
        content_hash = get_file_hash(content_bytes)
        
        # Create object name for page content
        parsed_url = urlparse(url)
        domain = parsed_url.netloc or 'unknown'
        domain = sanitize_filename(domain)
        
        hash_prefix = content_hash[:2]
        object_name = f"pages/{domain}/{hash_prefix}/{content_hash}.html"
        
        # Check if content already exists
        if self.client.file_exists(object_name):
            logger.debug(f"Page content already exists in storage: {object_name}")
            return {
                'bucket': self.client.settings.minio_bucket_name,
                'object_name': object_name,
                'file_hash': content_hash,
                'size': len(content_bytes),
                'already_exists': True
            }
        
        # Upload the content
        result = self.client.upload_file(
            object_name=object_name,
            data=content_bytes,
            content_type=content_type
        )
        
        result['already_exists'] = False
        return result
    
    def get_media_file(self, object_name: str) -> Optional[bytes]:
        """Retrieve a media file from storage."""
        try:
            return self.client.download_file(object_name)
        except Exception as e:
            logger.error(f"Error retrieving media file {object_name}: {e}")
            return None
    
    def get_page_content(self, object_name: str) -> Optional[str]:
        """Retrieve page content from storage."""
        try:
            content_bytes = self.client.download_file(object_name)
            return content_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Error retrieving page content {object_name}: {e}")
            return None
    
    def cleanup_old_files(self, days_old: int = 30) -> int:
        """Clean up files older than specified days."""
        # This would require implementing date-based cleanup logic
        # For now, just return 0
        logger.info(f"Cleanup of files older than {days_old} days not yet implemented")
        return 0
