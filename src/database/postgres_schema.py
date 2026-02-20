"""
Jackdaw Sentry - PostgreSQL Compliance Database Schema
GDPR/DORA/MiCA/AMLR compliant data storage
"""

import asyncpg
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class PostgresSchema:
    """PostgreSQL schema management for compliance data"""
    
    def __init__(self, pool):
        self.pool = pool
    
    async def create_schema(self):
        """Create complete database schema"""
        logger.info("Creating PostgreSQL compliance schema...")
        
        await self.create_extensions()
        await self.create_compliance_schema()
        await self.create_audit_schema()
        await self.create_gdpr_schema()
        await self.create_indexes()
        await self.create_triggers()
        
        logger.info("✅ PostgreSQL schema creation completed")
    
    async def create_extensions(self):
        """Create required extensions"""
        extensions = [
            "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"",
            "CREATE EXTENSION IF NOT EXISTS \"pgcrypto\"",
            "CREATE EXTENSION IF NOT EXISTS \"btree_gin\"",
            "CREATE EXTENSION IF NOT EXISTS \"pg_trgm\""
        ]
        
        async with self.pool.acquire() as conn:
            for ext in extensions:
                await conn.execute(ext)
                logger.info(f"✅ Created extension: {ext}")
    
    async def create_compliance_schema(self):
        """Create compliance-related tables"""
        
        # Investigations table
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS compliance.investigations (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                case_number VARCHAR(50) UNIQUE NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'open',
                priority VARCHAR(20) NOT NULL DEFAULT 'medium',
                investigator_id UUID NOT NULL REFERENCES compliance.users(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                closed_at TIMESTAMP WITH TIME ZONE,
                retention_until TIMESTAMP WITH TIME ZONE,
                gdpr_consent_recorded BOOLEAN DEFAULT TRUE,
                data_classification VARCHAR(20) DEFAULT 'confidential'
            )
        """)
        
        # SAR (Suspicious Activity Reports) table
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS compliance.sar_reports (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                investigation_id UUID NOT NULL REFERENCES compliance.investigations(id),
                sar_number VARCHAR(50) UNIQUE NOT NULL,
                reporting_authority VARCHAR(100) NOT NULL,
                report_date DATE NOT NULL,
                transaction_count INTEGER NOT NULL DEFAULT 0,
                total_amount DECIMAL(30, 18),
                currency VARCHAR(10),
                suspicious_activity_type VARCHAR(100) NOT NULL,
                narrative TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'draft',
                filed_at TIMESTAMP WITH TIME ZONE,
                acknowledgement_received BOOLEAN DEFAULT FALSE,
                retention_until TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Address watchlists table
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS compliance.address_watchlists (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                address_hash VARCHAR(64) NOT NULL, -- SHA-256 hash of address for GDPR
                blockchain VARCHAR(50) NOT NULL,
                original_address_encrypted BYTEA NOT NULL, -- Encrypted original address
                watchlist_type VARCHAR(50) NOT NULL, -- sanctions, high_risk, etc.
                source VARCHAR(100) NOT NULL, -- OFAC, UN, EU, etc.
                risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
                reason TEXT,
                added_by UUID NOT NULL REFERENCES compliance.users(id),
                added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                valid_until TIMESTAMP WITH TIME ZONE,
                is_active BOOLEAN DEFAULT TRUE,
                retention_until TIMESTAMP WITH TIME ZONE
            )
        """)
        
        # Regulatory reports table
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS compliance.regulatory_reports (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                investigation_id UUID NOT NULL REFERENCES compliance.investigations(id),
                report_type VARCHAR(50) NOT NULL, -- AMLR, DORA, MiCA, etc.
                jurisdiction VARCHAR(10) NOT NULL, -- EU, US, UK, etc.
                reporting_period_start DATE NOT NULL,
                reporting_period_end DATE NOT NULL,
                report_data JSONB NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'draft',
                submitted_at TIMESTAMP WITH TIME ZONE,
                submission_reference VARCHAR(100),
                retention_until TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Users table
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS compliance.users (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                username VARCHAR(100) UNIQUE NOT NULL,
                email_encrypted BYTEA NOT NULL, -- Encrypted for GDPR
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'analyst',
                permissions JSONB NOT NULL DEFAULT '[]',
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP WITH TIME ZONE,
                gdpr_consent_date TIMESTAMP WITH TIME ZONE,
                data_processing_consent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        logger.info("✅ Created compliance tables")
    
    async def create_audit_schema(self):
        """Create audit trail tables"""
        
        # Audit log table
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS compliance.audit_log (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID REFERENCES compliance.users(id),
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(50) NOT NULL,
                resource_id UUID,
                old_values JSONB,
                new_values JSONB,
                ip_address INET,
                user_agent TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                session_id VARCHAR(255),
                compliance_impact VARCHAR(50) DEFAULT 'low',
                retention_until TIMESTAMP WITH TIME ZONE
            )
        """)
        
        # Data access log table
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS compliance.data_access_log (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID NOT NULL REFERENCES compliance.users(id),
                data_type VARCHAR(50) NOT NULL, -- address, transaction, investigation
                data_id VARCHAR(255) NOT NULL,
                access_type VARCHAR(50) NOT NULL, -- read, write, delete
                purpose VARCHAR(100),
                legal_basis VARCHAR(100), -- GDPR legal basis
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                ip_address INET,
                retention_until TIMESTAMP WITH TIME ZONE
            )
        """)
        
        logger.info("✅ Created audit tables")
    
    async def create_gdpr_schema(self):
        """Create GDPR compliance tables"""
        
        # Data subject requests table
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS compliance.gdpr_requests (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                request_type VARCHAR(50) NOT NULL, -- access, rectification, erasure, portability
                subject_identifier VARCHAR(255) NOT NULL, -- Hashed email or other identifier
                request_data JSONB,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                assigned_to UUID REFERENCES compliance.users(id),
                received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                due_date TIMESTAMP WITH TIME ZONE,
                    CONSTRAINT check_due_date CHECK (due_date > received_at),
                completed_at TIMESTAMP WITH TIME ZONE,
                response_data JSONB,
                notes TEXT,
                retention_until TIMESTAMP WITH TIME ZONE
            )
        """)
        
        # Data processing records table
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS compliance.data_processing_records (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                processing_activity VARCHAR(100) NOT NULL,
                data_types JSONB NOT NULL, -- Array of data types processed
                purposes JSONB NOT NULL, -- Array of processing purposes
                legal_basis VARCHAR(100) NOT NULL,
                data_subject_categories JSONB NOT NULL,
                recipients JSONB, -- Who receives the data
                retention_period VARCHAR(100),
                security_measures TEXT,
                controller VARCHAR(100) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                retention_until TIMESTAMP WITH TIME ZONE
            )
        """)
        
        # Data breach incidents table
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS compliance.data_breach_incidents (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                incident_id VARCHAR(50) UNIQUE NOT NULL,
                breach_type VARCHAR(100) NOT NULL,
                affected_data_types JSONB NOT NULL,
                affected_subjects_count INTEGER,
                discovery_date TIMESTAMP WITH TIME ZONE NOT NULL,
                containment_date TIMESTAMP WITH TIME ZONE,
                notification_date TIMESTAMP WITH TIME ZONE,
                description TEXT NOT NULL,
                impact_assessment TEXT,
                remediation_actions TEXT,
                reported_to_authority BOOLEAN DEFAULT FALSE,
                authority_notification_date TIMESTAMP WITH TIME ZONE,
                status VARCHAR(50) NOT NULL DEFAULT 'open',
                retention_until TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        logger.info("✅ Created GDPR tables")
    
    async def create_indexes(self):
        """Create performance indexes"""
        indexes = [
            # Investigations indexes
            "CREATE INDEX IF NOT EXISTS idx_investigations_status ON compliance.investigations(status)",
            "CREATE INDEX IF NOT EXISTS idx_investigations_investigator ON compliance.investigations(investigator_id)",
            "CREATE INDEX IF NOT EXISTS idx_investigations_created_at ON compliance.investigations(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_investigations_retention ON compliance.investigations(retention_until)",
            
            # SAR reports indexes
            "CREATE INDEX IF NOT EXISTS idx_sar_investigation ON compliance.sar_reports(investigation_id)",
            "CREATE INDEX IF NOT EXISTS idx_sar_status ON compliance.sar_reports(status)",
            "CREATE INDEX IF NOT EXISTS idx_sar_date ON compliance.sar_reports(report_date)",
            "CREATE INDEX IF NOT EXISTS idx_sar_retention ON compliance.sar_reports(retention_until)",
            
            # Watchlist indexes
            "CREATE INDEX IF NOT EXISTS idx_watchlist_address ON compliance.address_watchlists(address_hash)",
            "CREATE INDEX IF NOT EXISTS idx_watchlist_blockchain ON compliance.address_watchlists(blockchain)",
            "CREATE INDEX IF NOT EXISTS idx_watchlist_active ON compliance.address_watchlists(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_watchlist_retention ON compliance.address_watchlists(retention_until)",
            
            # Audit log indexes
            "CREATE INDEX IF NOT EXISTS idx_audit_user ON compliance.audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON compliance.audit_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_resource ON compliance.audit_log(resource_type, resource_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_retention ON compliance.audit_log(retention_until)",
            
            # Data access log indexes
            "CREATE INDEX IF NOT EXISTS idx_access_user ON compliance.data_access_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_access_timestamp ON compliance.data_access_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_access_data_type ON compliance.data_access_log(data_type)",
            "CREATE INDEX IF NOT EXISTS idx_access_retention ON compliance.data_access_log(retention_until)",
            
            # GDPR requests indexes
            "CREATE INDEX IF NOT EXISTS idx_gdpr_status ON compliance.gdpr_requests(status)",
            "CREATE INDEX IF NOT EXISTS idx_gdpr_type ON compliance.gdpr_requests(request_type)",
            "CREATE INDEX IF NOT EXISTS idx_gdpr_due_date ON compliance.gdpr_requests(due_date)",
            "CREATE INDEX IF NOT EXISTS idx_gdpr_retention ON compliance.gdpr_requests(retention_until)"
        ]
        
        async with self.pool.acquire() as conn:
            for index in indexes:
                await conn.execute(index)
                logger.info(f"✅ Created index: {index}")
    
    async def create_triggers(self):
        """Create automated triggers"""
        
        # Update timestamp trigger
        await self.pool.execute("""
            CREATE OR REPLACE FUNCTION compliance.update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        # Add triggers to tables with updated_at columns
        triggers = [
            "CREATE TRIGGER update_investigations_updated_at BEFORE UPDATE ON compliance.investigations FOR EACH ROW EXECUTE FUNCTION compliance.update_updated_at_column()",
            "CREATE TRIGGER update_sar_reports_updated_at BEFORE UPDATE ON compliance.sar_reports FOR EACH ROW EXECUTE FUNCTION compliance.update_updated_at_column()",
            "CREATE TRIGGER update_regulatory_reports_updated_at BEFORE UPDATE ON compliance.regulatory_reports FOR EACH ROW EXECUTE FUNCTION compliance.update_updated_at_column()",
            "CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON compliance.users FOR EACH ROW EXECUTE FUNCTION compliance.update_updated_at_column()",
            "CREATE TRIGGER update_data_processing_records_updated_at BEFORE UPDATE ON compliance.data_processing_records FOR EACH ROW EXECUTE FUNCTION compliance.update_updated_at_column()",
            "CREATE TRIGGER update_data_breach_incidents_updated_at BEFORE UPDATE ON compliance.data_breach_incidents FOR EACH ROW EXECUTE FUNCTION compliance.update_updated_at_column()"
        ]
        
        async with self.pool.acquire() as conn:
            for trigger in triggers:
                try:
                    await conn.execute(trigger)
                    logger.info(f"✅ Created trigger: {trigger}")
                except Exception as e:
                    logger.error(f"❌ Failed to create trigger: {trigger}, Error: {e}")
        
        # Audit trigger for automatic logging
        await self.pool.execute("""
            CREATE OR REPLACE FUNCTION compliance.audit_trigger_function()
            RETURNS TRIGGER AS $$
            BEGIN
                IF TG_OP = 'INSERT' THEN
                    INSERT INTO compliance.audit_log (action, resource_type, resource_id, new_values)
                    VALUES (TG_OP, TG_TABLE_NAME, NEW.id, row_to_json(NEW));
                    RETURN NEW;
                ELSIF TG_OP = 'UPDATE' THEN
                    INSERT INTO compliance.audit_log (action, resource_type, resource_id, old_values, new_values)
                    VALUES (TG_OP, TG_TABLE_NAME, NEW.id, row_to_json(OLD), row_to_json(NEW));
                    RETURN NEW;
                ELSIF TG_OP = 'DELETE' THEN
                    INSERT INTO compliance.audit_log (action, resource_type, resource_id, old_values)
                    VALUES (TG_OP, TG_TABLE_NAME, OLD.id, row_to_json(OLD));
                    RETURN OLD;
                END IF;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Add audit triggers to sensitive tables
        audit_triggers = [
            "CREATE TRIGGER audit_investigations AFTER INSERT OR UPDATE OR DELETE ON compliance.investigations FOR EACH ROW EXECUTE FUNCTION compliance.audit_trigger_function()",
            "CREATE TRIGGER audit_sar_reports AFTER INSERT OR UPDATE OR DELETE ON compliance.sar_reports FOR EACH ROW EXECUTE FUNCTION compliance.audit_trigger_function()",
            "CREATE TRIGGER audit_address_watchlists AFTER INSERT OR UPDATE OR DELETE ON compliance.address_watchlists FOR EACH ROW EXECUTE FUNCTION compliance.audit_trigger_function()",
            "CREATE TRIGGER audit_users AFTER INSERT OR UPDATE OR DELETE ON compliance.users FOR EACH ROW EXECUTE FUNCTION compliance.audit_trigger_function()"
        ]
        
        async with self.pool.acquire() as conn:
            for trigger in audit_triggers:
                try:
                    await conn.execute(trigger)
                    logger.info(f"✅ Created audit trigger: {trigger}")
                except Exception as e:
                    logger.error(f"❌ Failed to create audit trigger: {trigger}, Error: {e}")


async def create_postgres_schema():
    """Initialize PostgreSQL database schema"""
    from src.api.config import settings
    
    pool = await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        min_size=2,
        max_size=10
    )
    
    try:
        # Create compliance schema namespace (actual tables are managed by the
        # API migration manager via src/api/migrations/*.sql on startup)
        await pool.execute("CREATE SCHEMA IF NOT EXISTS compliance")
        logger.info("✅ compliance schema namespace ready")

        # Create initial admin user (idempotent — skips if already exists)
        await create_initial_admin_user(pool)

    finally:
        await pool.close()


async def create_initial_admin_user(pool):
    """No-op: admin user is seeded by 002_seed_admin_user.sql via the API migration manager."""
    logger.info("✅ Admin user seeded by migration (002_seed_admin_user.sql)")


if __name__ == "__main__":
    import asyncio
    asyncio.run(create_postgres_schema())
