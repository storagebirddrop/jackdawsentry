"""
Jackdaw Sentry - Seed Phrase Analysis
Advanced seed phrase analysis and wallet derivation tracking
"""

import asyncio
import logging
import hashlib
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
import bip_utils
from mnemonic import Mnemonic

from .models import (
    SeedAnalysisRequest, SeedAnalysisResult, WalletDerivation,
    DerivationType
)
from src.api.database import get_postgres_connection

logger = logging.getLogger(__name__)


class SeedPhraseAnalyzer:
    """Advanced seed phrase analysis and wallet derivation tracking"""
    
    def __init__(self):
        self.mnemonic = Mnemonic("english")
        self.cache = {}
        self.cache_ttl = 7200  # 2 hours
        self._initialized = False
    
    async def initialize(self):
        """Initialize the seed phrase analyzer"""
        if self._initialized:
            return
        
        logger.info("Initializing Seed Phrase Analyzer...")
        await self._create_seed_analysis_tables()
        self._initialized = True
        logger.info("Seed Phrase Analyzer initialized successfully")
    
    async def _create_seed_analysis_tables(self):
        """Create seed analysis tables"""
        
        create_seed_analysis_table = """
        CREATE TABLE IF NOT EXISTS seed_analysis_results (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            analysis_id VARCHAR(255) NOT NULL,
            seed_phrase_hash VARCHAR(255) NOT NULL,
            derivations JSONB DEFAULT '[]',
            total_wallets INTEGER NOT NULL DEFAULT 0,
            active_wallets INTEGER NOT NULL DEFAULT 0,
            total_balance DECIMAL(20,8) DEFAULT 0,
            blockchains TEXT[] DEFAULT '{}',
            processing_time_ms DECIMAL(10,2),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_seed_analysis_hash ON seed_analysis_results(seed_phrase_hash);
        CREATE INDEX IF NOT EXISTS idx_seed_analysis_created ON seed_analysis_results(created_at);
        """
        
        create_wallet_tracking_table = """
        CREATE TABLE IF NOT EXISTS wallet_derivations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            seed_phrase_hash VARCHAR(255) NOT NULL,
            derivation_path VARCHAR(255) NOT NULL,
            address VARCHAR(255) NOT NULL,
            blockchain VARCHAR(50) NOT NULL,
            address_type VARCHAR(50) NOT NULL,
            derivation_type VARCHAR(50) NOT NULL,
            derivation_index INTEGER NOT NULL,
            balance DECIMAL(20,8) DEFAULT 0,
            transaction_count INTEGER DEFAULT 0,
            first_seen TIMESTAMP WITH TIME ZONE,
            last_activity TIMESTAMP WITH TIME ZONE,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(seed_phrase_hash, derivation_path, address)
        );
        
        CREATE INDEX IF NOT EXISTS idx_wallet_derivations_hash ON wallet_derivations(seed_phrase_hash);
        CREATE INDEX IF NOT EXISTS idx_wallet_derivations_address ON wallet_derivations(address);
        CREATE INDEX IF NOT EXISTS idx_wallet_derivations_blockchain ON wallet_derivations(blockchain);
        CREATE INDEX IF NOT EXISTS idx_wallet_derivations_updated ON wallet_derivations(updated_at);
        """
        
        conn = await get_postgres_connection()
        try:
            await conn.execute(create_seed_analysis_table)
            await conn.execute(create_wallet_tracking_table)
            await conn.commit()
            logger.info("Seed analysis tables created/verified")
        except Exception as e:
            logger.error(f"Error creating seed analysis tables: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()
    
    async def analyze_seed_phrase(self, request: SeedAnalysisRequest) -> SeedAnalysisResult:
        """
        Analyze seed phrase and derive wallet addresses
        
        Args:
            request: Seed analysis request with parameters
            
        Returns:
            SeedAnalysisResult with derived wallets and analysis
        """
        
        start_time = datetime.now(timezone.utc)
        
        # Generate hash of seed phrase for privacy (don't store actual phrase)
        seed_phrase_hash = self._hash_seed_phrase(request.seed_phrase)
        
        # Check cache first
        cache_key = f"{seed_phrase_hash}:{':'.join(dt.value for dt in request.derivation_types)}:{':'.join(request.blockchains)}"
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if (datetime.now(timezone.utc) - cached_result['timestamp']).seconds < self.cache_ttl:
                logger.debug(f"Cache hit for seed phrase analysis: {seed_phrase_hash}")
                return cached_result['result']
        
        logger.info(f"Analyzing seed phrase with hash: {seed_phrase_hash}")
        
        try:
            # Validate seed phrase
            if not self.mnemonic.check(request.seed_phrase):
                raise ValueError("Invalid seed phrase")
            
            # Generate seed from mnemonic
            seed = self.mnemonic.to_seed(request.seed_phrase)
            
            # Derive wallets for each derivation type and blockchain
            all_derivations = []
            
            for derivation_type in request.derivation_types:
                for blockchain in request.blockchains:
                    derivations = await self._derive_wallets(
                        seed, derivation_type, blockchain, request.max_derivations
                    )
                    all_derivations.extend(derivations)
            
            # Check balances and activity if requested
            if request.check_balances:
                await self._enrich_wallet_data(all_derivations)
            
            # Filter inactive wallets if requested
            if not request.include_inactive:
                all_derivations = [d for d in all_derivations if d.balance > 0 or d.transaction_count > 0]
            
            # Calculate statistics
            total_balance = sum(d.balance or 0.0 for d in all_derivations)
            active_wallets = len([d for d in all_derivations if d.balance > 0 or d.transaction_count > 0])
            blockchains = set(d.blockchain for d in all_derivations)
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Create result
            result = SeedAnalysisResult(
                seed_phrase_hash=seed_phrase_hash,
                derivations=all_derivations,
                total_wallets=len(all_derivations),
                active_wallets=active_wallets,
                total_balance=total_balance,
                blockchains=blockchains,
                processing_time_ms=processing_time,
                metadata={
                    "derivation_types": [dt.value for dt in request.derivation_types],
                    "blockchains": request.blockchains,
                    "check_balances": request.check_balances,
                    "include_inactive": request.include_inactive,
                    "cache_hit": False,
                    "algorithm_version": "1.0"
                }
            )
            
            # Cache result
            self.cache[cache_key] = {
                'result': result,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Store in database
            await self._store_seed_analysis_result(result)
            
            logger.info(f"Seed phrase analysis complete: {len(all_derivations)} wallets derived in {processing_time:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Error in seed phrase analysis: {e}")
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return SeedAnalysisResult(
                seed_phrase_hash=seed_phrase_hash,
                derivations=[],
                total_wallets=0,
                active_wallets=0,
                total_balance=0.0,
                blockchains=set(),
                processing_time_ms=processing_time,
                metadata={
                    "error": str(e),
                    "cache_hit": False
                }
            )
    
    async def _derive_wallets(
        self,
        seed: bytes,
        derivation_type: DerivationType,
        blockchain: str,
        max_derivations: int
    ) -> List[WalletDerivation]:
        """Derive wallets from seed for specific derivation type and blockchain"""
        
        derivations = []
        
        try:
            # Create master key from seed
            master_key = bip_utils.Bip32SeedGenerator(seed).Generate()
            
            # Derive wallets based on type
            if derivation_type == DerivationType.BIP44:
                derivations = await self._derive_bip44_wallets(master_key, blockchain, max_derivations)
            elif derivation_type == DerivationType.BIP49:
                derivations = await self._derive_bip49_wallets(master_key, blockchain, max_derivations)
            elif derivation_type == DerivationType.BIP84:
                derivations = await self._derive_bip84_wallets(master_key, blockchain, max_derivations)
            elif derivation_type == DerivationType.BIP32:
                derivations = await self._derive_bip32_wallets(master_key, blockchain, max_derivations)
            elif derivation_type == DerivationType.CUSTOM:
                derivations = await self._derive_custom_wallets(master_key, blockchain, max_derivations)
            
        except Exception as e:
            logger.error(f"Error deriving wallets for {derivation_type.value} on {blockchain}: {e}")
        
        return derivations
    
    async def _derive_bip44_wallets(
        self,
        master_key: bip_utils.Bip32MasterKey,
        blockchain: str,
        max_derivations: int
    ) -> List[WalletDerivation]:
        """Derive BIP44 wallets (standard hierarchical deterministic)"""
        
        derivations = []
        
        # BIP44 path: m/44'/coin'/account'/change/address
        coin_type = self._get_coin_type(blockchain)
        
        for account in range(max_derivations):
            try:
                # Derive account key
                account_key = master_key.DerivePath(f"m/44'/{coin_type}'/{account}'")
                
                # External chain (change = 0)
                external_key = account_key.DerivePath("0")
                
                # Derive addresses
                for address_index in range(20):  # 20 addresses per account
                    try:
                        address_key = external_key.DerivePath(str(address_index))
                        
                        # Generate address based on blockchain
                        address = self._generate_address_from_key(address_key, blockchain, "P2PKH")
                        
                        derivation = WalletDerivation(
                            derivation_path=f"m/44'/{coin_type}'/{account}'/0/{address_index}",
                            address=address,
                            blockchain=blockchain,
                            address_type="P2PKH",
                            derivation_type=DerivationType.BIP44,
                            index=address_index
                        )
                        
                        derivations.append(derivation)
                        
                    except Exception as e:
                        logger.debug(f"Error deriving address {address_index}: {e}")
                        continue
                
                # Internal chain (change = 1) - for change addresses
                internal_key = account_key.DerivePath("1")
                
                for address_index in range(10):  # 10 change addresses per account
                    try:
                        address_key = internal_key.DerivePath(str(address_index))
                        
                        # Generate address based on blockchain
                        address = self._generate_address_from_key(address_key, blockchain, "P2PKH")
                        
                        derivation = WalletDerivation(
                            derivation_path=f"m/44'/{coin_type}'/{account}'/1/{address_index}",
                            address=address,
                            blockchain=blockchain,
                            address_type="P2PKH",
                            derivation_type=DerivationType.BIP44,
                            index=address_index
                        )
                        
                        derivations.append(derivation)
                        
                    except Exception as e:
                        logger.debug(f"Error deriving change address {address_index}: {e}")
                        continue
                
            except Exception as e:
                logger.debug(f"Error deriving account {account}: {e}")
                continue
        
        return derivations
    
    async def _derive_bip49_wallets(
        self,
        master_key: bip_utils.Bip32MasterKey,
        blockchain: str,
        max_derivations: int
    ) -> List[WalletDerivation]:
        """Derive BIP49 wallets (SegWit compatible)"""
        
        derivations = []
        
        # BIP49 path: m/49'/coin'/account'/change/address
        coin_type = self._get_coin_type(blockchain)
        
        for account in range(max_derivations):
            try:
                # Derive account key
                account_key = master_key.DerivePath(f"m/49'/{coin_type}'/{account}'")
                
                # External chain
                external_key = account_key.DerivePath("0")
                
                for address_index in range(20):
                    try:
                        address_key = external_key.DerivePath(str(address_index))
                        address = self._generate_address_from_key(address_key, blockchain, "P2SH")
                        
                        derivation = WalletDerivation(
                            derivation_path=f"m/49'/{coin_type}'/{account}'/0/{address_index}",
                            address=address,
                            blockchain=blockchain,
                            address_type="P2SH",
                            derivation_type=DerivationType.BIP49,
                            index=address_index
                        )
                        
                        derivations.append(derivation)
                        
                    except Exception as e:
                        logger.debug(f"Error deriving BIP49 address {address_index}: {e}")
                        continue
                
            except Exception as e:
                logger.debug(f"Error deriving BIP49 account {account}: {e}")
                continue
        
        return derivations
    
    async def _derive_bip84_wallets(
        self,
        master_key: bip_utils.Bip32MasterKey,
        blockchain: str,
        max_derivations: int
    ) -> List[WalletDerivation]:
        """Derive BIP84 wallets (Native SegWit)"""
        
        derivations = []
        
        # BIP84 path: m/84'/coin'/account'/change/address
        coin_type = self._get_coin_type(blockchain)
        
        for account in range(max_derivations):
            try:
                # Derive account key
                account_key = master_key.DerivePath(f"m/84'/{coin_type}'/{account}'")
                
                # External chain
                external_key = account_key.DerivePath("0")
                
                for address_index in range(20):
                    try:
                        address_key = external_key.DerivePath(str(address_index))
                        address = self._generate_address_from_key(address_key, blockchain, "P2WPKH")
                        
                        derivation = WalletDerivation(
                            derivation_path=f"m/84'/{coin_type}'/{account}'/0/{address_index}",
                            address=address,
                            blockchain=blockchain,
                            address_type="P2WPKH",
                            derivation_type=DerivationType.BIP84,
                            index=address_index
                        )
                        
                        derivations.append(derivation)
                        
                    except Exception as e:
                        logger.debug(f"Error deriving BIP84 address {address_index}: {e}")
                        continue
                
            except Exception as e:
                logger.debug(f"Error deriving BIP84 account {account}: {e}")
                continue
        
        return derivations
    
    async def _derive_bip32_wallets(
        self,
        master_key: bip_utils.Bip32MasterKey,
        blockchain: str,
        max_derivations: int
    ) -> List[WalletDerivation]:
        """Derive BIP32 wallets (hierarchical deterministic)"""
        
        derivations = []
        
        # Simple BIP32 path: m/account'/address
        for account in range(max_derivations):
            try:
                account_key = master_key.DerivePath(f"m/{account}'")
                
                for address_index in range(20):
                    try:
                        address_key = account_key.DerivePath(str(address_index))
                        address = self._generate_address_from_key(address_key, blockchain, "P2PKH")
                        
                        derivation = WalletDerivation(
                            derivation_path=f"m/{account}'/{address_index}",
                            address=address,
                            blockchain=blockchain,
                            address_type="P2PKH",
                            derivation_type=DerivationType.BIP32,
                            index=address_index
                        )
                        
                        derivations.append(derivation)
                        
                    except Exception as e:
                        logger.debug(f"Error deriving BIP32 address {address_index}: {e}")
                        continue
                
            except Exception as e:
                logger.debug(f"Error deriving BIP32 account {account}: {e}")
                continue
        
        return derivations
    
    async def _derive_custom_wallets(
        self,
        master_key: bip_utils.Bip32MasterKey,
        blockchain: str,
        max_derivations: int
    ) -> List[WalletDerivation]:
        """Derive custom wallet patterns"""
        
        derivations = []
        
        # Custom patterns for common wallet structures
        custom_patterns = [
            "m/44'/60'/0'/0/x",      # Ethereum standard
            "m/44'/0'/0'/0/x",       # Bitcoin standard
            "m/84'/0'/0'/0/x",       # Bitcoin native SegWit
            "m/49'/0'/0'/0/x",       # Bitcoin SegWit
        ]
        
        for pattern_index, pattern in enumerate(custom_patterns):
            try:
                for address_index in range(min(50, max_derivations)):
                    try:
                        path = pattern.replace("x", str(address_index))
                        address_key = master_key.DerivePath(path)
                        
                        # Determine address type based on pattern
                        if "84'" in path:
                            address_type = "P2WPKH"
                        elif "49'" in path:
                            address_type = "P2SH"
                        else:
                            address_type = "P2PKH"
                        
                        address = self._generate_address_from_key(address_key, blockchain, address_type)
                        
                        derivation = WalletDerivation(
                            derivation_path=path,
                            address=address,
                            blockchain=blockchain,
                            address_type=address_type,
                            derivation_type=DerivationType.CUSTOM,
                            index=address_index
                        )
                        
                        derivations.append(derivation)
                        
                    except Exception as e:
                        logger.debug(f"Error deriving custom address {address_index}: {e}")
                        continue
                
            except Exception as e:
                logger.debug(f"Error in custom pattern {pattern}: {e}")
                continue
        
        return derivations
    
    def _get_coin_type(self, blockchain: str) -> int:
        """Get BIP44 coin type for blockchain"""
        
        coin_types = {
            "bitcoin": 0,
            "ethereum": 60,
            "litecoin": 2,
            "dogecoin": 3,
            "bitcoin_cash": 145,
            "ethereum_classic": 61,
            "dash": 5,
            "zcash": 133,
            "ripple": 144,
            "tron": 195,
            "binance": 714,
            "polygon": 966,
            "arbitrum": 966,
            "optimism": 966,
            "avalanche": 966,
            "base": 966,
        }
        
        return coin_types.get(blockchain.lower(), 0)
    
    def _generate_address_from_key(
        self,
        key: bip_utils.Bip32PrivateKey,
        blockchain: str,
        address_type: str
    ) -> str:
        """Generate address from private key based on blockchain and type"""
        
        try:
            if blockchain.lower() in ["ethereum", "polygon", "arbitrum", "optimism", "avalanche", "base", "binance"]:
                # Ethereum-based chains
                if address_type == "P2PKH":
                    return key.PublicKey().ToAddress()
                else:
                    return key.PublicKey().ToAddress()
            
            elif blockchain.lower() == "bitcoin":
                # Bitcoin
                if address_type == "P2PKH":
                    return key.PublicKey().ToAddress()
                elif address_type == "P2SH":
                    return key.PublicKey().ToSegWitAddress()
                elif address_type == "P2WPKH":
                    return key.PublicKey().ToBech32Address()
                else:
                    return key.PublicKey().ToAddress()
            
            else:
                # Default to standard address
                return key.PublicKey().ToAddress()
        
        except Exception as e:
            logger.error(f"Error generating address for {blockchain} ({address_type}): {e}")
            raise
    
    async def _enrich_wallet_data(self, derivations: List[WalletDerivation]):
        """Enrich wallet data with balance and transaction information"""
        
        # This would integrate with existing blockchain collectors
        # For now, set placeholder values
        for derivation in derivations:
            # Placeholder - would call blockchain APIs to get real data
            derivation.balance = 0.0
            derivation.transaction_count = 0
            derivation.first_seen = None
            derivation.last_activity = None
    
    def _hash_seed_phrase(self, seed_phrase: str) -> str:
        """Generate hash of seed phrase for privacy"""
        
        return hashlib.sha256(seed_phrase.encode()).hexdigest()
    
    async def _store_seed_analysis_result(self, result: SeedAnalysisResult):
        """Store seed analysis result in database"""
        
        insert_query = """
        INSERT INTO seed_analysis_results (
            analysis_id, seed_phrase_hash, derivations, total_wallets,
            active_wallets, total_balance, blockchains, processing_time_ms, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        conn = await get_postgres_connection()
        try:
            await conn.execute(
                insert_query,
                result.analysis_id,
                result.seed_phrase_hash,
                [d.model_dump() for d in result.derivations],
                result.total_wallets,
                result.active_wallets,
                result.total_balance,
                list(result.blockchains),
                result.processing_time_ms,
                result.metadata
            )
            await conn.commit()
        except Exception as e:
            logger.error(f"Error storing seed analysis result: {e}")
            await conn.rollback()
        finally:
            await conn.close()
    
    def clear_cache(self):
        """Clear the seed phrase analysis cache"""
        self.cache.clear()
        logger.info("Seed phrase analysis cache cleared")


# Global analyzer instance
_analyzer = None

def get_seed_analyzer() -> SeedPhraseAnalyzer:
    """Get the global seed analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = SeedPhraseAnalyzer()
    return _analyzer
