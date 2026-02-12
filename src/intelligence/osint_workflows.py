"""
Jackdaw Sentry - OSINT Workflows Integration
Structured investigation workflows for blockchain analysis
Inspired by Legendary_Crypto OSINT workflows and methodologies
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import aiohttp
import json
import re
from enum import Enum

from src.api.database import get_neo4j_session, get_redis_connection
from src.api.config import settings

logger = logging.getLogger(__name__)


class InvestigationType(Enum):
    """Investigation types"""
    BITCOIN_ADDRESS = "bitcoin_address"
    ETHEREUM_ADDRESS = "ethereum_address"
    ENS_DOMAIN = "ens_domain"
    SCAM_ABUSE_CHECK = "scam_abuse_check"
    LIGHTNING_PAYMENT = "lightning_payment"
    NFT_WALLET_PROFILING = "nft_wallet_profiling"
    CROSS_CHAIN_ANALYSIS = "cross_chain_analysis"


class OSINTPlatform(Enum):
    """OSINT platforms"""
    BLOCKSTREAM = "blockstream"
    WALLETEXPLORER = "walletexplorer"
    BITCOINABUSE = "bitcoinabuse"
    CHECKBITCOINADDRESS = "checkbitcoinaddress"
    BREADCRUMBS = "breadcrumbs"
    GRAPHSENSE = "graphsense"
    ETHERSCAN = "etherscan"
    ETTECTIVE = "ethtective"
    TOKENVIEW = "tokenview"
    ENS_DOMAINS = "ens_domains"
    LENS_PROTOCOL = "lens_protocol"
    OPENSEA = "opensea"
    LOOKSRARE = "looksrare"
    DUNE = "dune"
    NANSEN = "nansen"
    CHAINABUSE = "chainabuse"
    BADBITCOIN = "badbitcoin"
    LIGHTNING_DECODER = "lightning_decoder"
    AMBOSS = "amboss"


@dataclass
class OSINTResult:
    """OSINT investigation result"""
    platform: OSINTPlatform
    data: Any
    success: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InvestigationStep:
    """Investigation step"""
    step_id: str
    step_name: str
    platform: OSINTPlatform
    description: str
    url: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[OSINTResult] = None
    status: str = "pending"  # pending, running, completed, failed
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BitcoinInvestigation:
    """Bitcoin address investigation workflow"""
    
    def __init__(self):
        self.session = None
        self.cache_ttl = 3600  # 1 hour
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def investigate_address(self, address: str) -> Dict[str, Any]:
        """Investigate Bitcoin address using structured workflow"""
        investigation_id = f"btc_inv_{datetime.now(timezone.utc).timestamp()}"
        
        workflow = {
            'investigation_id': investigation_id,
            'address': address,
            'type': InvestigationType.BITCOIN_ADDRESS.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'steps': [],
            'findings': [],
            'evidence': [],
            'risk_assessment': {}
        }
        
        try:
            # Step 1: Blockstream.info for transaction history
            step1 = InvestigationStep(
                step_id=f"{investigation_id}_1",
                step_name="Transaction History Analysis",
                platform=OSINTPlatform.BLOCKSTREAM,
                description="Check transaction history on Blockstream.info",
                url=f"https://blockstream.info/api/address/{address}",
                parameters={'address': address}
            )
            
            workflow['steps'].append(step1)
            step1.result = await self._check_blockstream(address)
            step1.status = "completed" if step1.result.success else "failed"
            step1.timestamp = datetime.now(timezone.utc)
            
            if step1.result.success:
                workflow['findings'].append({
                    'type': 'transaction_history',
                    'description': f"Transaction history found on Blockstream.info",
                    'data': step1.result.data,
                    'risk_level': self._assess_transaction_risk(step1.result.data),
                    'confidence': 0.8
                })
                
                workflow['evidence'].append({
                    'platform': 'blockstream',
                    'data': step1.result.data,
                    'timestamp': step1.result.timestamp.isoformat()
                })
            
            # Step 2: WalletExplorer for clustering
            step2 = InvestigationStep(
                step_id=f"{investigation_id}_2",
                step_name="Address Clustering",
                platform=OSINTPlatform.WALLETEXPLORER,
                description="Cluster address on WalletExplorer",
                url=f"https://www.walletexplorer.com/api/address/{address}",
                parameters={'address': address}
            )
            
            workflow['steps'].append(step2)
            step2.result = await self._check_wallet_explorer(address)
            step2.status = "completed" if step2.result.success else "failed"
            step2.timestamp = datetime.now(timezone.utc)
            
            if step2.result.success:
                workflow['findings'].append({
                    'type': 'address_clustering',
                    'description': f"Address clustering found on WalletExplorer",
                    'data': step2.result.data,
                    'risk_level': 'medium',
                    'confidence': 0.7
                })
                
                workflow['evidence'].append({
                    'platform': 'wallet_explorer',
                    'data': step2.result.data,
                    'timestamp': step2.result.timestamp.isoformat()
                })
            
            # Step 3: Cross-reference with abuse databases
            step3 = InvestigationStep(
                step_id=f"{investigation_id}_3",
                step_name="Abuse Database Check",
                platform=OSINTPlatform.BITCOINABUSE,
                description="Check against BitcoinAbuse database",
                url=f"https://www.bitcoinabuse.com/api/reports/check",
                parameters={'address': address}
            )
            
            workflow['steps'].append(step3)
            step3.result = await self._check_bitcoin_abuse(address)
            step3.status = "completed" if step3.result.success else "failed"
            step3.timestamp = datetime.now(timezone.utc)
            
            if step3.result.success:
                workflow['findings'].append({
                    'type': 'abuse_reports',
                    'description': f"Abuse reports found on BitcoinAbuse",
                    'data': step3.result.data,
                    'risk_level': 'high' if step3.result.data.get('count', 0) > 0 else 'low',
                    'confidence': 0.9
                })
                
                workflow['evidence'].append({
                    'platform': 'bitcoin_abuse',
                    'data': step3.result.data,
                    'timestamp': step3.result.timestamp.isoformat()
                })
            
            # Step 4: Visualization with Breadcrumbs
            step4 = InvestigationStep(
                step_id=f"{investigation_id}_4",
                step_name="Transaction Visualization",
                platform=OSINTPlatform.BREADCRUMBS,
                description="Visualize transaction flow with Breadcrumbs",
                url=f"https://breadcrumbs.app/address/{address}",
                parameters={'address': address}
            )
            
            workflow['steps'].append(step4)
            step4.result = await self._check_breadcrumbs(address)
            step4.status = "completed" if step4.result.success else "failed"
            step4.timestamp = datetime.now(timezone.utc)
            
            if step4.result.success:
                workflow['findings'].append({
                    'type': 'transaction_visualization',
                    'description': f"Transaction visualization available on Breadcrumbs",
                    'data': step4.result.data,
                    'risk_level': 'medium',
                    'confidence': 0.6
                })
                
                workflow['evidence'].append({
                    'platform': 'breadcrumbs',
                    'data': step4.result.data,
                    'timestamp': step4.result.timestamp.isoformat()
                })
            
            # Generate risk assessment
            workflow['risk_assessment'] = self._generate_risk_assessment(workflow['findings'])
            
            return workflow
            
        except Exception as e:
            logger.error(f"Bitcoin investigation failed: {e}")
            return {
                'investigation_id': investigation_id,
                'address': address,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'steps': [],
                'findings': [],
                'evidence': [],
                'risk_assessment': {}
            }
    
    async def _check_blockstream(self, address: str) -> OSINTResult:
        """Check Blockstream.info for address"""
        try:
            url = f"https://blockstream.info/api/address/{address}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return OSINTResult(
                        platform=OSINTPlatform.BLOCKSTREAM,
                        data=data,
                        success=True,
                        timestamp=datetime.now(timezone.utc)
                    )
                else:
                    return OSINTResult(
                        platform=OSINTPlatform.BLOCKSTREAM,
                        data=None,
                        success=False,
                        error=f"HTTP {response.status}",
                        timestamp=datetime.now(timezone.utc)
                    )
        except Exception as e:
            return OSINTResult(
                platform=OSINTPlatform.BLOCKSTREAM,
                data=None,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_wallet_explorer(self, address: str) -> OSINTResult:
        """Check WalletExplorer for address clustering"""
        try:
            url = f"https://www.walletexplorer.com/api/address/{address}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return OSINTResult(
                        platform=OSINTPlatform.WALLETEXPLORER,
                        data=data,
                        success=True,
                        timestamp=datetime.now(timezone.utc)
                    )
                else:
                    return OSINTResult(
                        platform=OSINTPlatform.WALLETEXPLORER,
                        data=None,
                        success=False,
                        error=f"HTTP {response.status}",
                        timestamp=datetime.now(timezone.utc)
                    )
        except Exception as e:
            return OSINTResult(
                platform=OSINTPlatform.WALLETEXPLORER,
                data=None,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_bitcoin_abuse(self, address: str) -> OSINTResult:
        """Check BitcoinAbuse database"""
        try:
            url = "https://www.bitcoinabuse.com/api/reports/check"
            payload = {'address': address}
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return OSINTResult(
                        platform=OSINTPlatform.BITCOINABUSE,
                        data=data,
                        success=True,
                        timestamp=datetime.now(timezone.utc)
                    )
                else:
                    return OSINTResult(
                        platform=OSINTPlatform.BITCOINABUSE,
                        data=None,
                        success=False,
                        error=f"HTTP {response.status}",
                        timestamp=datetime.now(timezone.utc)
                    )
        except Exception as e:
            return OSINTResult(
                platform=OSINTPlatform.BITCOINABUSE,
                data=None,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_breadcrumbs(self, address: str) -> OSINTResult:
        """Check Breadcrumbs for visualization"""
        try:
            url = f"https://breadcrumbs.app/address/{address}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    # Breadcrumbs returns HTML, so we'll indicate availability
                    return OSINTResult(
                        platform=OSINTPlatform.BREADCRUMBS,
                        data={'visualization_available': True, 'url': url},
                        success=True,
                        timestamp=datetime.now(timezone.utc)
                    )
                else:
                    return OSINTResult(
                        platform=OSINTPlatform.BREADCRUMBS,
                        data={'visualization_available': False},
                        success=False,
                        error=f"HTTP {response.status}",
                        timestamp=datetime.now(timezone.utc)
                    )
        except Exception as e:
            return OSINTResult(
                platform=OSINTPlatform.BREADCRUMBS,
                data={'visualization_available': False},
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc)
            )
    
    def _assess_transaction_risk(self, transaction_data: Dict[str, Any]) -> str:
        """Assess risk based on transaction data"""
        try:
            # Simple risk assessment based on transaction patterns
            tx_count = len(transaction_data.get('txs', []))
            total_received = transaction_data.get('total_received', 0)
            total_sent = transaction_data.get('total_sent', 0)
            
            # High transaction count indicates potential mixing or high activity
            if tx_count > 1000:
                return 'high'
            elif tx_count > 100:
                return 'medium'
            elif total_received > 1000 or total_sent > 1000:
                return 'medium'
            else:
                return 'low'
        except Exception:
            return 'unknown'
    
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


class EthereumInvestigation:
    """Ethereum address investigation workflow"""
    
    def __init__(self):
        self.session = None
        self.cache_ttl = 3600  # 1 hour
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def investigate_address(self, address: str) -> Dict[str, Any]:
        """Investigate Ethereum address using structured workflow"""
        investigation_id = f"eth_inv_{datetime.now(timezone.utc).timestamp()}"
        
        workflow = {
            'investigation_id': investigation_id,
            'address': address,
            'type': InvestigationType.ETHEREUM_ADDRESS.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'steps': [],
            'findings': [],
            'evidence': [],
            'risk_assessment': {}
        }
        
        try:
            # Step 1: Etherscan for transaction history
            step1 = InvestigationStep(
                step_id=f"{investigation_id}_1",
                step_name="Etherscan Analysis",
                platform=OSINTPlatform.ETHERSCAN,
                description="Check transaction history on Etherscan",
                url=f"https://api.etherscan.io/api",
                parameters={'address': address}
            )
            
            workflow['steps'].append(step1)
            step1.result = await self._check_etherscan(address)
            step1.status = "completed" if step1.result.success else "failed"
            step1.timestamp = datetime.now(timezone.utc)
            
            if step1.result.success:
                workflow['findings'].append({
                    'type': 'transaction_history',
                    'description': f"Transaction history found on Etherscan",
                    'data': step1.result.data,
                    'risk_level': self._assess_ethereum_risk(step1.result.data),
                    'confidence': 0.8
                })
                
                workflow['evidence'].append({
                    'platform': 'etherscan',
                    'data': step1.result.data,
                    'timestamp': step1.result.timestamp.isoformat()
                })
            
            # Step 2: Ethtective for verification
            step2 = InvestigationStep(
                step_id=f"{investigation_id}_2",
                step_name="Ethtective Verification",
                platform=OSINTPlatform.ETTECTIVE,
                description="Verify address on Ethtective",
                url=f"https://ethtective.com/api/address/{address}",
                parameters={'address': address}
            )
            
            workflow['steps'].append(step2)
            step2.result = await self._check_ethtective(address)
            step2.status = "completed" if step2.result.success else "failed"
            step2.timestamp = datetime.now(timezone.utc)
            
            if step2.result.success:
                workflow['findings'].append({
                    'type': 'address_verification',
                    'description': f"Address verification on Ethtective",
                    'data': step2.result.data,
                    'risk_level': 'medium',
                    'confidence': 0.7
                })
                
                workflow['evidence'].append({
                    'platform': 'ethtective',
                    'data': step2.result.data,
                    'timestamp': step2.result.timestamp.isoformat()
                })
            
            # Step 3: Tokenview for ERC-20 activity
            step3 = InvestigationStep(
                step_id=f"{investigation_id}_3",
                step_name="ERC-20 Activity Analysis",
                platform=OSINTPlatform.TOKENVIEW,
                description="Check ERC-20 token activity on Tokenview",
                url=f"https://tokenview.io/api/address/{address}",
                parameters={'address': address}
            )
            
            workflow['steps'].append(step3)
            step3.result = await self._check_tokenview(address)
            step3.status = "completed" if step3.result.success else "failed"
            step3.timestamp = datetime.now(timezone.utc)
            
            if step3.result.success:
                workflow['findings'].append({
                    'type': 'token_activity',
                    'description': f"ERC-20 activity found on Tokenview",
                    'data': step3.result.data,
                    'risk_level': 'medium',
                    'confidence': 0.6
                })
                
                workflow['evidence'].append({
                    'platform': 'tokenview',
                    'data': step3.result.data,
                    'timestamp': step3.result.timestamp.isoformat()
                })
            
            # Step 4: Visualization with Breadcrumbs
            step4 = InvestigationStep(
                step_id=f"{investigation_id}_4",
                step_name="Transaction Visualization",
                platform=OSINTPlatform.BREADCRUMBS,
                description="Visualize transaction flow with Breadcrumbs",
                url=f"https://breadcrumbs.app/address/{address}",
                parameters={'address': address}
            )
            
            workflow['steps'].append(step4)
            step4.result = await self._check_breadcrumbs_eth(address)
            step4.status = "completed" if step4.result.success else "failed"
            step4.timestamp = datetime.now(timezone.utc)
            
            if step4.result.success:
                workflow['findings'].append({
                    'type': 'transaction_visualization',
                    'description': f"Transaction visualization available on Breadcrumbs",
                    'data': step4.result.data,
                    'risk_level': 'medium',
                    'confidence': 0.6
                })
                
                workflow['evidence'].append({
                    'platform': 'breadcrumbs',
                    'data': step4.result.data,
                    'timestamp': step4.result.timestamp.isoformat()
                })
            
            # Generate risk assessment
            workflow['risk_assessment'] = self._generate_risk_assessment(workflow['findings'])
            
            return workflow
            
        except Exception as e:
            logger.error(f"Ethereum investigation failed: {e}")
            return {
                'investigation_id': investigation_id,
                'address': address,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'steps': [],
                'findings': [],
                'evidence': [],
                'risk_assessment': {}
            }
    
    async def _check_etherscan(self, address: str) -> OSINTResult:
        """Check Etherscan for address"""
        try:
            url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&sort=desc&apikey={settings.ETHERSCAN_API_KEY}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return OSINTResult(
                        platform=OSINTPlatform.ETHERSCAN,
                        data=data,
                        success=True,
                        timestamp=datetime.now(timezone.utc)
                    )
                else:
                    return OSINTResult(
                        platform=OSINTPlatform.ETHERSCAN,
                        data=None,
                        success=False,
                        error=f"HTTP {response.status}",
                        timestamp=datetime.now(timezone.utc)
                    )
        except Exception as e:
            return OSINTResult(
                platform=OSINTPlatform.ETHERSCAN,
                data=None,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_ethtective(self, address: str) -> OSINTResult:
        """Check Ethtective for address"""
        try:
            url = f"https://ethtective.com/api/address/{address}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return OSINTResult(
                        platform=OSINTPlatform.ETTECTIVE,
                        data=data,
                        success=True,
                        timestamp=datetime.now(timezone.utc)
                    )
                else:
                    return OSINTResult(
                        platform=OSINTPlatform.ETTECTIVE,
                        data=None,
                        success=False,
                        error=f"HTTP {response.status}",
                        timestamp=datetime.now(timezone.utc)
                    )
        except Exception as e:
            return OSINTResult(
                platform=OSINTPlatform.ETTECTIVE,
                data=None,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_tokenview(self, address: str) -> OSINTResult:
        """Check Tokenview for ERC-20 activity"""
        try:
            url = f"https://tokenview.io/api/address/{address}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return OSINTResult(
                        platform=OSINTPlatform.TOKENVIEW,
                        data=data,
                        success=True,
                        timestamp=datetime.now(timezone.utc)
                    )
                else:
                    return OSINTResult(
                        platform=OSINTPlatform.TOKENVIEW,
                        data=None,
                        success=False,
                        error=f"HTTP {response.status}",
                        timestamp=datetime.now(timezone.utc)
                    )
        except Exception as e:
            return OSINTResult(
                platform=OSINTPlatform.TOKENVIEW,
                data=None,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_breadcrumbs_eth(self, address: str) -> OSINTResult:
        """Check Breadcrumbs for Ethereum address"""
        try:
            url = f"https://breadcrumbs.app/address/{address}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    # Breadcrumbs returns HTML, so we'll indicate availability
                    return OSINTResult(
                        platform=OSINTPlatform.BREADCRUMBS,
                        data={'visualization_available': True, 'url': url},
                        success=True,
                        timestamp=datetime.now(timezone.utc)
                    )
                else:
                    return OSINTResult(
                        platform=OSINTPlatform.BREADCRUMBS,
                        data={'visualization_available': False},
                        success=False,
                        error=f"HTTP {response.status}",
                        timestamp=datetime.now(timezone.utc)
                    )
        except Exception as e:
            return OSINTResult(
                platform=OSINTPlatform.BREADCRUMBS,
                data={'visualization_available': False},
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc)
            )
    
    def _assess_ethereum_risk(self, transaction_data: Dict[str, Any]) -> str:
        """Assess risk based on Ethereum transaction data"""
        try:
            # Simple risk assessment based on transaction patterns
            tx_count = len(transaction_data.get('result', []))
            
            # High transaction count indicates potential mixing or high activity
            if tx_count > 500:
                return 'high'
            elif tx_count > 100:
                return 'medium'
            else:
                return 'low'
        except Exception:
            return 'unknown'
    
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


class OSINTWorkflowsManager:
    """Manager for OSINT investigation workflows"""
    
    def __init__(self):
        self.active_investigations = {}
        self.cache_ttl = 3600  # 1 hour
    
    async def start_investigation(self, address: str, investigation_type: InvestigationType, user_id: str = None) -> Dict[str, Any]:
        """Start structured OSINT investigation"""
        investigation_id = f"osint_{datetime.now(timezone.utc).timestamp()}"
        
        try:
            if investigation_type == InvestigationType.BITCOIN_ADDRESS:
                bitcoin_investigator = BitcoinInvestigation()
                async with bitcoin_investigator:
                    investigation = await bitcoin_investigator.investigate_address(address)
            
            elif investigation_type == InvestigationType.ETHEREUM_ADDRESS:
                ethereum_investigator = EthereumInvestigation()
                async with ethereum_investigator:
                    investigation = await ethereum_investigator.investigate_address(address)
            
            else:
                return {
                    'error': f'Unsupported investigation type: {investigation_type.value}',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Add metadata
            investigation['user_id'] = user_id
            investigation['investigation_id'] = investigation_id
            
            # Store active investigation
            self.active_investigations[investigation_id] = investigation
            
            # Log investigation start
            logger.info(f"Started OSINT investigation for address {address}, type: {investigation_type.value}, ID: {investigation_id}")
            
            return investigation
            
        except Exception as e:
            logger.error(f"OSINT investigation failed: {e}")
            return {
                'investigation_id': investigation_id,
                'address': address,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'steps': [],
                'findings': [],
                'evidence': [],
                'risk_assessment': {}
            }
    
    async def get_investigation_status(self, investigation_id: str) -> Dict[str, Any]:
        """Get investigation status"""
        if investigation_id in self.active_investigations:
            return self.active_investigations[investigation_id]
        else:
            return {'error': 'Investigation not found'}
    
    async def generate_investigation_report(self, investigation_id: str) -> Dict[str, Any]:
        """Generate comprehensive investigation report"""
        if investigation_id not in self.active_investigations:
            return {'error': 'Investigation not found'}
        
        investigation = self.active_investigations[investigation_id]
        
        report = {
            'report_id': f"osint_report_{investigation_id}",
            'investigation_id': investigation_id,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'case_number': f"OSINT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{investigation_id[:8]}",
            'investigating_analyst': 'Jackdaw Sentry OSINT Workflows',
            'methodology': 'Structured multi-platform OSINT investigation',
            'investigation': investigation,
            'executive_summary': self._generate_executive_summary(investigation),
            'recommendations': self._generate_recommendations(investigation)
        }
        
        return report
    
    def _generate_executive_summary(self, investigation: Dict[str, Any]) -> str:
        """Generate executive summary"""
        risk_assessment = investigation.get('risk_assessment', {})
        overall_risk = risk_assessment.get('overall_risk', 'unknown')
        confidence = risk_assessment.get('confidence', 0.0)
        finding_count = risk_assessment.get('finding_count', 0)
        step_count = len(investigation.get('steps', []))
        
        summary = f"""
