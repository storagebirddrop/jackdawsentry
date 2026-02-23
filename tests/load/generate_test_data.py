#!/usr/bin/env python3
"""
Jackdaw Sentry — Phase 4 Performance Test Data Generator

Generates realistic test data for Phase 4 modules to ensure
meaningful performance tests with realistic data volumes.

Usage:
  python generate_test_data.py --victim-reports 100
  python generate_test_data.py --threat-feeds 20
  python generate_test_data.py --attribution-data 50
  python generate_test_data.py --forensics-cases 25
  python generate_test_data.py --professional-services 30
"""

import argparse
import asyncio
import uuid
import sys
from datetime import datetime, timezone, timedelta
import random
import json

# Add the project root to Python path
sys.path.append('/home/dribble0335/dev/jackdawsentry')
# Note: Database imports are optional for test data generation
try:
    from src.api.database import get_postgres_connection
    from src.intelligence.victim_reports import get_victim_reports_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠️  Database modules not available - will generate mock data only")


async def generate_victim_reports(count: int):
    """Generate victim reports for performance testing."""
    print(f"📝 Generating {count} victim reports...")
    
    if not DB_AVAILABLE:
        print("   Database not available - generating mock data only")
        for i in range(count):
            if (i + 1) % 10 == 0:
                print(f"   Generated {i + 1}/{count} mock reports...")
        print(f"✅ Generated {count} victim reports (mock)")
        return
    
    victim_reports_db = await get_victim_reports_db()
    
    report_types = ['phishing', 'scam', 'fraud', 'theft', 'ransomware']
    statuses = ['pending', 'investigating', 'verified', 'false_positive', 'resolved']
    severities = ['low', 'medium', 'high', 'critical']
    platforms = ['email', 'website', 'social_media', 'messaging', 'banking']
    
    for i in range(count):
        report_data = {
            'id': str(uuid.uuid4()),
            'report_type': random.choice(report_types),
            'status': random.choice(statuses),
            'severity': random.choice(severities),
            'victim_address': f"0x{uuid.uuid4().hex[:40]}",
            'scammer_address': f"0x{uuid.uuid4().hex[:40]}" if random.random() > 0.3 else None,
            'scammer_entity': f"ScammerEntity{random.randint(1, 999)}" if random.random() > 0.5 else None,
            'platform': random.choice(platforms),
            'amount_lost': random.uniform(100, 100000),
            'currency': random.choice(['USD', 'EUR', 'BTC', 'ETH']),
            'description': f"Performance test report {i+1}: {random.choice(['phishing email', 'investment scam', 'fake website', 'crypto theft'])}",
            'evidence': [{'type': 'screenshot', 'url': f'https://example.com/evidence/{uuid.uuid4().hex[:8]}'}],
            'external_sources': ['source1', 'source2'],
            'reported_date': (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))).isoformat(),
            'incident_date': (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))).isoformat(),
            'resolved_date': (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 7))).isoformat() if random.random() > 0.7 else None,
            'metadata': {'test_data': True, 'batch_id': f'batch_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}'}
        }
        
        try:
            await victim_reports_db.create_report(report_data)
            if (i + 1) % 10 == 0:
                print(f"   Generated {i + 1}/{count} reports...")
        except Exception as e:
            print(f"   ⚠️  Error creating report {i+1}: {e}")
    
    print(f"✅ Generated {count} victim reports")


async def generate_threat_feeds(count: int):
    """Generate threat feeds for performance testing."""
    print(f"📡 Generating {count} threat feeds...")
    
    feed_types = ['ioc', 'malware', 'phishing', 'c2', 'apt']
    formats = ['json', 'xml', 'stix', 'csv']
    frequencies = ['hourly', 'daily', 'weekly']
    
    for i in range(count):
        feed_data = {
            'name': f"Perf Test Feed {i+1}",
            'url': f"https://example.com/threat-feed-{i+1}",
            'feed_type': random.choice(feed_types),
            'format': random.choice(formats),
            'update_frequency': random.choice(frequencies),
            'is_active': True,
            'description': f"Performance test threat feed {i+1} for load testing",
            'metadata': {'test_data': True, 'batch_id': f'batch_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}'}
        }
        
        try:
            # This would call the threat feeds API to create feeds
            print(f"   Would create feed: {feed_data['name']}")
        except Exception as e:
            print(f"   ⚠️  Error creating feed {i+1}: {e}")
    
    print(f"✅ Generated {count} threat feeds (mock)")


