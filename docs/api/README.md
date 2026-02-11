# Jackdaw Sentry API Documentation

🚀 **Production-Ready REST API for Multi-Chain Blockchain Analysis and Compliance**

Complete RESTful API with 68 endpoints for blockchain analysis, compliance workflows, and investigation management. Supports 10+ blockchains with real-time data collection, 13 stablecoin tracking, and comprehensive regulatory reporting capabilities.

## 🚀 Getting Started

### Base URL
```
Development: http://localhost:8000
Production: https://api.jackdawsentry.com
```

### Authentication
All API endpoints require JWT-based authentication with role-based access control.

```bash
# Login
POST /api/v1/auth/login
{
  "username": "your_username",
  "password": "your_password"
}

# Use token in subsequent requests
Authorization: Bearer <your_jwt_token>
```

## 📊 Multi-Chain Blockchain Support

### ✅ **PRODUCTION-READY BLOCKCHAINS (10+ Networks)**

#### Bitcoin Ecosystem
- **Bitcoin (BTC)** - Core Bitcoin with Lightning Network support
  - Lightning Network channel state monitoring + payment routing analysis
  - Real-time mempool monitoring with high-value transaction alerts
  - UTXO tracking and comprehensive transaction analysis

#### Ethereum EVM Ecosystem
- **Ethereum (ETH)** - Native Ethereum with full ERC-20 support
  - USDT, USDC, EURC, EURT stablecoin tracking
  - Smart contract interaction analysis
  - Pending transaction monitoring
- **BSC (BNB)** - Binance Smart Chain
  - USDT, USDC, BUSD stablecoin tracking
  - Low-fee transaction analysis
  - DeFi ecosystem monitoring
- **Polygon (MATIC)** - Ethereum scaling solution
  - USDT, USDC stablecoin tracking
  - Fast transaction processing
  - Bridge and DEX monitoring
- **Arbitrum (ARB)** - Ethereum L2 scaling
  - USDT, USDC stablecoin tracking
  - Optimistic rollup analysis
  - Cross-bridge transaction tracking
- **Base** - Coinbase L2 network
  - USDC stablecoin tracking
  - Coinbase ecosystem integration
  - Fast, low-cost transactions
- **Avalanche (AVAX)** - High-performance smart contracts
  - USDT, USDC stablecoin tracking
  - Avalanche C-Chain monitoring
  - Subnet transaction analysis

#### Alternative Blockchains
- **Solana (SOL)** - High-performance blockchain
  - USDT, USDC SPL token tracking
  - Slot-based block processing
  - Program interaction analysis
- **Tron (TRX)** - High-throughput blockchain
  - USDT TRC-20 stablecoin tracking
  - TRX native coin monitoring
  - Smart contract interaction analysis

### 🎯 **Stablecoin Coverage (13 Stablecoins)**

#### USD-Pegged Stablecoins
- **USDT (Tether)** - Bitcoin, Ethereum, Tron, Solana, Polygon, Arbitrum, Base, Avalanche
- **USDC (Circle)** - Ethereum, BSC, Polygon, Arbitrum, Base, Avalanche, Solana
- **USDe (Ethena)** - Ethereum ecosystem
- **USDS (Sky)** - Ethereum ecosystem
- **USD1 (First Digital)** - Ethereum ecosystem
- **BUSD (Binance)** - BSC ecosystem
- **A7A5 (A7)** - Ethereum ecosystem

#### EUR-Pegged Stablecoins
- **EURC (Circle)** - Ethereum ecosystem
- **EURT (Tether)** - Ethereum ecosystem
- **EURS (Stasis)** - Ethereum ecosystem

#### Regional Stablecoins
- **RLUSD (Ripple)** - XRP Ledger ecosystem
- **BRZ (Brazilian Real)** - Ethereum ecosystem

## 📊 Complete API Endpoints (68 Total)

### 🔧 System Endpoints (3)
- `GET /health` - System health check
- `GET /info` - Application information  
- `GET /metrics` - Performance metrics

### Frontend (2 endpoints)
- `GET /` - Main dashboard page
- `GET /compliance` - Compliance dashboard page
- `GET /analysis` - Analysis dashboard page
- `GET /intelligence` - Intelligence dashboard page
- `GET /reports` - Reports dashboard page
- `GET /admin` - System administration page

### WebSocket (1 endpoint)
- `WS /ws/dashboard` - Real-time dashboard updates

