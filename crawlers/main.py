"""Main crawler entry point."""

import sys
import signal
from datetime import datetime

from core import setup_logging, get_logger
from config import get_settings
from database import get_db_manager
from .manager import CrawlerManager


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger = get_logger(__name__)
    logger.info("Received shutdown signal, stopping crawler...")
    sys.exit(0)


def main():
    """Main crawler function."""
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting Noctipede Crawler")
    
    try:
        # Initialize database
        db_manager = get_db_manager()
        if not db_manager.test_connection():
            logger.error("Database connection failed")
            return 1
        
        # Create tables if they don't exist
        db_manager.create_tables()
        
        # Initialize crawler manager
        crawler_manager = CrawlerManager()
        
        # Load sites and start crawling
        sites = crawler_manager.load_sites_from_file()
        if not sites:
            logger.error("No sites found to crawl")
            return 1
        
        logger.info(f"Starting to crawl {len(sites)} sites")
        start_time = datetime.utcnow()
        
        # Start crawling
        results = crawler_manager.crawl_sites(sites)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Log results
        logger.info(f"Crawling completed in {duration:.2f} seconds")
        logger.info(f"Total sites: {results['total_sites']}")
        logger.info(f"Successful: {results['successful']}")
        logger.info(f"Failed: {results['failed']}")
        
        # Cleanup
        crawler_manager.shutdown()
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error in crawler: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