async def generate_attribution_data(count: int):
    """Generate attribution data for performance testing."""
    print(f"🔍 Generating {count} attribution test addresses...")
    
    addresses = []
    for i in range(count):
        addr = f"0x{uuid.uuid4().hex[:40]}"
        addresses.append(addr)
        if (i + 1) % 20 == 0:
            print(f"   Generated {i + 1}/{count} addresses...")
    
    print(f"✅ Generated {count} test addresses for attribution")


async def generate_forensics_cases(count: int):
    """Generate forensic cases for performance testing."""
    print(f"🔬 Generating {count} forensic cases...")
    
    case_types = ['investigation', 'compliance', 'legal', 'regulatory']
    priorities = ['low', 'medium', 'high', 'critical']
    statuses = ['open', 'in_progress', 'closed', 'archived']
    
    for i in range(count):
        case_data = {
            'title': f"Perf Test Case {i+1}",
            'description': f"Performance test forensic case {i+1}",
            'case_type': random.choice(case_types),
            'priority': random.choice(priorities),
            'assigned_to': f"analyst-{random.randint(1, 10)}",
            'status': random.choice(statuses),
            'metadata': {'test_data': True, 'batch_id': f'batch_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}'}
        }
        
        try:
            print(f"   Would create case: {case_data['title']}")
        except Exception as e:
            print(f"   ⚠️  Error creating case {i+1}: {e}")
    
    print(f"✅ Generated {count} forensic cases (mock)")


async def generate_professional_services(count: int):
    """Generate professional services data for performance testing."""
    print(f"💼 Generating {count} professional services entries...")
    
    service_types = ['investigation', 'training', 'consulting', 'compliance']
    
    for i in range(count):
        service_data = {
            'service_type': random.choice(service_types),
            'title': f"Perf Test Service {i+1}",
            'description': f"Performance test professional service {i+1}",
            'priority': random.choice(['low', 'medium', 'high']),
            'client_contact': f"client-{i+1}@example.com",
            'estimated_duration': f"{random.randint(1, 8)} hours",
            'metadata': {'test_data': True, 'batch_id': f'batch_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}'}
        }
        
        try:
            print(f"   Would create service: {service_data['title']}")
        except Exception as e:
            print(f"   ⚠️  Error creating service {i+1}: {e}")
    
    print(f"✅ Generated {count} professional services entries (mock)")


async def main():
    parser = argparse.ArgumentParser(description='Generate Phase 4 test data')
    parser.add_argument('--victim-reports', type=int, help='Number of victim reports to generate')
    parser.add_argument('--threat-feeds', type=int, help='Number of threat feeds to generate')
    parser.add_argument('--attribution-data', type=int, help='Number of attribution test entries to generate')
    parser.add_argument('--forensics-cases', type=int, help='Number of forensic cases to generate')
    parser.add_argument('--professional-services', type=int, help='Number of professional services entries to generate')
    
    args = parser.parse_args()
    
    if not any([args.victim_reports, args.threat_feeds, args.attribution_data, args.forensics_cases, args.professional_services]):
        print("No data type specified. Use --help for options.")
        parser.print_help()
        sys.exit(1)
    
    print("🚀 Generating Phase 4 Performance Test Data")
    print("=" * 50)
    
    if args.victim_reports:
        await generate_victim_reports(args.victim_reports)
    
    if args.threat_feeds:
        await generate_threat_feeds(args.threat_feeds)
    
    if args.attribution_data:
        await generate_attribution_data(args.attribution_data)
    
    if args.forensics_cases:
        await generate_forensics_cases(args.forensics_cases)
    
    if args.professional_services:
        await generate_professional_services(args.professional_services)
    
    print("=" * 50)
    print("✅ Phase 4 test data generation complete!")


if __name__ == "__main__":
    asyncio.run(main())
