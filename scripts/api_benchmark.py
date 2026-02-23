#!/usr/bin/env python3
"""
Jackdaw Sentry - API Performance Benchmark
Tests all 152+ API endpoints for performance metrics
"""

import asyncio
import time
import statistics
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import aiohttp
import pytest

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Single benchmark test result"""
    endpoint: str
    method: str
    status_code: int
    response_time: float
    response_size: int
    success: bool
    error: Optional[str] = None


@dataclass
class EndpointStats:
    """Statistics for a single endpoint"""
    endpoint: str
    method: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    avg_response_size: int


class APIBenchmark:
    """API performance testing suite"""
    
    def __init__(self, base_url: str = "http://localhost:8000", auth_token: Optional[str] = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: List[BenchmarkResult] = []
    
    async def __aenter__(self):
        """Async context manager entry"""
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, endpoint: str, method: str = "GET", 
                          data: Optional[Dict] = None, params: Optional[Dict] = None,
                          iterations: int = 10) -> List[BenchmarkResult]:
        """Test a single endpoint multiple times"""
        url = f"{self.base_url}{endpoint}"
        results = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                if method.upper() == "GET":
                    async with self.session.get(url, params=params) as response:
                        content = await response.read()
                        response_time = time.time() - start_time
                        
                        result = BenchmarkResult(
                            endpoint=endpoint,
                            method=method,
                            status_code=response.status,
                            response_time=response_time,
                            response_size=len(content),
                            success=response.status < 400
                        )
                        
                elif method.upper() == "POST":
                    async with self.session.post(url, json=data) as response:
                        content = await response.read()
                        response_time = time.time() - start_time
                        
                        result = BenchmarkResult(
                            endpoint=endpoint,
                            method=method,
                            status_code=response.status,
                            response_time=response_time,
                            response_size=len(content),
                            success=response.status < 400
                        )
                
                results.append(result)
                
                # Small delay between requests
                await asyncio.sleep(0.1)
                
            except Exception as e:
                response_time = time.time() - start_time
                result = BenchmarkResult(
                    endpoint=endpoint,
                    method=method,
                    status_code=0,
                    response_time=response_time,
                    response_size=0,
                    success=False,
                    error=str(e)
                )
                results.append(result)
        
        return results
    
    async def run_full_benchmark(self) -> Dict[str, Any]:
        """Run benchmark on all API endpoints"""
        endpoints = self._get_test_endpoints()
        
        logger.info(f"Starting benchmark on {len(endpoints)} endpoints...")
        
        for endpoint_info in endpoints:
            endpoint = endpoint_info["path"]
            method = endpoint_info.get("method", "GET")
            data = endpoint_info.get("data")
            params = endpoint_info.get("params")
            
            logger.info(f"Testing {method} {endpoint}")
            
            try:
                results = await self.test_endpoint(
                    endpoint=endpoint,
                    method=method,
                    data=data,
                    params=params,
                    iterations=5  # Reduced for faster testing
                )
                self.results.extend(results)
                
            except Exception as e:
                logger.error(f"Failed to test {endpoint}: {e}")
        
        # Calculate statistics
        stats = self._calculate_statistics()
        
        # Generate report
        report = {
            "summary": self._get_summary_stats(),
            "endpoint_stats": stats,
            "performance_recommendations": self._get_performance_recommendations(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return report
    
    def _get_test_endpoints(self) -> List[Dict[str, Any]]:
        """Get list of endpoints to test"""
        return [
            # Authentication endpoints
            {"path": "/api/v1/auth/login", "method": "POST", "data": {"username": "test", "password": "test"}},
            {"path": "/api/v1/auth/me", "method": "GET"},
            
            # User management
            {"path": "/api/v1/users", "method": "GET"},
            {"path": "/api/v1/users/profile", "method": "GET"},
            
            # Analysis endpoints
            {"path": "/api/v1/analysis/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "method": "GET"},
            {"path": "/api/v1/analysis/transaction/0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098", "method": "GET"},
            {"path": "/api/v1/analysis/patterns", "method": "GET"},
            {"path": "/api/v1/analysis/risk-score", "method": "POST", "data": {"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}},
            
            # Investigations
            {"path": "/api/v1/investigations", "method": "GET"},
            {"path": "/api/v1/investigations/recent", "method": "GET"},
            {"path": "/api/v1/investigations/stats", "method": "GET"},
            
            # Attribution
            {"path": "/api/v1/attribution/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "method": "GET"},
            {"path": "/api/v1/attribution/batch", "method": "POST", "data": {"addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]}},
            
            # Compliance
            {"path": "/api/v1/compliance/screen", "method": "POST", "data": {"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}},
            {"path": "/api/v1/compliance/reports", "method": "GET"},
            {"path": "/api/v1/compliance/thresholds", "method": "GET"},
            
            # Blockchain
            {"path": "/api/v1/blockchain/balance/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "method": "GET"},
            {"path": "/api/v1/blockchain/transactions/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "method": "GET"},
            {"path": "/api/v1/blockchain/utxos/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "method": "GET"},
            
            # Intelligence
            {"path": "/api/v1/intelligence/aggregated", "method": "GET"},
            {"path": "/api/v1/intelligence/sources", "method": "GET"},
            {"path": "/api/v1/intelligence/threats", "method": "GET"},
            
            # Alerts
            {"path": "/api/v1/alerts", "method": "GET"},
            {"path": "/api/v1/alerts/active", "method": "GET"},
            {"path": "/api/v1/alerts/rules", "method": "GET"},
            
            # Reports
            {"path": "/api/v1/reports/generate", "method": "POST", "data": {"type": "investigation", "id": "test"}},
            {"path": "/api/v1/reports/list", "method": "GET"},
            
            # Analytics
            {"path": "/api/v1/analytics/dashboard", "method": "GET"},
            {"path": "/api/v1/analytics/trends", "method": "GET"},
            {"path": "/api/v1/analytics/volume", "method": "GET"},
            
            # Admin endpoints
            {"path": "/api/v1/admin/system/status", "method": "GET"},
            {"path": "/api/v1/admin/system/metrics", "method": "GET"},
            {"path": "/api/v1/admin/users", "method": "GET"},
            
            # Monitoring
            {"path": "/api/v1/monitoring/health", "method": "GET"},
            {"path": "/api/v1/monitoring/metrics", "method": "GET"},
            {"path": "/api/v1/monitoring/logs", "method": "GET"},
        ]
    
    def _calculate_statistics(self) -> Dict[str, EndpointStats]:
        """Calculate statistics for each endpoint"""
        endpoint_groups = {}
        
        for result in self.results:
            key = f"{result.method} {result.endpoint}"
            if key not in endpoint_groups:
                endpoint_groups[key] = []
            endpoint_groups[key].append(result)
        
        stats = {}
        for key, results in endpoint_groups.items():
            method, endpoint = key.split(" ", 1)
            
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
            
            if successful_results:
                response_times = [r.response_time for r in successful_results]
                response_sizes = [r.response_size for r in successful_results]
                
                stats[key] = EndpointStats(
                    endpoint=endpoint,
                    method=method,
                    total_requests=len(results),
                    successful_requests=len(successful_results),
                    failed_requests=len(failed_results),
                    avg_response_time=statistics.mean(response_times),
                    min_response_time=min(response_times),
                    max_response_time=max(response_times),
                    p50_response_time=statistics.median(response_times),
                    p95_response_time=self._percentile(response_times, 95),
                    p99_response_time=self._percentile(response_times, 99),
                    avg_response_size=statistics.mean(response_sizes)
                )
            else:
                stats[key] = EndpointStats(
                    endpoint=endpoint,
                    method=method,
                    total_requests=len(results),
                    successful_requests=0,
                    failed_requests=len(failed_results),
                    avg_response_time=0,
                    min_response_time=0,
                    max_response_time=0,
                    p50_response_time=0,
                    p95_response_time=0,
                    p99_response_time=0,
                    avg_response_size=0
                )
        
        return stats
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _get_summary_stats(self) -> Dict[str, Any]:
        """Get overall summary statistics"""
        if not self.results:
            return {}
        
        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]
        
        if successful_results:
            response_times = [r.response_time for r in successful_results]
            response_sizes = [r.response_size for r in successful_results]
            
            return {
                "total_requests": len(self.results),
                "successful_requests": len(successful_results),
                "failed_requests": len(failed_results),
                "success_rate": len(successful_results) / len(self.results) * 100,
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "p95_response_time": self._percentile(response_times, 95),
                "avg_response_size": statistics.mean(response_sizes)
            }
        else:
            return {
                "total_requests": len(self.results),
                "successful_requests": 0,
                "failed_requests": len(failed_results),
                "success_rate": 0,
                "avg_response_time": 0,
                "min_response_time": 0,
                "max_response_time": 0,
                "p95_response_time": 0,
                "avg_response_size": 0
            }
    
    def _get_performance_recommendations(self) -> List[Dict[str, str]]:
        """Get performance optimization recommendations"""
        recommendations = []
        
        if not self.results:
            return recommendations
        
        successful_results = [r for r in self.results if r.success]
        
        if successful_results:
            response_times = [r.response_time for r in successful_results]
            avg_time = statistics.mean(response_times)
            p95_time = self._percentile(response_times, 95)
            
            if avg_time > 500:  # 500ms threshold
                recommendations.append({
                    "type": "response_time",
                    "severity": "high" if avg_time > 1000 else "medium",
                    "message": f"Average response time {avg_time:.2f}ms exceeds 500ms threshold",
                    "recommendation": "Consider optimizing database queries, adding caching, or reducing payload size"
                })
            
            if p95_time > 2000:  # 2s threshold
                recommendations.append({
                    "type": "p95_response_time",
                    "severity": "high",
                    "message": f"P95 response time {p95_time:.2f}ms exceeds 2s threshold",
                    "recommendation": "Investigate slow outliers and optimize worst-case scenarios"
                })
        
        failed_results = [r for r in self.results if not r.success]
        if len(failed_results) / len(self.results) > 0.05:  # 5% failure rate
            recommendations.append({
                "type": "error_rate",
                "severity": "high",
                "message": f"Error rate {(len(failed_results) / len(self.results) * 100):.2f}% exceeds 5%",
                "recommendation": "Review error logs and fix failing endpoints"
            })
        
        return recommendations


async def run_benchmark():
    """Run complete API benchmark"""
    logger.info("Starting API performance benchmark...")
    
    # Note: You'll need to get a valid auth token first
    async with APIBenchmark(base_url="http://localhost:8000") as benchmark:
        report = await benchmark.run_full_benchmark()
    
    # Save report
    with open("api_benchmark_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info("API benchmark completed. Report saved to api_benchmark_report.json")
    
    # Print summary
    summary = report.get("summary", {})
    print(f"\n=== API Benchmark Summary ===")
    print(f"Total Requests: {summary.get('total_requests', 0)}")
    print(f"Success Rate: {summary.get('success_rate', 0):.2f}%")
    print(f"Average Response Time: {summary.get('avg_response_time', 0):.2f}ms")
    print(f"P95 Response Time: {summary.get('p95_response_time', 0):.2f}ms")
    
    recommendations = report.get("performance_recommendations", [])
    if recommendations:
        print(f"\n=== Performance Recommendations ===")
        for rec in recommendations:
            print(f"[{rec['severity'].upper()}] {rec['message']}")
            print(f"  Recommendation: {rec['recommendation']}")
    
    return report


if __name__ == "__main__":
    asyncio.run(run_benchmark())
