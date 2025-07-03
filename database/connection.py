"""Database connection management."""

import time
from contextlib import contextmanager
from typing import Generator, Optional, Any, Callable
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.exc import OperationalError, DisconnectionError, TimeoutError
from core import get_logger
from config import get_settings

logger = get_logger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.session_factory = None
        self.scoped_session = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the database engine with connection pooling."""
        self.engine = create_engine(
            self.settings.database_url,
            pool_size=self.settings.db_pool_size,
            max_overflow=self.settings.db_max_overflow,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False,
            connect_args={
                "charset": "utf8mb4",
                "connect_timeout": 30,
                "read_timeout": 30,
                "write_timeout": 30,
                "autocommit": True,
                "sql_mode": "TRADITIONAL",
                "program_name": "noctipede",
                "client_flag": 0,
            }
        )
        
        self.session_factory = sessionmaker(bind=self.engine)
        self.scoped_session = scoped_session(self.session_factory)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_scoped_session(self) -> Session:
        """Get a scoped session for thread-safe operations."""
        return self.scoped_session()
    
    def remove_scoped_session(self):
        """Remove the scoped session."""
        self.scoped_session.remove()
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def create_tables(self):
        """Create all database tables."""
        from .models import Base
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created successfully")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_db_session() -> Session:
    """Get a scoped database session."""
    return get_db_manager().get_scoped_session()


def execute_with_retry(
    operation: Callable[[], Any],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0
) -> Any:
    """Execute a database operation with retry logic."""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return operation()
        except (OperationalError, DisconnectionError, TimeoutError) as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = delay * (backoff_factor ** attempt)
                logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"Database operation failed after {max_retries} attempts: {e}")
    
    raise last_exception
