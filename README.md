# Jackdaw Sentry

Enterprise-grade blockchain onchain analysis platform for freelance crypto compliance investigators, focusing on cross-chain stablecoin tracking across 15+ blockchains, Lightning Network analysis, and full EU regulatory compliance (GDPR/DORA/MiCA/AMLR).

## 🎯 Core Capabilities

### Multi-Chain Analysis
- **15+ Blockchains**: Ethereum, Tron, BSC, Solana, Base, Arbitrum, Hyperliquid L1, Polygon, Plasma, Avalanche, XRPL, Stellar, Sei
- **13 Stablecoins**: USDT, USDC, RLUSD, USDe, USDS, USD1, BUSD, A7A5, EURC, EURT, BRZ, EURS
- **Cross-Bridge Tracking**: Monitor stablecoin flows across DEXs and bridges
- **Lightning Network**: Complete channel state and payment routing analysis

### Compliance & Reporting
- **EU Regulations**: Full GDPR/DORA/MiCA/AMLR compliance
- **SAR Generation**: EU AMLR-compliant suspicious activity reporting
- **Investigation Management**: Case tracking for freelance investigators
- **Audit Trails**: Complete investigation history for legal defensibility

### Intelligence Integration
- **OSINT First**: Open-source sanctions lists (OFAC, UN, EU, UK)
- **Dark Web Monitoring**: Threat intelligence from underground sources
- **ML Models**: Address clustering and risk scoring
- **Commercial Extensibility**: Ready for premium intelligence feeds

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- 8GB+ RAM (for local blockchain data)
- 100GB+ storage (for full node data)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/jackdaw-sentry.git
   cd jackdaw-sentry
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

4. **Initialize databases:**
   ```bash
   python scripts/init_databases.py
   ```

5. **Access dashboard:**
   - Web UI: http://localhost:3000
   - API: http://localhost:8000
   - Neo4j Browser: http://localhost:7474

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Blockchain    │    │   Intelligence  │    │   Compliance    │
│   Collectors    │───▶│   Feeds (OSINT) │───▶│   Reports       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Redis Streams │───▶│   Analysis      │───▶│   PostgreSQL    │
│   (Message Q)   │    │   Engine (ML)   │    │   (Compliance)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Neo4j Graph   │
                       │   Database      │
                       └─────────────────┘
```

## 📊 Supported Blockchains

### EVM Compatible
- Ethereum, BSC, Polygon, Avalanche, Arbitrum, Base, Plasma

### Non-EVM
- Solana, Tron, XRPL (Ripple), Stellar, Sei, Hyperliquid L1

### Layer 2 Solutions
- Lightning Network (Bitcoin), Optimistic Rollups, ZK-Rollups

## 💰 Supported Stablecoins

### USD-Pegged
- USDT (Tether), USDC (Circle), BUSD (Binance), RLUSD (Ripple)
- USDe (Ethena), USDS (Sky), USD1 (First Digital), A7A5 (A7)

### EUR-Pegged
- EURC (Circle), EURT (Tether), EURS (Stasis), BRZ (Brazilian Real)

## 🔍 Key Features

### Transaction Analysis
- Real-time cross-chain transaction monitoring
- Stablecoin flow visualization across bridges
- Lightning Network payment routing analysis
- Mixer and privacy tool detection

### Risk Assessment
- ML-powered address clustering
- Sanctions screening (OFAC, UN, EU, UK)
- Dark web threat intelligence integration
- Custom risk scoring models

### Compliance Tools
- EU AMLR-compliant SAR generation
- Investigation case management
- Automated regulatory reporting
- GDPR data subject rights management

## 📚 Documentation

- [Installation Guide](docs/installation.md)
- [API Reference](docs/api/README.md)
- [Database Schema](docs/database/README.md)
- [Compliance Framework](docs/compliance/README.md)
- [Development Guide](docs/development.md)

## 🛡️ Security & Privacy

- **GDPR by Design**: Data minimization and automated deletion
- **End-to-End Encryption**: All data encrypted at rest and in transit
- **Audit Logging**: Complete access tracking for compliance
- **Local Deployment**: Full control over your data

## 📈 Performance

- **Throughput**: 1000+ transactions per second analysis
- **Latency**: Sub-second query responses
- **Storage**: Configurable retention policies (GDPR compliant)
- **Scalability**: Horizontal scaling with Docker Swarm

## 🤝 Contributing

We welcome contributions from the crypto compliance community. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## 🆘 Support

- [Documentation](docs/)
- [Issue Tracker](https://github.com/yourusername/jackdaw-sentry/issues)
- [Discord Community](https://discord.gg/jackdawsentry)

---

**Jackdaw Sentry** - Professional-grade blockchain analysis for the modern compliance investigator.
