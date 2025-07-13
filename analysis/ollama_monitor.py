"""Ollama usage monitoring and statistics tracking."""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from threading import Lock
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from database.connection import get_db_manager
from core import get_logger

logger = get_logger(__name__)

Base = declarative_base()

@dataclass
class RequestStats:
    """Statistics for a single request."""
    model_name: str
    request_type: str
    success: bool
    duration: float
    tokens_used: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class OllamaUsage(Base):
    """Database model for tracking Ollama usage."""
    __tablename__ = 'ollama_usage'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(255), nullable=False, index=True)
    request_type = Column(String(50), nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    duration = Column(Float, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class OllamaMonitor:
    """Monitor and track Ollama API usage statistics."""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self._stats_lock = Lock()
        self._memory_stats = {}
        self._ensure_table_exists()
        logger.info("Ollama monitor initialized")
    
    def _ensure_table_exists(self):
        """Ensure the ollama_usage table exists."""
        try:
            OllamaUsage.__table__.create(self.db_manager.engine, checkfirst=True)
            logger.info("Ollama usage table ready")
        except Exception as e:
            logger.error(f"Failed to create ollama_usage table: {e}")
    
    def track_request(self, stats: RequestStats):
        """Track a completed request."""
        try:
            # Store in database
            self._store_in_database(stats)
            
            # Update memory stats
            with self._stats_lock:
                model_key = stats.model_name
                if model_key not in self._memory_stats:
                    self._memory_stats[model_key] = {
                        'total_requests': 0,
                        'successful_requests': 0,
                        'failed_requests': 0,
                        'total_duration': 0.0,
                        'total_tokens': 0,
                        'last_request': None
                    }
                
                model_stats = self._memory_stats[model_key]
                model_stats['total_requests'] += 1
                model_stats['total_duration'] += stats.duration
                model_stats['last_request'] = stats.timestamp
                
                if stats.success:
                    model_stats['successful_requests'] += 1
                    if stats.tokens_used:
                        model_stats['total_tokens'] += stats.tokens_used
                else:
                    model_stats['failed_requests'] += 1
            
            logger.debug(f"Tracked {stats.request_type} request for {stats.model_name}: "
                        f"{'success' if stats.success else 'failed'} in {stats.duration:.2f}s")
                        
        except Exception as e:
            logger.error(f"Failed to track request: {e}")
    
    def _store_in_database(self, stats: RequestStats):
        """Store request stats in database."""
        try:
            with self.db_manager.get_session() as session:
                usage_record = OllamaUsage(
                    model_name=stats.model_name,
                    request_type=stats.request_type,
                    success=stats.success,
                    duration=stats.duration,
                    tokens_used=stats.tokens_used,
                    error_message=stats.error_message,
                    created_at=stats.timestamp
                )
                session.add(usage_record)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to store usage in database: {e}")
    
    def get_model_stats(self, model_name: str = None, hours: int = 24) -> Dict[str, Any]:
        """Get statistics for a specific model or all models."""
        try:
            with self.db_manager.get_session() as session:
                # Calculate time threshold
                since = datetime.utcnow() - timedelta(hours=hours)
                
                # Base query
                query = session.query(OllamaUsage).filter(OllamaUsage.created_at >= since)
                
                if model_name:
                    query = query.filter(OllamaUsage.model_name == model_name)
                
                records = query.all()
                
                # Aggregate statistics
                stats = {}
                for record in records:
                    model = record.model_name
                    if model not in stats:
                        stats[model] = {
                            'total_requests': 0,
                            'successful_requests': 0,
                            'failed_requests': 0,
                            'total_duration': 0.0,
                            'total_tokens': 0,
                            'avg_duration': 0.0,
                            'success_rate': 0.0,
                            'request_types': {},
                            'last_request': None
                        }
                    
                    model_stats = stats[model]
                    model_stats['total_requests'] += 1
                    model_stats['total_duration'] += record.duration
                    
                    if record.success:
                        model_stats['successful_requests'] += 1
                        if record.tokens_used:
                            model_stats['total_tokens'] += record.tokens_used
                    else:
                        model_stats['failed_requests'] += 1
                    
                    # Track request types
                    req_type = record.request_type
                    if req_type not in model_stats['request_types']:
                        model_stats['request_types'][req_type] = 0
                    model_stats['request_types'][req_type] += 1
                    
                    # Update last request time
                    if (model_stats['last_request'] is None or 
                        record.created_at > model_stats['last_request']):
                        model_stats['last_request'] = record.created_at
                
                # Calculate derived metrics
                for model, model_stats in stats.items():
                    total = model_stats['total_requests']
                    if total > 0:
                        model_stats['avg_duration'] = model_stats['total_duration'] / total
                        model_stats['success_rate'] = model_stats['successful_requests'] / total * 100
                
                return stats if not model_name else stats.get(model_name, {})
                
        except Exception as e:
            logger.error(f"Failed to get model stats: {e}")
            return {}
    
    def get_summary_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get overall summary statistics."""
        try:
            all_stats = self.get_model_stats(hours=hours)
            
            summary = {
                'total_models': len(all_stats),
                'total_requests': sum(s['total_requests'] for s in all_stats.values()),
                'total_successful': sum(s['successful_requests'] for s in all_stats.values()),
                'total_failed': sum(s['failed_requests'] for s in all_stats.values()),
                'total_duration': sum(s['total_duration'] for s in all_stats.values()),
                'total_tokens': sum(s['total_tokens'] for s in all_stats.values()),
                'models': all_stats,
                'time_period_hours': hours
            }
            
            if summary['total_requests'] > 0:
                summary['overall_success_rate'] = summary['total_successful'] / summary['total_requests'] * 100
                summary['avg_duration'] = summary['total_duration'] / summary['total_requests']
            else:
                summary['overall_success_rate'] = 0.0
                summary['avg_duration'] = 0.0
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get summary stats: {e}")
            return {}
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current in-memory statistics (since last restart)."""
        with self._stats_lock:
            return dict(self._memory_stats)
    
    def clear_old_records(self, days: int = 30):
        """Clear old usage records to prevent database bloat."""
        try:
            with self.db_manager.get_session() as session:
                cutoff = datetime.utcnow() - timedelta(days=days)
                deleted = session.query(OllamaUsage).filter(
                    OllamaUsage.created_at < cutoff
                ).delete()
                session.commit()
                logger.info(f"Cleared {deleted} old usage records older than {days} days")
                return deleted
        except Exception as e:
            logger.error(f"Failed to clear old records: {e}")
            return 0

# Global monitor instance
_monitor_instance = None
_monitor_lock = Lock()

def get_ollama_monitor() -> OllamaMonitor:
    """Get the global Ollama monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        with _monitor_lock:
            if _monitor_instance is None:
                _monitor_instance = OllamaMonitor()
    return _monitor_instance

def track_ollama_request(model_name: str, request_type: str, success: bool, 
                        duration: float, tokens_used: Optional[int] = None,
                        error_message: Optional[str] = None):
    """Convenience function to track an Ollama request."""
    monitor = get_ollama_monitor()
    stats = RequestStats(
        model_name=model_name,
        request_type=request_type,
        success=success,
        duration=duration,
        tokens_used=tokens_used,
        error_message=error_message
    )
    monitor.track_request(stats)
