# Database Documentation

Jackdaw Sentry uses a dual-database architecture optimized for blockchain analysis and compliance workflows.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Neo4j Graph   │    │  PostgreSQL     │    │     Redis       │
│   Database      │    │  Compliance    │    │   Cache & MQ    │
│                 │    │   Database     │    │                 │
│ • Transaction   │    │ • SAR Reports  │    │ • Session Store │
│   Flow          │    │ • Investigations│    │ • Message Queue │
│ • Address       │    │ • Audit Trails  │    │ • Caching      │
│   Relationships │    │ • GDPR Data    │    │                 │
│ • Cross-Chain   │    │ • User Mgmt    │    │                 │
│   Analysis      │    │ • Compliance    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📊 Neo4j Graph Database

### Purpose
- **Transaction Flow Analysis**: Track money movement across multiple hops
- **Address Clustering**: Identify related addresses and entities
- **Cross-Chain Analysis**: Follow stablecoin movements between blockchains
- **Lightning Network**: Channel state and routing analysis

### Key Node Types
- **Address**: Blockchain wallet addresses with metadata
- **Transaction**: Individual transactions with value and timestamp
- **Entity**: Clustered addresses representing real-world entities
- **Blockchain**: Supported blockchain networks
- **Stablecoin**: Stablecoin contracts and metadata
- **LightningNode**: Lightning Network nodes
- **LightningChannel**: Lightning Network channels

### Key Relationships
- **SENT**: Money flow between addresses
- **CONTAINS**: Entity-address relationships
- **ISSUED_ON**: Stablecoin-blockchain relationships
- **CHANNEL**: Lightning node connections
- **PART_OF**: Transaction-block relationships

### Schema Features
- **Cross-chain transaction tracking**
- **Stablecoin bridge monitoring**
- **Lightning Network topology**
- **Address clustering algorithms**
- **Risk scoring integration**

## 🗃️ PostgreSQL Compliance Database

### Purpose
- **Regulatory Compliance**: GDPR/DORA/MiCA/AMLR compliance data
- **Investigation Management**: Case tracking and evidence management
- **Audit Trails**: Complete access and modification logs
- **User Management**: Authentication and authorization
- **Reporting**: SAR generation and regulatory reports

### Key Tables

#### Compliance Schema
- **investigations**: Case management and tracking
- **sar_reports**: Suspicious Activity Reports
- **address_watchlists**: Sanctions and high-risk addresses
- **regulatory_reports**: EU regulatory compliance reports
- **users**: User management and permissions

#### Audit Schema
- **audit_log**: Complete audit trail of all modifications
- **data_access_log**: GDPR-compliant access logging

#### GDPR Schema
- **gdpr_requests**: Data subject requests (access, erasure, etc.)
- **data_processing_records**: Article 30 processing records
- **data_breach_incidents**: Data breach tracking and reporting
- **user_consent**: Consent management and tracking

### Compliance Features
- **7-year data retention** (EU AML requirement)
- **Automated data deletion** after retention period
- **Encrypted sensitive data** (GDPR compliance)
- **Consent management** with version tracking
- **Audit logging** for all data access
- **Data subject request** handling

## ⚡ Redis Cache & Message Queue

### Purpose
- **Caching**: Frequently accessed data and query results
- **Session Management**: User session storage
- **Message Queue**: Async task processing
- **Rate Limiting**: API rate limiting
- **Real-time Updates**: WebSocket message broadcasting

### Key Uses
- **Query result caching** for performance
- **Blockchain data buffering** before database storage
- **Background task queuing** for analysis
- **User session storage** for authentication
- **Real-time notifications** for investigation updates

## 🔧 Configuration

### Environment Variables
```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=jackdawsentry_compliance
POSTGRES_USER=jackdawsentry_user
POSTGRES_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password
```

### Connection Pools
- **Neo4j**: 50 max connections
- **PostgreSQL**: 20 max connections
- **Redis**: 20 max connections

## 📈 Performance Optimization

### Neo4j Optimization
- **Indexes** on frequently queried properties
- **Constraints** for data integrity
- **Custom procedures** for complex queries
- **Connection pooling** for concurrent access

### PostgreSQL Optimization
- **Indexes** on foreign keys and search columns
- **Partitioning** for large audit tables
- **Triggers** for automated audit logging
- **Connection pooling** for high concurrency

### Redis Optimization
- **TTL settings** for automatic cache expiration
- **Memory management** for large datasets
- **Pipeline commands** for batch operations
- **Cluster support** for horizontal scaling

## 🔒 Security & Compliance

### Data Protection
- **Encryption at rest** for all sensitive data
- **Encryption in transit** for all connections
- **Access controls** with role-based permissions
- **Audit logging** for all data operations

### GDPR Compliance
- **Data minimization** principles
- **Consent management** with withdrawal support
- **Data subject rights** implementation
- **Automated retention** and deletion policies
- **Breach notification** procedures

### Regulatory Compliance
- **7-year retention** for AML compliance
- **SAR generation** with regulatory templates
- **Audit trails** for legal defensibility
- **Reporting automation** for EU authorities

## 🚀 Scaling Considerations

### Vertical Scaling
- **Memory allocation** for large graph datasets
- **CPU optimization** for complex queries
- **Storage performance** with SSDs
- **Network bandwidth** for high-throughput operations

### Horizontal Scaling
- **Neo4j clustering** (Enterprise Edition)
- **PostgreSQL replication** and sharding
- **Redis clustering** for distributed caching
- **Load balancing** for API services

### Backup & Recovery
- **Automated backups** for all databases
- **Point-in-time recovery** capabilities
- **Cross-region replication** for disaster recovery
- **Regular testing** of backup procedures

## 📊 Monitoring & Maintenance

### Health Checks
- **Connection monitoring** with automatic reconnection
- **Performance metrics** tracking
- **Error rate monitoring** and alerting
- **Resource usage** optimization

### Maintenance Tasks
- **Data cleanup** of expired records
- **Index optimization** for query performance
- **Statistics updates** for query planning
- **Log rotation** and archival

## 🔍 Query Examples

### Neo4j Queries
```cypher
// Find cross-chain stablecoin flows
MATCH path = (start:Address)-[:SENT*1..5]->(end:Address)
WHERE ALL(rel IN relationships(path) WHERE rel.stablecoin = 'USDT')
AND size(collect(DISTINCT rel.blockchain)) > 1
RETURN path, sum(rel.value) as total_value
```

### PostgreSQL Queries
```sql
-- Get open investigations with SAR reports
SELECT i.case_number, i.title, i.status, 
       COUNT(s.id) as sar_count
FROM compliance.investigations i
LEFT JOIN compliance.sar_reports s ON i.id = s.investigation_id
WHERE i.status = 'open'
GROUP BY i.id, i.case_number, i.title, i.status;
```

## 📚 Additional Resources

- [Neo4j Documentation](https://neo4j.com/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [GDPR Compliance Guide](../compliance/gdpr.md)
- [Database Schema Details](schema.md)
