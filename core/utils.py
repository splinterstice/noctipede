"""Core utility functions."""

import hashlib
import re
from urllib.parse import urlparse
from typing import Optional


def get_file_hash(content: bytes, algorithm: str = 'sha256') -> str:
    """Generate hash for file content."""
    hasher = hashlib.new(algorithm)
    hasher.update(content)
    return hasher.hexdigest()


def is_valid_url(url: str) -> bool:
    """Check if a URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename for safe storage."""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
    
    # Limit length
    if len(sanitized) > max_length:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        max_name_length = max_length - len(ext) - 1 if ext else max_length
        sanitized = name[:max_name_length] + ('.' + ext if ext else '')
    
    return sanitized or 'unnamed_file'


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


def is_onion_url(url: str) -> bool:
    """Check if URL is a Tor .onion address."""
    return '.onion' in url.lower()


def is_i2p_url(url: str) -> bool:
    """Check if URL is an I2P .i2p address."""
    return '.i2p' in url.lower()


def get_network_type(url: str) -> str:
    """Determine the network type of a URL."""
    if is_onion_url(url):
        return 'tor'
    elif is_i2p_url(url):
        return 'i2p'
    else:
        return 'clearnet'