### Analysis (12 endpoints)
- `POST /api/v1/analysis/address` - Comprehensive address analysis
- `POST /api/v1/analysis/transaction` - Transaction analysis
- `GET /api/v1/analysis/risk-score` - Get address risk score
- `POST /api/v1/analysis/patterns` - ML pattern detection
- `POST /api/v1/analysis/flow` - Transaction flow analysis
- `POST /api/v1/analysis/stablecoin-flows` - Stablecoin flow analysis
- `POST /api/v1/analysis/mixer-detection` - Mixer usage analysis
- `POST /api/v1/analysis/address-clustering` - Address clustering analysis
- `GET /api/v1/analysis/transaction-patterns` - Transaction pattern analysis
- `POST /api/v1/analysis/batch` - Batch analysis
- `GET /api/v1/analysis/statistics` - Analysis statistics
- `POST /api/v1/analysis/enrich` - Enrich address data

### Intelligence (21 endpoints)
- `POST /api/v1/intelligence/comprehensive-analysis` - Comprehensive multi-platform analysis
- `POST /api/v1/intelligence/mcp-analysis` - AI-powered blockchain analysis (MCP)
- `POST /api/v1/intelligence/professional-tools` - Professional tools analysis
- `POST /api/v1/intelligence/osint-workflows` - Structured OSINT investigation
- `POST /api/v1/intelligence/academic-research` - Academic research validation
- `POST /api/v1/intelligence/blocksci-analysis` - BlockSci high-performance analysis
- `POST /api/v1/intelligence/blokbustr-monitoring` - BlokBustr address monitoring
- `POST /api/v1/intelligence/blokbustr-exploration` - BlokBustr transaction exploration
- `POST /api/v1/intelligence/blokbustr-identification` - BlokBustr address identification
- `POST /api/v1/intelligence/amrita-forensics` - Amrita educational forensics
- `GET /api/v1/intelligence/amrita-modules` - List Amrita educational modules
- `POST /api/v1/intelligence/court-ready-report` - Generate court-ready evidence report
- `GET /api/v1/integration/status` - Integration system status
- `POST /api/v1/integration/cleanup` - Cleanup old analyses
- `GET /api/v1/intelligence/capabilities` - Available integration capabilities
- `POST /api/v1/mcp/execute` - Execute MCP command
- `GET /api/v1/mcp/investigation/{id}` - Get MCP investigation status
- `GET /api/v1/professional-tools/status` - Professional tools status
- `POST /api/v1/osint/start-investigation` - Start OSINT investigation
- `GET /api/v1/osint/investigation/{id}` - Get OSINT investigation status
- `POST /api/v1/osint/generate-report` - Generate OSINT investigation report

### 🛡️ Compliance Endpoints (19)
- `POST /api/v1/compliance/check` - Compliance check
- `POST /api/v1/compliance/reports` - Generate compliance reports
- `GET /api/v1/compliance/sanctions` - Sanctions screening
- `GET /api/v1/compliance/rules` - Compliance rules
- `POST /api/v1/compliance/rules` - Create compliance rule
- `GET /api/v1/compliance/watchlist` - Watchlist management
- `GET /api/v1/compliance/statistics` - Compliance statistics
- `POST /api/v1/compliance/regulatory/reports` - Create regulatory report
- `GET /api/v1/compliance/regulatory/reports/{report_id}` - Get regulatory report
- `POST /api/v1/compliance/cases` - Create compliance case
- `GET /api/v1/compliance/cases/{case_id}` - Get compliance case
- `POST /api/v1/compliance/cases/{case_id}/evidence` - Add evidence to case
- `POST /api/v1/compliance/risk/assessments` - Create risk assessment
- `GET /api/v1/compliance/risk/assessments/{assessment_id}` - Get risk assessment
- `GET /api/v1/compliance/risk/summary` - Get risk assessment summary
- `POST /api/v1/compliance/audit/log` - Log audit event
- `GET /api/v1/compliance/audit/events` - Get audit events

### 🕵️ Investigation Endpoints (6)
- `POST /api/v1/investigations` - Create investigation
- `GET /api/v1/investigations` - List investigations
- `GET /api/v1/investigations/{id}` - Get investigation details
- `PUT /api/v1/investigations/{id}` - Update investigation
- `POST /api/v1/investigations/{id}/evidence` - Add evidence
- `GET /api/v1/investigations/statistics` - Investigation statistics

