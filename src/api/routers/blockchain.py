"""
Jackdaw Sentry - Blockchain Router
Blockchain data and node management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, field_validator
import logging
import time

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_neo4j_session, get_redis_connection
from src.api.exceptions import BlockchainException
from src.api.config import get_supported_blockchains, get_blockchain_config
from src.collectors.rpc.factory import get_rpc_client
from src.collectors.base import Transaction, Block, Address

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class BlockchainQueryRequest(BaseModel):
    blockchain: str
    query_type: str  # transaction, address, block, contract
    identifier: str
    include_details: bool = True
    
    @field_validator('blockchain')
    @classmethod
    def validate_blockchain(cls, v):
        supported = get_supported_blockchains()
        if v.lower() not in supported:
            raise ValueError(f'Unsupported blockchain: {v}')
        return v.lower()

    @field_validator('query_type')
    @classmethod
    def validate_query_type(cls, v):
        valid_types = ["transaction", "address", "block", "contract"]
        if v not in valid_types:
            raise ValueError(f'Invalid query type: {v}')
        return v


class NodeStatusRequest(BaseModel):
    blockchain: str
    node_url: Optional[str] = None
    
    @field_validator('blockchain')
    @classmethod
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
    """Query blockchain data from Neo4j"""
    try:
        start = time.monotonic()
        logger.info(f"Querying {request.blockchain} for {request.query_type}: {request.identifier}")

        data: Dict[str, Any] = {"blockchain": request.blockchain}

        async with get_neo4j_session() as session:
            if request.query_type == "transaction":
                result = await session.run(
                    """
                    OPTIONAL MATCH (t:Transaction {hash: $id, blockchain: $bc})
                    OPTIONAL MATCH (from_a:Address)-[:SENT]->(t)
                    OPTIONAL MATCH (t)-[:RECEIVED]->(to_a:Address)
                    RETURN t, from_a.address AS from_addr, to_a.address AS to_addr
                    """,
                    id=request.identifier, bc=request.blockchain,
                )
                rec = await result.single()
                if rec and rec["t"]:
                    props = dict(rec["t"])
                    data.update(props)
                    data["from_address"] = rec["from_addr"]
                    data["to_address"] = rec["to_addr"]
                else:
                    # Live RPC fallback
                    rpc_tx = await _rpc_lookup_transaction(
                        request.blockchain, request.identifier
                    )
                    if rpc_tx:
                        data.update(_transaction_to_dict(rpc_tx))
                        data["data_source"] = "live_rpc"
                    else:
                        data["transaction_hash"] = request.identifier
                        data["note"] = "Transaction not found in database or via live RPC"

            elif request.query_type == "address":
                result = await session.run(
                    """
                    OPTIONAL MATCH (a:Address {address: $id, blockchain: $bc})
                    OPTIONAL MATCH (a)-[r:SENT|RECEIVED]-()
                    RETURN a, count(r) AS tx_count
                    """,
                    id=request.identifier, bc=request.blockchain,
                )
                rec = await result.single()
                if rec and rec["a"]:
                    props = dict(rec["a"])
                    data.update(props)
                    data["transaction_count"] = rec["tx_count"]
                else:
                    # Live RPC fallback
                    rpc_addr = await _rpc_lookup_address(
                        request.blockchain, request.identifier
                    )
                    if rpc_addr:
                        data.update(_address_to_dict(rpc_addr))
                        data["data_source"] = "live_rpc"
                    else:
                        data["address"] = request.identifier
                        data["transaction_count"] = 0
                        data["note"] = "Address not found in database or via live RPC"

            elif request.query_type == "block":
                result = await session.run(
                    """
                    OPTIONAL MATCH (b:Block {number: toInteger($id), blockchain: $bc})
                    OPTIONAL MATCH (b)-[:CONTAINS]->(t:Transaction)
                    RETURN b, count(t) AS tx_count
                    """,
                    id=request.identifier, bc=request.blockchain,
                )
                rec = await result.single()
                if rec and rec["b"]:
                    props = dict(rec["b"])
                    data.update(props)
                    data["transaction_count"] = rec["tx_count"]
                else:
                    data["block_number"] = request.identifier
                    data["note"] = "Block not found in database"

            else:  # contract
                result = await session.run(
                    "OPTIONAL MATCH (c:Contract {address: $id, blockchain: $bc}) RETURN c",
                    id=request.identifier, bc=request.blockchain,
                )
                rec = await result.single()
                if rec and rec["c"]:
                    data.update(dict(rec["c"]))
                else:
                    data["contract_address"] = request.identifier
                    data["note"] = "Contract not found in database"

        elapsed_ms = int((time.monotonic() - start) * 1000)
        metadata = {
            "query_type": request.query_type,
            "include_details": request.include_details,
            "data_source": data.get("data_source", "neo4j"),
            "processing_time_ms": elapsed_ms,
        }

        return BlockchainResponse(
            success=True, blockchain_data=data,
            metadata=metadata, timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Blockchain query failed: {e}")
        raise BlockchainException(
            message=f"Blockchain query failed: {str(e)}",
            blockchain=request.blockchain,
            error_code="BLOCKCHAIN_QUERY_FAILED",
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
                "last_sync": datetime.now(timezone.utc) - timedelta(minutes=5),
                "sync_status": "healthy"
            }
        
        return {
            "success": True,
            "blockchains": blockchain_info,
            "total_supported": len(supported),
            "timestamp": datetime.now(timezone.utc)
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
            "latest_block_timestamp": datetime.now(timezone.utc) - timedelta(seconds=30),
            "peer_count": 25,
            "rpc_latency_ms": 45,
            "uptime_percentage": 99.8,
            "last_check": datetime.now(timezone.utc)
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
            timestamp=datetime.now(timezone.utc)
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
    """Get latest transactions from Neo4j"""
    try:
        logger.info(f"Getting latest {limit} transactions from {blockchain}")

        async with get_neo4j_session() as session:
            result = await session.run(
                """
                MATCH (t:Transaction {blockchain: $bc})
                RETURN t ORDER BY t.timestamp DESC LIMIT $limit
                """,
                bc=blockchain, limit=min(limit, 50),
            )
            records = await result.data()

        transactions = [dict(r["t"]) for r in records]

        return {
            "success": True,
            "blockchain": blockchain,
            "transactions": transactions,
            "count": len(transactions),
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Latest transactions retrieval failed: {e}")
        raise BlockchainException(
            message=f"Latest transactions retrieval failed: {str(e)}",
            blockchain=blockchain,
            error_code="LATEST_TRANSACTIONS_FAILED",
        )


@router.get("/{blockchain}/blocks/latest")
async def get_latest_blocks(
    blockchain: str,
    limit: int = 20,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]]))
):
    """Get latest blocks from Neo4j"""
    try:
        logger.info(f"Getting latest {limit} blocks from {blockchain}")

        async with get_neo4j_session() as session:
            result = await session.run(
                """
                MATCH (b:Block {blockchain: $bc})
                OPTIONAL MATCH (b)-[:CONTAINS]->(t:Transaction)
                RETURN b, count(t) AS tx_count
                ORDER BY b.number DESC LIMIT $limit
                """,
                bc=blockchain, limit=min(limit, 20),
            )
            records = await result.data()

        blocks = []
        for r in records:
            b = dict(r["b"])
            b["transaction_count"] = r["tx_count"]
            blocks.append(b)

        return {
            "success": True,
            "blockchain": blockchain,
            "blocks": blocks,
            "count": len(blocks),
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Latest blocks retrieval failed: {e}")
        raise BlockchainException(
            message=f"Latest blocks retrieval failed: {str(e)}",
            blockchain=blockchain,
            error_code="LATEST_BLOCKS_FAILED",
        )


# =============================================================================
# New direct-lookup endpoints (M9.1)
# =============================================================================


@router.get("/{blockchain}/tx/{tx_hash}")
async def get_transaction_by_hash(
    blockchain: str,
    tx_hash: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]])),
):
    """Look up a single transaction by hash.

    Checks Neo4j first; falls back to live RPC if not found.
    """
    blockchain = blockchain.lower()
    if blockchain not in get_supported_blockchains():
        raise HTTPException(status_code=400, detail=f"Unsupported blockchain: {blockchain}")

    start = time.monotonic()

    # 1. Neo4j lookup
    async with get_neo4j_session() as session:
        result = await session.run(
            """
            OPTIONAL MATCH (t:Transaction {hash: $id, blockchain: $bc})
            OPTIONAL MATCH (from_a:Address)-[:SENT]->(t)
            OPTIONAL MATCH (t)-[:RECEIVED]->(to_a:Address)
            RETURN t, from_a.address AS from_addr, to_a.address AS to_addr
            """,
            id=tx_hash, bc=blockchain,
        )
        rec = await result.single()

    if rec and rec["t"]:
        data = dict(rec["t"])
        data["from_address"] = rec["from_addr"]
        data["to_address"] = rec["to_addr"]
        data["data_source"] = "neo4j"
    else:
        # 2. Live RPC fallback
        tx = await _rpc_lookup_transaction(blockchain, tx_hash)
        if tx is None:
            raise HTTPException(status_code=404, detail="Transaction not found")
        data = _transaction_to_dict(tx)
        data["data_source"] = "live_rpc"

    elapsed_ms = int((time.monotonic() - start) * 1000)
    return {
        "success": True,
        "blockchain": blockchain,
        "transaction": data,
        "metadata": {"processing_time_ms": elapsed_ms, "data_source": data.get("data_source", "neo4j")},
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/{blockchain}/address/{address}")
async def get_address(
    blockchain: str,
    address: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]])),
):
    """Look up address info (balance, tx count, type).

    Checks Neo4j first; falls back to live RPC if not found.
    """
    blockchain = blockchain.lower()
    if blockchain not in get_supported_blockchains():
        raise HTTPException(status_code=400, detail=f"Unsupported blockchain: {blockchain}")

    normalized_address = address.lower()
    start = time.monotonic()

    # 1. Neo4j lookup
    async with get_neo4j_session() as session:
        result = await session.run(
            """
            OPTIONAL MATCH (a:Address {address: $id, blockchain: $bc})
            OPTIONAL MATCH (a)-[r:SENT|RECEIVED]-()
            RETURN a, count(r) AS tx_count
            """,
            id=normalized_address, bc=blockchain,
        )
        rec = await result.single()

    if rec and rec["a"]:
        data = dict(rec["a"])
        data["transaction_count"] = rec["tx_count"]
        data["data_source"] = "neo4j"
    else:
        # 2. Live RPC fallback
        addr_info = await _rpc_lookup_address(blockchain, normalized_address)
        if addr_info is None:
            raise HTTPException(status_code=404, detail="Address not found")
        data = _address_to_dict(addr_info)
        data["data_source"] = "live_rpc"

    elapsed_ms = int((time.monotonic() - start) * 1000)
    return {
        "success": True,
        "blockchain": blockchain,
        "address": data,
        "metadata": {"processing_time_ms": elapsed_ms, "data_source": data.get("data_source", "neo4j")},
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/{blockchain}/address/{address}/transactions")
async def get_address_transactions(
    blockchain: str,
    address: str,
    limit: int = 25,
    offset: int = 0,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]])),
):
    """Paginated transaction history for an address.

    Checks Neo4j first; falls back to live RPC if available.
    """
    blockchain = blockchain.lower()
    if blockchain not in get_supported_blockchains():
        raise HTTPException(status_code=400, detail=f"Unsupported blockchain: {blockchain}")

    limit = min(max(limit, 1), 50)
    offset = min(max(offset, 0), 10_000)
    start = time.monotonic()
    transactions: List[Dict[str, Any]] = []
    data_source = "neo4j"

    # 1. Neo4j lookup
    async with get_neo4j_session() as session:
        result = await session.run(
            """
            MATCH (a:Address {address: $addr, blockchain: $bc})-[:SENT|RECEIVED]-(t:Transaction)
            RETURN t ORDER BY t.timestamp DESC SKIP $skip LIMIT $limit
            """,
            addr=address.lower(), bc=blockchain, skip=offset, limit=limit,
        )
        records = await result.data()
        transactions = [dict(r["t"]) for r in records]

    # 2. Live RPC fallback if Neo4j returned nothing
    if not transactions:
        client = get_rpc_client(blockchain)
        if client:
            try:
                rpc_txs = await client.get_address_transactions(
                    address, limit=limit, offset=offset
                )
                transactions = [_transaction_to_dict(tx) for tx in rpc_txs]
                data_source = "live_rpc"
            except Exception as exc:
                logger.warning(f"RPC address tx lookup failed for {blockchain}: {exc}")

    elapsed_ms = int((time.monotonic() - start) * 1000)
    return {
        "success": True,
        "blockchain": blockchain,
        "address": address,
        "transactions": transactions,
        "count": len(transactions),
        "metadata": {"processing_time_ms": elapsed_ms, "data_source": data_source, "offset": offset, "limit": limit},
        "timestamp": datetime.now(timezone.utc),
    }


# =============================================================================
# RPC fallback helpers
# =============================================================================


async def _rpc_lookup_transaction(
    blockchain: str, tx_hash: str
) -> Optional[Transaction]:
    """Attempt a live RPC lookup for a transaction. Returns None on failure."""
    client = get_rpc_client(blockchain)
    if client is None:
        return None
    try:
        tx = await client.get_transaction(tx_hash)
        if tx:
            # Cache in Neo4j asynchronously (best-effort)
            try:
                await _store_transaction_neo4j(tx)
            except Exception as exc:
                logger.debug(f"Neo4j cache-store failed: {exc}")
        return tx
    except Exception as exc:
        logger.warning(f"Live RPC tx lookup failed for {blockchain}/{tx_hash}: {exc}")
        return None


async def _rpc_lookup_address(
    blockchain: str, address: str
) -> Optional[Address]:
    """Attempt a live RPC lookup for address info. Returns None on failure."""
    client = get_rpc_client(blockchain)
    if client is None:
        return None
    try:
        return await client.get_address_info(address)
    except Exception as exc:
        logger.warning(f"Live RPC address lookup failed for {blockchain}/{address}: {exc}")
        return None


async def _store_transaction_neo4j(tx: Transaction) -> None:
    """Best-effort cache of a live-fetched transaction into Neo4j."""
    async with get_neo4j_session() as session:
        await session.run(
            """
            MERGE (t:Transaction {hash: $hash, blockchain: $bc})
            ON CREATE SET
                t.value = $value,
                t.timestamp = $ts,
                t.block_number = $block_num,
                t.block_hash = $block_hash,
                t.gas_used = $gas_used,
                t.fee = $fee,
                t.status = $status,
                t.confirmations = $confirmations,
                t.fetched_at = datetime()
            WITH t
            FOREACH (_ IN CASE WHEN $from_addr <> '' THEN [1] ELSE [] END |
                MERGE (from_a:Address {address: $from_addr, blockchain: $bc})
                MERGE (from_a)-[:SENT]->(t)
            )
            FOREACH (_ IN CASE WHEN $to_addr IS NOT NULL AND $to_addr <> '' THEN [1] ELSE [] END |
                MERGE (to_a:Address {address: $to_addr, blockchain: $bc})
                MERGE (t)-[:RECEIVED]->(to_a)
            )
            """,
            hash=tx.hash,
            bc=tx.blockchain,
            value=float(tx.value) if tx.value else 0.0,
            ts=tx.timestamp.isoformat(),
            block_num=tx.block_number,
            block_hash=tx.block_hash,
            gas_used=tx.gas_used,
            fee=tx.fee,
            status=tx.status,
            confirmations=tx.confirmations,
            from_addr=tx.from_address or "",
            to_addr=tx.to_address or "",
        )


def _transaction_to_dict(tx: Transaction) -> Dict[str, Any]:
    """Convert a Transaction dataclass to a JSON-serializable dict."""
    return {
        "hash": tx.hash,
        "blockchain": tx.blockchain,
        "from_address": tx.from_address,
        "to_address": tx.to_address,
        "value": float(tx.value) if tx.value else 0.0,
        "timestamp": tx.timestamp.isoformat() if tx.timestamp else None,
        "block_number": tx.block_number,
        "block_hash": tx.block_hash,
        "gas_used": tx.gas_used,
        "gas_price": tx.gas_price,
        "fee": tx.fee,
        "status": tx.status,
        "confirmations": tx.confirmations,
        "contract_address": tx.contract_address,
        "token_transfers": tx.token_transfers,
    }


def _address_to_dict(addr: Address) -> Dict[str, Any]:
    """Convert an Address dataclass to a JSON-serializable dict."""
    return {
        "address": addr.address,
        "blockchain": addr.blockchain,
        "balance": float(addr.balance) if addr.balance else 0.0,
        "transaction_count": addr.transaction_count,
        "type": addr.type,
        "risk_score": addr.risk_score,
        "labels": addr.labels or [],
        "first_seen": addr.first_seen.isoformat() if addr.first_seen else None,
        "last_seen": addr.last_seen.isoformat() if addr.last_seen else None,
    }


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
    """Get blockchain system statistics from Neo4j"""
    try:
        stats: Dict[str, Any] = {
            "supported_blockchains": len(get_supported_blockchains()),
        }

        async with get_neo4j_session() as session:
            result = await session.run(
                """
                OPTIONAL MATCH (t:Transaction)
                WITH count(t) AS total_tx
                OPTIONAL MATCH (a:Address)
                WITH total_tx, count(a) AS total_addr
                OPTIONAL MATCH (b:Block)
                WITH total_tx, total_addr, count(b) AS total_blk
                OPTIONAL MATCH (t2:Transaction)
                WITH total_tx, total_addr, total_blk,
                     CASE WHEN t2 IS NOT NULL THEN t2.blockchain ELSE NULL END AS bc
                RETURN total_tx, total_addr, total_blk,
                       collect(bc) AS all_bc
                """
            )
            rec = await result.single()
            stats["total_transactions"] = rec["total_tx"] if rec else 0
            stats["total_addresses"] = rec["total_addr"] if rec else 0
            stats["total_blocks"] = rec["total_blk"] if rec else 0

            blockchain_distribution: Dict[str, int] = {}
            if rec:
                for bc in rec["all_bc"]:
                    if bc:
                        blockchain_distribution[bc] = blockchain_distribution.get(bc, 0) + 1
            stats["blockchain_distribution"] = dict(
                sorted(blockchain_distribution.items(), key=lambda x: x[1], reverse=True)
            )

        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Blockchain statistics failed: {e}")
        raise BlockchainException(
            message=f"Blockchain statistics failed: {str(e)}",
            blockchain="system",
            error_code="STATISTICS_FAILED",
        )
