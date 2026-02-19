"""
Jackdaw Sentry - Sanctions List Screening and Management
Comprehensive sanctions screening for OFAC, UN, EU, UK, and other international sanctions lists
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import re

from src.api.database import get_neo4j_session, get_redis_connection
from src.api.config import settings

logger = logging.getLogger(__name__)


class SanctionsListType(Enum):
    """Sanctions list types"""
    OFAC = "ofac"  # US Office of Foreign Assets Control
    UN = "un"  # United Nations Security Council
    EU = "eu"  # European Union
    UK = "uk"  # United Kingdom
    HMT = "hmt"  # UK HM Treasury
    OFSI = "ofsi"  # UK Office of Financial Sanctions Implementation
    BIS = "bis"  # US Bureau of Industry and Security
    STATE = "state"  # US State Department
    TREASURY = "treasury"  # US Treasury
    JAPAN = "japan"  # Japan Ministry of Finance
    CANADA = "canada"  # Canada Department of Finance
    AUSTRALIA = "australia"  # Australian Department of Foreign Affairs
    SWITZERLAND = "switzerland"  # Swiss State Secretariat for Economic Affairs
    CUSTOM = "custom"  # Custom sanctions lists


class SanctionsEntityType(Enum):
    """Sanctions entity types"""
    INDIVIDUAL = "individual"
    ENTITY = "entity"
    VESSEL = "vessel"
    AIRCRAFT = "aircraft"
    ORGANIZATION = "organization"
    POLITICAL_PARTY = "political_party"
    TERRORIST_ORG = "terrorist_organization"
    CYBER_THREAT_ACTOR = "cyber_threat_actor"


class SanctionsProgramType(Enum):
    """Sanctions program types"""
    TERRORISM = "terrorism"
    NUCLEAR_PROLIFERATION = "nuclear_proliferation"
    HUMAN_RIGHTS = "human_rights"
    CYBER = "cyber"
    DRUG_TRAFFICKING = "drug_trafficking"
    MONEY_LAUNDERING = "money_laundering"
    WEAPONS = "weapons"
    CORRUPTION = "corruption"
    REGIONAL = "regional"
    COUNTER_NARCOTICS = "counter_narcotics"
    COUNTER_TERRORISM = "counter_terrorism"
    MAGNITSKY = "magnitsky"
    IRAN = "iran"
    NORTH_KOREA = "north_korea"
    RUSSIA = "russia"
    SYRIA = "syria"
    VENEZUELA = "venezuela"
    YEMEN = "yemen"
    MYANMAR = "myanmar"
    BELARUS = "belarus"
    SUDAN = "sudan"
    LIBERIA = "liberia"
    SOMALIA = "somalia"
    LEBANON = "lebanon"
    ZIMBABWE = "zimbabwe"


@dataclass
class SanctionsEntity:
    """Sanctions entity representation"""
    entity_id: str
    list_type: SanctionsListType
    entity_type: SanctionsEntityType
    primary_name: str
    aliases: List[str] = field(default_factory=list)
    addresses: List[str] = field(default_factory=list)
    nationalities: List[str] = field(default_factory=list)
    dates_of_birth: List[str] = field(default_factory=list)
    places_of_birth: List[str] = field(default_factory=list)
    identification_numbers: Dict[str, List[str]] = field(default_factory=dict)
    programs: List[SanctionsProgramType] = field(default_factory=list)
    sanctions_date: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)
    additional_info: Dict[str, Any] = field(default_factory=dict)
    risk_score: float = 0.0
    confidence: float = 0.0


@dataclass
class SanctionsMatch:
    """Sanctions match result"""
    entity_id: str
    matched_address: str
    matched_field: str  # name, address, identification, etc.
    match_score: float
    confidence: float
    list_type: SanctionsListType
    entity_type: SanctionsEntityType
    entity_name: str
    aliases: List[str]
    programs: List[SanctionsProgramType]
    sanctions_date: Optional[datetime]
    last_updated: datetime
    risk_level: str
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SanctionsScreeningResult:
    """Sanctions screening result"""
    address: str
    blockchain: str
    screened_at: datetime
    matches: List[SanctionsMatch]
    overall_risk_score: float
    risk_level: str
    recommendations: List[str] = field(default_factory=list)
    screening_duration: timedelta = field(default_factory=lambda: timedelta(0))
    metadata: Dict[str, Any] = field(default_factory=dict)


class SanctionsManager:
    """Sanctions list management and screening system"""
    
    def __init__(self):
        self.sanctions_lists = {}
        self.entity_index = {}  # For fast lookups
        self.address_index = {}  # Address-based index
        self.name_index = {}  # Name-based index
        self.id_index = {}  # ID-based index
        
        # Screening thresholds
        self.min_match_score = 0.7
        self.high_risk_threshold = 0.85
        self.max_cache_age = timedelta(hours=24)
        
        # Cache for screening results
        self.screening_cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Initialize with sample data
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize with sample sanctions data"""
        # Sample OFAC SDN list entities
        sample_entities = [
            {
                "entity_id": "OFAC-12345",
                "list_type": SanctionsListType.OFAC,
                "entity_type": SanctionsEntityType.INDIVIDUAL,
                "primary_name": "AL QAEDA",
                "aliases": ["Al Qa'eda", "Al-Qaeda"],
                "addresses": ["123 Main St", "456 Oak Ave"],
                "nationalities": ["Afghanistan"],
                "programs": [SanctionsProgramType.TERRORISM, SanctionsProgramType.COUNTER_TERRORISM],
                "sanctions_date": datetime(2001, 10, 12),
                "risk_score": 0.95
            },
            {
                "entity_id": "OFAC-67890",
                "list_type": SanctionsListType.OFAC,
                "entity_type": SanctionsEntityType.ENTITY,
                "primary_name": "IRANIAN REVOLUTIONARY GUARD CORPS",
                "aliases": ["IRGC", "Revolutionary Guards"],
                "addresses": ["Tehran, Iran"],
                "programs": [SanctionsProgramType.IRAN, SanctionsProgramType.TERRORISM],
                "sanctions_date": datetime(2019, 10, 31),
                "risk_score": 0.90
            },
            {
                "entity_id": "UN-11111",
                "list_type": SanctionsListType.UN,
                "entity_type": SanctionsEntityType.INDIVIDUAL,
                "primary_name": "JOHN DOE",
                "aliases": ["John Smith", "J. Doe"],
                "addresses": ["789 Pine St", "321 Elm Rd"],
                "identification_numbers": {
                    "passport": ["A12345678"],
                    "ssn": ["123-45-6789"]
                },
                "programs": [SanctionsProgramType.TERRORISM],
                "sanctions_date": datetime(2020, 1, 15),
                "risk_score": 0.85
            }
        ]
        
        # Load sample entities
        for entity_data in sample_entities:
            entity = SanctionsEntity(**entity_data)
            self._add_entity_to_indexes(entity)
    
    def _add_entity_to_indexes(self, entity: SanctionsEntity):
        """Add entity to all indexes for fast lookups"""
        # Add to main list
        list_key = entity.list_type.value
        if list_key not in self.sanctions_lists:
            self.sanctions_lists[list_key] = []
        self.sanctions_lists[list_key].append(entity)
        
        # Add to ID index
        self.id_index[entity.entity_id] = entity
        
        # Add to name index (normalized)
        normalized_name = self._normalize_text(entity.primary_name)
        if normalized_name not in self.name_index:
            self.name_index[normalized_name] = []
        self.name_index[normalized_name].append(entity)
        
        # Add aliases to name index
        for alias in entity.aliases:
            normalized_alias = self._normalize_text(alias)
            if normalized_alias not in self.name_index:
                self.name_index[normalized_alias] = []
            self.name_index[normalized_alias].append(entity)
        
        # Add addresses to address index
        for address in entity.addresses:
            normalized_address = self._normalize_text(address)
            if normalized_address not in self.address_index:
                self.address_index[normalized_address] = []
            self.address_index[normalized_address].append(entity)
        
        # Add identification numbers to ID index
        for id_type, ids in entity.identification_numbers.items():
            for id_value in ids:
                normalized_id = self._normalize_text(id_value)
                if normalized_id not in self.id_index:
                    self.id_index[normalized_id] = []
                self.id_index[normalized_id].append(entity)
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching"""
        if not text:
            return ""
        
        # Convert to lowercase and remove special characters
        normalized = text.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()
    
    async def screen_address(self, address: str, blockchain: str = None) -> SanctionsScreeningResult:
        """Screen an address against all sanctions lists"""
        try:
            start_time = datetime.now(timezone.utc)
            
            # Check cache first
            cache_key = f"{address}_{blockchain}" if blockchain else address
            cached_result = await self.get_cached_screening(cache_key)
            if cached_result:
                return cached_result
            
            matches = []
            normalized_address = self._normalize_text(address)
            
            # Search in address index
            if normalized_address in self.address_index:
                for entity in self.address_index[normalized_address]:
                    match = self._create_address_match(entity, address, normalized_address)
                    if match:
                        matches.append(match)
            
            # Search in name index (in case address looks like a name)
            if normalized_address in self.name_index:
                for entity in self.name_index[normalized_address]:
                    match = self._create_name_match(entity, address, normalized_address)
                    if match:
                        matches.append(match)
            
            # Calculate overall risk score and level
            overall_risk_score = max([match.risk_score for match in matches]) if matches else 0.0
            risk_level = self._determine_risk_level(overall_risk_score)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(matches, risk_level)
            
            # Create screening result
            screening_duration = datetime.now(timezone.utc) - start_time
            result = SanctionsScreeningResult(
                address=address,
                blockchain=blockchain or "unknown",
                screened_at=start_time,
                matches=matches,
                overall_risk_score=overall_risk_score,
                risk_level=risk_level,
                recommendations=recommendations,
                screening_duration=screening_duration,
                metadata={
                    'total_lists_checked': len(self.sanctions_lists),
                    'total_entities_in_lists': sum(len(entities) for entities in self.sanctions_lists.values())
                }
            )
            
            # Cache result
            await self.cache_screening_result(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error screening address {address}: {e}")
            return SanctionsScreeningResult(
                address=address,
                blockchain=blockchain or "unknown",
                screened_at=datetime.now(timezone.utc),
                matches=[],
                overall_risk_score=0.0,
                risk_level="low",
                recommendations=[],
                metadata={'error': str(e)}
            )
    
    def _create_address_match(self, entity: SanctionsEntity, address: str, normalized_address: str) -> Optional[SanctionsMatch]:
        """Create a match for address"""
        # Calculate match score based on exact match
        match_score = 1.0 if normalized_address in self.address_index else 0.0
        
        if match_score >= self.min_match_score:
            return SanctionsMatch(
                entity_id=entity.entity_id,
                matched_address=address,
                matched_field="address",
                match_score=match_score,
                confidence=0.95,  # High confidence for exact address match
                list_type=entity.list_type,
                entity_type=entity.entity_type,
                entity_name=entity.primary_name,
                aliases=entity.aliases,
                programs=entity.programs,
                sanctions_date=entity.sanctions_date,
                last_updated=entity.last_updated,
                risk_level=self._determine_risk_level(entity.risk_score),
                recommendations=self._generate_entity_recommendations(entity),
                metadata={
                    'match_type': 'exact_address',
                    'entity_risk_score': entity.risk_score
                }
            )
        
        return None
    
    def _create_name_match(self, entity: SanctionsEntity, address: str, normalized_address: str) -> Optional[SanctionsMatch]:
        """Create a match for name (when address looks like a name)"""
        # Calculate match score based on name similarity
        match_score = 0.7  # Lower confidence for name-based address match
        
        if match_score >= self.min_match_score:
            return SanctionsMatch(
                entity_id=entity.entity_id,
                matched_address=address,
                matched_field="name_as_address",
                match_score=match_score,
                confidence=0.6,  # Lower confidence for name-based match
                list_type=entity.list_type,
                entity_type=entity.entity_type,
                entity_name=entity.primary_name,
                aliases=entity.aliases,
                programs=entity.programs,
                sanctions_date=entity.sanctions_date,
                last_updated=entity.last_updated,
                risk_level=self._determine_risk_level(entity.risk_score * 0.8),  # Lower risk for name-based match
                recommendations=self._generate_entity_recommendations(entity),
                metadata={
                    'match_type': 'name_as_address',
                    'entity_risk_score': entity.risk_score
                }
            )
        
        return None
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level from score"""
        if risk_score >= 0.9:
            return "critical"
        elif risk_score >= 0.8:
            return "high"
        elif risk_score >= 0.6:
            return "medium"
        elif risk_score >= 0.3:
            return "low"
        else:
            return "very_low"
    
    def _generate_recommendations(self, matches: List[SanctionsMatch], risk_level: str) -> List[str]:
        """Generate recommendations based on matches and risk level"""
        recommendations = []
        
        if not matches:
            recommendations.append("No sanctions matches found")
            return recommendations
        
        if risk_level in ["critical", "high"]:
            recommendations.append("IMMEDIATE INVESTIGATION REQUIRED")
            recommendations.append("Freeze all associated assets")
            recommendations.append("Report to compliance officer")
            recommendations.append("Enhanced monitoring recommended")
            
            # Specific recommendations based on programs
            programs = set()
            for match in matches:
                programs.update(match.programs)
            
            if SanctionsProgramType.TERRORISM in programs:
                recommendations.append("Terrorism-related sanctions - highest priority")
            if SanctionsProgramType.NUCLEAR_PROLIFERATION in programs:
                recommendations.append("Nuclear proliferation sanctions - highest priority")
            if SanctionsProgramType.HUMAN_RIGHTS in programs:
                recommendations.append("Human rights violations - high priority")
        
        elif risk_level == "medium":
            recommendations.append("Enhanced monitoring required")
            recommendations.append("Review transaction patterns")
            recommendations.append("Consider additional verification")
        
        elif risk_level == "low":
            recommendations.append("Standard monitoring sufficient")
            recommendations.append("Periodic review recommended")
        
        return recommendations
    
    def _generate_entity_recommendations(self, entity: SanctionsEntity) -> List[str]:
        """Generate recommendations for a specific entity"""
        recommendations = []
        
        # Recommendations based on entity type
        if entity.entity_type == SanctionsEntityType.INDIVIDUAL:
            recommendations.append("Individual sanctions - verify identity")
        elif entity.entity_type == SanctionsEntityType.ENTITY:
            recommendations.append("Entity sanctions - verify corporate structure")
        elif entity.entity_type == SanctionsEntityType.VESSEL:
            recommendations.append("Vessel sanctions - monitor maritime activity")
        elif entity.entity_type == SanctionsEntityType.AIRCRAFT:
            recommendations.append("Aircraft sanctions - monitor aviation activity")
        
        # Recommendations based on programs
        if SanctionsProgramType.TERRORISM in entity.programs:
            recommendations.append("Terrorism-related - highest priority")
        elif SanctionsProgramType.NUCLEAR_PROLIFERATION in entity.programs:
            recommendations.append("Nuclear proliferation - highest priority")
        elif SanctionsProgramType.HUMAN_RIGHTS in entity.programs:
            recommendations.append("Human rights violations - high priority")
        
        return recommendations
    
    async def screen_transaction(self, from_address: str, to_address: str, blockchain: str, amount: float = 0.0) -> Dict[str, Any]:
        """Screen a transaction against sanctions lists"""
        try:
            # Screen both addresses
            from_screening = await self.screen_address(from_address, blockchain)
            to_screening = await self.screen_address(to_address, blockchain)
            
            # Combine results
            all_matches = from_screening.matches + to_screening.matches
            overall_risk_score = max(from_screening.overall_risk_score, to_screening.overall_risk_score)
            
            # Determine overall risk level
            if overall_risk_score >= 0.9:
                risk_level = "critical"
            elif overall_risk_score >= 0.8:
                risk_level = "high"
            elif overall_risk_score >= 0.6:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            # Generate transaction-specific recommendations
            recommendations = []
            if all_matches:
                recommendations.append("TRANCTION INVOLVES SANCTIONED ENTITY")
                if risk_level in ["critical", "high"]:
                    recommendations.append("BLOCK TRANSACTION IMMEDIATELY")
                    recommendations.append("REPORT TO COMPLIANCE OFFICER")
                else:
                    recommendations.append("ENHANCED MONITORING REQUIRED")
            else:
                recommendations.append("No sanctions matches found")
            
            # Add amount-based recommendations
            if amount > 10000:  # High value threshold
                recommendations.append("High-value transaction - additional verification required")
            
            return {
                'from_address': from_address,
                'to_address': to_address,
                'blockchain': blockchain,
                'amount': amount,
                'screening_timestamp': datetime.now(timezone.utc).isoformat(),
                'from_address_screening': {
                    'matches': len(from_screening.matches),
                    'risk_score': from_screening.overall_risk_score,
                    'risk_level': from_screening.risk_level
                },
                'to_address_screening': {
                    'matches': len(to_screening.matches),
                    'risk_score': to_screening.overall_risk_score,
                    'risk_level': to_screening.risk_level
                },
                'overall_risk_score': overall_risk_score,
                'risk_level': risk_level,
                'total_matches': len(all_matches),
                'matches': [match.__dict__ for match in all_matches],
                'recommendations': recommendations,
                'screening_duration': (from_screening.screening_duration + to_screening.screening_duration).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Error screening transaction: {e}")
            return {
                'error': str(e),
                'screening_timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def update_sanctions_list(self, list_type: SanctionsListType, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update a sanctions list with new entities"""
        try:
            updated_count = 0
            errors = []
            
            # Clear existing list
            list_key = list_type.value
            if list_key in self.sanctions_lists:
                del self.sanctions_lists[list_key]
            
            # Clear indexes
            self._clear_indexes()
            
            # Add new entities
            for entity_data in entities:
                try:
                    # Convert data types
                    entity_data['list_type'] = list_type
                    entity_data['entity_type'] = SanctionsEntityType(entity_data.get('entity_type', 'individual'))
                    entity_data['programs'] = [SanctionsProgramType(p) for p in entity_data.get('programs', [])]
                    
                    if 'sanctions_date' in entity_data and entity_data['sanctions_date']:
                        entity_data['sanctions_date'] = datetime.fromisoformat(entity_data['sanctions_date'])
                    
                    entity = SanctionsEntity(**entity_data)
                    self._add_entity_to_indexes(entity)
                    updated_count += 1
                    
                except Exception as e:
                    errors.append(f"Error processing entity {entity_data.get('entity_id', 'unknown')}: {e}")
            
            # Cache update
            await self.cache_sanctions_data()
            
            return {
                'list_type': list_type.value,
                'updated_count': updated_count,
                'total_entities': updated_count,
                'errors': errors,
                'update_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating sanctions list {list_type}: {e}")
            return {'error': str(e)}
    
    def _clear_indexes(self):
        """Clear all indexes"""
        self.entity_index.clear()
        self.address_index.clear()
        self.name_index.clear()
        self.id_index.clear()
    
    async def get_sanctions_statistics(self) -> Dict[str, Any]:
        """Get sanctions list statistics"""
        try:
            stats = {
                'total_lists': len(self.sanctions_lists),
                'total_entities': sum(len(entities) for entities in self.sanctions_lists.values()),
                'list_breakdown': {},
                'entity_type_breakdown': {},
                'program_breakdown': {},
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            # List breakdown
            for list_name, entities in self.sanctions_lists.items():
                stats['list_breakdown'][list_name] = len(entities)
            
            # Entity type breakdown
            entity_type_counts = {}
            for entities in self.sanctions_lists.values():
                for entity in entities:
                    entity_type = entity.entity_type.value
                    entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1
            stats['entity_type_breakdown'] = entity_type_counts
            
            # Program breakdown
            program_counts = {}
            for entities in self.sanctions_lists.values():
                for entity in entities:
                    for program in entity.programs:
                        program_name = program.value
                        program_counts[program_name] = program_counts.get(program_name, 0) + 1
            stats['program_breakdown'] = program_counts
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting sanctions statistics: {e}")
            return {'error': str(e)}
    
    async def search_sanctions_entities(self, query: str, list_type: SanctionsListType = None) -> List[Dict[str, Any]]:
        """Search sanctions entities by name or other criteria"""
        try:
            normalized_query = self._normalize_text(query)
            results = []
            
            # Search in name index
            if normalized_query in self.name_index:
                for entity in self.name_index[normalized_query]:
                    if list_type is None or entity.list_type == list_type:
                        results.append({
                            'entity_id': entity.entity_id,
                            'list_type': entity.list_type.value,
                            'entity_type': entity.entity_type.value,
                            'primary_name': entity.primary_name,
                            'aliases': entity.aliases,
                            'programs': [p.value for p in entity.programs],
                            'sanctions_date': entity.sanctions_date.isoformat() if entity.sanctions_date else None,
                            'risk_score': entity.risk_score
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching sanctions entities: {e}")
            return []
    
    async def cache_screening_result(self, key: str, result: SanctionsScreeningResult):
        """Cache screening result in Redis"""
        try:
            async with get_redis_connection() as redis:
                # Convert to dict for JSON serialization
                result_dict = {
                    'address': result.address,
                    'blockchain': result.blockchain,
                    'screened_at': result.screened_at.isoformat(),
                    'matches': [match.__dict__ for match in result.matches],
                    'overall_risk_score': result.overall_risk_score,
                    'risk_level': result.risk_level,
                    'recommendations': result.recommendations,
                    'screening_duration': result.screening_duration.total_seconds(),
                    'metadata': result.metadata
                }
                
                await redis.setex(f"sanctions_screening:{key}", self.cache_ttl, json.dumps(result_dict))
        except Exception as e:
            logger.error(f"Error caching screening result: {e}")
    
    async def get_cached_screening(self, key: str) -> Optional[SanctionsScreeningResult]:
        """Get cached screening result from Redis"""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(f"sanctions_screening:{key}")
                if cached:
                    result_dict = json.loads(cached)
                    return SanctionsScreeningResult(
                        address=result_dict['address'],
                        blockchain=result_dict['blockchain'],
                        screened_at=datetime.fromisoformat(result_dict['screened_at']),
                        matches=[SanctionsMatch(**match) for match in result_dict['matches']],
                        overall_risk_score=result_dict['overall_risk_score'],
                        risk_level=result_dict['risk_level'],
                        recommendations=result_dict['recommendations'],
                        screening_duration=timedelta(seconds=result_dict['screening_duration']),
                        metadata=result_dict['metadata']
                    )
        except Exception as e:
            logger.error(f"Error getting cached screening result: {e}")
        
        return None
    
    async def cache_sanctions_data(self):
        """Cache sanctions data in Redis"""
        try:
            async with get_redis_connection() as redis:
                # Cache basic statistics
                stats = await self.get_sanctions_statistics()
                await redis.setex("sanctions_stats", 3600, json.dumps(stats))
        except Exception as e:
            logger.error(f"Error caching sanctions data: {e}")


# Global sanctions manager instance
_sanctions_manager: Optional[SanctionsManager] = None


def get_sanctions_manager() -> SanctionsManager:
    """Get global sanctions manager instance"""
    global _sanctions_manager
    if _sanctions_manager is None:
        _sanctions_manager = SanctionsManager()
    return _sanctions_manager