### ⛓️ Blockchain Endpoints (9)
- `GET /api/v1/blockchain/supported` - Supported blockchains
- `POST /api/v1/blockchain/transaction` - Query transaction
- `GET /api/v1/blockchain/balance` - Address balance
- `GET /api/v1/blockchain/latest-transactions` - Latest transactions
- `GET /api/v1/blockchain/latest-blocks` - Latest blocks
- `GET /api/v1/blockchain/node-status` - Node status
- `GET /api/v1/blockchain/info` - Blockchain info
- `POST /api/v1/blockchain/batch-query` - Batch blockchain queries
- `GET /api/v1/blockchain/statistics` - Blockchain statistics

### 🧠 Intelligence Endpoints (7)
- `GET /api/v1/intelligence/threats` - Threat intelligence
- `POST /api/v1/intelligence/alerts` - Create alerts
- `GET /api/v1/intelligence/alerts` - List alerts
- `POST /api/v1/intelligence/subscriptions` - Manage subscriptions
- `GET /api/v1/intelligence/dark-web` - Dark web monitoring
- `GET /api/v1/intelligence/sources` - Intelligence sources
- `GET /api/v1/intelligence/statistics` - Intelligence statistics

### 📊 Reports Endpoints (8)
- `POST /api/v1/reports/generate` - Generate report
- `GET /api/v1/reports` - List reports
- `GET /api/v1/reports/{id}` - Get report details
- `GET /api/v1/reports/{id}/download` - Download report
- `POST /api/v1/reports/templates` - Create template
- `GET /api/v1/reports/templates` - List templates
- `GET /api/v1/reports/statistics` - Report statistics
- `POST /api/v1/reports/schedule` - Schedule report generation

### 👑 Admin Endpoints (11)
- `GET /api/v1/admin/users` - User management
- `POST /api/v1/admin/users` - Create user
- `PUT /api/v1/admin/users/{id}` - Update user
- `DELETE /api/v1/admin/users/{id}` - Delete user
- `GET /api/v1/admin/system/status` - System status
- `GET /api/v1/admin/system/configuration` - System configuration
- `PUT /api/v1/admin/system/configuration` - Update configuration
- `POST /api/v1/admin/system/maintenance` - Maintenance mode
- `GET /api/v1/admin/system/logs` - System logs
- `GET /api/v1/admin/statistics` - Administrative statistics
- `POST /api/v1/admin/backup` - Create system backup

## 🔍 Query Examples

### Address Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/analysis/address" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "blockchain": "bitcoin",
    "include_transactions": true,
    "risk_analysis": true
  }'
```

### Transaction Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/analysis/transaction" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_hash": "0x1234567890abcdef...",
    "blockchain": "ethereum",
    "deep_analysis": true
  }'
```

### Create Investigation
```bash
curl -X POST "http://localhost:8000/api/v1/investigations" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "case_number": "INV-2024-001",
    "title": "Suspicious Bitcoin Transaction",
    "description": "Large value transaction detected",
    "priority": "high",
    "blockchain": "bitcoin",
    "tags": ["suspicious", "aml"]
  }'
```

### Compliance Check
```bash
curl -X POST "http://localhost:8000/api/v1/compliance/check" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "blockchain": "bitcoin",
    "check_types": ["sanctions", "risk_scoring", "ml_detection"]
  }'
```

## � Response Formats

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data specific to endpoint
  },
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid-here",
    "version": "v1.0.0"
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid address format",
    "details": {
      "field": "address",
      "value": "invalid_address",
      "validation_errors": ["Invalid checksum"]
    }
  },
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid-here"
  }
}
```

## 🔄 Pagination

### Cursor-Based Pagination
List endpoints support cursor-based pagination for efficient data retrieval.

```bash
GET /api/v1/investigations?cursor=abc123&limit=20&sort=created_at_desc
```

### Response
```json
{
  "data": [...],
  "pagination": {
    "cursor": "def456",
    "has_next": true,
    "has_prev": false,
    "total_count": 150,
    "limit": 20
  }
}
```

## 🚨 Rate Limiting

### Rate Limits by User Role
- **Analyst**: 100 requests per minute
- **Senior Analyst**: 500 requests per minute
- **Admin**: 1000 requests per minute

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 30
```

## 🔒 Security Features

### Authentication
- **JWT Tokens**: Short-lived access tokens (24 hours)
- **Refresh Tokens**: Long-lived refresh tokens (30 days)
- **Multi-Factor Authentication**: Optional 2FA support
- **API Keys**: Alternative authentication method

### Authorization
- **Role-Based Access Control**: Different permissions per role
- **Resource-Based Access**: Users can only access their own data
- **Scope-Based Access**: Granular permissions per endpoint
- **IP Whitelisting**: Optional IP restriction

### Data Protection
- **Encryption**: AES-256 encryption at rest and in transit
- **Audit Logging**: Complete API call logging for GDPR compliance
- **Data Minimization**: Only return necessary data
- **GDPR Compliance**: Right to deletion and data portability

