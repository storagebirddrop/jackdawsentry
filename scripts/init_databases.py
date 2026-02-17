#!/usr/bin/env python3
"""
Jackdaw Sentry - Database Initialization Script
Sets up Neo4j and PostgreSQL databases with GDPR-compliant schemas
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.api.database import init_databases
from src.database.neo4j_schema import create_neo4j_schema
from src.database.postgres_schema import create_postgres_schema
from src.database.gdpr_compliance import setup_gdpr_compliance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main initialization function"""
    logger.info("Starting Jackdaw Sentry database initialization...")
    
    try:
        # Initialize database connections
        logger.info("Initializing database connections...")
        await init_databases()
        
        # Create Neo4j schema
        logger.info("Creating Neo4j graph schema...")
        await create_neo4j_schema()
        logger.info("✅ Neo4j schema created successfully")
        
        # Create PostgreSQL schema
        logger.info("Creating PostgreSQL compliance schema...")
        await create_postgres_schema()
        logger.info("✅ PostgreSQL schema created successfully")
        
        # Setup GDPR compliance
        logger.info("Setting up GDPR compliance framework...")
        await setup_gdpr_compliance()
        logger.info("✅ GDPR compliance framework setup complete")
        
        # Verify initialization
        logger.info("Verifying database initialization...")
        await verify_initialization()
        logger.info("✅ Database verification successful")
        
        logger.info("🎉 Jackdaw Sentry database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)


async def verify_initialization():
    """Verify that databases are properly initialized"""
    from src.api.database import get_neo4j_driver, get_postgres_pool
    
    # Test Neo4j
    driver = get_neo4j_driver()
    async with driver.session() as session:
        result = await session.run("MATCH (n) RETURN count(n) as count")
        count = await result.single()
        logger.info(f"Neo4j nodes created: {count['count']}")
    
    # Test PostgreSQL
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        result = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'compliance'"
        )
        logger.info(f"PostgreSQL compliance tables created: {len(result)}")
        for table in result:
            logger.info(f"  - {table['table_name']}")


if __name__ == "__main__":
    asyncio.run(main())