Executive Summary - OSINT Investigation Report

Investigation Target: {investigation.get('address', 'Unknown')}
Investigation Type: {investigation.get('type', 'Unknown')}
Investigation Date: {investigation.get('timestamp', 'Unknown')}
Overall Risk Level: {overall_risk.upper()}
Confidence Score: {confidence:.2f}
Key Findings: {finding_count} significant items identified
Steps Completed: {step_count}/{step_count} investigation steps

Recommendations:
"""
        
        if overall_risk == 'critical':
            summary += "- IMMEDIATE INVESTIGATION REQUIRED\n"
            summary += "- Enhanced monitoring and tracking recommended\n"
            summary += "- Consider law enforcement involvement\n"
        elif overall_risk == 'high':
            summary += "- Enhanced monitoring required\n"
            summary += "- Review all connected addresses\n"
            summary += "- Implement transaction monitoring\n"
        elif overall_risk == 'medium':
            summary += "- Standard monitoring with alerts\n"
            summary += "- Periodic investigation review\n"
            summary += "- Cross-platform verification\n"
        else:
            summary += "- Standard monitoring sufficient\n"
        
        summary += f"\nThis report was generated using structured OSINT workflows across multiple platforms."
        summary += f" All data sources are publicly accessible and verifiable."
        
        return summary
    
    def _generate_recommendations(self, investigation: Dict[str, Any]) -> List[str]:
        """Generate investigation recommendations"""
        risk_assessment = investigation.get('risk_assessment', {})
        overall_risk = risk_assessment.get('overall_risk', 'unknown')
        findings = investigation.get('findings', [])
        
        recommendations = []
        
        # Risk-based recommendations
        if overall_risk == 'critical':
            recommendations.extend([
                "Immediate enhanced monitoring required",
                "Consider blocking associated addresses",
                "Report to relevant authorities",
                "Implement transaction monitoring",
                "Cross-reference with law enforcement databases"
            ])
        elif overall_risk == 'high':
            recommendations.extend([
                "Enhanced monitoring with alerts",
                "Investigate transaction patterns",
                "Verify address ownership",
                "Monitor connected addresses"
            ])
        elif overall_risk == 'medium':
            recommendations.extend([
                "Standard monitoring with periodic reviews",
                "Cross-platform verification",
                "Maintain investigation log"
            ])
        else:
            recommendations.extend([
                "Standard monitoring sufficient",
                "Periodic risk assessment"
            ])
        
        # Finding-specific recommendations
        for finding in findings:
            if finding.get('type') == 'transaction_history':
                recommendations.append("Monitor transaction patterns for anomalies")
            elif finding.get('type') == 'abuse_reports':
                recommendations.append("Review abuse reports for additional context")
            elif finding.get('type') == 'address_clustering':
                recommendations.append("Investigate clustered addresses for related activity")
        
        return list(set(recommendations))  # Remove duplicates


# Global OSINT workflows manager instance
_osint_workflows_manager: Optional[OSINTWorkflowsManager] = None


def get_osint_workflows_manager() -> OSINTWorkflowsManager:
    """Get global OSINT workflows manager instance"""
    global _osint_workflows_manager
    if _osint_workflows_manager is None:
        _osint_workflows_manager = OSINTWorkflowsManager()
    return _osint_workflows_manager
