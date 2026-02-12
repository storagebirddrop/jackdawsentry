"""
Jackdaw Sentry - GDPR Compliance Framework
Data protection, consent management, and automated deletion
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import json
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class GDPRComplianceManager:
    """GDPR compliance management for Jackdaw Sentry"""
    
    def __init__(self, postgres_pool, neo4j_driver, encryption_key: str):
        self.postgres_pool = postgres_pool
        self.neo4j_driver = neo4j_driver
        self.fernet = Fernet(encryption_key.encode())
    
    async def initialize_compliance_framework(self):
        """Initialize GDPR compliance framework"""
        logger.info("Initializing GDPR compliance framework...")
        
        await self.setup_data_processing_records()
        await self.setup_retention_policies()
        await self.setup_consent_management()
        await self.setup_data_subject_request_handling()
        
        logger.info("✅ GDPR compliance framework initialized")
    
    async def setup_data_processing_records(self):
        """Setup GDPR Article 30 processing records"""
        processing_activities = [
            {
                "processing_activity": "Blockchain Transaction Analysis",
                "data_types": ["wallet_addresses", "transaction_hashes", "amounts", "timestamps"],
                "purposes": ["fraud_detection", "aml_compliance", "regulatory_reporting"],
                "legal_basis": "legitimate_interest",
                "data_subject_categories": ["crypto_users", "transaction_participants"],
                "recipients": ["regulatory_authorities", "law_enforcement"],
                "retention_period": "7_years",
                "security_measures": "encryption_at_rest_and_transit",
                "controller": "Jackdaw Sentry"
            },
            {
                "processing_activity": "Address Risk Assessment",
                "data_types": ["risk_scores", "address_classifications", "behavioral_patterns"],
                "purposes": ["risk_management", "compliance_monitoring"],
                "legal_basis": "legal_obligation",
                "data_subject_categories": ["crypto_users"],
                "recipients": ["compliance_officers", "regulatory_authorities"],
                "retention_period": "7_years",
                "security_measures": "encryption_access_controls",
                "controller": "Jackdaw Sentry"
            },
            {
                "processing_activity": "Investigation Case Management",
                "data_types": ["case_details", "evidence", "analyst_notes", "sar_reports"],
                "purposes": ["regulatory_compliance", "criminal_investigation"],
                "legal_basis": "legal_obligation",
                "data_subject_categories": ["suspected_individuals", "investigation_subjects"],
                "recipients": ["regulatory_authorities", "law_enforcement"],
                "retention_period": "7_years",
                "security_measures": "strict_access_controls_audit_logging",
                "controller": "Jackdaw Sentry"
            }
        ]
        
        query = """
        INSERT INTO compliance.data_processing_records (
            processing_activity, data_types, purposes, legal_basis,
            data_subject_categories, recipients, retention_period,
            security_measures, controller
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT DO NOTHING
        """
        
        async with self.postgres_pool.acquire() as conn:
            for activity in processing_activities:
                await conn.execute(query, **activity)
        
        logger.info("✅ Setup data processing records")
    
    async def setup_retention_policies(self):
        """Setup automated data retention policies"""
        
        # Create retention policy function
        retention_function = """
        CREATE OR REPLACE FUNCTION compliance.cleanup_expired_data()
        RETURNS void AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            -- Delete expired investigations
            DELETE FROM compliance.investigations 
            WHERE retention_until < NOW()
            RETURNING id INTO deleted_count;
            
            -- Delete expired SAR reports
            DELETE FROM compliance.sar_reports 
            WHERE retention_until < NOW();
            
            -- Delete expired watchlist entries
            DELETE FROM compliance.address_watchlists 
            WHERE retention_until < NOW();
            
            -- Delete expired audit logs
            DELETE FROM compliance.audit_log 
            WHERE retention_until < NOW();
            
            -- Delete expired data access logs
            DELETE FROM compliance.data_access_log 
            WHERE retention_until < NOW();
            
            -- Delete expired GDPR requests
            DELETE FROM compliance.gdpr_requests 
            WHERE retention_until < NOW();
            
            -- Delete expired data processing records
            DELETE FROM compliance.data_processing_records 
            WHERE retention_until < NOW();
            
            -- Delete expired data breach incidents
            DELETE FROM compliance.data_breach_incidents 
            WHERE retention_until < NOW();
            
            RAISE NOTICE 'Expired data cleanup completed';
        END;
        $$ LANGUAGE plpgsql;
        """
        
        async with self.postgres_pool.acquire() as conn:
            await conn.execute(retention_function)
        
        logger.info("✅ Setup retention policies")
    
    async def setup_consent_management(self):
        """Setup GDPR consent management"""
        
        # Create consent tracking table
        consent_table = """
        CREATE TABLE IF NOT EXISTS compliance.user_consent (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES compliance.users(id),
            consent_type VARCHAR(50) NOT NULL, -- data_processing, marketing, analytics
            consent_given BOOLEAN NOT NULL,
            consent_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            consent_version VARCHAR(20) NOT NULL DEFAULT '1.0',
            ip_address INET,
            user_agent TEXT,
            withdrawn_at TIMESTAMP WITH TIME ZONE,
            retention_until TIMESTAMP WITH TIME ZONE GENERATED ALWAYS AS (consent_date + INTERVAL '7 years') STORED,
            UNIQUE(user_id, consent_type, consent_version)
        )
        """
        
        async with self.postgres_pool.acquire() as conn:
            await conn.execute(consent_table)
        
        logger.info("✅ Setup consent management")
    
    async def setup_data_subject_request_handling(self):
        """Setup GDPR data subject request handling"""
        
        # Create request processing functions
        request_functions = [
            # Access request handler
            """
            CREATE OR REPLACE FUNCTION compliance.handle_access_request(request_id UUID)
            RETURNS JSONB AS $$
            DECLARE
                request_record RECORD;
                user_data JSONB := '{}';
            BEGIN
                -- Get request details
                SELECT * INTO request_record 
                FROM compliance.gdpr_requests 
                WHERE id = request_id;
                
                IF NOT FOUND THEN
                    RETURN jsonb_build_object('error', 'Request not found');
                END IF;
                
                -- Collect user data from all tables
                -- Investigations
                SELECT jsonb_agg(row_to_json(i.*)) INTO user_data.investigations
                FROM compliance.investigations i
                WHERE i.investigator_id = request_record.subject_identifier::UUID;
                
                -- SAR reports
                SELECT jsonb_agg(row_to_json(s.*)) INTO user_data.sar_reports
                FROM compliance.sar_reports s
                JOIN compliance.investigations i ON s.investigation_id = i.id
                WHERE i.investigator_id = request_record.subject_identifier::UUID;
                
                -- Data access logs
                SELECT jsonb_agg(row_to_json(d.*)) INTO user_data.data_access_logs
                FROM compliance.data_access_log d
                WHERE d.user_id = request_record.subject_identifier::UUID;
                
                -- Update request status
                UPDATE compliance.gdpr_requests 
                SET status = 'completed', 
                    completed_at = NOW(),
                    response_data = user_data
                WHERE id = request_id;
                
                RETURN user_data;
            END;
            $$ LANGUAGE plpgsql;
            """,
            
            # Erasure request handler
            """
            CREATE OR REPLACE FUNCTION compliance.handle_erasure_request(request_id UUID)
            RETURNS BOOLEAN AS $$
            DECLARE
                request_record RECORD;
                user_id UUID;
            BEGIN
                -- Get request details
                SELECT * INTO request_record 
                FROM compliance.gdpr_requests 
                WHERE id = request_id;
                
                IF NOT FOUND THEN
                    RETURN FALSE;
                END IF;
                
                -- Parse user ID from subject identifier
                user_id := request_record.subject_identifier::UUID;
                
                -- Anonymize user data (don't delete due to legal requirements)
                UPDATE compliance.users 
                SET username = 'DELETED_' || substr(md5(random()::text), 1, 20),
                    email_encrypted = crypt('deleted', gen_salt('bf')),
                    is_active = FALSE
                WHERE id = user_id;
                
                -- Mark request as completed
                UPDATE compliance.gdpr_requests 
                SET status = 'completed', 
                    completed_at = NOW(),
                    notes = 'User data anonymized as per GDPR right to erasure'
                WHERE id = request_id;
                
                RETURN TRUE;
            END;
            $$ LANGUAGE plpgsql;
            """
        ]
        
        async with self.postgres_pool.acquire() as conn:
            for func in request_functions:
                await conn.execute(func)
        
        logger.info("✅ Setup data subject request handling")
    
    async def hash_address(self, address: str) -> str:
        """Hash blockchain address for GDPR compliance"""
        return hashlib.sha256(address.encode()).hexdigest()
    
    async def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.fernet.encrypt(data.encode()).decode()
    
    async def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    async def log_data_access(self, user_id: str, data_type: str, data_id: str, 
                           access_type: str, purpose: str, legal_basis: str,
                           ip_address: str = None):
        """Log data access for GDPR compliance"""
        query = """
        INSERT INTO compliance.data_access_log (
            user_id, data_type, data_id, access_type, purpose, legal_basis, ip_address
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        
        async with self.postgres_pool.acquire() as conn:
            await conn.execute(query, user_id, data_type, data_id, access_type, purpose, legal_basis, ip_address)
    
    async def create_data_subject_request(self, request_type: str, subject_identifier: str,
                                     request_data: Dict[str, Any]) -> str:
        """Create GDPR data subject request"""
        query = """
        INSERT INTO compliance.gdpr_requests (
            request_type, subject_identifier, request_data, status
        ) VALUES ($1, $2, $3, 'pending')
        RETURNING id
        """
        
        async with self.postgres_pool.acquire() as conn:
            request_id = await conn.fetchval(query, request_type, subject_identifier, json.dumps(request_data))
        
        logger.info(f"Created GDPR request: {request_id} of type: {request_type}")
        return request_id
    
    async def get_user_consent(self, user_id: str, consent_type: str) -> Optional[Dict]:
        """Get user consent record"""
        query = """
        SELECT * FROM compliance.user_consent 
        WHERE user_id = $1 AND consent_type = $2 
        ORDER BY consent_date DESC 
        LIMIT 1
        """
        
        async with self.postgres_pool.acquire() as conn:
            record = await conn.fetchrow(query, user_id, consent_type)
            return dict(record) if record else None
    
    async def update_user_consent(self, user_id: str, consent_type: str, 
                              consent_given: bool, ip_address: str = None,
                              user_agent: str = None):
        """Update user consent"""
        query = """
        INSERT INTO compliance.user_consent (
            user_id, consent_type, consent_given, ip_address, user_agent
        ) VALUES ($1, $2, $3, $4, $5)
        """
        
        async with self.postgres_pool.acquire() as conn:
            await conn.execute(query, user_id, consent_type, consent_given, ip_address, user_agent)
        
        logger.info(f"Updated consent for user {user_id}: {consent_type} = {consent_given}")
    
    async def cleanup_expired_data(self):
        """Clean up expired data according to retention policies"""
        query = "SELECT compliance.cleanup_expired_data()"
        
        async with self.postgres_pool.acquire() as conn:
            await conn.execute(query)
        
        logger.info("Completed expired data cleanup")
    
    async def generate_data_processing_report(self) -> Dict[str, Any]:
        """Generate GDPR Article 30 data processing report"""
        query = """
        SELECT 
            processing_activity,
            data_types,
            purposes,
            legal_basis,
            data_subject_categories,
            recipients,
            retention_period,
            security_measures
        FROM compliance.data_processing_records
        ORDER BY processing_activity
        """
        
        async with self.postgres_pool.acquire() as conn:
            records = await conn.fetch(query)
        
        return {
            "controller": "Jackdaw Sentry",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "processing_activities": [dict(record) for record in records]
        }
    
    async def start_background_tasks(self):
        """Start background GDPR compliance tasks"""
        # Schedule daily data cleanup
        asyncio.create_task(self.schedule_data_cleanup())
        
        # Schedule weekly consent review
        asyncio.create_task(self.schedule_consent_review())
    
    async def schedule_data_cleanup(self):
        """Schedule daily data cleanup"""
        while True:
            try:
                await self.cleanup_expired_data()
                await asyncio.sleep(24 * 3600)  # Run daily
            except Exception as e:
                logger.error(f"Error in data cleanup: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour
    
    async def schedule_consent_review(self):
        """Schedule weekly consent review"""
        while True:
            try:
                await self.review_expired_consent()
                await asyncio.sleep(7 * 24 * 3600)  # Run weekly
            except Exception as e:
                logger.error(f"Error in consent review: {e}")
                await asyncio.sleep(24 * 3600)  # Retry in 1 day
    
    async def review_expired_consent(self):
        """Review and handle expired consent"""
        query = """
        SELECT DISTINCT user_id, consent_type 
        FROM compliance.user_consent 
        WHERE consent_given = TRUE 
        AND consent_date < NOW() - INTERVAL '1 year'
        """
        
        async with self.postgres_pool.acquire() as conn:
            expired_consent = await conn.fetch(query)
        
        for record in expired_consent:
            logger.warning(f"Consent expired for user {record['user_id']} - {record['consent_type']}")
            # Here you could trigger consent renewal notifications


async def setup_gdpr_compliance():
    """Setup GDPR compliance framework"""
    from src.api.config import settings
    from src.api.database import get_postgres_pool, get_neo4j_driver
    
    postgres_pool = get_postgres_pool()
    neo4j_driver = get_neo4j_driver()
    
    gdpr_manager = GDPRComplianceManager(
        postgres_pool, 
        neo4j_driver, 
        settings.ENCRYPTION_KEY
    )
    
    await gdpr_manager.initialize_compliance_framework()
    await gdpr_manager.start_background_tasks()
    
    return gdpr_manager


if __name__ == "__main__":
    import asyncio
    asyncio.run(setup_gdpr_compliance())
