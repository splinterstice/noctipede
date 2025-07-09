"""Application settings and configuration."""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Configuration
    mariadb_host: str = Field(default="mariadb", env="MARIADB_HOST")
    mariadb_port: int = Field(default=3306, env="MARIADB_PORT")
    mariadb_user: str = Field(default="splinter-research", env="MARIADB_USER")
    mariadb_password: str = Field(env="MARIADB_PASSWORD")
    mariadb_database: str = Field(default="splinter-research", env="MARIADB_DATABASE")
    mariadb_root_password: Optional[str] = Field(default=None, env="MARIADB_ROOT_PASSWORD")
    
    # MinIO Configuration
    minio_endpoint: str = Field(default="minio:9000", env="MINIO_ENDPOINT")
    minio_access_key: str = Field(env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(env="MINIO_SECRET_KEY")
    minio_bucket_name: str = Field(default="noctipede-data", env="MINIO_BUCKET_NAME")
    minio_secure: bool = Field(default=False, env="MINIO_SECURE")
    
    # AI/Ollama Configuration
    ollama_endpoint: str = Field(env="OLLAMA_ENDPOINT")
    ollama_vision_model: str = Field(default="llama3.2-vision:11b", env="OLLAMA_VISION_MODEL")
    ollama_text_model: str = Field(default="gemma3:12b", env="OLLAMA_TEXT_MODEL")
    ollama_moderation_model: str = Field(default="gemma3:12b", env="OLLAMA_MODERATION_MODEL")
    
    # Crawler Configuration
    max_links_per_page: int = Field(default=500, env="MAX_LINKS_PER_PAGE")
    max_queue_size: int = Field(default=1000, env="MAX_QUEUE_SIZE")
    max_crawl_depth: int = Field(default=10, env="MAX_CRAWL_DEPTH")
    max_offsite_depth: int = Field(default=1, env="MAX_OFFSITE_DEPTH")
    crawl_delay_seconds: int = Field(default=3, env="CRAWL_DELAY_SECONDS")
    skip_recent_crawls: bool = Field(default=True, env="SKIP_RECENT_CRAWLS")
    recent_crawl_hours: int = Field(default=24, env="RECENT_CRAWL_HOURS")
    max_concurrent_crawlers: int = Field(default=10, env="MAX_CONCURRENT_CRAWLERS")
    
    # Network Configuration
    tor_proxy_host: str = Field(default="127.0.0.1", env="TOR_PROXY_HOST")
    tor_proxy_port: int = Field(default=9050, env="TOR_PROXY_PORT")
    i2p_proxy_host: str = Field(default="127.0.0.1", env="I2P_PROXY_HOST")
    i2p_proxy_port: int = Field(default=4444, env="I2P_PROXY_PORT")
    use_i2p_internal_proxies: bool = Field(default=True, env="USE_I2P_INTERNAL_PROXIES")
    i2p_internal_proxies: str = Field(default="", env="I2P_INTERNAL_PROXIES")
    
    # Application Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    output_dir: str = Field(default="/app/output", env="OUTPUT_DIR")
    sites_file_path: str = Field(default="/app/data/sites.txt", env="SITES_FILE_PATH")
    web_server_port: int = Field(default=8080, env="WEB_SERVER_PORT")
    web_server_host: str = Field(default="0.0.0.0", env="WEB_SERVER_HOST")
    
    # Content Analysis Configuration
    content_analysis_enabled: bool = Field(default=True, env="CONTENT_ANALYSIS_ENABLED")
    image_analysis_enabled: bool = Field(default=True, env="IMAGE_ANALYSIS_ENABLED")
    moderation_threshold: int = Field(default=30, env="MODERATION_THRESHOLD")
    max_image_size_mb: int = Field(default=10, env="MAX_IMAGE_SIZE_MB")
    supported_image_formats: str = Field(default="webp,jpg,jpeg,png,gif,bmp,tiff,svg", env="SUPPORTED_IMAGE_FORMATS")
    
    # Performance Configuration
    db_pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=30, env="DB_MAX_OVERFLOW")
    worker_threads: int = Field(default=4, env="WORKER_THREADS")
    batch_size: int = Field(default=100, env="BATCH_SIZE")
    
    @property
    def database_url(self) -> str:
        """Get the database connection URL."""
        return f"mysql+pymysql://{self.mariadb_user}:{self.mariadb_password}@{self.mariadb_host}:{self.mariadb_port}/{self.mariadb_database}?charset=utf8mb4"
    
    @property
    def i2p_internal_proxies_list(self) -> List[str]:
        """Get I2P internal proxies as a list."""
        if not self.i2p_internal_proxies:
            return []
        return [proxy.strip() for proxy in self.i2p_internal_proxies.split(",") if proxy.strip()]
    
    @property
    def supported_image_formats_list(self) -> List[str]:
        """Get supported image formats as a list."""
        return [fmt.strip().lower() for fmt in self.supported_image_formats.split(",") if fmt.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
