"""MinIO object storage integration."""

from .client import StorageClient, get_storage_client
from .manager import StorageManager

# Global storage manager instance
_storage_manager = None

def get_storage_manager():
    """Get or create the global storage manager instance."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager

__all__ = ['StorageClient', 'get_storage_client', 'StorageManager', 'get_storage_manager']
