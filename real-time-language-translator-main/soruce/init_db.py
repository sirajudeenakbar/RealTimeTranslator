#!/usr/bin/env python
"""
Database Initialization Script for Language Translator
Run this script to set up MySQL database and tables
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import Database
from config import DB_NAME

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_database():
    """Initialize database and create tables"""
    logger.info("=" * 60)
    logger.info("Starting Database Initialization")
    logger.info("=" * 60)
    
    db = Database()
    
    # Step 1: Create database
    logger.info(f"\nStep 1: Creating database '{DB_NAME}'...")
    if db.create_database_if_not_exists():
        logger.info("✓ Database creation completed")
    else:
        logger.error("✗ Failed to create database")
        return False
    
    # Step 2: Connect to database
    logger.info(f"\nStep 2: Connecting to database '{DB_NAME}'...")
    if db.connect():
        logger.info("✓ Database connection successful")
    else:
        logger.error("✗ Failed to connect to database")
        logger.info("\nMake sure:")
        logger.info("1. XAMPP is running with MySQL service started")
        logger.info("2. MySQL credentials in .env are correct (default: root/empty)")
        logger.info("3. MySQL is listening on localhost:3306")
        return False
    
    # Step 3: Create tables
    logger.info(f"\nStep 3: Creating tables...")
    try:
        db.create_tables()
        logger.info("✓ All tables created successfully")
    except Exception as e:
        logger.error(f"✗ Error creating tables: {e}")
        db.close()
        return False
    
    # Step 4: Verify tables
    logger.info(f"\nStep 4: Verifying tables...")
    try:
        cursor = db.connection.cursor()
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        cursor.close()
        
        logger.info(f"✓ Found {len(tables)} tables:")
        for table in tables:
            logger.info(f"  - {table[0]}")
    except Exception as e:
        logger.error(f"✗ Error verifying tables: {e}")
        db.close()
        return False
    
    db.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("Database Initialization Completed Successfully!")
    logger.info("=" * 60)
    logger.info("\nYou can now start the API server with: python api_server.py")
    
    return True

if __name__ == '__main__':
    try:
        success = initialize_database()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nInitialization cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
