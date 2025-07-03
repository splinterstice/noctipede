"""Database session management utilities."""

import threading
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy.orm import Session
from core import get_logger
from .connection import get_db_manager

logger = get_logger(__name__)


class DatabaseSession:
    """Thread-safe database session manager."""
    
    def __init__(self):
        self._local = threading.local()
        self._db_manager = get_db_manager()
    
    def get_session(self) -> Session:
        """Get or create a session for the current thread."""
        if not hasattr(self._local, 'session') or self._local.session is None:
            self._local.session = self._db_manager.get_scoped_session()
        return self._local.session
    
    def close_session(self):
        """Close the current thread's session."""
        if hasattr(self._local, 'session') and self._local.session is not None:
            self._local.session.close()
            self._local.session = None
    
    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """Context manager for database transactions."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            # Don't close the session here as it's managed per-thread
            pass
    
    def __enter__(self) -> Session:
        """Enter context manager."""
        return self.get_session()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if exc_type is not None:
            self.get_session().rollback()
        else:
            self.get_session().commit()


# Global session manager
_session_manager: Optional[DatabaseSession] = None


def get_session_manager() -> DatabaseSession:
    """Get the global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = DatabaseSession()
    return _session_manager
