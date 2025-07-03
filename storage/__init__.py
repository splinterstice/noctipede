"""MinIO object storage integration."""

from .client import StorageClient, get_storage_client
from .manager import StorageManager

__all__ = ['StorageClient', 'get_storage_client', 'StorageManager']
