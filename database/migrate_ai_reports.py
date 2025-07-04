#!/usr/bin/env python3
"""
Database migration script to add AI Reports tables.
Run this script to create the new tables for the AI reporting system.
"""

import sys
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the project root to the path
sys.path.insert(0, '/app')

from database.models import Base, UserQuery, GeneratedReport, QueryTemplate
from database.connection import get_database_url
from config import get_settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_ai_reports_tables():
    """Create the AI reports tables in the database."""
    
    try:
        # Get database URL
        settings = get_settings()
        database_url = get_database_url()
        
        logger.info(f"Connecting to database...")
        engine = create_engine(database_url)
        
        # Create tables
        logger.info("Creating AI Reports tables...")
        
        # Create the new tables
        UserQuery.__table__.create(engine, checkfirst=True)
        logger.info("✅ Created user_queries table")
        
        GeneratedReport.__table__.create(engine, checkfirst=True)
        logger.info("✅ Created generated_reports table")
        
        QueryTemplate.__table__.create(engine, checkfirst=True)
        logger.info("✅ Created query_templates table")
        
        logger.info("🎉 All AI Reports tables created successfully!")
        
        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES LIKE '%user_queries%'"))
            if result.fetchone():
                logger.info("✅ Verified user_queries table exists")
            
            result = conn.execute(text("SHOW TABLES LIKE '%generated_reports%'"))
            if result.fetchone():
                logger.info("✅ Verified generated_reports table exists")
                
            result = conn.execute(text("SHOW TABLES LIKE '%query_templates%'"))
            if result.fetchone():
                logger.info("✅ Verified query_templates table exists")
        
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


def check_existing_tables():
    """Check which tables already exist."""
    
    try:
        settings = get_settings()
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check existing tables
            result = conn.execute(text("SHOW TABLES"))
            existing_tables = [row[0] for row in result.fetchall()]
            
            logger.info("📋 Existing tables:")
            for table in sorted(existing_tables):
                logger.info(f"   - {table}")
            
            # Check if AI reports tables exist
            ai_tables = ['user_queries', 'generated_reports', 'query_templates']
            missing_tables = [table for table in ai_tables if table not in existing_tables]
            
            if missing_tables:
                logger.info(f"🔍 Missing AI Reports tables: {', '.join(missing_tables)}")
                return False
            else:
                logger.info("✅ All AI Reports tables already exist")
                return True
                
    except Exception as e:
        logger.error(f"❌ Error checking tables: {e}")
        return False


def main():
    """Main migration function."""
    
    logger.info("🚀 Starting AI Reports Database Migration")
    logger.info("=" * 50)
    
    # Check current state
    if check_existing_tables():
        logger.info("✅ Migration not needed - all tables exist")
        return True
    
    # Create missing tables
    logger.info("📝 Creating missing AI Reports tables...")
    
    if create_ai_reports_tables():
        logger.info("✅ Migration completed successfully!")
        logger.info("")
        logger.info("🎯 Next steps:")
        logger.info("   1. Restart the portal service")
        logger.info("   2. Visit http://localhost:8080/ai-reports")
        logger.info("   3. Start asking AI questions about your data!")
        return True
    else:
        logger.error("❌ Migration failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
