"""
Jackdaw Sentry - VASP Registry
Comprehensive database of Virtual Asset Service Providers
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
import json

from .models import VASP, EntityType, RiskLevel, VASPResult, AttributionSearchFilters
from src.api.database import get_postgres_connection

logger = logging.getLogger(__name__)


class VASPRegistry:
    """Registry for managing VASP data and classifications"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        self._initialized = False
    
    async def initialize(self):
        """Initialize the VASP registry with default data"""
        if self._initialized:
            return
        
        logger.info("Initializing VASP Registry...")
        
        # Create tables if they don't exist
        await self._create_tables()
        
        # Load initial VASP data if empty
        await self._load_default_vasps()
        
        self._initialized = True
        logger.info("VASP Registry initialized successfully")
    
    async def _create_tables(self):
        """Create VASP registry tables"""
        
        create_vasps_table = """
        CREATE TABLE IF NOT EXISTS vasp_registry (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            entity_type VARCHAR(50) NOT NULL,
            risk_level VARCHAR(20) NOT NULL,
            jurisdictions JSONB DEFAULT '[]',
            registration_numbers JSONB DEFAULT '{}',
            website VARCHAR(255),
            description TEXT,
            founded_year INTEGER,
            active_countries JSONB DEFAULT '[]',
            supported_blockchains JSONB DEFAULT '[]',
            compliance_program BOOLEAN,
            regulatory_licenses JSONB DEFAULT '[]',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(name, entity_type)
        );
        
        CREATE INDEX IF NOT EXISTS idx_vasp_entity_type ON vasp_registry(entity_type);
        CREATE INDEX IF NOT EXISTS idx_vasp_risk_level ON vasp_registry(risk_level);
        CREATE INDEX IF NOT EXISTS idx_vasp_jurisdictions ON vasp_registry USING GIN(jurisdictions);
        CREATE INDEX IF NOT EXISTS idx_vasp_blockchains ON vasp_registry USING GIN(supported_blockchains);
        """
        
        create_sources_table = """
        CREATE TABLE IF NOT EXISTS attribution_sources (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            source_type VARCHAR(50) NOT NULL,
            reliability_score DECIMAL(5,4) NOT NULL,
            description TEXT,
            url VARCHAR(255),
            api_endpoint VARCHAR(255),
            authentication_required BOOLEAN DEFAULT FALSE,
            rate_limit_per_hour INTEGER,
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_sources_type ON attribution_sources(source_type);
        CREATE INDEX IF NOT EXISTS idx_sources_reliability ON attribution_sources(reliability_score);
        """
        
        conn = await get_postgres_connection()
        try:
            await conn.execute(create_vasps_table)
            await conn.execute(create_sources_table)
            await conn.commit()
            logger.info("VASP registry tables created/verified")
        except Exception as e:
            logger.error(f"Error creating VASP tables: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()
    
    async def _load_default_vasps(self):
        """Load default VASP data if registry is empty"""
        
        check_query = "SELECT COUNT(*) FROM vasp_registry"
        conn = await get_postgres_connection()
        
        try:
            result = await conn.fetchval(check_query)
            if result > 0:
                logger.info(f"VASP registry already contains {result} entries")
                return
            
            logger.info("Loading default VASP data...")
            
            # Default major exchanges
            default_vasps = [
                {
                    "name": "Binance",
                    "entity_type": EntityType.EXCHANGE,
                    "risk_level": RiskLevel.MEDIUM,
                    "jurisdictions": ["CY", "MT"],  # Cyprus, Malta
                    "website": "https://www.binance.com",
                    "founded_year": 2017,
                    "active_countries": ["global"],
                    "supported_blockchains": ["bitcoin", "ethereum", "bsc", "polygon", "arbitrum", "avalanche", "optimism"],
                    "compliance_program": True,
                    "regulatory_licenses": ["CYSEC", "MSB"]
                },
                {
                    "name": "Coinbase",
                    "entity_type": EntityType.EXCHANGE,
                    "risk_level": RiskLevel.LOW,
                    "jurisdictions": ["US"],
                    "website": "https://www.coinbase.com",
                    "founded_year": 2012,
                    "active_countries": ["US", "EU", "UK", "AU", "CA"],
                    "supported_blockchains": ["bitcoin", "ethereum", "polygon", "arbitrum", "base", "avalanche"],
                    "compliance_program": True,
                    "regulatory_licenses": ["FINCEN", "FCA", "MAS"]
                },
                {
                    "name": "Kraken",
                    "entity_type": EntityType.EXCHANGE,
                    "risk_level": RiskLevel.LOW,
                    "jurisdictions": ["US"],
                    "website": "https://www.kraken.com",
                    "founded_year": 2011,
                    "active_countries": ["US", "EU", "UK", "AU", "CA", "JP"],
                    "supported_blockchains": ["bitcoin", "ethereum", "polygon", "arbitrum", "optimism"],
                    "compliance_program": True,
                    "regulatory_licenses": ["FINCEN", "FCA"]
                },
                {
                    "name": "Tornado Cash",
                    "entity_type": EntityType.MIXER,
                    "risk_level": RiskLevel.CRITICAL,
                    "jurisdictions": ["unknown"],
                    "website": None,
                    "founded_year": 2019,
                    "active_countries": ["global"],
                    "supported_blockchains": ["ethereum", "arbitrum", "optimism", "base"],
                    "compliance_program": False,
                    "regulatory_licenses": []
                },
                {
                    "name": "Uniswap",
                    "entity_type": EntityType.DEFI,
                    "risk_level": RiskLevel.MEDIUM,
                    "jurisdictions": ["US"],
                    "website": "https://uniswap.org",
                    "founded_year": 2018,
                    "active_countries": ["global"],
                    "supported_blockchains": ["ethereum", "arbitrum", "optimism", "base", "polygon"],
                    "compliance_program": True,
                    "regulatory_licenses": []
                }
            ]
            
            # Insert default VASPs
            insert_query = """
            INSERT INTO vasp_registry (
                name, entity_type, risk_level, jurisdictions, website, 
                founded_year, active_countries, supported_blockchains,
                compliance_program, regulatory_licenses
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """
            
            for vasp_data in default_vasps:
                await conn.execute(
                    insert_query,
                    vasp_data["name"],
                    vasp_data["entity_type"].value,
                    vasp_data["risk_level"].value,
                    json.dumps(vasp_data["jurisdictions"]),
                    vasp_data["website"],
                    vasp_data["founded_year"],
                    json.dumps(vasp_data["active_countries"]),
                    json.dumps(vasp_data["supported_blockchains"]),
                    vasp_data["compliance_program"],
                    json.dumps(vasp_data["regulatory_licenses"])
                )
            
            # Load default attribution sources
            default_sources = [
                {
                    "name": "On-Chain Analysis",
                    "source_type": "on_chain",
                    "reliability_score": 0.85,
                    "description": "Direct blockchain transaction analysis"
                },
                {
                    "name": "Exchange Disclosures",
                    "source_type": "exchange_disclosure",
                    "reliability_score": 0.95,
                    "description": "Official exchange address disclosures"
                },
                {
                    "name": "Regulatory Filings",
                    "source_type": "regulatory",
                    "reliability_score": 0.90,
                    "description": "Official regulatory address filings"
                },
                {
                    "name": "Crowdsourced Intelligence",
                    "source_type": "crowdsourced",
                    "reliability_score": 0.60,
                    "description": "Community-contributed address labels"
                }
            ]
            
            insert_source_query = """
            INSERT INTO attribution_sources (
                name, source_type, reliability_score, description
            ) VALUES ($1, $2, $3, $4)
            """
            
            for source_data in default_sources:
                await conn.execute(
                    insert_source_query,
                    source_data["name"],
                    source_data["source_type"],
                    source_data["reliability_score"],
                    source_data["description"]
                )
            
            await conn.commit()
            logger.info(f"Loaded {len(default_vasps)} default VASPs and {len(default_sources)} attribution sources")
            
        except Exception as e:
            logger.error(f"Error loading default VASP data: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()
    
    async def search_vasps(
        self, 
        query: Optional[str] = None,
        filters: Optional[AttributionSearchFilters] = None
    ) -> List[VASP]:
        """Search VASPs with optional filters"""
        
        where_clauses = []
        params = []
        param_count = 0
        
        base_query = """
        SELECT id, name, entity_type, risk_level, jurisdictions, registration_numbers,
               website, description, founded_year, active_countries, supported_blockchains,
               compliance_program, regulatory_licenses, created_at, updated_at
        FROM vasp_registry
        """
        
        if query:
            param_count += 1
            where_clauses.append(f"(name ILIKE ${param_count} OR description ILIKE ${param_count})")
            params.append(f"%{query}%")
        
        if filters:
            if filters.entity_types:
                param_count += 1
                placeholders = ','.join(f'${param_count}' for _ in filters.entity_types)
                where_clauses.append(f"entity_type IN ({placeholders})")
                params.extend([et.value for et in filters.entity_types])
            
            if filters.risk_levels:
                param_count += 1
                placeholders = ','.join(f'${param_count}' for _ in filters.risk_levels)
                where_clauses.append(f"risk_level IN ({placeholders})")
                params.extend([rl.value for rl in filters.risk_levels])
            
            if filters.jurisdictions:
                param_count += 1
                where_clauses.append(f"jurisdictions ? ${param_count}")
                params.append(filters.jurisdictions[0])  # TODO: Handle multiple jurisdictions
            
            if filters.supported_blockchains:
                param_count += 1
                where_clauses.append(f"supported_blockchains ? ${param_count}")
                params.append(filters.supported_blockchains[0])  # TODO: Handle multiple blockchains
        
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)
        
        base_query += " ORDER BY name LIMIT 100"
        
        conn = await get_postgres_connection()
        try:
            rows = await conn.fetch(base_query, *params)
            
            vasps = []
            for row in rows:
                vasp = VASP(
                    id=row['id'],
                    name=row['name'],
                    entity_type=EntityType(row['entity_type']),
                    risk_level=RiskLevel(row['risk_level']),
                    jurisdictions=row['jurisdictions'],
                    registration_numbers=row['registration_numbers'],
                    website=row['website'],
                    description=row['description'],
                    founded_year=row['founded_year'],
                    active_countries=row['active_countries'],
                    supported_blockchains=row['supported_blockchains'],
                    compliance_program=row['compliance_program'],
                    regulatory_licenses=row['regulatory_licenses'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                vasps.append(vasp)
            
            return vasps
            
        except Exception as e:
            logger.error(f"Error searching VASPs: {e}")
            raise
        finally:
            await conn.close()
    
    async def get_vasp_by_id(self, vasp_id: int) -> Optional[VASP]:
        """Get VASP by ID"""
        
        query = """
        SELECT id, name, entity_type, risk_level, jurisdictions, registration_numbers,
               website, description, founded_year, active_countries, supported_blockchains,
               compliance_program, regulatory_licenses, created_at, updated_at
        FROM vasp_registry WHERE id = $1
        """
        
        conn = await get_postgres_connection()
        try:
            row = await conn.fetchrow(query, vasp_id)
            if not row:
                return None
            
            return VASP(
                id=row['id'],
                name=row['name'],
                entity_type=EntityType(row['entity_type']),
                risk_level=RiskLevel(row['risk_level']),
                jurisdictions=row['jurisdictions'],
                registration_numbers=row['registration_numbers'],
                website=row['website'],
                description=row['description'],
                founded_year=row['founded_year'],
                active_countries=row['active_countries'],
                supported_blockchains=row['supported_blockchains'],
                compliance_program=row['compliance_program'],
                regulatory_licenses=row['regulatory_licenses'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
        except Exception as e:
            logger.error(f"Error getting VASP by ID: {e}")
            raise
        finally:
            await conn.close()
    
    async def get_attribution_sources(self) -> List[Dict]:
        """Get all attribution sources"""
        
        query = """
        SELECT id, name, source_type, reliability_score, description, url,
               api_endpoint, authentication_required, rate_limit_per_hour, last_updated
        FROM attribution_sources
        ORDER BY reliability_score DESC
        """
        
        conn = await get_postgres_connection()
        try:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting attribution sources: {e}")
            raise
        finally:
            await conn.close()
    
    async def add_vasp(self, vasp: VASP) -> VASP:
        """Add a new VASP to the registry"""
        
        insert_query = """
        INSERT INTO vasp_registry (
            name, entity_type, risk_level, jurisdictions, registration_numbers,
            website, description, founded_year, active_countries, supported_blockchains,
            compliance_program, regulatory_licenses
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING id, created_at, updated_at
        """
        
        conn = await get_postgres_connection()
        try:
            result = await conn.fetchrow(
                insert_query,
                vasp.name,
                vasp.entity_type.value,
                vasp.risk_level.value,
                json.dumps(vasp.jurisdictions),
                json.dumps(vasp.registration_numbers),
                vasp.website,
                vasp.description,
                vasp.founded_year,
                json.dumps(vasp.active_countries),
                json.dumps(vasp.supported_blockchains),
                vasp.compliance_program,
                json.dumps(vasp.regulatory_licenses)
            )
            
            vasp.id = result['id']
            vasp.created_at = result['created_at']
            vasp.updated_at = result['updated_at']
            
            await conn.commit()
            logger.info(f"Added VASP: {vasp.name}")
            return vasp
            
        except Exception as e:
            logger.error(f"Error adding VASP: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()


# Global VASP registry instance
_vasp_registry = None

def get_vasp_registry() -> VASPRegistry:
    """Get the global VASP registry instance"""
    global _vasp_registry
    if _vasp_registry is None:
        _vasp_registry = VASPRegistry()
    return _vasp_registry
