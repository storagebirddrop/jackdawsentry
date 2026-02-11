"""
Jackdaw Sentry - Logging Configuration
Centralized logging setup with GDPR compliance
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime

from src.api.config import settings


class JackdawSentryFormatter(logging.Formatter):
    """Custom formatter for Jackdaw Sentry with GDPR compliance"""
    
    def format(self, record):
        # Base format
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'thread': record.thread,
            'process': record.process
        }
        
        # Add GDPR compliance fields if available
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
        if hasattr(record, 'resource_accessed'):
            log_entry['resource_accessed'] = record.resource_accessed
        
        # Add exception information
        if record.exc_info:
            log_entry['exception'] = {
                'type': type(record.exc_info[1]).__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info[1])
            }
        
        return json.dumps(log_entry, default=str)


class GDPRFilter(logging.Filter):
    """Filter to ensure GDPR compliance in logs"""
    
    def __init__(self, include_sensitive: bool = False):
        super().__init__()
        self.include_sensitive = include_sensitive
    
    def filter(self, record):
        # Remove sensitive data from logs unless explicitly included
        if not self.include_sensitive:
            # Filter out potential sensitive data patterns
            message = record.getMessage()
            
            # Remove potential passwords, tokens, keys
            sensitive_patterns = [
                'password', 'token', 'key', 'secret', 'credential',
                'authorization', 'bearer', 'jwt', 'encryption_key'
            ]
            
            for pattern in sensitive_patterns:
                if pattern.lower() in message.lower():
                    record.msg = f"[FILTERED: {pattern.upper()}]"
                    break
        
        return True


class StructuredHandler(logging.Handler):
    """Custom handler for structured logging"""
    
    def __init__(self, filename: str, level: int = logging.INFO):
        super().__init__(level)
        self.filename = filename
        self.backup_count = 5
        self.backup_count = 5
        self.max_bytes = 100 * 1024 * 1024  # 100MB
        
        # Ensure log directory exists
        log_dir = Path(filename).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    def emit(self, record):
        try:
            log_entry = json.loads(self.format(record))
            
            # Write to file
            with open(self.filename, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            print(f"Logging error: {e}", file=sys.stderr)
    
    def rotate_log(self):
        """Rotate log file when it gets too large"""
        try:
            if Path(self.filename).stat().st_size > self.max_bytes:
                # Rotate log file
                backup_path = f"{self.filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                Path(self.filename).rename(backup_path)
                
                # Clean old backups
                self._clean_old_backups()
                
        except Exception as e:
            print(f"Log rotation error: {e}", file=sys.stderr)
    
    def _clean_old_backups(self):
        """Clean old backup files"""
        try:
            log_dir = Path(self.filename).parent
            backup_files = sorted(log_dir.glob(f"{Path(self.filename).stem}.*"))
            
            # Keep only the most recent backups
            for old_backup in backup_files[:-self.backup_count]:
                old_backup.unlink()
                
        except Exception as e:
            print(f"Backup cleanup error: {e}", file=sys.stderr)


def setup_logging():
    """Setup comprehensive logging configuration"""
    
    # Create log directory
    log_dir = Path(settings.LOG_FILE_PATH)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Define log levels and formats
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure formatters
    json_formatter = JackdawSentryFormatter()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure handlers
    handlers = {}
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    handlers['console'] = console_handler
    
    # File handler for application logs
    app_log_file = log_dir / "jackdawsentry.log"
    file_handler = StructuredHandler(str(app_log_file), log_level)
    file_handler.setFormatter(json_formatter)
    file_handler.addFilter(GDPRFilter(include_sensitive=False))
    handlers['file'] = file_handler
    
    # File handler for audit logs (GDPR compliance)
    audit_log_file = log_dir / "audit.log"
    audit_handler = StructuredHandler(str(audit_log_file), logging.INFO)
    audit_handler.setFormatter(json_formatter)
    audit_handler.addFilter(GDPRFilter(include_sensitive=True))  # Include sensitive data for audit
    handlers['audit'] = audit_handler
    
    # File handler for error logs
    error_log_file = log_dir / "errors.log"
    error_handler = StructuredHandler(str(error_log_file), logging.ERROR)
    error_handler.setFormatter(json_formatter)
    handlers['error'] = error_handler
    
    # File handler for security logs
    security_log_file = log_dir / "security.log"
    security_handler = StructuredHandler(str(security_log_file), logging.WARNING)
    security_handler.setFormatter(json_formatter)
    security_handler.addFilter(GDPRFilter(include_sensitive=True))
    handlers['security'] = security_handler
    
    # Configure loggers
    loggers = {
        # Root logger
        '': {
            'level': log_level,
            'handlers': ['console', 'file', 'error'],
            'propagate': False
        },
        
        # Application logger
        'jackdawsentry': {
            'level': log_level,
            'handlers': ['console', 'file'],
            'propagate': False
        },
        
        # Audit logger (GDPR compliance)
        'audit': {
            'level': logging.INFO,
            'handlers': ['audit'],
            'propagate': False
        },
        
        # Security logger
        'security': {
            'level': logging.WARNING,
            'handlers': ['security'],
            'propagate': False
        },
        
        # Database logger
        'database': {
            'level': logging.INFO,
            'handlers': ['file'],
            'propagate': False
        },
        
        # API logger
        'api': {
            'level': logging.INFO,
            'handlers': ['file'],
            'propagate': False
        },
        
        # Blockchain collectors logger
        'collectors': {
            'level': logging.INFO,
            'handlers': ['file'],
            'propagate': False
        },
        
        # Analysis engine logger
        'analysis': {
            'level': logging.INFO,
            'handlers': ['file'],
            'propagate': False
        }
    }
    
    # Apply configuration
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': 'src.api.logging_config.JackdawSentryFormatter',
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'console',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                '()': 'src.api.logging_config.StructuredHandler',
                'level': log_level,
                'formatter': 'json',
                'filename': str(app_log_file)
            },
            'audit': {
                '()': 'src.api.logging_config.StructuredHandler',
                'level': 'INFO',
                'formatter': 'json',
                'filename': str(audit_log_file)
            },
            'error': {
                '()': 'src.api.logging_config.StructuredHandler',
                'level': 'ERROR',
                'formatter': 'json',
                'filename': str(error_log_file)
            },
            'security': {
                '()': 'src.api.logging_config.StructuredHandler',
                'level': 'WARNING',
                'formatter': 'json',
                'filename': str(security_log_file)
            }
        },
        'loggers': loggers
    })
    
    # Set up logger instances
    logger = logging.getLogger('jackdawsentry')
    audit_logger = logging.getLogger('audit')
    security_logger = logging.getLogger('security')
    database_logger = logging.getLogger('database')
    api_logger = logging.getLogger('api')
    
    return {
        'logger': logger,
        'audit_logger': audit_logger,
        'security_logger': security_logger,
        'database_logger': database_logger,
        'api_logger': api_logger
    }


def get_logger(name: str = 'jackdawsentry') -> logging.Logger:
    """Get a configured logger instance"""
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: int, message: str, **context):
    """Log with additional context for GDPR compliance"""
    extra = {
        'timestamp': datetime.utcnow().isoformat(),
        **context
    }
    logger.log(level, message, extra=extra)


def log_security_event(event_type: str, details: Dict[str, Any], user_id: str = None):
    """Log security events"""
    security_logger = logging.getLogger('security')
    security_logger.warning(
        f"Security event: {event_type}",
        extra={
            'event_type': event_type,
            'details': details,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    )


def log_audit_event(action: str, resource_type: str, resource_id: str = None, 
                user_id: str = None, success: bool = True, 
                details: Dict[str, Any] = None):
    """Log audit events for GDPR compliance"""
    audit_logger = logging.getLogger('audit')
    audit_logger.info(
        f"Audit: {action}",
        extra={
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'user_id': user_id,
            'success': success,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
    )


def log_error_with_traceback(logger: logging.Logger, message: str, exception: Exception):
    """Log errors with full traceback"""
    logger.error(
        f"Error: {message}",
        extra={
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': logger.formatException(exception),
            'timestamp': datetime.utcnow().isoformat()
        },
        exc_info=True
    )
