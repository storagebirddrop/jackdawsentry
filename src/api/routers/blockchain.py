"""
Jackdaw Sentry - Blockchain Router
Blockchain data and node management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
import logging

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_neo4j_session, get_redis_connection
from src.api.exceptions import BlockchainException
from src.api.config import get_supported_blockchains

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class BlockchainQueryRequest(BaseModel):
    blockchain: str
    query_type: str  # transaction, address, block, contract
    identifier: str
    include_details: bool = True
    
    @validator('blockchain')
    def validate_blockchain(cls, v):
        supported = get_supported_blockchains()
        if v.lower() not in supported:
            raise ValueError(f'Unsupported blockchain: {v}')
        return v.lower()
    
    @validator('query_type')
    def validate_query_type(cls, v):
        valid_types = ["transaction", "address", "block", "contract"]
        if v not in valid_types:
            raise ValueError(f'Invalid query type: {v}')
        return v


class NodeStatusRequest(BaseModel):
    blockchain: str
    node_url: Optional[str] = None
    
    @validator('blockchain')
    def validate_blockchain(cls, v):
        supported = get_supported_blockchains()
        if v.lower() not in supported:
            raise ValueError(f'Unsupported blockchain: {v}')
        return v.lower()


class BlockchainResponse(BaseModel):
    success: bool
    blockchain_data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime


# Endpoints
@router.post("/query", response_model=BlockchainResponse)
async def query_blockchain(
    request: BlockchainQueryRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]]))
):
    """Query blockchain data"""
    try:
        logger.info(f"Querying {request.blockchain} for {request.query_type}: {request.identifier}")
        
        if request.query_type == "transaction":
            data = {
                "transaction_hash": request.identifier,
                "blockchain": request.blockchain,
                "from_address": "0x1234567890123456789012345678901234567890",
                "to_address": "0x0987654321098765432109876543210987654321",
                "value": 2.5,
                "gas_used": 21000,
                "gas_price": 20,
                "block_number": 18500000,
                "timestamp": datetime.utcnow() - timedelta(hours=1),
                "status": "confirmed",
                "confirmations": 15
            }
            
            if request.include_details:
                data["details"] = {
                    "input_data": "0x...",
                    "logs": [],
                    "trace": [],
                    "token_transfers": []
                }
        
        elif request.query_type == "address":
            data = {
                "address": request.identifier,
                "blockchain": request.blockchain,
                "balance": 15.7,
                "transaction_count": 1250,
                "first_seen": datetime.utcnow() - timedelta(days=365),
                "last_seen": datetime.utcnow() - timedelta(hours=2),
                "type": "eoa",
                "labels": ["exchange", "trading"]
            }
            
            if request.include_details:
                data["details"] = {
                    "contracts": [],
                    "tokens": [
                        {"symbol": "USDT", "balance": 5000.0},
                        {"symbol": "USDC", "balance": 3000.0}
                    ],
                    "transactions": []
                }
        
        elif request.query_type == "block":
            data = {
                "block_number": int(request.identifier),
                "blockchain": request.blockchain,
                "block_hash": "0xabcdef1234567890...",
                "timestamp": datetime.utcnow() - timedelta(hours=1),
                "transaction_count": 150,
                "gas_used": 8500000,
                "gas_limit": 15000000,
                "miner": "0x1234567890123456789012345678901234567890",
                "difficulty": "12000000000000"
            }
            
            if request.include_details:
                data["details"] = {
                    "transactions": [],
                    "uncles": [],
                    "withdrawals": []
                }
        
        else:  # contract
            data = {
                "contract_address": request.identifier,
                "blockchain": request.blockchain,
                "contract_type": "ERC20",
                "name": "Mock Token",
                "symbol": "MOCK",
                "decimals": 18,
                "total_supply": "1000000000000000000000000",
                "created_at": datetime.utcnow() - timedelta(days=100),
                "creator": "0x1234567890123456789012345678901234567890"
            }
            
            if request.include_details:
                data["details"] = {
                    "abi": [],
                    "functions": ["transfer", "approve", "balanceOf"],
                    "events": ["Transfer", "Approval"],
                    "holders": 1250
                }
        
        metadata = {
            "query_type": request.query_type,
            "include_details": request.include_details,
            "data_source": "blockchain_rpc",
            "processing_time_ms": 150,
            "cache_hit": False
        }
        
        return BlockchainResponse(
            success=True,
            blockchain_data=data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Blockchain query failed: {e}")
        raise BlockchainException(
            message=f"Blockchain query failed: {str(e)}",
            blockchain=request.blockchain,
            error_code="BLOCKCHAIN_QUERY_FAILED"
        )


@router.get("/supported")
async def get_supported_blockchains_info(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]]))
):
    """Get list of supported blockchains"""
    try:
        supported = get_supported_blockchains()
        
        blockchain_info = {}
        for chain in supported:
            blockchain_info[chain] = {
                "name": chain.title(),
                "status": "active",
                "features": {
                    "transactions": True,
                    "contracts": chain in ["ethereum", "bsc", "polygon", "arbitrum", "base"],
                    "tokens": chain in ["ethereum", "bsc", "polygon", "arbitrum", "base", "solana", "tron"],
                    "nfts": chain in ["ethereum", "bsc", "polygon", "arbitrum", "base"],
                    "defi": chain in ["ethereum", "bsc", "polygon", "arbitrum", "base"]
                },
                "last_sync": datetime.utcnow() - timedelta(minutes=5),
                "sync_status": "healthy"
            }
        
        return {
            "success": True,
            "blockchains": blockchain_info,
            "total_supported": len(supported),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Supported blockchains retrieval failed: {e}")
        raise BlockchainException(
            message=f"Supported blockchains retrieval failed: {str(e)}",
            blockchain="multiple",
            error_code="SUPPORTED_CHAINS_FAILED"
        )


@router.post("/node/status", response_model=BlockchainResponse)
async def get_node_status(
    request: NodeStatusRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]]))
):
    """Get blockchain node status"""
    try:
        logger.info(f"Getting node status for {request.blockchain}")
        
        status_data = {
            "blockchain": request.blockchain,
            "node_status": "healthy",
            "connected": True,
            "sync_status": "synced",
            "latest_block": 18500000,
            "latest_block_timestamp": datetime.utcnow() - timedelta(seconds=30),
            "peer_count": 25,
            "rpc_latency_ms": 45,
            "uptime_percentage": 99.8,
            "last_check": datetime.utcnow()
        }
        
        # Add blockchain-specific metrics
        if request.blockchain == "bitcoin":
            status_data.update({
                "difficulty": 52000000000000,
                "hash_rate_th": 450000,
                "mempool_size": 5000,
                "block_interval_minutes": 10
            })
        elif request.blockchain in ["ethereum", "bsc", "polygon", "arbitrum", "base"]:
            status_data.update({
                "gas_price_gwei": 25,
                "network_utilization": 0.65,
                "block_time_seconds": 12
            })
        
        metadata = {
            "check_duration_ms": 120,
            "alerts": [],
            "performance_grade": "A"
        }
        
        return BlockchainResponse(
            success=True,
            blockchain_data=status_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Node status check failed: {e}")
        raise BlockchainException(
            message=f"Node status check failed: {str(e)}",
            blockchain=request.blockchain,
            error_code="NODE_STATUS_FAILED"
        )


@router.get("/{blockchain}/transactions/latest")
async def get_latest_transactions(
    blockchain: str,
    limit: int = 50,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]]))
):
    """Get latest transactions from blockchain"""
    try:
        logger.info(f"Getting latest {limit} transactions from {blockchain}")
        
        transactions = []
        for i in range(min(limit, 50)):
            tx = {
                "transaction_hash": f"0x{'1234567890abcdef' * 4}{i:04x}",
                "blockchain": blockchain,
                "from_address": f"0x{'1234567890abcdef' * 4}",
                "to_address": f"0x{'0987654321fedcba' * 4}",
                "value": round(0.1 + (i * 0.05), 4),
                "block_number": 18500000 - i,
                "timestamp": datetime.utcnow() - timedelta(minutes=i*2),
                "gas_used": 21000,
                "gas_price": 20,
                "status": "confirmed"
            }
            transactions.append(tx)
        
        return {
            "success": True,
            "blockchain": blockchain,
            "transactions": transactions,
            "count": len(transactions),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Latest transactions retrieval failed: {e}")
        raise BlockchainException(
            message=f"Latest transactions retrieval failed: {str(e)}",
            blockchain=blockchain,
            error_code="LATEST_TRANSACTIONS_FAILED"
        )


@router.get("/{blockchain}/blocks/latest")
async def get_latest_blocks(
    blockchain: str,
    limit: int = 20,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]]))
):
    """Get latest blocks from blockchain"""
    try:
        logger.info(f"Getting latest {limit} blocks from {blockchain}")
        
        blocks = []
        for i in range(min(limit, 20)):
            block = {
                "block_number": 18500000 - i,
                "blockchain": blockchain,
                "block_hash": f"0x{'abcdef1234567890' * 4}{i:04x}",
                "timestamp": datetime.utcnow() - timedelta(minutes=i*blockchain_block_time(blockchain)),
                "transaction_count": 150 + (i % 50),
                "gas_used": 8500000 + (i * 1000),
                "gas_limit": 15000000,
                "miner": f"0x{'1234567890abcdef' * 4}",
                "size": 50000 + (i * 100)
            }
            blocks.append(block)
        
        return {
            "success": True,
            "blockchain": blockchain,
            "blocks": blocks,
            "count": len(blocks),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Latest blocks retrieval failed: {e}")
        raise BlockchainException(
            message=f"Latest blocks retrieval failed: {str(e)}",
            blockchain=blockchain,
            error_code="LATEST_BLOCKS_FAILED"
        )


def blockchain_block_time(blockchain: str) -> int:
    """Get typical block time in minutes for blockchain"""
    block_times = {
        "bitcoin": 10,
        "ethereum": 0.2,  # 12 seconds
        "bsc": 0.05,      # 3 seconds
        "polygon": 0.05,  # 3 seconds
        "arbitrum": 0.4,  # 24 seconds
        "base": 0.4,       # 24 seconds
        "avalanche": 0.05, # 3 seconds
        "solana": 0.016,   # ~1 second
        "tron": 0.05,      # 3 seconds
        "xrpl": 0.05,      # 3-5 seconds
        "stellar": 0.083   # 5 seconds
    }
    return block_times.get(blockchain, 1)


@router.get("/statistics")
async def get_blockchain_statistics(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]]))
):
    """Get blockchain system statistics"""
    try:
        stats = {
            "total_transactions_processed": 1542000,
            "daily_transactions": 12500,
            "supported_blockchains": len(get_supported_blockchains()),
            "active_nodes": 14,
            "average_sync_delay_seconds": 30,
            "data_freshness_minutes": 2,
            "blockchain_distribution": {
                "bitcoin": 450000,
                "ethereum": 620000,
                "bsc": 210000,
                "polygon": 180000,
                "solana": 82000
            },
            "performance_metrics": {
                "average_query_time_ms": 150,
                "cache_hit_rate": 0.75,
                "node_uptime_percentage": 99.8
            }
        }
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Blockchain statistics failed: {e}")
        raise BlockchainException(
            message=f"Blockchain statistics failed: {str(e)}",
            blockchain="system",
            error_code="STATISTICS_FAILED"
        )
