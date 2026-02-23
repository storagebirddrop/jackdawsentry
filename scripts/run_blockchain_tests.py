#!/usr/bin/env python3
"""
Jackdaw Sentry Blockchain Analysis Test Runner
Comprehensive test execution for blockchain analysis functionality
"""

import os
import sys
import subprocess
import argparse
import time
import json
from datetime import datetime, timezone
from pathlib import Path

class BlockchainTestRunner:
    """Comprehensive test runner for blockchain analysis"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent.parent / "tests" / "test_blockchain_analysis"
        self.results_dir = Path(__file__).parent.parent / "test_results"
        self.results_dir.mkdir(exist_ok=True)
        
    def run_test_suite(self, test_suite, verbose=False, coverage=False):
        """Run a specific test suite"""
        print(f"\n{'='*60}")
        print(f"Running {test_suite} Test Suite")
        print(f"{'='*60}")
        
        # Build pytest command
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir / f"test_{test_suite}.py"),
            "-v" if verbose else "-q",
            "--tb=short",
            "--durations=10"
        ]
        
        if coverage:
            cmd.extend([
                "--cov=src.analysis",
                "--cov=src.api.routers",
                "--cov-report=html",
                f"--cov-report=term-missing",
                f"--cov-report=json:{self.results_dir / f'coverage_{test_suite}.json'}"
            ])
        
        # Add custom markers
        cmd.extend([
            "-m", "not integration"  # Skip integration tests by default
        ])
        
        print(f"Command: {' '.join(cmd)}")
        
        # Run tests
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        end_time = time.time()
        
        # Save results
        results = {
            "test_suite": test_suite,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": end_time - start_time,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
        
        results_file = self.results_dir / f"test_results_{test_suite}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Print summary
        self.print_test_summary(results)
        
        return results["success"]
    
    def run_all_tests(self, verbose=False, coverage=False, include_integration=False):
        """Run all blockchain analysis tests"""
        print(f"\n{'='*80}")
        print("Running Complete Blockchain Analysis Test Suite")
        print(f"{'='*80}")
        
        test_suites = [
            "address_analysis",
            "transaction_analysis", 
            "pattern_detection",
            "cross_chain_analysis",
            "graph_visualization",
            "alert_system",
            "integration"
        ]
        
        results = {}
        overall_success = True
        
        for test_suite in test_suites:
            if test_suite == "integration" and not include_integration:
                print(f"\nSkipping {test_suite} (use --include-integration to run)")
                continue
                
            success = self.run_test_suite(test_suite, verbose, coverage)
            results[test_suite] = success
            overall_success = overall_success and success
            
            if not success:
                print(f"\n⚠️  {test_suite} tests failed!")
        
        # Generate overall report
        self.generate_overall_report(results)
        
        return overall_success
    
    def run_performance_tests(self):
        """Run performance-focused tests"""
        print(f"\n{'='*60}")
        print("Running Performance Test Suite")
        print(f"{'='*60}")
        
        # Run performance tests with specific markers
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-v",
            "--tb=short",
            "-m", "performance",
            "--benchmark-only",
            "--benchmark-json=" + str(self.results_dir / "benchmark_results.json")
        ]
        
        print(f"Command: {' '.join(cmd)}")
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        end_time = time.time()
        
        results = {
            "test_type": "performance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": end_time - start_time,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
        
        results_file = self.results_dir / "performance_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.print_test_summary(results)
        return results["success"]
    
    def run_integration_tests(self):
        """Run integration tests with real blockchain data"""
        print(f"\n{'='*60}")
        print("Running Integration Test Suite")
        print("⚠️  This requires active blockchain node connections!")
        print(f"{'='*60}")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir / "test_integration.py"),
            "-v",
            "--tb=short",
            "-m", "integration"
        ]
        
        print(f"Command: {' '.join(cmd)}")
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        end_time = time.time()
        
        results = {
            "test_type": "integration",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": end_time - start_time,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
        
        results_file = self.results_dir / "integration_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.print_test_summary(results)
        return results["success"]
    
    def run_smoke_tests(self):
        """Run quick smoke tests"""
        print(f"\n{'='*60}")
        print("Running Smoke Tests")
        print(f"{'='*60}")
        
        # Quick smoke tests
        smoke_tests = [
            str(self.test_dir / "test_address_analysis.py::TestAddressAnalysis::test_address_analysis_risk_scoring"),
            str(self.test_dir / "test_transaction_analysis.py::TestTransactionAnalysis::test_transaction_analysis_basic"),
            str(self.test_dir / "test_pattern_detection.py::TestPatternDetection::test_pattern_detection_basic"),
            str(self.test_dir / "test_alert_system.py::TestAlertSystem::test_alert_creation_basic")
        ]
        
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "--tb=short"
        ] + smoke_tests
        
        print(f"Command: {' '.join(cmd)}")
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        end_time = time.time()
        
        results = {
            "test_type": "smoke",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": end_time - start_time,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
        
        results_file = self.results_dir / "smoke_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.print_test_summary(results)
        return results["success"]
    
    def print_test_summary(self, results):
        """Print test results summary"""
        print(f"\n📊 Test Results Summary")
        print(f"{'='*40}")
        print(f"Test Suite: {results.get('test_suite', results.get('test_type', 'unknown'))}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Duration: {results['duration_seconds']:.2f} seconds")
        print(f"Exit Code: {results['exit_code']}")
        
        if results["success"]:
            print(f"✅ Status: PASSED")
        else:
            print(f"❌ Status: FAILED")
            
            # Show error summary
            if results["stderr"]:
                print(f"\n🚨 Error Summary:")
                error_lines = results["stderr"].split('\n')[-10:]  # Last 10 lines
                for line in error_lines:
                    if line.strip():
                        print(f"   {line}")
        
        print(f"{'='*40}")
    
    def generate_overall_report(self, suite_results):
        """Generate overall test report"""
        report = {
            "report_type": "overall_test_summary",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test_suites": suite_results,
            "total_suites": len(suite_results),
            "passed_suites": sum(1 for success in suite_results.values() if success),
            "failed_suites": sum(1 for success in suite_results.values() if not success),
            "overall_success": all(suite_results.values())
        }
        
        report_file = self.results_dir / "overall_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print overall summary
        print(f"\n{'='*80}")
        print("📋 Overall Test Summary")
        print(f"{'='*80}")
        print(f"Total Test Suites: {report['total_suites']}")
        print(f"Passed: {report['passed_suites']}")
        print(f"Failed: {report['failed_suites']}")
        print(f"Overall Status: {'✅ PASSED' if report['overall_success'] else '❌ FAILED'}")
        print(f"Report saved to: {report_file}")
        print(f"{'='*80}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Jackdaw Sentry Blockchain Analysis Test Runner")
    
    parser.add_argument(
        "--suite", 
        choices=["address_analysis", "transaction_analysis", "pattern_detection", 
                "cross_chain_analysis", "graph_visualization", "alert_system", "integration"],
        help="Run specific test suite"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all test suites"
    )
    
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Run performance tests"
    )
    
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run quick smoke tests"
    )
    
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests (requires blockchain connections)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--include-integration",
        action="store_true",
        help="Include integration tests in --all run"
    )
    
    args = parser.parse_args()
    
    # Change to project directory
    project_dir = Path(__file__).parent.parent
    os.chdir(project_dir)
    
    # Verify test directory exists
    test_dir = project_dir / "tests" / "test_blockchain_analysis"
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        sys.exit(1)
    
    runner = BlockchainTestRunner()
    
    # Run tests based on arguments
    success = True
    
    if args.suite:
        success = runner.run_test_suite(args.suite, args.verbose, args.coverage)
    elif args.performance:
        success = runner.run_performance_tests()
    elif args.smoke:
        success = runner.run_smoke_tests()
    elif args.integration:
        success = runner.run_integration_tests()
    elif args.all:
        success = runner.run_all_tests(args.verbose, args.coverage, args.include_integration)
    else:
        # Default: run smoke tests
        print("No test specified. Running smoke tests...")
        success = runner.run_smoke_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
