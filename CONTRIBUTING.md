# Contributing to Jackdaw Sentry

🤝 **Contributing Guide for Jackdaw Sentry**

We welcome contributions from the crypto compliance and blockchain analysis community! This guide will help you get started contributing to Jackdaw Sentry.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code of Conduct](#code-of-conduct)
- [Contribution Guidelines](#contribution-guidelines)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## 🚀 Getting Started

### Prerequisites
- **Python 3.11+** - Development environment
- **Docker & Docker Compose** - For local development
- **Git** - Version control
- **GitHub Account** - For pull requests
- **Discord Account** - For community discussion

### Quick Start
```bash
# 1. Fork the repository
git clone https://github.com/YOUR_USERNAME/jackdaw-sentry.git
cd jackdaw-sentry

# 2. Add upstream remote
git remote add upstream https://github.com/storagebirddrop/jackdaw-sentry.git

# 3. Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements-test.txt

# 5. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 6. Start development services
docker compose up -d

# 7. Run database migrations
python -c "
import sys
sys.path.append('.')
from src.api.migrations.migration_manager import run_database_migrations
import asyncio
asyncio.run(run_database_migrations())
"

# 8. Start development server
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

## 🔧 Development Setup

### IDE Configuration
We recommend using **VS Code** with the following extensions:
- **Python** - Python language support
- **Docker** - Docker integration
- **GitLens** - Git history and blame
- **Pylance** - Python type checking
- **Python Docstring Generator** - Documentation generation

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run pre-commit manually
pre-commit run --all-files
```

### Development Dependencies
```bash
# Install development requirements
pip install -r requirements-test.txt

# Key development tools:
# - pytest: Testing framework
# - black: Code formatting
# - isort: Import sorting
# - flake8: Linting
# - mypy: Type checking
# - pre-commit: Git hooks
```

## 📜 Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inclusive environment for all contributors, regardless of:
- Experience level
- Gender identity and expression
- Sexual orientation
- Disability
- Personal appearance
- Body size
- Race
- Ethnicity
- Age
- Religion
- Nationality

### Expected Behavior
- **Be Respectful**: Treat all contributors with respect
- **Be Inclusive**: Welcome newcomers and help them learn
- **Be Collaborative**: Work together to solve problems
- **Be Constructive**: Provide helpful feedback and suggestions
- **Be Professional**: Maintain professional conduct

### Unacceptable Behavior
- Harassment, discrimination, or derogatory language
- Personal attacks or insults
- Public or private harassment
- Publishing others' private information
- Any other conduct that could reasonably be considered inappropriate

### Reporting Issues
If you experience or witness unacceptable behavior, please contact:
- **Email**: conduct@jackdawsentry.com
- **Discord**: Contact moderators directly
- **GitHub**: Report issues to repository maintainers

## 📝 Contribution Guidelines

### Types of Contributions
We welcome the following types of contributions:

#### 🐛 Bug Reports
- Use the issue tracker for bug reports
- Provide detailed reproduction steps
- Include system information
- Add screenshots if applicable

#### ✨ Feature Requests
- Use the issue tracker for feature requests
- Describe the problem you're trying to solve
- Explain why the feature would be valuable
- Consider implementation complexity

#### 📚 Documentation
- Improve existing documentation
- Add missing documentation
- Fix typos and grammatical errors
- Translate documentation to other languages

#### 🧪 Testing
- Add new tests for existing functionality
- Improve test coverage
- Add integration tests
- Add performance tests

#### 🔧 Code Contributions
- Fix bugs and issues
- Implement new features
- Refactor existing code
- Improve performance

### Before You Contribute
1. **Check existing issues** - Search for duplicates
2. **Discuss major changes** - Create an issue first
3. **Follow coding standards** - See below
4. **Write tests** - Ensure test coverage
5. **Update documentation** - Keep docs in sync

## 🔄 Development Workflow

### 1. Create an Issue
- Use descriptive titles
- Provide detailed descriptions
- Add appropriate labels
- Assign to relevant team members

### 2. Create a Branch
```bash
# From your fork
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-number-description

# Or for documentation
git checkout -b docs/update-documentation
```

### 3. Make Changes
- Follow coding standards (see below)
- Write tests for new functionality
- Update documentation
- Commit frequently with clear messages

### 4. Test Your Changes
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api/test_main.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run linting
flake8 src/
black src/
isort src/
mypy src/
```

### 5. Submit Pull Request
- Push to your fork
- Create pull request to upstream
- Fill out PR template
- Request review from maintainers

### 6. Address Feedback
- Respond to review comments promptly
- Make requested changes
- Update tests and documentation
- Re-request review when ready

## 🧪 Testing Guidelines

### Test Structure
```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── performance/    # Performance tests
├── security/       # Security tests
├── compliance/     # Compliance tests
└── e2e/           # End-to-end tests
```

### Writing Tests
```python
# Example test structure
import pytest
from src.api.main import app
from fastapi.testclient import TestClient

class TestExample:
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_example_endpoint(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

### Test Coverage Requirements
- **New Features**: 100% test coverage
- **Bug Fixes**: Tests for the specific bug
- **Refactoring**: No regression in test coverage
- **Minimum Coverage**: 80% overall

### Test Categories
- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **Performance Tests**: Test performance characteristics
- **Security Tests**: Test security vulnerabilities
- **Compliance Tests**: Test GDPR/AML compliance

## 📚 Documentation

### Documentation Structure
```
docs/
├── api/            # API documentation
├── deployment/     # Deployment guides
├── security/       # Security guides
├── development/    # Development guides
├── user-guide/     # User documentation
└── architecture/   # Architecture documentation
```

### Writing Documentation
- Use clear, concise language
- Include code examples
- Add screenshots where helpful
- Follow markdown formatting
- Update table of contents

### API Documentation
- Document all endpoints
- Include request/response examples
- Document authentication requirements
- Add error codes and handling

## 🔄 Pull Request Process

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
- [ ] Ready for review
```

### Review Process
1. **Automated Checks**: CI/CD pipeline validation
2. **Peer Review**: At least one maintainer review
3. **Security Review**: For security-sensitive changes
4. **Documentation Review**: For documentation changes
5. **Final Approval**: Maintainer approval required

### Merge Requirements
- All tests passing
- Code review approved
- Documentation updated
- No merge conflicts
- Security review completed (if applicable)

## 📋 Coding Standards

### Python Style Guide
- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://black.readthedocs.io/) for formatting
- Use [isort](https://isort.readthedocs.io/) for import sorting
- Use [mypy](https://mypy.readthedocs.io/) for type checking

### Code Organization
```python
# Import order: standard library, third-party, local
import os
import sys
from typing import Optional

import fastapi
import pydantic

from src.api import config
from src.api.database import get_db

# Constants at top
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Classes and functions
class ExampleClass:
    """Example class with docstring."""
    
    def __init__(self, param: str):
        self.param = param
    
    def method(self) -> str:
        """Example method with docstring."""
        return self.param.upper()
```

### Type Hints
```python
from typing import List, Dict, Optional, Union

def process_data(
    data: List[Dict[str, str]],
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Union[str, int]]:
    """Process data with type hints."""
    return {"processed": len(data)}
```

### Error Handling
```python
import logging

logger = logging.getLogger(__name__)

def risky_operation() -> str:
    """Perform risky operation with proper error handling."""
    try:
        # Risky operation here
        result = "success"
        return result
    except ValueError as e:
        logger.error(f"Value error in risky_operation: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in risky_operation: {e}")
        raise
```

### Security Considerations
- Never commit secrets or API keys
- Use environment variables for configuration
- Validate all user input
- Use parameterized queries for database operations
- Implement proper authentication and authorization

## 🚀 Release Process

### Version Bumping
```bash
# Bump patch version
bump2version patch

# Bump minor version
bump2version minor

# Bump major version
bump2version major
```

### Release Checklist
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Version bumped
- [ ] Tag created
- [ ] Release notes prepared
- [ ] Security review completed

### Release Steps
1. Update version numbers
2. Update CHANGELOG.md
3. Create release tag
4. Generate release notes
5. Deploy to staging
6. Test staging deployment
7. Deploy to production
8. Monitor production deployment

## 🏆 Recognition

### Contributor Recognition
- Contributors listed in README.md
- Featured in release notes
- Recognition in Discord community
- Annual contributor awards

### Contribution Types
- **Code Contributions**: Bug fixes, features, refactoring
- **Documentation**: Docs, guides, tutorials
- **Testing**: Test cases, test infrastructure
- **Community**: Support, moderation, feedback
- **Design**: UI/UX, graphics, branding

## 📞 Getting Help

### Resources
- **Documentation**: [docs/](docs/)
- **Discord Community**: [Jackdaw Sentry Discord](https://discord.gg/jackdawsentry)
- **GitHub Issues**: [Issue Tracker](https://github.com/yourusername/jackdaw-sentry/issues)
- **Email**: dev@jackdawsentry.com

### Getting Started Help
- **New Contributors**: Ask in Discord #new-contributors
- **Technical Questions**: Ask in Discord #development
- **Documentation**: Ask in Discord #documentation
- **General**: Ask in Discord #general

### Code Review Help
- **First PR**: Request help in Discord #code-review
- **Complex Changes**: Ask for design review
- **Security**: Tag @security-team in PR
- **Performance**: Tag @performance-team in PR

## 📄 License

By contributing to Jackdaw Sentry, you agree that your contributions will be licensed under the MIT License, the same license as the project.

---

## 🙏 Thank You

Thank you for contributing to Jackdaw Sentry! Your contributions help make blockchain analysis and compliance tools better for everyone.

**Happy Contributing!** 🚀

---

**Contributing Guide Version**: v1.0.0  
**Last Updated**: January 2024  
**Maintainers**: Jackdaw Sentry Team  
**Contact**: dev@jackdawsentry.com
