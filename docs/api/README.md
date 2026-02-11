# Jackdaw Sentry API Documentation

RESTful and GraphQL API for blockchain analysis and compliance workflows.

## 🚀 Getting Started

### Base URL
```
Development: http://localhost:8000
Production: https://api.jackdawsentry.com
```

### Authentication
All API endpoints require authentication using JWT tokens.

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

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Get current user info

### Analysis
- `GET /api/v1/analysis/address/{address}` - Analyze address
- `GET /api/v1/analysis/transaction/{hash}` - Analyze transaction
- `POST /api/v1/analysis/cross-chain` - Cross-chain analysis
- `GET /api/v1/analysis/risk-score/{address}` - Get address risk score
- `POST /api/v1/analysis/clustering` - Address clustering analysis

### Investigations
- `GET /api/v1/investigations` - List investigations
- `POST /api/v1/investigations` - Create investigation
- `GET /api/v1/investigations/{id}` - Get investigation details
- `PUT /api/v1/investigations/{id}` - Update investigation
- `POST /api/v1/investigations/{id}/evidence` - Add evidence

### Compliance
- `GET /api/v1/compliance/sars` - List SAR reports
- `POST /api/v1/compliance/sars` - Create SAR report
- `GET /api/v1/compliance/watchlists` - Get watchlists
- `POST /api/v1/compliance/screening` - Address screening
- `GET /api/v1/compliance/reports` - Get compliance reports

### Blockchain
- `GET /api/v1/blockchain/supported` - Supported blockchains
- `GET /api/v1/blockchain/{chain}/info` - Chain information
- `GET /api/v1/blockchain/{chain}/block/{number}` - Get block
- `GET /api/v1/blockchain/{chain}/tx/{hash}` - Get transaction
- `GET /api/v1/blockchain/{chain}/address/{address}` - Address info

### Intelligence
- `GET /api/v1/intelligence/sanctions` - Sanctions lists
- `GET /api/v1/intelligence/dark-web` - Dark web intelligence
- `GET /api/v1/intelligence/threats` - Threat intelligence
- `POST /api/v1/intelligence/enrich` - Enrich address data

### Reports
- `GET /api/v1/reports/sar/{id}` - Get SAR report
- `POST /api/v1/reports/generate` - Generate report
- `GET /api/v1/reports/templates` - Report templates
- `GET /api/v1/reports/history` - Report history

### Admin
- `GET /api/v1/admin/users` - User management
- `GET /api/v1/admin/system` - System status
- `GET /api/v1/admin/metrics` - System metrics
- `POST /api/v1/admin/config` - Update configuration

## 🔍 Query Examples

### Address Analysis
```bash
curl -X GET "http://localhost:8000/api/v1/analysis/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" \
  -H "Authorization: Bearer <token>"
```

### Cross-Chain Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/analysis/cross-chain" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "blockchains": ["bitcoin", "ethereum", "polygon"],
    "time_range": "24h"
  }'
```

### Create Investigation
```bash
curl -X POST "http://localhost:8000/api/v1/investigations" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Suspicious Bitcoin Transaction",
    "description": "Large value transaction detected",
    "priority": "high",
    "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
  }'
```

### SAR Generation
```bash
curl -X POST "http://localhost:8000/api/v1/compliance/sars" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "investigation_id": "uuid-here",
    "reporting_authority": "FIU",
    "suspicious_activity_type": "money_laundering",
    "narrative": "Suspicious pattern detected...",
    "amount": 100000,
    "currency": "USD"
  }'
```

## 📝 GraphQL API

### Endpoint
```
POST /graphql
```

### Schema
```graphql
type Query {
  address(address: String!, blockchain: String!): Address
  transaction(hash: String!, blockchain: String!): Transaction
  investigation(id: ID!): Investigation
  investigations(filter: InvestigationFilter): [Investigation]
  crossChainAnalysis(input: CrossChainInput!): CrossChainResult
}

type Mutation {
  createInvestigation(input: CreateInvestigationInput!): Investigation
  updateInvestigation(id: ID!, input: UpdateInvestigationInput!): Investigation
  createSAR(input: CreateSARInput!): SAR
  addEvidence(investigationId: ID!, evidence: EvidenceInput!): Evidence
}

