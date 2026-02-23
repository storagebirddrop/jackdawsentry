# Jackdaw Sentry Security Configuration

# Security Testing Configuration for All Phases (1-4)
# This file defines security requirements and test configurations

## Authentication & Authorization
AUTHENTICATION_REQUIRED = True
JWT_SECRET_KEY_REQUIRED = True
PASSWORD_MIN_LENGTH = 8
PASSWORD_COMPLEXITY_REQUIRED = True
SESSION_TIMEOUT_MINUTES = 30
MAX_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCKOUT_DURATION_MINUTES = 15

## Data Protection
ENCRYPTION_AT_REST = True
ENCRYPTION_IN_TRANSIT = True
GDPR_COMPLIANCE = True
DATA_RETENTION_DAYS = 365
PERSONAL_DATA_REDIRECTION = True
AUDIT_LOGGING = True

## Input Validation
SQL_INJECTION_PROTECTION = True
XSS_PROTECTION = True
CSRF_PROTECTION = True
FILE_TYPE_VALIDATION = True
MAX_FILE_SIZE_MB = 10
ALLOWED_FILE_TYPES = ['txt', 'pdf', 'json', 'csv', 'png', 'jpg', 'jpeg']

## Rate Limiting
RATE_LIMITING_ENABLED = True
REQUESTS_PER_MINUTE = 100
BURST_LIMIT = 20
RATE_LIMIT_PER_USER = True
RATE_LIMIT_PER_IP = True

## Security Headers
SECURITY_HEADERS_ENABLED = True
X_FRAME_OPTIONS = "DENY"
X_CONTENT_TYPE_OPTIONS = "nosniff"
X_XSS_PROTECTION = "1; mode=block"
REFERRER_POLICY = "strict-origin-when-cross-origin"
CONTENT_SECURITY_POLICY = "default-src 'self'"

## Phase 4 Module Security
VICTIM_REPORTS_PERMISSIONS = {
    'read': ['admin', 'analyst', 'viewer'],
    'write': ['admin', 'analyst'],
    'delete': ['admin']
}

THREAT_FEEDS_PERMISSIONS = {
    'read': ['admin', 'analyst', 'viewer'],
    'write': ['admin', 'analyst'],
    'delete': ['admin']
}

ATTRIBUTION_PERMISSIONS = {
    'read': ['admin', 'analyst', 'viewer'],
    'write': ['admin', 'analyst'],
    'delete': ['admin']
}

PROFESSIONAL_SERVICES_PERMISSIONS = {
    'read': ['admin', 'analyst', 'viewer'],
    'write': ['admin', 'analyst'],
    'delete': ['admin']
}

FORENSICS_PERMISSIONS = {
    'read': ['admin', 'analyst', 'viewer'],
    'write': ['admin', 'analyst'],
    'delete': ['admin']
}

## Compliance Requirements
GDPR_ARTICLES = [
    'ARTICLE_5_DATA_MINIMIZATION',
    'ARTICLE_6_LAWFULNESS',
    'ARTICLE_7_LIMITATION',
    'ARTICLE_9_SPECIAL_CATEGORIES',
    'ARTICLE_15_RIGHT_OF_ACCESS',
    'ARTICLE_16_RIGHT_TO_RECTIFICATION',
    'ARTICLE_17_RIGHT_TO_ERASURE',
    'ARTICLE_20_RIGHT_TO_DATA_PORTABILITY'
]

SECURITY_STANDARDS = [
    'ISO_27001',
    'SOC_2_TYPE_II',
    'NIST_CYBERSECURITY_FRAMEWORK',
    'OWASP_TOP_10'
]

## Testing Configuration
SECURITY_TEST_TIMEOUT_SECONDS = 300
SECURITY_TEST_COVERAGE_THRESHOLD = 80
SECURITY_TEST_RETRY_ATTEMPTS = 3
SECURITY_TEST_PARALLEL_WORKERS = 4
