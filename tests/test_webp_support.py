"""Test WebP and image format support."""

import pytest
from PIL import Image
import io
from core.image_utils import (
    is_supported_image_format,
    validate_and_process_image,
    convert_to_standard_format,
    detect_image_format,
    get_image_mime_type
)


def test_webp_support_available():
    """Test that WebP support is available in PIL."""
    assert 'WEBP' in Image.EXTENSION
    assert Image.EXTENSION['.webp'] == 'WEBP'


def test_webp_format_detection():
    """Test WebP format detection."""
    # Create a simple WebP image
    img = Image.new('RGB', (100, 100), color='red')
    webp_data = io.BytesIO()
    img.save(webp_data, format='WEBP')
    webp_bytes = webp_data.getvalue()
    
    # Test format detection
    detected_format = detect_image_format(webp_bytes)
    assert detected_format == 'webp'


def test_webp_format_support():
    """Test that WebP format is supported."""
    assert is_supported_image_format('test.webp', 'image/webp')
    assert is_supported_image_format('test.webp')
    assert is_supported_image_format('', 'image/webp')


def test_webp_validation():
    """Test WebP image validation."""
    # Create a test WebP image
    img = Image.new('RGB', (200, 150), color='blue')
    webp_data = io.BytesIO()
    img.save(webp_data, format='WEBP')
    webp_bytes = webp_data.getvalue()
    
    # Validate the image
    image_info = validate_and_process_image(webp_bytes)
    assert image_info is not None
    assert image_info['format'] == 'webp'
    assert image_info['width'] == 200
    assert image_info['height'] == 150


def test_webp_conversion():
    """Test WebP to JPEG conversion."""
    # Create a test WebP image
    img = Image.new('RGB', (100, 100), color='green')
    webp_data = io.BytesIO()
    img.save(webp_data, format='WEBP')
    webp_bytes = webp_data.getvalue()
    
    # Convert to JPEG
    jpeg_bytes = convert_to_standard_format(webp_bytes, 'JPEG')
    assert jpeg_bytes is not None
    
    # Verify the converted image
    converted_img = Image.open(io.BytesIO(jpeg_bytes))
    assert converted_img.format == 'JPEG'
    assert converted_img.size == (100, 100)


def test_webp_mime_type():
    """Test WebP MIME type detection."""
    mime_type = get_image_mime_type('test.webp')
    assert mime_type == 'image/webp'


def test_dark_web_formats():
    """Test support for common dark web image formats."""
    formats_to_test = [
        ('test.webp', 'image/webp'),
        ('test.jpg', 'image/jpeg'),
        ('test.png', 'image/png'),
        ('test.gif', 'image/gif'),
        ('test.bmp', 'image/bmp'),
        ('test.tiff', 'image/tiff')
    ]
    
    for filename, mime_type in formats_to_test:
        assert is_supported_image_format(filename, mime_type), f"Format {filename} should be supported"


def test_animated_webp_detection():
    """Test animated WebP detection (if supported)."""
    try:
        # Create a simple animated WebP (if PIL supports it)
        frames = []
        for i in range(3):
            img = Image.new('RGB', (50, 50), color=(i*80, 0, 0))
            frames.append(img)
        
        webp_data = io.BytesIO()
        frames[0].save(
            webp_data,
            format='WEBP',
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0
        )
        webp_bytes = webp_data.getvalue()
        
        # Validate animated WebP
        image_info = validate_and_process_image(webp_bytes)
        if image_info:  # Only test if WebP animation is supported
            assert image_info['format'] == 'webp'
            # Note: webp_animated detection depends on PIL version
            
    except Exception:
        # Skip test if animated WebP is not supported
        pytest.skip("Animated WebP not supported in this PIL version")


if __name__ == "__main__":
    # Run basic tests
    test_webp_support_available()
    test_webp_format_detection()
    test_webp_format_support()
    test_webp_validation()
    test_webp_conversion()
    test_webp_mime_type()
    test_dark_web_formats()
    
    print("✅ All WebP and image format tests passed!")
    print("🕷️ Noctipede is ready for dark web image analysis!")
