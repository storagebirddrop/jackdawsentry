# Jackdaw Sentry API Developer Guide

## Overview

Jackdaw Sentry is an enterprise blockchain intelligence platform that provides comprehensive attribution, pattern detection, and compliance monitoring across 18+ blockchains. This guide covers API usage, authentication, and best practices for developers.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Best Practices](#best-practices)
7. [SDKs and Libraries](#sdks-and-libraries)
8. [Examples](#examples)

## Getting Started

### Prerequisites

- Python 3.8+ (for Python SDK)
- API access token
- Valid blockchain addresses for testing

### Base URL

```
Production: https://api.jackdawsentry.com
Staging: https://staging-api.jackdawsentry.com
Local: http://localhost:8000
```

### Quick Start

```python
import requests

# Base configuration
BASE_URL = "https://api.jackdawsentry.com"
API_TOKEN = "your_api_token_here"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Test authentication
response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
print(f"Status: {response.status_code}")
print(f"User: {response.json()}")
```

## Authentication

### JWT Token Authentication

All API requests require a valid JWT token in the Authorization header:

```http
Authorization: Bearer <your_jwt_token>
```

### Getting a Token

```python
import requests

# Login credentials
login_data = {
    "username": "your_username",
    "password": "your_password"
}

response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json=login_data
)

if response.status_code == 200:
    token_data = response.json()
    api_token = token_data["access_token"]
    expires_in = token_data["expires_in"]
    
    print(f"Token expires in {expires_in} seconds")
else:
    print(f"Login failed: {response.json()}")
```

### Token Refresh

JWT tokens expire after 30 minutes by default. Implement token refresh logic:

```python
import time
from datetime import datetime, timedelta

class TokenManager:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None
        self.expires_at = None
    
    def get_token(self):
        if not self.token or datetime.now() >= self.expires_at:
            self.refresh_token()
        return self.token
    
    def refresh_token(self):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": self.username, "password": self.password}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
        else:
            raise Exception("Failed to refresh token")

# Usage
token_manager = TokenManager("username", "password")
headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
```

## API Endpoints

### Analysis Endpoints

#### Address Analysis

```http
GET /api/v1/analysis/address/{address}
```

Analyzes a blockchain address for risk factors, transaction patterns, and entity attribution.

**Parameters:**
- `address` (string, required): Blockchain address to analyze
- `include_transactions` (boolean, optional): Include transaction history (default: false)
- `blockchain` (string, optional): Specify blockchain if auto-detection fails

**Response:**
```json
{
  "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
  "blockchain": "bitcoin",
  "risk_score": 0.15,
  "risk_level": "LOW",
  "entity_attribution": {
    "name": "Genesis Block",
    "category": "exchange",
    "confidence": 0.95,
    "source": "internal_database"
  },
  "transaction_patterns": [
    {
      "pattern": "peeling_chain",
      "confidence": 0.87,
      "transactions": ["0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098"]
    }
  ],
  "statistics": {
    "total_transactions": 0,
    "total_value": 0,
    "first_seen": "2009-01-03T00:00:00Z",
    "last_seen": "2009-01-03T00:00:00Z"
  }
}
```

#### Transaction Analysis

```http
GET /api/v1/analysis/transaction/{hash}
```

Analyzes a specific transaction for compliance flags and network connections.

**Parameters:**
- `hash` (string, required): Transaction hash
- `blockchain` (string, optional): Blockchain network

#### Pattern Detection

```http
POST /api/v1/analysis/patterns
```

Detects advanced money laundering patterns across transactions.

**Request Body:**
```json
{
  "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
  "blockchain": "bitcoin",
  "patterns": ["peeling_chain", "layering", "mixing"],
  "timeframe": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-12-31T23:59:59Z"
  }
}
```

### Investigation Endpoints

#### Create Investigation

```http
POST /api/v1/investigations
```

Creates a new investigation case.

**Request Body:**
```json
{
  "title": "Suspicious Bitcoin Address Investigation",
  "description": "Investigating unusual transaction patterns",
  "priority": "HIGH",
  "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
  "tags": ["suspicious", "high_volume"],
  "assigned_to": "analyst_001"
}
```

**Response:**
```json
{
  "id": "inv_123456789",
  "title": "Suspicious Bitcoin Address Investigation",
  "status": "OPEN",
  "priority": "HIGH",
  "created_at": "2024-01-15T10:30:00Z",
  "created_by": "investigator_001",
  "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
  "evidence_count": 0,
  "timeline_events": []
}
```

#### Get Investigation Details

```http
GET /api/v1/investigations/{investigation_id}
```

#### Add Evidence to Investigation

```http
POST /api/v1/investigations/{investigation_id}/evidence
```

**Request Body:**
```json
{
  "type": "transaction_analysis",
  "description": "Suspicious peeling chain pattern detected",
  "data": {
    "transaction_hash": "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",
    "pattern_confidence": 0.92,
    "risk_indicators": ["mixing", "layering"]
  },
  "source": "automated_analysis"
}
```

### Compliance Endpoints

#### Address Screening

```http
POST /api/v1/compliance/screen
```

Screens addresses against sanctions lists and internal risk databases.

**Request Body:**
```json
{
  "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
  "include_sanctions": true,
  "include_risk_scoring": true,
  "jurisdictions": ["US", "EU", "UK"]
}
```

**Response:**
```json
{
  "screening_results": [
    {
      "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
      "sanctions_hits": [],
      "risk_score": 0.15,
      "risk_level": "LOW",
      "risk_factors": [
        {
          "category": "entity_type",
          "description": "Genesis address - historical significance",
          "weight": 0.1
        }
      ],
      "recommendations": ["monitor_transactions"]
    }
  ],
  "overall_risk": "LOW",
  "screened_at": "2024-01-15T10:30:00Z"
}
```

#### Generate Compliance Report

```http
POST /api/v1/compliance/reports
```

**Request Body:**
```json
{
  "report_type": "sar",  // sar, ctr, annual_review
  "period": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-31T23:59:59Z"
  },
  "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
  "format": "pdf"
}
```

### Blockchain Endpoints

#### Get Balance

```http
GET /api/v1/blockchain/balance/{blockchain}/{address}
```

**Example:**
```http
GET /api/v1/blockchain/balance/bitcoin/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```

#### Get Transaction History

```http
GET /api/v1/blockchain/transactions/{blockchain}/{address}
```

**Parameters:**
- `limit` (integer, optional): Maximum transactions to return (default: 100)
- `offset` (integer, optional): Pagination offset (default: 0)
- `start_date` (string, optional): ISO date string
- `end_date` (string, optional): ISO date string

### Intelligence Endpoints

#### Get Aggregated Intelligence

```http
GET /api/v1/intelligence/aggregated
```

#### Get Threat Intelligence

```http
GET /api/v1/intelligence/threats
```

**Parameters:**
- `severity` (string, optional): Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
- `category` (string, optional): Filter by threat category
- `active_only` (boolean, optional): Show only active threats

## Error Handling

### Standard Error Response Format

```json
{
  "error": {
    "code": "INVALID_ADDRESS",
    "message": "Invalid blockchain address format",
    "details": {
      "address": "invalid_address",
      "blockchain": "bitcoin",
      "validation_errors": ["Invalid checksum"]
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_ADDRESS` | Invalid blockchain address format | 400 |
| `INSUFFICIENT_PERMISSIONS` | User lacks required permissions | 403 |
| `RATE_LIMIT_EXCEEDED` | API rate limit exceeded | 429 |
| `BLOCKCHAIN_UNAVAILABLE` | Blockchain node unavailable | 503 |
| `ANALYSIS_TIMEOUT` | Analysis request timed out | 408 |
| `INVALID_TOKEN` | Invalid or expired JWT token | 401 |
| `RESOURCE_NOT_FOUND` | Requested resource not found | 404 |

### Error Handling Best Practices

```python
import requests
from requests.exceptions import RequestException

def analyze_address(address):
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/analysis/address/{address}",
            headers=headers,
            timeout=30
        )
        
        # Handle HTTP errors
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        error_data = e.response.json()
        print(f"API Error: {error_data['error']['code']}")
        print(f"Message: {error_data['error']['message']}")
        
        # Handle specific error cases
        if error_data['error']['code'] == 'RATE_LIMIT_EXCEEDED':
            retry_after = e.response.headers.get('Retry-After', 60)
            print(f"Rate limited. Retry after {retry_after} seconds")
        
        return None
        
    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
        
    except RequestException as e:
        print(f"Network error: {e}")
        return None
```

## Rate Limiting

### Rate Limits

- **Standard Plan**: 100 requests/minute, 10,000 requests/day
- **Professional Plan**: 500 requests/minute, 50,000 requests/day  
- **Enterprise Plan**: 2,000 requests/minute, 200,000 requests/day

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248600
```

### Handling Rate Limits

```python
import time
import requests

def make_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue
        
        response.raise_for_status()
        return response.json()
    
    raise Exception("Max retries exceeded due to rate limiting")
```

## Best Practices

### 1. Use Bulk Operations

For multiple addresses, use bulk endpoints instead of individual requests:

```python
# Bad: Multiple individual requests
for address in addresses:
    result = analyze_address(address)

# Good: Single bulk request
results = bulk_analyze_addresses(addresses)
```

### 2. Implement Caching

Cache frequently requested data to reduce API calls:

```python
import functools
import time
from datetime import timedelta, datetime

def cache_result(ttl_seconds=3600):
    cache = {}
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = datetime.now()
            
            if key in cache:
                cached_time, result = cache[key]
                if (now - cached_time) < timedelta(seconds=ttl_seconds):
                    return result
            
            result = func(*args, **kwargs)
            cache[key] = (now, result)
            return result
        
        return wrapper
    return decorator

@cache_result(ttl_seconds=300)  # 5 minutes cache
def get_address_analysis(address):
    return analyze_address(address)
```

### 3. Handle Timeouts Gracefully

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure session with retries and timeouts
session = requests.Session()

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

def api_request(url, headers, timeout=30):
    try:
        response = session.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
```

### 4. Use Webhooks for Real-time Updates

Instead of polling, use webhooks for real-time alerts:

```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook/alerts', methods=['POST'])
def handle_alert_webhook():
    data = request.json
    
    if data['type'] == 'new_alert':
        alert = data['alert']
        process_alert(alert)
    
    return {'status': 'received'}

def process_alert(alert):
    print(f"New alert: {alert['severity']} - {alert['description']}")
    # Handle alert logic here
```

## SDKs and Libraries

### Python SDK

```bash
pip install jackdawsentry-python
```

```python
from jackdawsentry import JackdawClient

client = JackdawClient(
    api_key="your_api_key",
    base_url="https://api.jackdawsentry.com"
)

# Address analysis
analysis = client.analysis.address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
print(f"Risk score: {analysis.risk_score}")

# Investigation management
investigation = client.investigations.create(
    title="Suspicious Activity",
    addresses=["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
)
```

### JavaScript SDK

```bash
npm install jackdawsentry-js
```

```javascript
import { JackdawClient } from 'jackdawsentry-js';

const client = new JackdawClient({
  apiKey: 'your_api_key',
  baseUrl: 'https://api.jackdawsentry.com'
});

// Address analysis
const analysis = await client.analysis.address('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa');
console.log(`Risk score: ${analysis.risk_score}`);

// Compliance screening
const screening = await client.compliance.screen({
  addresses: ['1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'],
  includeSanctions: true
});
```

## Examples

### Complete Investigation Workflow

```python
import requests
import time

class InvestigationWorkflow:
    def __init__(self, api_token):
        self.base_url = "https://api.jackdawsentry.com"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    def run_investigation(self, suspicious_addresses):
        """Run complete investigation workflow"""
        
        # 1. Create investigation
        investigation = self.create_investigation(suspicious_addresses)
        investigation_id = investigation["id"]
        
        # 2. Analyze each address
        for address in suspicious_addresses:
            analysis = self.analyze_address(address)
            
            # Add evidence if high risk
            if analysis["risk_score"] > 0.7:
                self.add_evidence(investigation_id, {
                    "type": "high_risk_address",
                    "address": address,
                    "risk_score": analysis["risk_score"],
                    "risk_factors": analysis["risk_factors"]
                })
        
        # 3. Check for patterns
        patterns = self.detect_patterns(suspicious_addresses)
        if patterns["patterns"]:
            self.add_evidence(investigation_id, {
                "type": "pattern_detection",
                "patterns": patterns["patterns"]
            })
        
        # 4. Generate compliance report
        report = self.generate_compliance_report(investigation_id)
        
        # 5. Update investigation status
        self.update_investigation_status(investigation_id, "READY_FOR_REVIEW")
        
        return {
            "investigation_id": investigation_id,
            "report_url": report["download_url"],
            "summary": self.get_investigation_summary(investigation_id)
        }
    
    def create_investigation(self, addresses):
        response = requests.post(
            f"{self.base_url}/api/v1/investigations",
            headers=self.headers,
            json={
                "title": f"Investigation of {len(addresses)} suspicious addresses",
                "priority": "HIGH",
                "addresses": addresses
            }
        )
        return response.json()
    
    def analyze_address(self, address):
        response = requests.get(
            f"{self.base_url}/api/v1/analysis/address/{address}",
            headers=self.headers
        )
        return response.json()
    
    def detect_patterns(self, addresses):
        response = requests.post(
            f"{self.base_url}/api/v1/analysis/patterns",
            headers=self.headers,
            json={"addresses": addresses}
        )
        return response.json()
    
    def add_evidence(self, investigation_id, evidence):
        response = requests.post(
            f"{self.base_url}/api/v1/investigations/{investigation_id}/evidence",
            headers=self.headers,
            json=evidence
        )
        return response.json()
    
    def generate_compliance_report(self, investigation_id):
        response = requests.post(
            f"{self.base_url}/api/v1/compliance/reports",
            headers=self.headers,
            json={
                "report_type": "investigation_summary",
                "investigation_id": investigation_id,
                "format": "pdf"
            }
        )
        return response.json()
    
    def update_investigation_status(self, investigation_id, status):
        response = requests.patch(
            f"{self.base_url}/api/v1/investigations/{investigation_id}",
            headers=self.headers,
            json={"status": status}
        )
        return response.json()
    
    def get_investigation_summary(self, investigation_id):
        response = requests.get(
            f"{self.base_url}/api/v1/investigations/{investigation_id}",
            headers=self.headers
        )
        return response.json()

# Usage
workflow = InvestigationWorkflow("your_api_token")

suspicious_addresses = [
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
]

result = workflow.run_investigation(suspicious_addresses)
print(f"Investigation completed: {result['investigation_id']}")
print(f"Report available at: {result['report_url']}")
```

### Real-time Monitoring

```python
import asyncio
import websockets
import json

class AlertMonitor:
    def __init__(self, api_token):
        self.api_token = api_token
        self.websocket_url = "wss://api.jackdawsentry.com/ws/alerts"
    
    async def monitor_alerts(self, callback):
        """Monitor real-time alerts"""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        
        async with websockets.connect(
            self.websocket_url,
            extra_headers=headers
        ) as websocket:
            
            print("Connected to alert stream")
            
            async for message in websocket:
                try:
                    alert_data = json.loads(message)
                    await callback(alert_data)
                except json.JSONDecodeError:
                    print(f"Invalid message: {message}")
    
    async def alert_handler(self, alert):
        """Handle incoming alerts"""
        if alert['severity'] in ['HIGH', 'CRITICAL']:
            print(f"🚨 {alert['severity']}: {alert['description']}")
            
            # Trigger investigation
            if alert['addresses']:
                await self.trigger_investigation(alert['addresses'])
        else:
            print(f"ℹ️ {alert['severity']}: {alert['description']}")
    
    async def trigger_investigation(self, addresses):
        """Automatically trigger investigation for high-priority alerts"""
        # Implementation would call the investigation workflow
        print(f"Triggering investigation for {len(addresses)} addresses")

# Usage
monitor = AlertMonitor("your_api_token")

async def main():
    await monitor.monitor_alerts(monitor.alert_handler)

# Run the monitor
asyncio.run(main())
```

## Support

- **Documentation**: https://docs.jackdawsentry.com
- **API Reference**: https://api.jackdawsentry.com/docs
- **Support Email**: api-support@jackdawsentry.com
- **Status Page**: https://status.jackdawsentry.com

## Changelog

### v1.2.0 (2024-01-15)
- Added cross-chain analysis endpoints
- Improved pattern detection accuracy
- New webhook event types

### v1.1.0 (2024-01-01)
- Added bulk compliance screening
- Enhanced investigation management
- Performance improvements

### v1.0.0 (2023-12-01)
- Initial API release
- Core analysis and investigation features
- Authentication and RBAC system
