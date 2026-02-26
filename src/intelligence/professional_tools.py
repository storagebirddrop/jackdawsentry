"""
Jackdaw Sentry - Professional Tools Integration
Integration with professional blockchain analysis platforms
Inspired by On-Chain-Investigations-Tools-List and professional clusterers
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import aiohttp

from src.api.config import settings
from src.api.database import get_neo4j_session
from src.api.database import get_redis_connection
from .anchain_integration import AnChainIntegration
from .integration_manager import IntegrationManager

logger = logging.getLogger(__name__)


class ProfessionalToolType(Enum):
    """Professional tool types"""

    CHAINALYSIS = "chainalysis"
    ELLIPTIC = "elliptic"
    CIPHERBLADE = "cipherblade"
    ARKHAM = "arkham"
    CIPHERTRACE = "ciphertrace"
    TRM_LABS = "trm_labs"
    SCORECHAIN = "scorechain"
    CRYSTAL_BLOCKCHAIN = "crystal_blockchain"
    AMLBOT = "amlbot"
    MISTTRACK = "misttrack"
    COINPATH = "coinpath"
    STORYLINE = "storyline"
    ANCHAIN_AI = "anchain_ai"


@dataclass
class ProfessionalToolConfig:
    """Professional tool configuration"""

    tool_type: ProfessionalToolType
    name: str
    api_endpoint: str
    api_key: str = ""
    rate_limit: int = 100  # requests per hour
    timeout: int = 30  # seconds
    cache_ttl: int = 3600  # 1 hour
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClusterResult:
    """Address clustering result"""

    cluster_id: str
    addresses: List[str]
    confidence: float
    labels: List[str]
    risk_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LabelResult:
    """Address labeling result"""

    address: str
    labels: List[str]
    categories: List[str]
    risk_level: str
    confidence: float
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ChainalysisIntegration:
    """Chainalysis Reactor API integration"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.CHAINALYSIS_API_KEY
        self.base_url = "https://reactor.chainalysis.com/api"
        self.session = None
        self.config = ProfessionalToolConfig(
            tool_type=ProfessionalToolType.CHAINALYSIS,
            name="Chainalysis Reactor",
            api_endpoint=self.base_url,
            api_key=self.api_key,
            rate_limit=1000,
            timeout=30,
        )

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def analyze_address(self, address: str) -> Dict[str, Any]:
        """Analyze address using Chainalysis"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Chainalysis Reactor endpoint for address analysis
            url = f"{self.base_url}/v2/entities"
            payload = {
                "entities": [
                    {"address": address, "blockchain": "ethereum"}  # or bitcoin, etc.
                ]
            }

            async with self.session.post(
                url, headers=headers, json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "address": address,
                        "chainalysis_data": data,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "chainalysis_reactor",
                    }
                else:
                    error_text = await response.text()
                    raise Exception(
                        f"Chainalysis API error: {response.status} - {error_text}"
                    )

        except Exception as e:
            logger.error(f"Chainalysis analysis failed: {e}")
            return {
                "address": address,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "chainalysis_reactor",
            }

    async def get_address_labels(self, address: str) -> LabelResult:
        """Get address labels from Chainalysis"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            url = f"{self.base_url}/v2/addresses/{address}/labels"

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return LabelResult(
                        address=address,
                        labels=data.get("labels", []),
                        categories=data.get("categories", []),
                        risk_level=data.get("riskLevel", "unknown"),
                        confidence=data.get("confidence", 0.0),
                        source="chainalysis_reactor",
                        metadata=data,
                    )
                else:
                    error_text = await response.text()
                    raise Exception(
                        f"Chainalysis labels error: {response.status} - {error_text}"
                    )

        except Exception as e:
            logger.error(f"Chainalysis labels failed: {e}")
            return LabelResult(
                address=address,
                labels=[],
                categories=[],
                risk_level="unknown",
                confidence=0.0,
                source="chainalysis_reactor",
                metadata={"error": str(e)},
            )