type Subscription {
  investigationUpdates(investigationId: ID!): InvestigationUpdate
  newAlerts(severity: AlertSeverity): Alert
  systemMetrics: SystemMetrics
}
```

### Example Queries
```graphql
query AddressAnalysis($address: String!, $blockchain: String!) {
  address(address: $address, blockchain: $blockchain) {
    address
    blockchain
    balance
    transactionCount
    riskScore
    firstSeen
    lastSeen
    labels
    transactions(first: 10) {
      edges {
        node {
          hash
          value
          timestamp
          fromAddress
          toAddress
        }
      }
    }
  }
}
```

```graphql
mutation CreateInvestigation($input: CreateInvestigationInput!) {
  createInvestigation(input: $input) {
    id
    caseNumber
    title
    status
    createdAt
  }
}
```

## 📊 Response Formats

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid-here"
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
      "value": "invalid_address"
    }
  },
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid-here"
  }
}
```

## 🔄 Pagination

### List Endpoints
List endpoints support pagination using cursor-based pagination.

```bash
GET /api/v1/investigations?cursor=abc123&limit=20
```

### Response
```json
{
  "data": [...],
  "pagination": {
    "cursor": "def456",
    "has_next": true,
    "has_prev": false,
    "total_count": 150
  }
}
```

## 🚨 Rate Limiting

### Limits
- **Standard Users**: 100 requests per minute
- **Premium Users**: 1000 requests per minute
- **Enterprise Users**: 10000 requests per minute

### Headers
Rate limit information is included in response headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## 🔒 Security

### Authentication
- **JWT Tokens**: Short-lived tokens (24 hours)
- **Refresh Tokens**: Long-lived refresh tokens (30 days)
- **Multi-Factor Authentication**: Optional 2FA support

### Authorization
- **Role-Based Access**: Different permissions for different roles
- **Scope-Based Access**: Granular permissions per endpoint
- **Resource-Based Access**: User can only access their own data

### Data Protection
- **Encryption**: All data encrypted at rest and in transit
- **Audit Logging**: All API calls logged for compliance
- **Data Minimization**: Only return necessary data

## 📈 Monitoring & Metrics

### Health Checks
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed system health
- `GET /api/v1/status` - API status with user info

### Metrics
- `GET /api/v1/admin/metrics` - System performance metrics
- `GET /api/v1/admin/usage` - Usage statistics
- `GET /api/v1/admin/alerts` - System alerts

## 🧪 Testing

### Test Environment
```
Base URL: http://localhost:8000
Test Data: Available in /test-data/
```

### Example Scripts
```bash
# Run API tests
python scripts/test_api.py

# Load test data
python scripts/load_test_data.py

# Performance testing
python scripts/performance_test.py
```

## 📚 SDKs & Libraries

### Python SDK
```python
from jackdawsentry import JackdawSentry

client = JackdawSentry(api_key="your_api_key")
address_info = client.analyze_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
```

### JavaScript SDK
```javascript
import { JackdawSentry } from 'jackdawsentry-js';

const client = new JackdawSentry({ apiKey: 'your_api_key' });
const addressInfo = await client.analyzeAddress('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa');
```

### Go SDK
```go
import "github.com/jackdawsentry/go-sdk"

client := jackdawsentry.NewClient("your_api_key")
addressInfo, err := client.AnalyzeAddress("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
```

## 🔧 Configuration

### Environment Variables
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=your-secret-key
API_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# CORS
ALLOWED_ORIGINS=["http://localhost:3000"]
```

## 📝 Changelog

### v1.0.0 (2024-01-01)
- Initial API release
- Core analysis endpoints
- Authentication and authorization
- Basic compliance features

### v1.1.0 (2024-02-01)
- GraphQL API added
- Enhanced filtering and sorting
- Improved error handling
- Performance optimizations

## 🤝 Contributing

### API Development
- Follow RESTful conventions
- Use proper HTTP status codes
- Include comprehensive error messages
- Add unit tests for new endpoints

### Documentation
- Update API documentation for changes
- Include example requests/responses
- Document error codes
- Provide migration guides

## 📞 Support

### Documentation
- [API Reference](https://docs.jackdawsentry.com/api)
- [GraphQL Schema](https://docs.jackdawsentry.com/graphql)
- [SDK Documentation](https://docs.jackdawsentry.com/sdks)

### Community
- [Discord Server](https://discord.gg/jackdawsentry)
- [GitHub Issues](https://github.com/jackdawsentry/api/issues)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/jackdawsentry)

---

**API Version**: v1.0
**Last Updated**: January 2024
**Support**: api@jackdawsentry.com
