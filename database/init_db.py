#!/usr/bin/env python3
"""Database initialization script."""

import sys
import os
sys.path.insert(0, '/app')

from database.connection import get_db_manager
from database.models import Base, Site
from core import get_logger

logger = get_logger(__name__)

def initialize_database():
    """Initialize database tables and seed data."""
    try:
        db_manager = get_db_manager()
        
        # Create all tables
        logger.info("Creating database tables...")
        db_manager.create_tables()
        
        # Check if we need to seed initial sites
        with db_manager.get_session() as session:
            site_count = session.query(Site).count()
            logger.info(f"Current sites in database: {site_count}")
            
            if site_count == 0:
                logger.info("Seeding initial sites...")
                
                # Add some initial sites
                initial_sites = [
                    Site(url="http://3g2upl4pq6kufc4m.onion", domain="duckduckgo.onion", network_type="tor", is_onion=True),
                    Site(url="http://identiguy.i2p", domain="identiguy.i2p", network_type="i2p", is_i2p=True),
                    Site(url="http://planet.i2p", domain="planet.i2p", network_type="i2p", is_i2p=True),
                    Site(url="https://example.com", domain="example.com", network_type="clearnet"),
                ]
                
                for site in initial_sites:
                    session.add(site)
                
                session.commit()
                logger.info(f"Added {len(initial_sites)} initial sites")
        
        logger.info("Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = initialize_database()
    sys.exit(0 if success else 1)
