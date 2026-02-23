#!/usr/bin/env python3
"""
Jackdaw Sentry - Competitive Benchmarking Runner
Script to run comprehensive competitive assessment and generate reports
"""

import asyncio
import argparse
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from competitive.benchmarking_suite import CompetitiveBenchmarkingSuite
from competitive.competitive_dashboard import CompetitiveDashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_benchmarking_suite(base_url: str, output_dir: str) -> None:
    """Run the complete competitive benchmarking suite"""
    logger.info(f"Starting competitive benchmarking suite for {base_url}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        async with CompetitiveBenchmarkingSuite(base_url) as suite:
            # Run all benchmarks
            results = await suite.run_all_benchmarks()
            
            # Generate timestamp for reports
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            
            # Save detailed results
            results_file = output_path / f"competitive_results_{timestamp}.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            # Save benchmark results
            from dataclasses import asdict
            benchmark_file = output_path / f"benchmark_results_{timestamp}.json"
            benchmark_data = {
                "metadata": {
                    "timestamp": timestamp,
                    "base_url": base_url,
                    "suite_version": "1.0.0"
                },
                "results": [asdict(result) for result in suite.results],
                "competitive_metrics": [asdict(metric) for metric in suite.competitive_metrics],
                "summary": {
                    "overall_parity": suite.calculate_overall_parity(),
                    "market_position": suite.assess_market_position(),
                    "strengths": suite.identify_strengths(),
                    "improvements": suite.identify_improvement_areas(),
                    "recommendations": suite.generate_recommendations()
                }
            }
            
            with open(benchmark_file, 'w') as f:
                json.dump(benchmark_data, f, indent=2, default=str)
            
            # Print summary
            print("\n" + "="*60)
            print("COMPETITIVE BENCHMARKING RESULTS")
            print("="*60)
            
            overall_parity = suite.calculate_overall_parity()
            market_position = suite.assess_market_position()
            
            print(f"\nOverall Competitive Parity: {overall_parity:.1f}%")
            print(f"Market Position: {market_position}")
            
            print(f"\nKey Strengths:")
            for strength in suite.identify_strengths()[:5]:
                print(f"  ✓ {strength}")
            
            print(f"\nImprovement Areas:")
            for improvement in suite.identify_improvement_areas()[:5]:
                print(f"  ○ {improvement}")
            
            print(f"\nRecommendations:")
            for rec in suite.generate_recommendations()[:5]:
                print(f"  → {rec}")
            
            print(f"\nDetailed Reports:")
            print(f"  Results: {results_file}")
            print(f"  Benchmark: {benchmark_file}")
            
            # Return success if parity is above threshold
            if overall_parity >= 80:
                logger.info("Competitive benchmarking completed successfully")
                sys.exit(0)
            else:
                logger.warning("Competitive parity below acceptable threshold")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"Benchmarking suite failed: {e}")
        sys.exit(2)

async def start_dashboard(base_url: str, data_dir: str) -> None:
    """Start the competitive monitoring dashboard"""
    logger.info(f"Starting competitive dashboard for {base_url}")
    
    try:
        async with CompetitiveDashboard(base_url) as dashboard:
            await dashboard.start_monitoring()
            
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")
    except Exception as e:
        logger.error(f"Dashboard failed: {e}")
        sys.exit(2)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Jackdaw Sentry Competitive Assessment Tools"
    )
    
    parser.add_argument(
        "command",
        choices=["benchmark", "dashboard", "both"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL for Jackdaw Sentry API"
    )
    
    parser.add_argument(
        "--output-dir",
        default="./competitive_reports",
        help="Output directory for reports"
    )
    
    parser.add_argument(
        "--data-dir",
        default="./competitive_data",
        help="Data directory for dashboard"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.command == "benchmark":
        asyncio.run(run_benchmarking_suite(args.url, args.output_dir))
    elif args.command == "dashboard":
        asyncio.run(start_dashboard(args.url, args.data_dir))
    elif args.command == "both":
        # Run benchmarking first
        asyncio.run(run_benchmarking_suite(args.url, args.output_dir))
        
        # Then start dashboard
        print("\nStarting dashboard (Ctrl+C to stop)...")
        asyncio.run(start_dashboard(args.url, args.data_dir))

if __name__ == "__main__":
    main()
