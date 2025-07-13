"""Simplified database session management for crawler operations."""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from core import get_logger
from .connection import get_db_manager

logger = get_logger(__name__)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Simple context manager for database sessions.
    
    Creates a fresh session, yields it, and handles commit/rollback/close.
    This is the recommended way to handle database operations.
    """
    db_manager = get_db_manager()
    session = db_manager.get_scoped_session()
    
    try:
        yield session
        session.commit()
        logger.debug("Database transaction committed successfully")
        
    except SQLAlchemyError as e:
        logger.error(f"Database error, rolling back: {e}")
        try:
            session.rollback()
        except Exception as rollback_error:
            logger.error(f"Error during rollback: {rollback_error}")
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error, rolling back: {e}")
        try:
            session.rollback()
        except Exception as rollback_error:
            logger.error(f"Error during rollback: {rollback_error}")
        raise
        
    finally:
        try:
            session.close()
            logger.debug("Database session closed")
        except Exception as close_error:
            logger.error(f"Error closing session: {close_error}")


def refresh_object(obj, session: Session):
    """Refresh an object to ensure it's bound to the current session."""
    if obj is None:
        return obj
        
    try:
        # If object has an ID, refresh it from database
        if hasattr(obj, 'id') and obj.id is not None:
            session.refresh(obj)
            return obj
        else:
            # Object doesn't have ID yet, return as-is
            return obj
            
    except Exception as e:
        logger.warning(f"Could not refresh object {obj}: {e}")
        # Try to merge instead
        try:
            return session.merge(obj)
        except Exception as merge_error:
            logger.error(f"Could not merge object {obj}: {merge_error}")
            return obj


def safe_update_site_counts(site_id: int, session: Session, increment_crawl=False, increment_page=False, increment_error=False):
    """Safely update site counters with null-safe arithmetic."""
    try:
        from .models import Site
        
        # Get fresh site object
        site = session.query(Site).filter_by(id=site_id).first()
        if not site:
            logger.warning(f"Site with ID {site_id} not found for counter update")
            return
            
        # Update counters with null-safe arithmetic
        if increment_crawl:
            site.crawl_count = (site.crawl_count or 0) + 1
            
        if increment_page:
            site.page_count = (site.page_count or 0) + 1
            
        if increment_error:
            site.error_count = (site.error_count or 0) + 1
            
        # Update last crawled time
        from datetime import datetime
        site.last_crawled = datetime.utcnow()
        
        # Flush to ensure update is applied
        session.flush()
        logger.debug(f"Updated counters for site {site_id}")
        
    except Exception as e:
        logger.error(f"Error updating site counters for site {site_id}: {e}")
        # Don't re-raise - counter updates shouldn't break the main flow
