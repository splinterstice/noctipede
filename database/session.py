"""Database session management utilities."""

import threading
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from core import get_logger
from .connection import get_db_manager

logger = get_logger(__name__)


class DatabaseSession:
    """Thread-safe database session manager with improved error handling."""
    
    def __init__(self):
        self._local = threading.local()
        self._db_manager = get_db_manager()
    
    def get_session(self) -> Session:
        """Get or create a fresh session for the current thread."""
        # Always create a fresh session to avoid stale session issues
        if hasattr(self._local, 'session') and self._local.session is not None:
            try:
                self._local.session.close()
            except Exception:
                pass  # Ignore close errors
        
        self._local.session = self._db_manager.get_scoped_session()
        return self._local.session
    
    def close_session(self):
        """Close the current thread's session."""
        if hasattr(self._local, 'session') and self._local.session is not None:
            try:
                self._local.session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
            finally:
                self._local.session = None
    
    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """Context manager for database transactions with proper error handling."""
        session = None
        try:
            session = self.get_session()
            yield session
            session.commit()
        except SQLAlchemyError as e:
            if session:
                try:
                    session.rollback()
                except Exception:
                    pass  # Ignore rollback errors
            logger.error(f"Database transaction error: {e}")
            raise
        except Exception as e:
            if session:
                try:
                    session.rollback()
                except Exception:
                    pass  # Ignore rollback errors
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass  # Ignore close errors
    
    @contextmanager
    def fresh_session(self) -> Generator[Session, None, None]:
        """Context manager that always provides a fresh session."""
        session = self._db_manager.get_scoped_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            try:
                session.rollback()
            except Exception:
                pass
            logger.error(f"Fresh session transaction error: {e}")
            raise
        finally:
            try:
                session.close()
            except Exception:
                pass
    
    def __enter__(self) -> Session:
        """Enter context manager."""
        return self.get_session()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        session = getattr(self._local, 'session', None)
        if session:
            try:
                if exc_type is not None:
                    session.rollback()
                else:
                    session.commit()
            except Exception as e:
                logger.warning(f"Error in session exit: {e}")
            finally:
                try:
                    session.close()
                except Exception:
                    pass
                self._local.session = None


# Global session manager
_session_manager: Optional[DatabaseSession] = None


def get_session_manager() -> DatabaseSession:
    """Get the global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = DatabaseSession()
    return _session_manager
