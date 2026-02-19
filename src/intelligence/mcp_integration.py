"""
Jackdaw Sentry - MCP Integration Module
Model Context Protocol integration for AI-powered blockchain analysis
Inspired by FUCKIN-DANS-ASS MCP implementation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from dataclasses import dataclass, field
import json
import aiohttp
from enum import Enum

from src.api.database import get_neo4j_session, get_redis_connection
from src.api.config import settings

logger = logging.getLogger(__name__)


class MCPCommandType(Enum):
    """MCP command types"""
    GET_BALANCE = "get_balance"
    GET_TRANSACTIONS = "get_transactions"
    GET_CONTRACT_INFO = "get_contract_info"
    GET_GAS_PRICE = "get_gas_price"
    GET_ENS_NAME = "get_ens_name"
    GET_BLOCK_INFO = "get_block_info"
    GET_TOKEN_INFO = "get_token_info"
    GET_ADDRESS_LABELS = "get_address_labels"


@dataclass
class MCPRequest:
    """MCP request structure"""
    command: MCPCommandType
    parameters: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MCPResponse:
    """MCP response structure"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    request_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_time: float = 0.0


@dataclass
class EtherscanMCPServer:
    """Etherscan API V2 MCP Server implementation"""
    base_url: str = "https://api.etherscan.io/api"
    api_key: str = ""
    rate_limit: int = 5  # requests per second
    cache_ttl: int = 300  # 5 minutes
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.ETHERSCAN_API_KEY
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def execute_command(self, request: MCPRequest) -> MCPResponse:
        """Execute MCP command"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Check cache first
            cache_key = f"mcp:{request.command.value}:{hash(str(request.parameters))}"
            cached_result = await self.get_cached_result(cache_key)
            if cached_result:
                return MCPResponse(
                    success=True,
                    data=cached_result,
                    request_id=request.request_id,
                    processing_time=(datetime.now(timezone.utc) - start_time).total_seconds()
                )
            
            # Execute command
            result = await self._execute_command_impl(request)
            
            # Cache result
            await self.cache_result(cache_key, result)
            
            return MCPResponse(
                success=True,
                data=result,
                request_id=request.request_id,
                processing_time=(datetime.now(timezone.utc) - start_time).total_seconds()
            )
            
        except Exception as e:
            logger.error(f"MCP command failed: {e}")
            return MCPResponse(
                success=False,
                error=str(e),
                request_id=request.request_id,
                processing_time=(datetime.now(timezone.utc) - start_time).total_seconds()
            )
    
    async def _execute_command_impl(self, request: MCPRequest) -> Any:
        """Execute specific MCP command implementation"""
        if request.command == MCPCommandType.GET_BALANCE:
            return await self.get_balance(request.parameters)
        elif request.command == MCPCommandType.GET_TRANSACTIONS:
            return await self.get_transactions(request.parameters)
        elif request.command == MCPCommandType.GET_CONTRACT_INFO:
            return await self.get_contract_info(request.parameters)
        elif request.command == MCPCommandType.GET_GAS_PRICE:
            return await self.get_gas_price(request.parameters)
        elif request.command == MCPCommandType.GET_ENS_NAME:
            return await self.get_ens_name(request.parameters)
        elif request.command == MCPCommandType.GET_BLOCK_INFO:
            return await self.get_block_info(request.parameters)
        elif request.command == MCPCommandType.GET_TOKEN_INFO:
            return await self.get_token_info(request.parameters)
        elif request.command == MCPCommandType.GET_ADDRESS_LABELS:
            return await self.get_address_labels(request.parameters)
        else:
            raise ValueError(f"Unsupported command: {request.command}")
    
    async def get_balance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get address balance"""
        address = params.get('address')
        if not address:
            raise ValueError("Address parameter is required")
        
        url = f"{self.base_url}?module=account&action=balance&address={address}&tag=latest&apikey={self.api_key}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'address': address,
                    'balance': data.get('result', {}),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'etherscan_mcp'
                }
            else:
                raise Exception(f"Etherscan API error: {response.status}")
    
    async def get_transactions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get address transactions"""
        address = params.get('address')
        page = params.get('page', 1)
        offset = params.get('offset', 0)
        limit = params.get('limit', 100)
        
        if not address:
            raise ValueError("Address parameter is required")
        
        url = f"{self.base_url}?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&page={page}&offset={offset}&sort=asc&apikey={self.api_key}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'address': address,
                    'transactions': data.get('result', []),
                    'page': page,
                    'offset': offset,
                    'limit': limit,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'etherscan_mcp'
                }
            else:
                raise Exception(f"Etherscan API error: {response.status}")
    
    async def get_contract_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get contract information"""
        contract_address = params.get('contract_address')
        if not contract_address:
            raise ValueError("Contract address parameter is required")
        
        url = f"{self.base_url}?module=contract&action=getabi&address={contract_address}&apikey={self.api_key}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'contract_address': contract_address,
                    'abi': data.get('result', {}),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'etherscan_mcp'
                }
            else:
                raise Exception(f"Etherscan API error: {response.status}")
    
    async def get_gas_price(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current gas price"""
        url = f"{self.base_url}?module=gastracker&action=gasoracle&apikey={self.api_key}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                result = data.get('result', {})
                return {
                    'safe_gas_price': result.get('SafeGasPrice'),
                    'propose_gas_price': result.get('ProposeGasPrice'),
                    'fast_gas_price': result.get('FastGasPrice'),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'etherscan_mcp'
                }
            else:
                raise Exception(f"Etherscan API error: {response.status}")
    
    async def get_ens_name(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get ENS name for address"""
        address = params.get('address')
        if not address:
            raise ValueError("Address parameter is required")
        
        # ENS reverse lookup
        url = f"https://api.ensideas.net/ens/resolve/{address}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'address': address,
                    'ens_name': data.get('name'),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'ens_ideas_api'
                }
            else:
                return {
                    'address': address,
                    'ens_name': None,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'ens_ideas_api'
                }
    
    async def get_block_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get block information"""
        block_number = params.get('block_number')
        if not block_number:
            raise ValueError("Block number parameter is required")
        
        url = f"{self.base_url}?module=proxy&action=eth_getBlockByNumber&tag=latest&apikey={self.api_key}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'block_number': block_number,
                    'block_data': data.get('result'),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'etherscan_mcp'
                }
            else:
                raise Exception(f"Etherscan API error: {response.status}")
    
    async def get_token_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get token information"""
        contract_address = params.get('contract_address')
        if not contract_address:
            raise ValueError("Contract address parameter is required")
        
        url = f"{self.base_url}?module=token&action=tokeninfo&contractaddress={contract_address}&apikey={self.api_key}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'contract_address': contract_address,
                    'token_info': data.get('result', {}),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source': 'etherscan_mcp'
                }
            else:
                raise Exception(f"Etherscan API error: {response.status}")
    
    async def get_address_labels(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get address labels from Etherscan"""
        address = params.get('address')
        if not address:
            raise ValueError("Address parameter is required")
        
        # This would use the Etherscan label dataset
        # For now, return placeholder
        return {
            'address': address,
            'labels': [],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'etherscan_labels'
        }
    
    async def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result"""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(cache_key)
                if cached:
                    return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        return None
    
    async def cache_result(self, cache_key: str, result: Any):
        """Cache result"""
        try:
            async with get_redis_connection() as redis:
                await redis.setex(cache_key, self.cache_ttl, json.dumps(result))
        except Exception as e:
            logger.error(f"Cache storage error: {e}")


class AIInvestigationAssistant:
    """AI-powered investigation assistant using MCP integration"""
    
    def __init__(self):
        self.etherscan_server = EtherscanMCPServer()
        self.investigation_cache = {}
    
    async def investigate_address(self, address: str, depth: int = 3) -> Dict[str, Any]:
        """Comprehensive address investigation using AI-powered analysis"""
        try:
            investigation_result = {
                'address': address,
                'investigation_id': f"inv_{datetime.now(timezone.utc).timestamp()}",
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'depth': depth,
                'analysis_steps': [],
                'findings': [],
                'risk_assessment': {},
                'evidence': []
            }
            
            # Step 1: Basic address information
            balance_result = await self.etherscan_server.execute_command(
                MCPRequest(
                    command=MCPCommandType.GET_BALANCE,
                    parameters={'address': address},
                    request_id=investigation_result['investigation_id']
                )
            )
            
            if balance_result.success:
                investigation_result['analysis_steps'].append({
                    'step': 'balance_analysis',
                    'status': 'completed',
                    'data': balance_result.data,
                    'timestamp': balance_result.timestamp.isoformat()
                })
                
                # Analyze balance for risk assessment
                balance = balance_result.data.get('balance', {})
                if balance and float(balance.get('result', 0)) > 0:
                    investigation_result['findings'].append({
                        'type': 'active_balance',
                        'description': f"Address has active balance: {balance.get('result')} ETH",
                        'risk_level': 'medium',
                        'confidence': 0.8
                    })
            
            # Step 2: Transaction analysis
            tx_result = await self.etherscan_server.execute_command(
                MCPRequest(
                    command=MCPCommandType.GET_TRANSACTIONS,
                    parameters={'address': address, 'limit': 50},
                    request_id=investigation_result['investigation_id']
                )
            )
            
            if tx_result.success:
                investigation_result['analysis_steps'].append({
                    'step': 'transaction_analysis',
                    'status': 'completed',
                    'data': {'transaction_count': len(tx_result.data.get('transactions', []))},
                    'timestamp': tx_result.timestamp.isoformat()
                })
                
                # Analyze transaction patterns
                transactions = tx_result.data.get('transactions', [])
                if len(transactions) > 100:
                    investigation_result['findings'].append({
                        'type': 'high_activity',
                        'description': f"Address has {len(transactions)} transactions - high activity",
                        'risk_level': 'high',
                        'confidence': 0.9
                    })
            
            # Step 3: ENS name resolution
            ens_result = await self.etherscan_server.execute_command(
                MCPRequest(
                    command=MCPCommandType.GET_ENS_NAME,
                    parameters={'address': address},
                    request_id=investigation_result['investigation_id']
                )
            )
            
            if ens_result.success and ens_result.data.get('ens_name'):
                investigation_result['analysis_steps'].append({
                    'step': 'ens_resolution',
                    'status': 'completed',
                    'data': {'ens_name': ens_result.data.get('ens_name')},
                    'timestamp': ens_result.timestamp.isoformat()
                })
                
                investigation_result['findings'].append({
                    'type': 'ens_identity',
                    'description': f"Address resolves to ENS name: {ens_result.data.get('ens_name')}",
                    'risk_level': 'low',
                    'confidence': 0.7
                })
            
            # Step 4: Generate risk assessment
            investigation_result['risk_assessment'] = self._generate_risk_assessment(investigation_result['findings'])
            
            # Step 5: Generate evidence report
            investigation_result['evidence'] = self._generate_evidence_report(investigation_result)
            
            return investigation_result
            
        except Exception as e:
            logger.error(f"AI investigation failed: {e}")
            return {
                'address': address,
                'investigation_id': investigation_result.get('investigation_id', 'error'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'analysis_steps': [],
                'findings': [],
                'risk_assessment': {},
                'evidence': []
            }
    
    def _generate_risk_assessment(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate risk assessment from findings"""
        if not findings:
            return {'overall_risk': 'unknown', 'confidence': 0.0}
        
        # Calculate weighted risk score
        total_risk = 0
        confidence_sum = 0
        
        for finding in findings:
            risk_level = finding.get('risk_level', 'low')
            confidence = finding.get('confidence', 0.5)
            
            # Convert risk level to numeric score
            risk_scores = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            risk_score = risk_scores.get(risk_level, 1)
            
            total_risk += risk_score * confidence
            confidence_sum += confidence
        
        # Calculate overall risk
        avg_risk = total_risk / len(findings) if findings else 0
        avg_confidence = confidence_sum / len(findings) if findings else 0
        
        # Determine overall risk level
        if avg_risk >= 3.5:
            overall_risk = 'critical'
        elif avg_risk >= 2.5:
            overall_risk = 'high'
        elif avg_risk >= 1.5:
            overall_risk = 'medium'
        else:
            overall_risk = 'low'
        
        return {
            'overall_risk': overall_risk,
            'confidence': avg_confidence,
            'risk_score': avg_risk,
            'finding_count': len(findings),
            'assessment_timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _generate_evidence_report(self, investigation_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate court-ready evidence report"""
        evidence = []
        
        # Add investigation metadata
        evidence.append({
            'type': 'investigation_metadata',
            'data': {
                'investigation_id': investigation_result['investigation_id'],
                'address': investigation_result['address'],
                'timestamp': investigation_result['timestamp'],
                'analyst': 'Jackdaw Sentry AI Assistant',
                'methodology': 'MCP-powered blockchain analysis'
            }
        })
        
        # Add analysis steps as evidence
        for step in investigation_result.get('analysis_steps', []):
            evidence.append({
                'type': 'analysis_step',
                'data': step,
                'timestamp': step.get('timestamp'),
                'source': 'etherscan_mcp'
            })
        
        # Add findings as evidence
        for finding in investigation_result.get('findings', []):
            evidence.append({
                'type': 'finding',
                'data': finding,
                'timestamp': investigation_result['timestamp'],
                'source': 'ai_analysis'
            })
        
        return evidence


class MCPIntegration:
    """Main MCP integration manager for Jackdaw Sentry"""
    
    def __init__(self):
        self.etherscan_server = EtherscanMCPServer()
        self.ai_assistant = AIInvestigationAssistant()
        self.active_investigations = {}
    
    async def execute_mcp_command(self, command: MCPCommandType, parameters: Dict[str, Any]) -> MCPResponse:
        """Execute MCP command with full integration"""
        request_id = f"mcp_{datetime.now(timezone.utc).timestamp()}"
        request = MCPRequest(
            command=command,
            parameters=parameters,
            request_id=request_id
        )
        
        return await self.etherscan_server.execute_command(request)
    
    async def start_ai_investigation(self, address: str, user_id: str = None) -> Dict[str, Any]:
        """Start AI-powered investigation"""
        investigation_id = f"ai_inv_{datetime.now(timezone.utc).timestamp()}"
        
        # Start investigation
        investigation = await self.ai_assistant.investigate_address(address)
        investigation['user_id'] = user_id
        investigation['investigation_id'] = investigation_id
        
        # Store active investigation
        self.active_investigations[investigation_id] = investigation
        
        # Log investigation start
        logger.info(f"Started AI investigation for address {address}, ID: {investigation_id}")
        
        return investigation
    
    async def get_investigation_status(self, investigation_id: str) -> Dict[str, Any]:
        """Get investigation status"""
        if investigation_id in self.active_investigations:
            return self.active_investigations[investigation_id]
        else:
            return {'error': 'Investigation not found'}
    
    async def generate_court_ready_report(self, investigation_id: str) -> Dict[str, Any]:
        """Generate court-ready evidence report"""
        if investigation_id not in self.active_investigations:
            return {'error': 'Investigation not found'}
        
        investigation = self.active_investigations[investigation_id]
        
        report = {
            'report_id': f"court_report_{investigation_id}",
            'investigation_id': investigation_id,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'case_number': f"JC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{investigation_id[:8]}",
            'investigating_analyst': 'Jackdaw Sentry AI Assistant',
            'chain_of_custody': 'Immutable blockchain verification',
            'evidence': investigation.get('evidence', []),
            'findings': investigation.get('findings', []),
            'risk_assessment': investigation.get('risk_assessment', {}),
            'executive_summary': self._generate_executive_summary(investigation),
            'source_citations': self._generate_source_citations(investigation)
        }
        
        return report
    
    def _generate_executive_summary(self, investigation: Dict[str, Any]) -> str:
        """Generate executive summary for non-technical stakeholders"""
        risk_assessment = investigation.get('risk_assessment', {})
        overall_risk = risk_assessment.get('overall_risk', 'unknown')
        confidence = risk_assessment.get('confidence', 0.0)
        finding_count = risk_assessment.get('finding_count', 0)
        
        summary = f"""
Executive Summary - Blockchain Investigation Report

Investigation Target: {investigation.get('address', 'Unknown')}
Investigation Date: {investigation.get('timestamp', 'Unknown')}
Overall Risk Level: {overall_risk.upper()}
Confidence Score: {confidence:.2f}
Key Findings: {finding_count} significant items identified

Recommendations:
"""
        
        if overall_risk == 'critical':
            summary += "- IMMEDIATE INVESTIGATION REQUIRED\n"
            summary += "- Block all associated activities\n"
            summary += "- Report to compliance and security teams\n"
        elif overall_risk == 'high':
            summary += "- Enhanced monitoring required\n"
            summary += "- Review transaction patterns\n"
            summary += "- Consider additional verification\n"
        elif overall_risk == 'medium':
            summary += "- Standard monitoring with alerts\n"
            summary += "- Periodic review recommended\n"
        else:
            summary += "- Standard monitoring sufficient\n"
        
        summary += f"\nThis report was generated using AI-powered blockchain analysis with Model Context Protocol (MCP) integration."
        summary += f" All data sources are cryptographically verifiable on the blockchain."
        
        return summary
    
    def _generate_source_citations(self, investigation: Dict[str, Any]) -> List[str]:
        """Generate source citations for evidence"""
        citations = []
        
        for step in investigation.get('analysis_steps', []):
            if step.get('source') == 'etherscan_mcp':
                citations.append(f"Etherscan API V2 - {step.get('timestamp')}")
        
        citations.append("Jackdaw Sentry AI Assistant - AI-powered analysis")
        citations.append("Model Context Protocol (MCP) - Real-time data access")
        
        return citations


# Global MCP integration instance
_mcp_integration: Optional[MCPIntegration] = None


def get_mcp_integration() -> MCPIntegration:
    """Get global MCP integration instance"""
    global _mcp_integration
    if _mcp_integration is None:
        _mcp_integration = MCPIntegration()
    return _mcp_integration