class EllipticIntegration:
    """Elliptic API integration"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.ELLIPTIC_API_KEY
        self.base_url = "https://api.elliptic.co"
        self.session = None
        self.config = ProfessionalToolConfig(
            tool_type=ProfessionalToolType.ELLIPTIC,
            name="Elliptic",
            api_endpoint=self.base_url,
            api_key=self.api_key,
            rate_limit=500,
            timeout=30,
        )

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def analyze_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Analyze transaction using Elliptic"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            url = f"{self.base_url}/v4/transactions"
            payload = {
                "txHash": tx_hash,
                "include": ["riskScore", "addresses", "blockchain"],
            }

            async with self.session.post(
                url, headers=headers, json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "tx_hash": tx_hash,
                        "elliptic_data": data,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "elliptic",
                    }
                else:
                    error_text = await response.text()
                    raise Exception(
                        f"Elliptic API error: {response.status} - {error_text}"
                    )

        except Exception as e:
            logger.error(f"Elliptic analysis failed: {e}")
            return {
                "tx_hash": tx_hash,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "elliptic",
            }


class CipherBladeIntegration:
    """CipherBlade API integration"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.CIPHERBLADE_API_KEY
        self.base_url = "https://api.cipherblade.com"
        self.session = None
        self.config = ProfessionalToolConfig(
            tool_type=ProfessionalToolType.CIPHERBLADE,
            name="CipherBlade",
            api_endpoint=self.base_url,
            api_key=self.api_key,
            rate_limit=1000,
            timeout=30,
        )

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def investigate_address(self, address: str) -> Dict[str, Any]:
        """Investigate address using CipherBlade"""
        try:
            headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}

            url = f"{self.base_url}/api/v1/addresses/{address}/investigate"

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "address": address,
                        "cipherblade_data": data,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "cipherblade",
                    }
                else:
                    error_text = await response.text()
                    raise Exception(
                        f"CipherBlade API error: {response.status} - {error_text}"
                    )

        except Exception as e:
            logger.error(f"CipherBlade investigation failed: {e}")
            return {
                "address": address,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "cipherblade",
            }


class ArkhamIntegration:
    """Arkham Intelligence API integration"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.ARKHAM_API_KEY
        self.base_url = "https://api.arkhamintelligence.com"
        self.session = None
        self.config = ProfessionalToolConfig(
            tool_type=ProfessionalToolType.ARKHAM,
            name="Arkham Intelligence",
            api_endpoint=self.base_url,
            api_key=self.api_key,
            rate_limit=500,
            timeout=30,
        )

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_entity_graph(self, address: str) -> Dict[str, Any]:
        """Get entity graph from Arkham"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            url = f"{self.base_url}/v1/entity/graph"
            payload = {
                "address": address,
                "depth": 2,
                "include": ["transactions", "labels", "risk_score"],
            }

            async with self.session.post(
                url, headers=headers, json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "address": address,
                        "arkham_data": data,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "arkham_intelligence",
                    }
                else:
                    error_text = await response.text()
                    raise Exception(
                        f"Arkham API error: {response.status} - {error_text}"
                    )

        except Exception as e:
            logger.error(f"Arkham graph analysis failed: {e}")
            return {
                "address": address,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "arkham_intelligence",
            }


class EtherscanLabelsImporter:
    """Etherscan labels dataset importer"""

    def __init__(self):
        self.labels_cache = {}
        self.phish_hack_labels = {}
        self.cache_ttl = 86400  # 24 hours
        self.last_imported_at: Optional[datetime] = None

    async def import_labels(self) -> Dict[str, Any]:
        """Import Etherscan labels dataset"""
        try:
            # Import from GitHub repository
            # Source: https://github.com/brianleect/etherscan-labels
            labels_url = "https://raw.githubusercontent.com/brianleect/etherscan-labels/main/data/labels.json"
            phish_hack_url = "https://raw.githubusercontent.com/brianleect/etherscan-labels/main/data/phish-hack.csv"

            async with aiohttp.ClientSession() as session:
                # Import labels
                async with session.get(labels_url) as response:
                    if response.status == 200:
                        labels_data = await response.json()
                        for label in labels_data:
                            address = label.get("address", "").lower()
                            if address:
                                self.labels_cache[address] = label

                # Import phishing/hack labels
                async with session.get(phish_hack_url) as response:
                    if response.status == 200:
                        csv_data = await response.text()
                        lines = csv_data.strip().split("\n")[1:]  # Skip header
                        for line in lines:
                            if line.strip():
                                parts = line.split(",")
                                if len(parts) >= 2:
                                    address = parts[0].strip().lower()
                                    label_type = parts[1].strip()
                                    if address:
                                        self.phish_hack_labels[address] = {
                                            "type": label_type,
                                            "category": "phishing_hack",
                                            "risk_level": "high",
                                        }

            self.last_imported_at = datetime.now(timezone.utc)
            return {
                "labels_imported": len(self.labels_cache),
                "phish_hack_imported": len(self.phish_hack_labels),
                "timestamp": self.last_imported_at.isoformat(),
                "source": "etherscan_labels",
            }

        except Exception as e:
            logger.error(f"Etherscan labels import failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "etherscan_labels",
            }

    async def get_address_labels(self, address: str) -> LabelResult:
        """Get labels for an address from imported dataset"""
        address_lower = address.lower()

        labels = []
        categories = []
        risk_level = "low"
        confidence = 0.5

        # Check regular labels
        if address_lower in self.labels_cache:
            label_data = self.labels_cache[address_lower]
            labels = [label_data.get("label", "unknown")]
            categories = [label_data.get("category", "unknown")]
            risk_level = label_data.get("risk_level", "low")
            confidence = 0.8

        # Check phishing/hack labels
        if address_lower in self.phish_hack_labels:
            phish_data = self.phish_hack_labels[address_lower]
            labels.append(phish_data.get("type", "phishing"))
            categories.append("phishing_hack")
            risk_level = "high"
            confidence = 0.9

        return LabelResult(
            address=address,
            labels=labels,
            categories=categories,
            risk_level=risk_level,
            confidence=confidence,
            source="etherscan_labels",
            metadata={
                "import_timestamp": datetime.now(timezone.utc).isoformat(),
                "dataset_version": "latest",
            },
        )


