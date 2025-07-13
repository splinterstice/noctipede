"""Image processing utilities with WebP and dark web format support."""

import io
import mimetypes
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageFile
from core import get_logger
from config import get_settings

logger = get_logger(__name__)

# Enable loading of truncated images (common on dark web)
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Common MIME types for dark web images
DARK_WEB_IMAGE_MIMES = {
    'image/webp': 'webp',
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg', 
    'image/png': 'png',
    'image/gif': 'gif',
    'image/bmp': 'bmp',
    'image/tiff': 'tiff',
    'image/tif': 'tiff',
    'image/svg+xml': 'svg',
    'image/x-icon': 'ico',
    'image/vnd.microsoft.icon': 'ico'
}

# File extensions to MIME type mapping
EXTENSION_TO_MIME = {
    '.webp': 'image/webp',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.bmp': 'image/bmp',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
}


def is_supported_image_format(filename: str, content_type: Optional[str] = None) -> bool:
    """Check if image format is supported for processing."""
    settings = get_settings()
    supported_formats = settings.supported_image_formats_list
    
    # Check by content type first
    if content_type and content_type in DARK_WEB_IMAGE_MIMES:
        format_ext = DARK_WEB_IMAGE_MIMES[content_type]
        return format_ext in supported_formats
    
    # Check by file extension
    if filename:
        ext = get_file_extension(filename).lower()
        if ext in EXTENSION_TO_MIME:
            format_ext = DARK_WEB_IMAGE_MIMES.get(EXTENSION_TO_MIME[ext], '')
            return format_ext in supported_formats
    
    return False


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    if '.' in filename:
        return '.' + filename.split('.')[-1].lower()
    return ''


def detect_image_format(image_data: bytes) -> Optional[str]:
    """Detect image format from binary data."""
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            return img.format.lower() if img.format else None
    except Exception as e:
        logger.debug(f"Could not detect image format: {e}")
        return None


def validate_and_process_image(image_data: bytes, max_size_mb: int = None) -> Optional[Dict[str, Any]]:
    """Validate and process image data, with special handling for WebP and dark web formats."""
    settings = get_settings()
    max_size = max_size_mb or settings.max_image_size_mb
    
    try:
        # Check file size
        if len(image_data) > max_size * 1024 * 1024:
            logger.warning(f"Image too large: {len(image_data)} bytes")
            return None
        
        # Try to open and validate the image
        with Image.open(io.BytesIO(image_data)) as img:
            # Get image info
            image_info = {
                'format': img.format.lower() if img.format else 'unknown',
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height,
                'has_transparency': img.mode in ('RGBA', 'LA', 'P'),
                'file_size': len(image_data)
            }
            
            # Special handling for WebP (very common on dark web)
            if img.format == 'WEBP':
                image_info['webp_lossless'] = 'lossless' in img.info
                image_info['webp_animated'] = getattr(img, 'is_animated', False)
            
            # Special handling for GIF animations (also common)
            elif img.format == 'GIF':
                image_info['gif_animated'] = getattr(img, 'is_animated', False)
                image_info['gif_frames'] = getattr(img, 'n_frames', 1)
            
            # Check if format is supported
            if image_info['format'] not in settings.supported_image_formats_list:
                logger.warning(f"Unsupported image format: {image_info['format']}")
                return None
            
            logger.debug(f"Processed {image_info['format']} image: {image_info['width']}x{image_info['height']}")
            return image_info
            
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return None


def convert_to_standard_format(image_data: bytes, target_format: str = 'JPEG') -> Optional[bytes]:
    """Convert image to a standard format for analysis."""
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            # Convert RGBA to RGB for JPEG
            if target_format.upper() == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Save to bytes
            output = io.BytesIO()
            img.save(output, format=target_format, quality=85, optimize=True)
            return output.getvalue()
            
    except Exception as e:
        logger.error(f"Error converting image to {target_format}: {e}")
        return None


def get_image_mime_type(filename: str, image_data: bytes = None) -> str:
    """Get MIME type for image file."""
    # Try to detect from data first
    if image_data:
        detected_format = detect_image_format(image_data)
        if detected_format:
            for mime, fmt in DARK_WEB_IMAGE_MIMES.items():
                if fmt == detected_format:
                    return mime
    
    # Fall back to filename extension
    ext = get_file_extension(filename)
    return EXTENSION_TO_MIME.get(ext, 'application/octet-stream')


def is_image_safe_to_process(image_data: bytes) -> bool:
    """Check if image is safe to process (not corrupted, not malicious)."""
    try:
        # Basic validation
        if len(image_data) < 10:  # Too small to be a valid image
            return False
        
        # Try to open and verify
        with Image.open(io.BytesIO(image_data)) as img:
            # Verify image can be loaded
            img.verify()
            
            # Check for reasonable dimensions
            if img.width > 10000 or img.height > 10000:
                logger.warning("Image dimensions too large, potentially malicious")
                return False
            
            # Check for reasonable file size vs dimensions ratio
            expected_size = img.width * img.height * 4  # Rough estimate
            if len(image_data) > expected_size * 2:  # Allow 2x overhead
                logger.warning("Image file size suspicious for dimensions")
                return False
            
            return True
            
    except Exception as e:
        logger.warning(f"Image failed safety check: {e}")
        return False


def extract_image_metadata(image_data: bytes) -> Dict[str, Any]:
    """Extract metadata from image, useful for forensic analysis."""
    metadata = {}
    
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            # Basic info
            metadata['format'] = img.format
            metadata['mode'] = img.mode
            metadata['size'] = img.size
            
            # EXIF data (if available)
            if hasattr(img, '_getexif') and img._getexif():
                metadata['has_exif'] = True
                # Don't extract full EXIF for privacy, just note presence
            else:
                metadata['has_exif'] = False
            
            # Other metadata
            if hasattr(img, 'info') and img.info:
                # Filter out potentially sensitive info
                safe_info = {}
                for key, value in img.info.items():
                    if key.lower() not in ['exif', 'gps', 'location']:
                        safe_info[key] = str(value)[:100]  # Limit length
                metadata['info'] = safe_info
            
    except Exception as e:
        logger.debug(f"Could not extract image metadata: {e}")
    
    return metadata
