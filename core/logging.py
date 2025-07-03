"""Logging configuration and utilities."""

import logging
import sys
import os
from typing import Optional
from config import get_settings


def setup_logging(level: Optional[str] = None) -> None:
    """Setup application logging configuration."""
    settings = get_settings()
    log_level = level or settings.log_level
    
    # Setup handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Try to add file handler if possible
    try:
        log_file = '/app/logs/noctipede.log'
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file, mode='a'))
    except (PermissionError, OSError) as e:
        print(f"Warning: Could not create log file: {e}. Logging to stdout only.")
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Set specific logger levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)
