#!/usr/bin/env python3
"""
Jackdaw Sentry - Collector Test Script
Test the multi-chain blockchain collectors
"""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from collectors.manager import get_collector_manager
from api.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_collector_initialization():
    """Test collector initialization"""
    logger.info("🚀 Testing Jackdaw Sentry Multi-Chain Collectors")
    
    try:
        # Get collector manager
        manager = get_collector_manager()
        
        # Initialize collectors
        logger.info("📡 Initializing blockchain collectors...")
        await manager.initialize()
        
        # Display initialized collectors
        logger.info(f"✅ Initialized {len(manager.collectors)} collectors:")
        for blockchain in manager.collectors.keys():
            logger.info(f"   - {blockchain}")
        
        # Test collector status
        logger.info("📊 Getting collector status...")
        status = await manager.get_all_status()
        
        logger.info("Collector Status:")
        logger.info(f"   Total Collectors: {status['manager']['total_collectors']}")
        logger.info(f"   Running Collectors: {status['manager']['running_collectors']}")
        
        # Display individual collector status
        for blockchain, collector_status in status['collectors'].items():
            if 'error' in collector_status:
                logger.warning(f"   {blockchain}: ❌ {collector_status['error']}")
            else:
                logger.info(f"   {blockchain}: ✅ Ready")
        
        # Test network stats (if collectors are running)
        logger.info("🌐 Getting network statistics...")
        network_stats = await manager.get_network_stats()
        
        for blockchain, stats in network_stats.items():
            if 'error' in stats:
                logger.warning(f"   {blockchain}: {stats['error']}")
            else:
                logger.info(f"   {blockchain}: {stats}")
        
        logger.info("🎉 Collector test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Collector test failed: {e}")
        raise


async def test_blockchain_connectivity():
    """Test connectivity to blockchain RPCs"""
    logger.info("🔗 Testing blockchain RPC connectivity...")
    
    manager = get_collector_manager()
    await manager.initialize()
    
    connectivity_results = {}
    
    for blockchain, collector in manager.collectors.items():
        try:
            # Test connection
            connected = await collector.connect()
            connectivity_results[blockchain] = connected
            
            if connected:
                logger.info(f"   {blockchain}: ✅ Connected")
                
                # Test getting latest block
                try:
                    latest_block = await collector.get_latest_block_number()
                    logger.info(f"   {blockchain}: Latest block {latest_block}")
                except Exception as e:
                    logger.warning(f"   {blockchain}: Could not get latest block - {e}")
            else:
                logger.warning(f"   {blockchain}: ❌ Connection failed")
            
            # Disconnect
            await collector.disconnect()
            
        except Exception as e:
            logger.error(f"   {blockchain}: ❌ Error - {e}")
            connectivity_results[blockchain] = False
    
    # Summary
    connected_count = sum(1 for connected in connectivity_results.values() if connected)
    total_count = len(connectivity_results)
    
    logger.info(f"📊 Connectivity Summary: {connected_count}/{total_count} blockchains connected")
    
    return connectivity_results


async def test_stablecoin_tracking():
    """Test stablecoin tracking capabilities"""
    logger.info("💰 Testing stablecoin tracking...")
    
    manager = get_collector_manager()
    await manager.initialize()
    
    stablecoin_info = {}
    
    for blockchain, collector in manager.collectors.items():
        try:
            if hasattr(collector, 'stablecoin_contracts'):
                contracts = collector.stablecoin_contracts
                if contracts:
                    logger.info(f"   {blockchain}: {len(contracts)} stablecoins")
                    for symbol in contracts.keys():
                        logger.info(f"      - {symbol}")
                    stablecoin_info[blockchain] = contracts
                else:
                    logger.info(f"   {blockchain}: No stablecoins configured")
            elif hasattr(collector, 'stablecoin_mints'):
                mints = collector.stablecoin_mints
                if mints:
                    logger.info(f"   {blockchain}: {len(mints)} stablecoins")
                    for symbol in mints.keys():
                        logger.info(f"      - {symbol}")
                    stablecoin_info[blockchain] = mints
                else:
                    logger.info(f"   {blockchain}: No stablecoins configured")
            else:
                logger.info(f"   {blockchain}: Stablecoin tracking not implemented")
        
        except Exception as e:
            logger.error(f"   {blockchain}: Error checking stablecoins - {e}")
    
    return stablecoin_info


async def main():
    """Main test function"""
    print("🎯 Jackdaw Sentry - Multi-Chain Collector Test")
    print("=" * 50)
    
    try:
        # Test 1: Collector Initialization
        await test_collector_initialization()
        print()
        
        # Test 2: Blockchain Connectivity
        await test_blockchain_connectivity()
        print()
        
        # Test 3: Stablecoin Tracking
        await test_stablecoin_tracking()
        print()
        
        print("🎉 All tests completed!")
        
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
