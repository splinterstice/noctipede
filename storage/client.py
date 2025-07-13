"""MinIO storage client."""

from typing import Optional, BinaryIO, Dict, Any
from minio import Minio
from minio.error import S3Error
from core import get_logger, get_file_hash
from config import get_settings

logger = get_logger(__name__)


class StorageClient:
    """MinIO storage client wrapper."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = Minio(
            self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=self.settings.minio_secure
        )
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the default bucket exists."""
        try:
            if not self.client.bucket_exists(self.settings.minio_bucket_name):
                self.client.make_bucket(self.settings.minio_bucket_name)
                logger.info(f"Created bucket: {self.settings.minio_bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise
    
    def upload_file(
        self,
        object_name: str,
        data: bytes,
        content_type: Optional[str] = None,
        bucket_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload file data to MinIO."""
        bucket = bucket_name or self.settings.minio_bucket_name
        
        try:
            # Calculate file hash
            file_hash = get_file_hash(data)
            
            # Upload to MinIO
            from io import BytesIO
            result = self.client.put_object(
                bucket,
                object_name,
                BytesIO(data),
                length=len(data),
                content_type=content_type
            )
            
            logger.info(f"Uploaded file to MinIO: {bucket}/{object_name}")
            
            return {
                'bucket': bucket,
                'object_name': object_name,
                'etag': result.etag,
                'file_hash': file_hash,
                'size': len(data)
            }
            
        except S3Error as e:
            logger.error(f"Error uploading file to MinIO: {e}")
            raise
    
    def download_file(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> bytes:
        """Download file data from MinIO."""
        bucket = bucket_name or self.settings.minio_bucket_name
        
        try:
            response = self.client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.debug(f"Downloaded file from MinIO: {bucket}/{object_name}")
            return data
            
        except S3Error as e:
            logger.error(f"Error downloading file from MinIO: {e}")
            raise
    
    def file_exists(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """Check if file exists in MinIO."""
        bucket = bucket_name or self.settings.minio_bucket_name
        
        try:
            self.client.stat_object(bucket, object_name)
            return True
        except S3Error:
            return False
    
    def delete_file(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """Delete file from MinIO."""
        bucket = bucket_name or self.settings.minio_bucket_name
        
        try:
            self.client.remove_object(bucket, object_name)
            logger.info(f"Deleted file from MinIO: {bucket}/{object_name}")
            return True
        except S3Error as e:
            logger.error(f"Error deleting file from MinIO: {e}")
            return False
    
    def get_file_info(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get file information from MinIO."""
        bucket = bucket_name or self.settings.minio_bucket_name
        
        try:
            stat = self.client.stat_object(bucket, object_name)
            return {
                'bucket': bucket,
                'object_name': object_name,
                'size': stat.size,
                'etag': stat.etag,
                'last_modified': stat.last_modified,
                'content_type': stat.content_type
            }
        except S3Error as e:
            logger.error(f"Error getting file info from MinIO: {e}")
            return None
    
    def list_files(
        self,
        prefix: Optional[str] = None,
        bucket_name: Optional[str] = None
    ) -> list:
        """List files in MinIO bucket."""
        bucket = bucket_name or self.settings.minio_bucket_name
        
        try:
            objects = self.client.list_objects(bucket, prefix=prefix)
            return [
                {
                    'object_name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified,
                    'etag': obj.etag
                }
                for obj in objects
            ]
        except S3Error as e:
            logger.error(f"Error listing files in MinIO: {e}")
            return []


# Global storage client instance
_storage_client: Optional[StorageClient] = None


def get_storage_client() -> StorageClient:
    """Get the global storage client instance."""
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client
