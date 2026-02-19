# Jackdaw Sentry Security Guide

**Security Guide for Jackdaw Sentry** *(partially implemented)*

Security architecture and practices for Jackdaw Sentry. Items marked ✅ are implemented in code; items marked ⚠️ are documented targets but **not yet wired up**.

## 📋 Table of Contents

- [Security Overview](#security-overview)
- [Secrets Management](#-secrets-management)
- [Authentication & Authorization](#authentication--authorization)
- [Data Protection](#data-protection)
- [GDPR Compliance](#gdpr-compliance)
- [Network Security](#network-security)
- [Application Security](#application-security)
- [Database Security](#database-security)
- [Monitoring & Auditing](#monitoring--auditing)
- [Security Best Practices](#security-best-practices)
- [Incident Response](#incident-response)

## 🔒 Security Overview

Jackdaw Sentry implements defense-in-depth security architecture with multiple layers of protection:

### Security Layers
1. **Network Layer**: Firewall, TLS/SSL, DDoS protection
2. **Application Layer**: Authentication, authorization, input validation
3. **Data Layer**: Encryption at rest and in transit
4. **Infrastructure Layer**: Container security, secrets management
5. **Compliance Layer**: GDPR, audit trails, data retention

### Security Features
- ✅ **JWT Authentication** with role-based access control (implemented in `src/api/auth.py`)
- ✅ **Bcrypt Password Hashing** for user credentials
- ✅ **GDPR Log Filter** redacts sensitive fields in structured logs
- ✅ **Security Headers** via Nginx reverse proxy (`docker/nginx.conf`)
- ✅ **Input Validation** via Pydantic models on all endpoints
- ✅ **Parameterized Queries** via asyncpg (`$1`, `$2` placeholders)
- ✅ **Fernet Encryption** (AES-128-CBC via `cryptography.fernet`) — key derived from `ENCRYPTION_KEY` via SHA-256; encrypt/decrypt verified
- ⚠️ **Audit Logging** with hash-chain integrity (scaffolded, not wired)
- ⚠️ **Rate Limiting** (middleware exists, Redis-backed limits not active)
- ⚠️ **Data Subject Rights** (GDPR endpoints not yet implemented)

## � Secrets Management

### Required Secrets

Jackdaw Sentry requires **6 cryptographic secrets** that must be generated before first run. All secrets must be at least 32 characters and generated from a cryptographically secure source.

| Variable | Purpose | Min Length |
|---|---|---|
| `API_SECRET_KEY` | FastAPI session signing | 32 chars |
| `NEO4J_PASSWORD` | Neo4j graph database auth | any |
| `POSTGRES_PASSWORD` | PostgreSQL database auth | any |
| `REDIS_PASSWORD` | Redis cache/queue auth | any |
| `ENCRYPTION_KEY` | AES-256-GCM data encryption | 32 chars |
| `JWT_SECRET_KEY` | JWT token signing (HS256) | 32 chars |

### Generating Secrets

Generate a single secret:
```bash
openssl rand -hex 32
```

Generate all required secrets at once:
```bash
for var in API_SECRET_KEY NEO4J_PASSWORD POSTGRES_PASSWORD REDIS_PASSWORD ENCRYPTION_KEY JWT_SECRET_KEY; do
  echo "$var=$(openssl rand -hex 32)"
done
```

Or using Python:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Security Rules

- **Never commit** real secrets to version control. Use `.env` (gitignored), not `.env.example`.
- **Rotate secrets** periodically — at minimum after any personnel change or suspected compromise.
- **Use unique secrets** per environment (dev, staging, production).
- **Production deployments** should use a secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager, Docker Secrets) rather than `.env` files.
- The `.env.example` file contains pre-generated example values for local development only. **Regenerate all secrets** for any non-local deployment.

---

## �� Authentication & Authorization

### JWT-Based Authentication
```python
# JWT Token Structure
{
  "sub": "user_id",
  "exp": 1640995200,
  "iat": 1640908800,
  "role": "analyst",
  "permissions": ["read", "write"],
  "session_id": "uuid-here"
}
```

### Role-Based Access Control (RBAC)
```python
# User Roles and Permissions
ROLES = {
    "analyst": ["read", "write"],
    "senior_analyst": ["read", "write", "investigate"],
    "admin": ["read", "write", "investigate", "admin"],
    "super_admin": ["*"]
}

# Permission Matrix
PERMISSIONS = {
    "analysis": ["analyst", "senior_analyst", "admin", "super_admin"],
    "compliance": ["senior_analyst", "admin", "super_admin"],
    "admin": ["admin", "super_admin"]
}
```

### Authentication Flow
```python
# Login Request
POST /api/v1/auth/login
{
  "username": "alice",
  "password": "your_password"
}

# Response
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "username": "alice",
    "role": "admin"
  }
}
```

### API Key Authentication (⚠️ Planned)
```python
# API key authentication is not yet implemented.
# All endpoints currently use JWT Bearer tokens.
```

## 🔐 Data Protection

### Encryption at Rest
```python
# AES-256-GCM Encryption
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key: str):
        self.key = key.encode()
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

### Encryption in Transit
```python
# TLS Configuration
SSL_CONTEXT = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
SSL_CONTEXT.check_hostname = True
SSL_CONTEXT.verify_mode = ssl.CERT_REQUIRED

# HTTPS Only Configuration
app.add_middleware(
    HTTPSRedirectMiddleware,
    https_redirect=True
)
```

### Sensitive Data Handling
```python
# PII Data Masking
def mask_pii(data: str, mask_char: str = "*") -> str:
    if len(data) <= 4:
        return mask_char * len(data)
    return data[:2] + mask_char * (len(data) - 4) + data[-2:]

# Example Usage
email = "user@example.com"
masked_email = mask_pii(email)  # "us***********.com"
```

## 🇪🇺 GDPR Compliance

### Data Subject Rights Implementation
```python
# Right to Access
def get_user_data(user_id: str) -> dict:
    return {
        "personal_data": get_user_personal_data(user_id),
        "processing_activities": get_user_activities(user_id),
        "data_retention": get_user_retention_info(user_id)
    }

# Right to Rectification
def update_user_data(user_id: str, updates: dict) -> bool:
    return update_user_personal_data(user_id, updates)

# Right to Erasure (Right to be Forgotten)
def delete_user_data(user_id: str) -> bool:
    # Delete from all databases
    delete_from_postgres(user_id)
    delete_from_neo4j(user_id)
    delete_from_redis(user_id)
    
    # Log deletion for audit
    log_data_deletion(user_id)
    return True

# Right to Data Portability
def export_user_data(user_id: str) -> dict:
    return {
        "format": "json",
        "data": get_all_user_data(user_id),
        "export_date": datetime.utcnow().isoformat()
    }
```

### Data Retention Policies
```python
# Automated Data Retention
class DataRetentionManager:
    def __init__(self):
        self.retention_policies = {
            "investigation_data": 2555,  # 7 years
            "audit_logs": 2555,          # 7 years
            "user_sessions": 90,         # 30 days
            "temp_data": 7,              # 7 days
            "analytics_data": 365        # 1 year
        }
    
    async def cleanup_expired_data(self):
        for data_type, retention_days in self.retention_policies.items():
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            await self.delete_data_before(data_type, cutoff_date)
```

### Consent Management
```python
# Consent Tracking
class ConsentManager:
    def __init__(self):
        self.consent_types = [
            "data_processing",
            "analytics",
            "marketing",
            "third_party_sharing"
        ]
    
    def record_consent(self, user_id: str, consent_type: str, granted: bool):
        consent_record = {
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": get_client_ip(),
            "user_agent": get_user_agent()
        }
        save_consent_record(consent_record)
    
    def check_consent(self, user_id: str, consent_type: str) -> bool:
        return get_latest_consent(user_id, consent_type)
```

## 🌐 Network Security

### Firewall Configuration
```bash
# UFW Firewall Rules
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (restrict to your IP)
sudo ufw allow from YOUR_IP to any port 22

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block direct API access
sudo ufw deny 8000/tcp

# Rate limiting
sudo ufw limit 22/tcp
sudo ufw limit 80/tcp
sudo ufw limit 443/tcp
```

### TLS/SSL Configuration
```nginx
# SSL Configuration in nginx.conf
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Certificates
    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

### DDoS Protection
```python
# Rate Limiting Middleware
class RateLimitMiddleware:
    def __init__(self, app, calls: int = 100, period: int = 60):
        self.app = app
        self.calls = calls
        self.period = period
        self.clients = defaultdict(list)
    
    async def __call__(self, scope, receive, send):
        client_ip = scope["client"][0]
        now = time.time()
        
        # Clean old requests
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip]
            if now - req_time < self.period
        ]
        
        # Check rate limit
        if len(self.clients[client_ip]) >= self.calls:
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"error": "Rate limit exceeded"}',
            })
            return
        
        self.clients[client_ip].append(now)
        await self.app(scope, receive, send)
```

## 🔒 Application Security

### Input Validation
```python
# Pydantic Models for Input Validation
from pydantic import BaseModel, validator
import re

class AddressAnalysisRequest(BaseModel):
    address: str
    blockchain: str
    include_transactions: bool = False
    risk_analysis: bool = True
    
    @validator('address')
    def validate_address(cls, v):
        if not re.match(r'^[a-zA-Z0-9]+$', v):
            raise ValueError('Invalid address format')
        return v
    
    @validator('blockchain')
    def validate_blockchain(cls, v):
        supported_chains = ['bitcoin', 'ethereum', 'polygon', 'solana']
        if v not in supported_chains:
            raise ValueError(f'Unsupported blockchain: {v}')
        return v
```

### SQL Injection Prevention
```python
# Parameterized Queries
async def get_user_investigations(user_id: str, limit: int = 10):
    query = """
        SELECT id, title, status, created_at 
        FROM investigations 
        WHERE user_id = $1 
        ORDER BY created_at DESC 
        LIMIT $2
    """
    return await database.fetch_all(query, user_id, limit)

# ORM Usage (SQLAlchemy)
from sqlalchemy.orm import Session
from sqlalchemy import text

def get_user_by_id(db: Session, user_id: str):
    return db.query(User).filter(User.id == user_id).first()
```

### XSS Prevention
```python
# Output Encoding
from markupsafe import escape

def render_user_input(user_input: str) -> str:
    return escape(user_input)

# Content Security Policy
CSP_POLICY = {
    "default-src": "'self'",
    "script-src": "'self' 'unsafe-inline'",
    "style-src": "'self' 'unsafe-inline'",
    "img-src": "'self' data: https:",
    "font-src": "'self'",
    "connect-src": "'self'"
}
```

### CSRF Protection
```python
# CSRF Token Implementation
class CSRFProtection:
    def __init__(self, app):
        self.app = app
        self.secret_key = os.environ.get('CSRF_SECRET_KEY')
    
    def generate_token(self, session_id: str) -> str:
        timestamp = str(int(time.time()))
        message = f"{session_id}:{timestamp}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{timestamp}:{signature}"
    
    def validate_token(self, session_id: str, token: str) -> bool:
        try:
            timestamp, signature = token.split(':', 1)
            message = f"{session_id}:{timestamp}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Check if token is recent (5 minutes)
            if int(time.time()) - int(timestamp) > 300:
                return False
            
            return hmac.compare_digest(signature, expected_signature)
        except:
            return False
```

## 🗄️ Database Security

### PostgreSQL Security
```sql
-- Row Level Security (RLS)
ALTER TABLE investigations ENABLE ROW LEVEL SECURITY;

-- Policy for users to see only their own investigations
CREATE POLICY user_investigations_policy ON investigations
    FOR ALL TO application_user
    USING (user_id = current_user_id());

-- Policy for admins to see all investigations
CREATE POLICY admin_investigations_policy ON investigations
    FOR ALL TO admin_user
    USING (true);

-- Database Roles
CREATE ROLE application_user;
CREATE ROLE admin_user;
CREATE ROLE readonly_user;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON investigations TO application_user;
GRANT ALL PRIVILEGES ON investigations TO admin_user;
GRANT SELECT ON investigations TO readonly_user;
```

### Neo4j Security
```cypher
-- Create users with specific permissions
CREATE USER analyst_user SET PASSWORD 'secure_password';
CREATE USER admin_user SET PASSWORD 'secure_password';

-- Grant roles
GRANT ROLE reader TO analyst_user;
GRANT ROLE publisher TO admin_user;

-- Property-based access control
CREATE CONSTRAINT user_id_constraint IF NOT EXISTS FOR (n:Investigation) REQUIRE n.user_id IS NOT NULL;
```

### Redis Security
```bash
# Redis Configuration
# redis.conf
requirepass ${REDIS_PASSWORD}
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command KEYS ""
rename-command CONFIG "CONFIG_b835c3f8a5d2e7f1"
rename-command DEBUG "DEBUG_b835c3f8a5d2e7f1"

# Enable TLS
tls-port 6380
port 0
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt
```

## 📊 Monitoring & Auditing

### Audit Logging
```python
# Comprehensive Audit Logging
class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)
        
        # File handler with rotation
        handler = RotatingFileHandler(
            '/app/logs/audit.log',
            maxBytes=100*1024*1024,  # 100MB
            backupCount=10
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_access(self, user_id: str, action: str, resource: str, 
                   ip_address: str, success: bool = True):
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "ip_address": ip_address,
            "success": success,
            "session_id": get_session_id(),
            "user_agent": get_user_agent()
        }
        self.logger.info(json.dumps(audit_entry))
    
    def log_data_access(self, user_id: str, data_type: str, 
                        data_id: str, purpose: str):
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "data_type": data_type,
            "data_id": data_id,
            "purpose": purpose,
            "legal_basis": "legitimate_interest",
            "retention_period": get_retention_period(data_type)
        }
        self.logger.info(json.dumps(audit_entry))
```

### Security Event Monitoring
```python
# Security Event Detection
class SecurityMonitor:
    def __init__(self):
        self.failed_login_attempts = defaultdict(list)
        self.suspicious_activities = []
        self.alert_thresholds = {
            "failed_logins": 5,
            "suspicious_requests": 10,
            "data_access_anomalies": 20
        }
    
    def detect_brute_force(self, ip_address: str, username: str):
        self.failed_login_attempts[ip_address].append(datetime.utcnow())
        
        # Clean old attempts (last hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.failed_login_attempts[ip_address] = [
            attempt for attempt in self.failed_login_attempts[ip_address]
            if attempt > cutoff
        ]
        
        if len(self.failed_login_attempts[ip_address]) >= self.alert_thresholds["failed_logins"]:
            self.trigger_security_alert("brute_force_attack", {
                "ip_address": ip_address,
                "username": username,
                "attempts": len(self.failed_login_attempts[ip_address])
            })
    
    def detect_data_access_anomalies(self, user_id: str, access_pattern: dict):
        # Implement anomaly detection logic
        if self.is_anomalous_access(user_id, access_pattern):
            self.trigger_security_alert("data_access_anomaly", {
                "user_id": user_id,
                "pattern": access_pattern
            })
```

### Intrusion Detection
```python
# Intrusion Detection System
class IntrusionDetection:
    def __init__(self):
        self.suspicious_patterns = [
            r"union.*select",  # SQL injection
            r"<script.*>",    # XSS
            r"\.\./",          # Path traversal
            r"passwd",         # System file access
            r"etc/shadow"      # Shadow file access
        ]
    
    def scan_request(self, request_data: dict) -> list:
        threats = []
        
        # Scan URL parameters
        for param, value in request_data.get("params", {}).items():
            for pattern in self.suspicious_patterns:
                if re.search(pattern, str(value), re.IGNORECASE):
                    threats.append({
                        "type": "malicious_input",
                        "parameter": param,
                        "pattern": pattern,
                        "value": str(value)[:100]  # Truncate for logging
                    })
        
        # Scan request body
        body = str(request_data.get("body", ""))
        for pattern in self.suspicious_patterns:
            if re.search(pattern, body, re.IGNORECASE):
                threats.append({
                    "type": "malicious_body",
                    "pattern": pattern,
                    "sample": body[:100]
                })
        
        return threats
```

## 🛡️ Security Best Practices

### Password Security
```python
# Password Policy
PASSWORD_POLICY = {
    "min_length": 12,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digits": True,
    "require_special": True,
    "forbidden_patterns": ["password", "123456", "qwerty"],
    "max_age_days": 90
}

# Password Hashing
import bcrypt
import secrets

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

### Session Security
```python
# Session Management
class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.session_timeout = 3600  # 1 hour
    
    def create_session(self, user_id: str) -> str:
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "ip_address": get_client_ip()
        }
        return session_id
    
    def validate_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Check timeout
        if time.time() - session["last_activity"] > self.session_timeout:
            del self.sessions[session_id]
            return False
        
        # Update last activity
        session["last_activity"] = time.time()
        return True
    
    def revoke_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
```

### API Security Headers
```python
# Security Headers Middleware
class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Add security headers to response
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        }
        
        # Process request
        await self.app(scope, receive, send)
```

## 🚨 Incident Response

### Security Incident Response Plan
```python
# Incident Response Framework
class IncidentResponse:
    def __init__(self):
        self.incident_levels = ["low", "medium", "high", "critical"]
        self.incident_types = [
            "data_breach",
            "unauthorized_access",
            "malware_detected",
            "ddos_attack",
            "suspicious_activity"
        ]
    
    def create_incident(self, incident_type: str, severity: str, 
                      description: str, affected_systems: list):
        incident = {
            "id": str(uuid.uuid4()),
            "type": incident_type,
            "severity": severity,
            "description": description,
            "affected_systems": affected_systems,
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
            "assigned_to": get_security_team(),
            "notifications_sent": []
        }
        
        self.save_incident(incident)
        self.notify_stakeholders(incident)
        self.initiate_response(incident)
        
        return incident
    
    def initiate_response(self, incident: dict):
        response_actions = {
            "data_breach": self.handle_data_breach,
            "unauthorized_access": self.handle_unauthorized_access,
            "malware_detected": self.handle_malware,
            "ddos_attack": self.handle_ddos,
            "suspicious_activity": self.handle_suspicious_activity
        }
        
        handler = response_actions.get(incident["type"])
        if handler:
            handler(incident)
```

### Data Breach Response
```python
# Data Breach Handling
def handle_data_breach(incident: dict):
    # 1. Containment
    isolate_affected_systems(incident["affected_systems"])
    
    # 2. Assessment
    breach_scope = assess_breach_scope(incident)
    
    # 3. Notification
    notify_data_protection_officer(incident)
    notify_management(incident)
    
    # 4. Documentation
    document_incident(incident, breach_scope)
    
    # 5. Remediation
    implement_security_measures(breach_scope)
    
    # 6. Reporting
    if breach_scope["requires_regulatory_reporting"]:
        file_regulatory_report(incident, breach_scope)
```

### Security Monitoring Dashboard
```python
# Real-time Security Dashboard
class SecurityDashboard:
    def __init__(self):
        self.metrics = {
            "failed_logins": 0,
            "blocked_ips": 0,
            "suspicious_activities": 0,
            "data_access_requests": 0,
            "security_events": []
        }
    
    def get_security_status(self) -> dict:
        return {
            "overall_status": self.calculate_risk_level(),
            "active_threats": self.get_active_threats(),
            "recent_events": self.get_recent_events(),
            "metrics": self.metrics,
            "recommendations": self.get_security_recommendations()
        }
    
    def calculate_risk_level(self) -> str:
        risk_score = (
            self.metrics["failed_logins"] * 0.1 +
            self.metrics["blocked_ips"] * 0.2 +
            self.metrics["suspicious_activities"] * 0.3
        )
        
        if risk_score < 1:
            return "low"
        elif risk_score < 5:
            return "medium"
        elif risk_score < 10:
            return "high"
        else:
            return "critical"
```

## 📚 Security Resources

### Security Standards
- **ISO 27001** - Information Security Management
- **NIST Cybersecurity Framework** - Security controls
- **OWASP Top 10** - Web application security risks
- **GDPR** - Data protection regulations
- **SOC 2** - Security controls for service organizations

### Security Tools
- **OWASP ZAP** - Web application security scanner
- **Nessus** - Vulnerability scanner
- **Fail2Ban** - Intrusion prevention
- **SELinux** - Security-enhanced Linux
- **AppArmor** - Application security framework

---

**Last Updated**: February 2025  
**Security Status**: ⚠️ Partial — see inline annotations above
