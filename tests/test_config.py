"""Test configuration management."""

import pytest
from config import Settings, get_settings


def test_settings_creation():
    """Test that settings can be created."""
    # This will use default values since we don't have env vars set
    settings = Settings(
        mariadb_password="test_password",
        minio_access_key="test_access_key",
        minio_secret_key="test_secret_key",
        ollama_endpoint="http://localhost:11434/api/generate"
    )
    
    assert settings.mariadb_host == "mariadb"
    assert settings.mariadb_port == 3306
    assert settings.mariadb_password == "test_password"
    assert settings.minio_access_key == "test_access_key"


def test_database_url():
    """Test database URL generation."""
    settings = Settings(
        mariadb_password="test_password",
        minio_access_key="test_access_key", 
        minio_secret_key="test_secret_key",
        ollama_endpoint="http://localhost:11434/api/generate"
    )
    
    expected_url = "mysql+pymysql://splinter-research:test_password@mariadb:3306/splinter-research"
    assert settings.database_url == expected_url


def test_supported_formats_list():
    """Test supported image formats parsing."""
    settings = Settings(
        mariadb_password="test_password",
        minio_access_key="test_access_key",
        minio_secret_key="test_secret_key", 
        ollama_endpoint="http://localhost:11434/api/generate",
        supported_image_formats="jpg,png,gif"
    )
    
    assert settings.supported_image_formats_list == ["jpg", "png", "gif"]
