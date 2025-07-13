"""Core utilities and shared functionality."""

from .logging import setup_logging, get_logger
from .utils import (
    get_file_hash, is_valid_url, sanitize_filename, extract_domain, 
    is_onion_url, is_i2p_url, get_network_type
)
from .image_utils import (
    is_supported_image_format, 
    validate_and_process_image, 
    convert_to_standard_format,
    is_image_safe_to_process,
    extract_image_metadata
)

__all__ = [
    'setup_logging', 'get_logger', 'get_file_hash', 'is_valid_url', 'sanitize_filename',
    'extract_domain', 'is_onion_url', 'is_i2p_url', 'get_network_type',
    'is_supported_image_format', 'validate_and_process_image', 'convert_to_standard_format',
    'is_image_safe_to_process', 'extract_image_metadata'
]