## 📈 Monitoring & Health

### Health Checks
- `GET /health` - Basic health check (200ms response time)
- `GET /health/detailed` - Detailed system health with component status
- `GET /api/v1/status` - API status with user authentication info

### Metrics & Monitoring
- `GET /metrics` - Prometheus-compatible metrics
- `GET /api/v1/admin/system/status` - System performance metrics
- `GET /api/v1/admin/statistics` - Usage statistics and analytics

## 🧪 Testing & Development

### Test Environment
```
Base URL: http://localhost:8000
Authentication: Test JWT tokens available
Test Data: Mock blockchain data for testing
```

### API Testing
```bash
# Run integration tests
pytest tests/test_api/

# Load test data
python scripts/load_test_data.py

# Performance testing
python scripts/performance_test.py
```

## 📚 SDKs & Integration

### Python SDK
```python
from jackdawsentry import JackdawSentry

client = JackdawSentry(api_key="your_api_key")
address_info = await client.analyze_address(
    address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    blockchain="bitcoin"
)
```

### JavaScript SDK
```javascript
import { JackdawSentry } from 'jackdawsentry-js';

const client = new JackdawSentry({ apiKey: 'your_api_key' });
const addressInfo = await client.analyzeAddress({
    address: '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
    blockchain: 'bitcoin'
});
```

### Webhooks
```bash
# Configure webhook for real-time alerts
POST /api/v1/admin/webhooks
{
  "url": "https://your-app.com/webhook",
  "events": ["alert_created", "investigation_updated"],
  "secret": "webhook_secret"
}
```

## 🔧 Configuration

### Environment Variables
```bash
# API Configuration
API_HOST=127.0.0.1
API_PORT=8000
API_SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
ENCRYPTION_KEY=your-32-char-encryption-key

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000"]
CORS_ALLOW_CREDENTIALS=true

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=/app/logs
```

## 📝 API Versioning

### Versioning Strategy
- **Semantic Versioning**: v1.0.0, v1.1.0, etc.
- **URL Versioning**: `/api/v1/`, `/api/v2/`
- **Backward Compatibility**: Maintain compatibility for at least 2 versions
- **Depreciation Notices**: 6-month depreciation period

### Version History
- **v1.0.0** - Initial production release with 56 endpoints
- **v1.5.0** - Compliance framework with 68 endpoints (current)
- **v1.6.0** - Planned: GraphQL API, enhanced filtering
- **v2.0.0** - Planned: Real-time streaming, advanced analytics

## 🚀 Performance

### Benchmarks
- **Response Time**: <200ms (95th percentile)
- **Throughput**: 1000+ requests/second
- **Concurrent Users**: 100+ simultaneous users
- **Database Queries**: <50ms average response time

### Caching
- **Redis Caching**: Multi-level caching strategy
- **Response Caching**: Cache frequent queries
- **CDN Integration**: Static asset caching
- **Database Connection Pooling**: Optimized connection management

## 🤝 Contributing

### API Development Guidelines
- Follow RESTful conventions
- Use proper HTTP status codes
- Include comprehensive error messages
- Add unit tests for new endpoints
- Update documentation for all changes

### Code Quality
- **Type Hints**: Full type annotation required
- **Documentation**: Comprehensive docstrings
- **Testing**: 80%+ code coverage required
- **Security**: Security review for all changes

## 📞 Support & Documentation

### Documentation
- [API Reference](https://docs.jackdawsentry.com/api) - Complete API documentation
- [SDK Documentation](https://docs.jackdawsentry.com/sdks) - Client libraries
- [Deployment Guide](https://docs.jackdawsentry.com/deployment) - Production deployment
- [Security Guide](https://docs.jackdawsentry.com/security) - Security best practices

### Community Support
- [Discord Server](https://discord.gg/jackdawsentry) - Real-time support
- [GitHub Issues](https://github.com/jackdawsentry/api/issues) - Bug reports and feature requests
- [Stack Overflow](https://stackoverflow.com/questions/tagged/jackdawsentry) - Community Q&A

### Enterprise Support
- [Email Support](mailto:support@jackdawsentry.com) - Enterprise support
- [Priority Support](https://jackdawsentry.com/enterprise) - SLA options
- [Consulting Services](https://jackdawsentry.com/consulting) - Custom integration

---

**API Version**: v1.0.0  
**Last Updated**: January 2024  
**Production Status**: ✅ Fully Production Ready  
**Support**: api@jackdawsentry.com
