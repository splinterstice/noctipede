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
            
        # If object has an ID, try to get fresh copy from database
        if hasattr(obj, 'id') and obj.id is not None:
            # Get the object's class
            obj_class = obj.__class__
            fresh_obj = session.query(obj_class).filter_by(id=obj.id).first()
            if fresh_obj:
                return fresh_obj
            else:
                logger.warning(f"Object {obj} with ID {obj.id} not found in database")
                return None
        
        # Try to merge the object into the current session
        return session.merge(obj)
        
    except DetachedInstanceError:
        # Object is detached, try to get fresh copy or merge
        logger.debug(f"Merging detached object {obj} into session")
        try:
            if hasattr(obj, 'id') and obj.id is not None:
                obj_class = obj.__class__
                fresh_obj = session.query(obj_class).filter_by(id=obj.id).first()
                return fresh_obj if fresh_obj else session.merge(obj)
            else:
                return session.merge(obj)
        except Exception as merge_error:
            logger.error(f"Could not merge detached object: {merge_error}")
            return None
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

def get_fresh_object(obj_class, obj_id, session: Session):
    """Get a fresh object from the database by ID."""
    try:
        if obj_id is None:
            return None
        return session.query(obj_class).filter_by(id=obj_id).first()
    except Exception as e:
        logger.error(f"Error getting fresh {obj_class.__name__} with ID {obj_id}: {e}")
        return None

def safe_commit(session: Session):
    """Safely commit a session with error handling."""
    try:
        session.commit()
        return True
    except Exception as e:
        logger.error(f"Error committing session: {e}")
        try:
            session.rollback()
        except Exception:
            pass  # Ignore rollback errors
        return False
