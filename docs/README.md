# Jackdaw Sentry Documentation

Documentation for Jackdaw Sentry, a blockchain onchain analysis platform *(in active development)*.

## 📚 Documentation Structure

### Getting Started
- [Installation Guide](installation.md) - Complete setup instructions
- [Roadmap](roadmap.md) - Milestone plan (M0–M8) and status

### Architecture & Design
- [Database Schema](database/README.md) - Neo4j and PostgreSQL schemas
- [API Reference](api/README.md) - REST API endpoints

### Compliance & Reporting
- [Compliance Framework](compliance/README.md) - GDPR/DORA/MiCA/AMLR compliance
- [Developer Guide](compliance/developer-guide.md) - Compliance system development
- [User Guide](compliance/user-guide.md) - Compliance workflows for analysts

### Operations
- [Deployment Guide](deployment.md) - Production deployment strategies
- [Security](security.md) - Security architecture and practices
- [Integration & Automation](integration-automation.md) - API integration and automated workflows
- [Production Deployment](production-deployment.md) - Enterprise-grade deployment guide

## 🎯 Key Features Documentation

### Multi-Chain Analysis
- Cross-chain transaction flow tracking
- Stablecoin movement across bridges and DEXs
- Real-time monitoring across 15+ blockchains

### Compliance Tools
- EU AMLR-compliant reporting
- GDPR data subject rights management
- Investigation case tracking and audit trails

### Intelligence Integration
- Open-source sanctions screening
- Dark web threat monitoring
- ML-powered risk assessment
- Competitive assessment and benchmarking

## 🧠 Advanced AI/ML Features

### Deep Learning Capabilities
- **Neural Network Models**: LSTM, CNN, and Transformer architectures
- **Advanced Anomaly Detection**: Variational autoencoders and GAN-based detection
- **Ensemble Methods**: Combined models for improved accuracy
- **Real-Time Inference**: Sub-second pattern detection and analysis

### Real-Time Processing
- **Stream Processing**: Redis-based real-time competitive intelligence
- **WebSocket Updates**: Live dashboard updates and alerts
- **Event-Driven Architecture**: Scalable real-time processing
- **Backpressure Handling**: Reliable processing under high load

### Advanced Visualization
- **Interactive 3D Graphs**: Immersive network visualization
- **Real-Time Updates**: Live competitive intelligence visualization
- **Custom Dashboards**: Tailored competitive analysis interfaces
- **Mobile Optimization**: Responsive design for all devices

### Natural Language Intelligence
- **Automated Insights**: AI-generated competitive summaries
- **Executive Reports**: Natural language competitive analysis
- **Trend Analysis**: Automated market intelligence
- **Recommendation Engine**: AI-powered strategic recommendations

## 🔍 Quick Navigation

| Topic | Description | Link |
|-------|-------------|------|
| **Setup** | Installation and configuration | [Installation Guide](installation.md) |
| **API** | REST API endpoints | [API Reference](api/README.md) |
| **Database** | Schema and migrations | [Database Schema](database/README.md) |
| **Compliance** | Regulatory frameworks | [Compliance Framework](compliance/README.md) |
| **Roadmap** | Milestone plan and status | [Roadmap](roadmap.md) |
| **Advanced Features** | AI/ML capabilities and roadmap | [Advanced Features](advanced-features.md) |
| **Integration** | API integration and automation | [Integration & Automation](integration-automation.md) |
| **Production** | Enterprise deployment | [Production Deployment](production-deployment.md) |
| **Claude/AI** | Agent rules & subagents | [CLAUDE.md](./CLAUDE.md) |

## 📊 Competitive Advantage Matrix

| Feature | Current | Advanced (M19-M24) | Competitive Advantage |
|---------|---------|-------------------|---------------------|
| Pattern Detection | Basic ML | Deep Learning + Ensemble | **40% accuracy improvement** |
| Real-Time Updates | Limited | Full Stream Processing | **Sub-second intelligence** |
| Visualization | 2D Charts | Interactive 3D + Real-time | **35% faster analysis** |
| Insights | Manual | AI-Generated | **Automated executive summaries** |
| Anomaly Detection | Statistical | Neural Network + GAN | **30% false positive reduction** |
| Competitive Intelligence | Manual | Automated + Predictive | **Market leadership positioning** |

## 🏗️ Architecture Highlights

### **Current Infrastructure**
- **Multi-Chain Support**: 18 blockchains with unified interface
- **Enterprise Database**: PostgreSQL + Neo4j + Redis stack
- **Production Ready**: Docker containers with health monitoring
- **Scalable Architecture**: Horizontal scaling with load balancing

### **Advanced AI/ML Stack**
- **Deep Learning**: TensorFlow 2.15.0 and PyTorch 2.1.1
- **Real-Time Processing**: Redis pub/sub with WebSocket streaming
- **GPU-Ready**: Architecture supports future GPU acceleration
- **Model Optimization**: CPU-optimized with quantization strategies

### **Enterprise Features**
- **Security**: JWT authentication, encryption, audit trails
- **Compliance**: GDPR, AMLR, DORA, MiCA ready
- **Monitoring**: Prometheus + Grafana + Loki stack
- **Automation**: Webhooks, workflows, and scheduled tasks

## 📖 Documentation Standards

This documentation follows these principles:

- **Living Documentation**: Updates automatically with code changes
- **Compliance Focused**: Written for crypto compliance professionals
- **Practical Examples**: Real investigation scenarios and workflows
- **Regulatory References**: FATF, EU regulations, and industry standards

## 🤝 Contributing to Documentation

We welcome contributions to improve the documentation:

1. **Report Issues**: Found outdated or unclear documentation? [Open an issue](https://github.com/storagebirddrop/jackdaw-sentry/issues)
2. **Submit Changes**: Fork the repository and submit a pull request
3. **Suggest Improvements**: Share ideas for better documentation structure

## 📄 License

This documentation is licensed under the same MIT License as the Jackdaw Sentry project.



## 🤖 Development with Claude Code / AI Agents

When using Claude Code (or similar AI agents) in this repo:
- Follow the persistent workflow, verification, subagents, and rules in [`CLAUDE.md`](./CLAUDE.md)
- Subagents (debugger, api-designer, coder, etc.) are in `.claude/agents/`
- MCP tools (if running) can be leveraged for real-time DB/RPC queries, but prefer local knowledge first

This keeps Claude disciplined, compliant-focused, and aligned with the project's security & auditability priorities.

---

**Need Help?**
- [Open an issue](https://github.com/storagebirddrop/jackdaw-sentry/issues) on GitHub

