"""Database models for Noctipede."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, LargeBinary, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT, LONGBLOB

Base = declarative_base()


class Site(Base):
    """Model for tracked websites."""
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True)
    url = Column(String(255), unique=True, nullable=False)
    domain = Column(String(255), nullable=True)  # Extracted domain
    network_type = Column(String(20), nullable=False, default='clearnet')  # clearnet, tor, i2p
    is_onion = Column(Boolean, default=False)  # Backward compatibility
    is_i2p = Column(Boolean, default=False)    # Backward compatibility
    last_crawled = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='active')  # active, inactive, blocked
    crawl_count = Column(Integer, default=0)
    page_count = Column(Integer, default=0)  # Number of pages crawled
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    
    # Relationships
    pages = relationship("Page", back_populates="site", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_site_url', 'url'),
        Index('idx_site_domain', 'domain'),
        Index('idx_site_network_type', 'network_type'),
        Index('idx_site_last_crawled', 'last_crawled'),
        Index('idx_site_status', 'status'),
    )


class Page(Base):
    """Model for crawled web pages."""
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    url = Column(String(500), nullable=False)
    title = Column(String(500), nullable=True)
    content = Column(LONGTEXT, nullable=True)
    content_hash = Column(String(64), nullable=True)  # SHA-256 hash
    status_code = Column(Integer, nullable=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)
    content_type = Column(String(100), nullable=True)
    content_length = Column(Integer, nullable=True)
    response_time = Column(Float, nullable=True)  # in seconds
    
    # Content analysis fields
    language = Column(String(10), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String(20), nullable=True)
    
    # Relationships
    site = relationship("Site", back_populates="pages")
    media_files = relationship("MediaFile", back_populates="page", cascade="all, delete-orphan")
    content_analyses = relationship("ContentAnalysis", back_populates="page", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="page", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_page_site_id', 'site_id'),
        Index('idx_page_url', 'url'),
        Index('idx_page_crawled_at', 'crawled_at'),
        Index('idx_page_content_hash', 'content_hash'),
        Index('idx_page_status_code', 'status_code'),
    )


class MediaFile(Base):
    """Model for media files found on pages."""
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey('pages.id'), nullable=False)
    url = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=True)  # image, video, audio, document
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_hash = Column(String(64), nullable=True)  # SHA-256 hash
    downloaded_at = Column(DateTime, nullable=True)
    
    # Storage information
    minio_bucket = Column(String(100), nullable=True)
    minio_object_name = Column(String(500), nullable=True)
    
    # Analysis fields
    description = Column(Text, nullable=True)  # AI-generated description
    analysis_score = Column(Float, nullable=True)  # Content analysis score
    is_flagged = Column(Boolean, default=False)
    flagged_reason = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, nullable=True)
    
    # Relationships
    page = relationship("Page", back_populates="media_files")
    
    # Indexes
    __table_args__ = (
        Index('idx_media_page_id', 'page_id'),
        Index('idx_media_file_type', 'file_type'),
        Index('idx_media_file_hash', 'file_hash'),
        Index('idx_media_is_flagged', 'is_flagged'),
        Index('idx_media_analyzed_at', 'analyzed_at'),
    )


class ContentAnalysis(Base):
    """Model for AI-powered content analysis results."""
    __tablename__ = "content_analyses"

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey('pages.id'), nullable=False)
    analysis_type = Column(String(50), nullable=False)  # sentiment, topic, moderation, etc.
    model_name = Column(String(100), nullable=False)
    analysis_result = Column(JSON, nullable=True)  # Structured analysis results
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    page = relationship("Page", back_populates="content_analyses")
    
    # Indexes
    __table_args__ = (
        Index('idx_analysis_page_id', 'page_id'),
        Index('idx_analysis_type', 'analysis_type'),
        Index('idx_analysis_created_at', 'created_at'),
    )


class Entity(Base):
    """Model for extracted entities from content."""
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey('pages.id'), nullable=False)
    entity_type = Column(String(50), nullable=False)  # PERSON, ORG, GPE, etc.
    entity_text = Column(String(255), nullable=False)
    confidence_score = Column(Float, nullable=True)
    start_position = Column(Integer, nullable=True)
    end_position = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    page = relationship("Page", back_populates="entities")
    
    # Indexes
    __table_args__ = (
        Index('idx_entity_page_id', 'page_id'),
        Index('idx_entity_type', 'entity_type'),
        Index('idx_entity_text', 'entity_text'),
    )


class TopicCluster(Base):
    """Model for topic clustering results."""
    __tablename__ = "topic_clusters"

    id = Column(Integer, primary_key=True)
    cluster_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # List of keywords
    page_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_cluster_name', 'cluster_name'),
        Index('idx_cluster_created_at', 'created_at'),
    )


class CrawlSession(Base):
    """Model for tracking crawl sessions."""
    __tablename__ = "crawl_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(20), default='running')  # running, completed, failed, stopped
    sites_crawled = Column(Integer, default=0)
    pages_crawled = Column(Integer, default=0)
    media_downloaded = Column(Integer, default=0)
    errors_encountered = Column(Integer, default=0)
    configuration = Column(JSON, nullable=True)  # Crawl configuration used
    
    # Indexes
    __table_args__ = (
        Index('idx_session_id', 'session_id'),
        Index('idx_session_started_at', 'started_at'),
        Index('idx_session_status', 'status'),
    )


class UserQuery(Base):
    """Model for storing user queries and AI interactions."""
    __tablename__ = "user_queries"

    id = Column(Integer, primary_key=True)
    query_text = Column(LONGTEXT, nullable=False)  # User's natural language query
    query_type = Column(String(50), nullable=False)  # report, analysis, search, etc.
    query_hash = Column(String(64), nullable=True)  # SHA-256 hash for deduplication
    user_session = Column(String(100), nullable=True)  # Session identifier
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6 address
    user_agent = Column(String(500), nullable=True)  # Browser user agent
    
    # Query processing
    processed_at = Column(DateTime, nullable=True)
    processing_time = Column(Float, nullable=True)  # Time in seconds
    status = Column(String(20), default='pending')  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # AI model information
    ai_model = Column(String(100), nullable=True)  # Model used for processing
    ai_prompt = Column(LONGTEXT, nullable=True)  # Generated prompt sent to AI
    ai_response = Column(LONGTEXT, nullable=True)  # Raw AI response
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reports = relationship("GeneratedReport", back_populates="query", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_query_hash', 'query_hash'),
        Index('idx_query_type', 'query_type'),
        Index('idx_query_status', 'status'),
        Index('idx_query_created_at', 'created_at'),
        Index('idx_query_user_session', 'user_session'),
    )


class GeneratedReport(Base):
    """Model for storing generated reports and analysis results."""
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey('user_queries.id'), nullable=False)
    
    # Report metadata
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(String(50), nullable=False)  # summary, detailed, chart, table, etc.
    format = Column(String(20), default='html')  # html, json, csv, pdf
    
    # Report content
    content = Column(LONGTEXT, nullable=True)  # Main report content
    data_json = Column(JSON, nullable=True)  # Structured data for charts/tables
    summary = Column(Text, nullable=True)  # Executive summary
    
    # Data sources and scope
    data_sources = Column(JSON, nullable=True)  # Which tables/data were queried
    date_range_start = Column(DateTime, nullable=True)  # Data time range
    date_range_end = Column(DateTime, nullable=True)
    record_count = Column(Integer, nullable=True)  # Number of records analyzed
    
    # Report statistics
    generation_time = Column(Float, nullable=True)  # Time to generate in seconds
    file_size = Column(Integer, nullable=True)  # Size in bytes
    view_count = Column(Integer, default=0)  # How many times viewed
    download_count = Column(Integer, default=0)  # How many times downloaded
    
    # Storage information
    minio_bucket = Column(String(100), nullable=True)  # If stored in MinIO
    minio_object_name = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=True)  # Local file path if applicable
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    is_public = Column(Boolean, default=False)  # Whether report can be shared
    
    # Relationships
    query = relationship("UserQuery", back_populates="reports")
    
    # Indexes
    __table_args__ = (
        Index('idx_report_query_id', 'query_id'),
        Index('idx_report_type', 'report_type'),
        Index('idx_report_created_at', 'created_at'),
        Index('idx_report_is_public', 'is_public'),
        Index('idx_report_expires_at', 'expires_at'),
    )


class QueryTemplate(Base):
    """Model for storing reusable query templates."""
    __tablename__ = "query_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # security, content, network, etc.
    
    # Template content
    template_text = Column(LONGTEXT, nullable=False)  # Template with placeholders
    parameters = Column(JSON, nullable=True)  # Parameter definitions
    example_query = Column(Text, nullable=True)  # Example of filled template
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_template_name', 'name'),
        Index('idx_template_category', 'category'),
        Index('idx_template_is_active', 'is_active'),
        Index('idx_template_usage_count', 'usage_count'),
    )
