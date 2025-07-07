"""Session binding fix for SQLAlchemy objects."""

from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import DetachedInstanceError
from core import get_logger

logger = get_logger(__name__)

def ensure_session_bound(obj, session: Session):
    """Ensure an SQLAlchemy object is bound to the current session."""
    if obj is None:
        return obj
        
    try:
        # Check if object is already bound to this session
        if obj in session:
            return obj
            
        # Try to merge the object into the current session
        return session.merge(obj)
        
    except DetachedInstanceError:
        # Object is detached, merge it
        logger.debug(f"Merging detached object {obj} into session")
        return session.merge(obj)
    except Exception as e:
        logger.warning(f"Error binding object to session: {e}")
        return obj

def refresh_if_needed(obj, session: Session):
    """Safely refresh an object if it's bound to the session."""
    if obj is None:
        return obj
        
    try:
        # Ensure object is bound to session first
        obj = ensure_session_bound(obj, session)
        
        # Only refresh if object is in session
        if obj in session:
            session.refresh(obj)
        
        return obj
        
    except Exception as e:
        logger.warning(f"Error refreshing object: {e}")
        return obj