class ProfessionalToolsManager:
    """Manager for professional blockchain analysis tools"""

    def __init__(self):
        self.tools = {}
        self.enabled_tools = set()
        self.etherscan_labels = EtherscanLabelsImporter()

        # Initialize tools based on configuration
        self._initialize_tools()

    def _initialize_tools(self):
        """Initialize professional tools"""
        # Chainalysis
        if settings.CHAINALYSIS_API_KEY:
            self.tools[ProfessionalToolType.CHAINALYSIS] = ChainalysisIntegration()
            self.enabled_tools.add(ProfessionalToolType.CHAINALYSIS)

        # Elliptic
        if settings.ELLIPTIC_API_KEY:
            self.tools[ProfessionalToolType.ELLIPTIC] = EllipticIntegration()
            self.enabled_tools.add(ProfessionalToolType.ELLIPTIC)

        # CipherBlade
        if settings.CIPHERBLADE_API_KEY:
            self.tools[ProfessionalToolType.CIPHERBLADE] = CipherBladeIntegration()
            self.enabled_tools.add(ProfessionalToolType.CIPHERBLADE)

        # Arkham
        if settings.ARKHAM_API_KEY:
            self.tools[ProfessionalToolType.ARKHAM] = ArkhamIntegration()
            self.enabled_tools.add(ProfessionalToolType.ARKHAM)

        # AnChain.ai — free-tier AML/sanctions + IP screening
        if getattr(settings, "ANCHAIN_API_KEY", None):
            self.tools[ProfessionalToolType.ANCHAIN_AI] = AnChainIntegration()
            self.enabled_tools.add(ProfessionalToolType.ANCHAIN_AI)

        logger.info(f"Initialized professional tools: {list(self.enabled_tools)}")

    async def analyze_with_all_tools(self, address: str) -> Dict[str, Any]:
        """Analyze address with all available professional tools"""
        results = {
            "address": address,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_results": {},
            "combined_assessment": {},
            "evidence": [],
        }

        # Analyze with each enabled tool
        for tool_type in self.enabled_tools:
            try:
                tool = self.tools[tool_type]

                if tool_type == ProfessionalToolType.CHAINALYSIS:
                    async with tool:
                        result = await tool.analyze_address(address)
                        results["tool_results"]["chainalysis"] = result

                elif tool_type == ProfessionalToolType.ELLIPTIC:
                    async with tool:
                        result = await tool.analyze_transaction(address)  # Placeholder
                        results["tool_results"]["elliptic"] = result

                elif tool_type == ProfessionalToolType.CIPHERBLADE:
                    async with tool:
                        result = await tool.investigate_address(address)
                        results["tool_results"]["cipherblade"] = result

                elif tool_type == ProfessionalToolType.ARKHAM:
                    async with tool:
                        result = await tool.get_entity_graph(address)
                        results["tool_results"]["arkham"] = result

                elif tool_type == ProfessionalToolType.ANCHAIN_AI:
                    async with tool:
                        # Detect blockchain for address
                        blockchain = IntegrationManager.detect_chain_for_address(address) or "ethereum"
                        screening = await tool.screen_address(address, blockchain)
                        
                        # Safely serialize screening result
                        try:
                            if hasattr(screening, '__dict__'):
                                anchain_data = screening.__dict__
                            elif isinstance(screening, dict):
                                anchain_data = screening
                            else:
                                anchain_data = {"error": "Unexpected result type", "type": str(type(screening))}
                        except Exception as serialize_error:
                            anchain_data = {"error": f"Serialization failed: {serialize_error}"}
                        
                        result = {
                            "address": address,
                            "blockchain": blockchain,
                            "anchain_data": anchain_data,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "source": "anchain_ai",
                        }
                        results["tool_results"]["anchain_ai"] = result

                # Add evidence
                if "error" not in result:
                    results["evidence"].append(
                        {
                            "tool": tool_type.value,
                            "result": result,
                            "timestamp": result.get(
                                "timestamp", datetime.now(timezone.utc).isoformat()
                            ),
                        }
                    )

            except Exception as e:
                logger.error(f"Tool {tool_type.value} analysis failed: {e}")
                results["tool_results"][tool_type.value] = {
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        # Get Etherscan labels
        try:
            etherscan_labels = await self.etherscan_labels.get_address_labels(address)
            results["tool_results"]["etherscan_labels"] = {
                "address": address,
                "labels": etherscan_labels.labels,
                "categories": etherscan_labels.categories,
                "risk_level": etherscan_labels.risk_level,
                "confidence": etherscan_labels.confidence,
                "source": "etherscan_labels",
                "timestamp": etherscan_labels.timestamp.isoformat(),
            }

            if etherscan_labels.labels:
                results["evidence"].append(
                    {
                        "tool": "etherscan_labels",
                        "result": {
                            "labels": etherscan_labels.labels,
                            "risk_level": etherscan_labels.risk_level,
                        },
                        "timestamp": etherscan_labels.timestamp.isoformat(),
                    }
                )
        except Exception as e:
            logger.error(f"Etherscan labels failed: {e}")

        # Generate combined assessment
        results["combined_assessment"] = self._generate_combined_assessment(results)

        return results

    def _generate_combined_assessment(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate combined assessment from all tool results"""
        tool_results = results.get("tool_results", {})

        # Collect all risk levels and confidence scores
        risk_levels = []
        confidence_scores = []
        all_labels = set()
        all_categories = set()

        for tool_name, tool_result in tool_results.items():
            if "error" not in tool_result:
                if tool_name == "etherscan_labels":
                    risk_levels.append(tool_result.get("risk_level", "low"))
                    confidence_scores.append(tool_result.get("confidence", 0.5))
                    all_labels.update(tool_result.get("labels", []))
                    all_categories.update(tool_result.get("categories", []))
                elif tool_name == "chainalysis":
                    # Extract risk from Chainalysis data
                    chainalysis_data = tool_result.get("chainalysis_data", {})
                    if "riskLevel" in chainalysis_data:
                        risk_levels.append(chainalysis_data["riskLevel"])
                    all_labels.update(chainalysis_data.get("labels", []))
                    all_categories.update(chainalysis_data.get("categories", []))
                elif tool_name == "cipherblade":
                    # Extract risk from CipherBlade data
                    cipherblade_data = tool_result.get("cipherblade_data", {})
                    if "risk_score" in cipherblade_data:
                        risk_score = cipherblade_data["risk_score"]
                        if risk_score >= 0.8:
                            risk_levels.append("critical")
                        elif risk_score >= 0.6:
                            risk_levels.append("high")
                        elif risk_score >= 0.4:
                            risk_levels.append("medium")
                        else:
                            risk_levels.append("low")
                    all_labels.update(cipherblade_data.get("labels", []))
                    all_categories.update(cipherblade_data.get("categories", []))

        # Calculate overall risk
        if risk_levels:
            # Weight risk levels (critical=4, high=3, medium=2, low=1)
            risk_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            total_weight = sum(risk_weights.get(level, 1) for level in risk_levels)
            avg_weight = total_weight / len(risk_levels)

            if avg_weight >= 3.5:
                overall_risk = "critical"
            elif avg_weight >= 2.5:
                overall_risk = "high"
            elif avg_weight >= 1.5:
                overall_risk = "medium"
            else:
                overall_risk = "low"
        else:
            overall_risk = "unknown"

        # Calculate average confidence
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.0
        )

        return {
            "overall_risk": overall_risk,
            "confidence": avg_confidence,
            "tools_used": list(tool_results.keys()),
            "total_labels": list(all_labels),
            "total_categories": list(all_categories),
            "evidence_count": len(results.get("evidence", [])),
            "assessment_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_tool_status(self) -> Dict[str, Any]:
        """Get status of all professional tools"""
        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "enabled_tools": list(self.enabled_tools),
            "tool_configs": {},
            "etherscan_labels_status": {},
        }

        for tool_type, tool in self.tools.items():
            status["tool_configs"][tool_type.value] = {
                "name": tool.config.name,
                "enabled": tool.config.enabled,
                "api_endpoint": tool.config.api_endpoint,
                "rate_limit": tool.config.rate_limit,
            }

        # Etherscan labels status
        status["etherscan_labels_status"] = {
            "labels_cached": len(self.etherscan_labels.labels_cache),
            "phish_hack_cached": len(self.etherscan_labels.phish_hack_labels),
            "last_import": (
                self.etherscan_labels.last_imported_at.isoformat()
                if self.etherscan_labels.last_imported_at
                else None
            ),
        }

        return status


# Global professional tools manager instance
_professional_tools_manager: Optional[ProfessionalToolsManager] = None


def get_professional_tools_manager() -> ProfessionalToolsManager:
    """Get global professional tools manager instance"""
    global _professional_tools_manager
    if _professional_tools_manager is None:
        _professional_tools_manager = ProfessionalToolsManager()
    return _professional_tools_manager
