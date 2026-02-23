"""
Compliance API Rate Limiting Module

This module provides comprehensive rate limiting functionality for compliance APIs including:
- Request rate limiting by user and endpoint
- Dynamic rate limit adjustment
- Rate limit violation monitoring and alerting
- Distributed rate limiting support
- Rate limit analytics and reporting
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Rate limit type enumeration"""

    USER_BASED = "user_based"
    IP_BASED = "ip_based"
    ENDPOINT_BASED = "endpoint_based"
    GLOBAL = "global"
    ROLE_BASED = "role_based"


class RateLimitAction(Enum):
    """Rate limit action enumeration"""

    REJECT = "reject"
    THROTTLE = "throttle"
    QUEUE = "queue"
    LOG_ONLY = "log_only"


@dataclass
class RateLimitRule:
    """Rate limit rule definition"""

    rule_id: str
    name: str
    rate_limit_type: RateLimitType
    requests_per_window: int
    window_seconds: int
    action: RateLimitAction
    priority: int = 0
    enabled: bool = True
    conditions: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RateLimitRequest:
    """Rate limit request definition"""

    request_id: str
    user_id: Optional[str]
    ip_address: Optional[str]
    endpoint: str
    method: str
    timestamp: datetime
    user_role: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RateLimitResult:
    """Rate limit result definition"""

    allowed: bool
    rule_id: str
    action: RateLimitAction
    remaining_requests: int
    reset_time: datetime
    violation: bool
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RateLimitViolation:
    """Rate limit violation definition"""

    violation_id: str
    rule_id: str
    request_id: str
    user_id: Optional[str]
    ip_address: Optional[str]
    endpoint: str
    timestamp: datetime
    action_taken: RateLimitAction
    metadata: Optional[Dict[str, Any]] = None


class ComplianceRateLimitingEngine:
    """Compliance API rate limiting engine"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.rules = {}
        self.violations = []
        self.request_history = defaultdict(lambda: deque(maxlen=1000))
        self.redis_client = None
        self.redis_url = redis_url
        self.default_limits = {
            "global": {"requests": 1000, "window": 3600},  # 1000 requests per hour
            "user": {"requests": 100, "window": 300},  # 100 requests per 5 minutes
            "ip": {"requests": 200, "window": 300},  # 200 requests per 5 minutes
            "endpoint": {
                "requests": 50,
                "window": 60,
            },  # 50 requests per minute per endpoint
        }

        # Initialize default rules
        self._initialize_default_rules()

    async def initialize(self):
        """Initialize rate limiting engine"""
        try:
            # Initialize Redis client
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()

            logger.info("Rate limiting engine initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize rate limiting engine: {e}")
            # Fallback to in-memory storage
            self.redis_client = None

    def _initialize_default_rules(self):
        """Initialize default rate limiting rules"""

        # Global rate limit
        global_rule = RateLimitRule(
            rule_id="global_limit",
            name="Global Rate Limit",
            rate_limit_type=RateLimitType.GLOBAL,
            requests_per_window=self.default_limits["global"]["requests"],
            window_seconds=self.default_limits["global"]["window"],
            action=RateLimitAction.REJECT,
            priority=1,
            enabled=True,
        )

        # User-based rate limit
        user_rule = RateLimitRule(
            rule_id="user_limit",
            name="User Rate Limit",
            rate_limit_type=RateLimitType.USER_BASED,
            requests_per_window=self.default_limits["user"]["requests"],
            window_seconds=self.default_limits["user"]["window"],
            action=RateLimitAction.REJECT,
            priority=2,
            enabled=True,
        )

        # IP-based rate limit
        ip_rule = RateLimitRule(
            rule_id="ip_limit",
            name="IP Rate Limit",
            rate_limit_type=RateLimitType.IP_BASED,
            requests_per_window=self.default_limits["ip"]["requests"],
            window_seconds=self.default_limits["ip"]["window"],
            action=RateLimitAction.REJECT,
            priority=3,
            enabled=True,
        )

        # Endpoint-based rate limit
        endpoint_rule = RateLimitRule(
            rule_id="endpoint_limit",
            name="Endpoint Rate Limit",
            rate_limit_type=RateLimitType.ENDPOINT_BASED,
            requests_per_window=self.default_limits["endpoint"]["requests"],
            window_seconds=self.default_limits["endpoint"]["window"],
            action=RateLimitAction.REJECT,
            priority=4,
            enabled=True,
        )

        # Compliance-specific rate limits
        compliance_rules = [
            RateLimitRule(
                rule_id="compliance_reports",
                name="Compliance Reports Rate Limit",
                rate_limit_type=RateLimitType.USER_BASED,
                requests_per_window=20,
                window_seconds=300,  # 20 reports per 5 minutes
                action=RateLimitAction.REJECT,
                priority=5,
                enabled=True,
                conditions={"endpoint_pattern": "/api/v1/compliance/reports"},
            ),
            RateLimitRule(
                rule_id="risk_assessments",
                name="Risk Assessment Rate Limit",
                rate_limit_type=RateLimitType.USER_BASED,
                requests_per_window=30,
                window_seconds=300,  # 30 assessments per 5 minutes
                action=RateLimitAction.REJECT,
                priority=5,
                enabled=True,
                conditions={"endpoint_pattern": "/api/v1/compliance/risk"},
            ),
            RateLimitRule(
                rule_id="case_management",
                name="Case Management Rate Limit",
                rate_limit_type=RateLimitType.USER_BASED,
                requests_per_window=50,
                window_seconds=300,  # 50 case operations per 5 minutes
                action=RateLimitAction.REJECT,
                priority=5,
                enabled=True,
                conditions={"endpoint_pattern": "/api/v1/compliance/cases"},
            ),
            RateLimitRule(
                rule_id="data_export",
                name="Data Export Rate Limit",
                rate_limit_type=RateLimitType.USER_BASED,
                requests_per_window=5,
                window_seconds=300,  # 5 exports per 5 minutes
                action=RateLimitAction.REJECT,
                priority=6,
                enabled=True,
                conditions={"endpoint_pattern": "/api/v1/compliance/export"},
            ),
            RateLimitRule(
                rule_id="analytics_queries",
                name="Analytics Queries Rate Limit",
                rate_limit_type=RateLimitType.USER_BASED,
                requests_per_window=40,
                window_seconds=300,  # 40 queries per 5 minutes
                action=RateLimitAction.REJECT,
                priority=5,
                enabled=True,
                conditions={"endpoint_pattern": "/api/v1/compliance/analytics"},
            ),
        ]

        # Add all rules
        self.rules[global_rule.rule_id] = global_rule
        self.rules[user_rule.rule_id] = user_rule
        self.rules[ip_rule.rule_id] = ip_rule
        self.rules[endpoint_rule.rule_id] = endpoint_rule

        for rule in compliance_rules:
            self.rules[rule.rule_id] = rule

    async def check_rate_limit(self, request: RateLimitRequest) -> RateLimitResult:
        """Check if request is allowed based on rate limiting rules"""
        try:
            # Get applicable rules
            applicable_rules = await self._get_applicable_rules(request)

            if not applicable_rules:
                return RateLimitResult(
                    allowed=True,
                    rule_id="none",
                    action=RateLimitAction.LOG_ONLY,
                    remaining_requests=999,
                    reset_time=datetime.now(timezone.utc) + timedelta(hours=1),
                    violation=False,
                )

            # Check each applicable rule
            for rule in applicable_rules:
                result = await self._check_rule(request, rule)

                if not result.allowed:
                    # Log violation
                    await self._log_violation(request, rule, result)

                    # Take action based on rule
                    await self._take_action(request, rule, result)

                    return result

            # All rules passed
            return RateLimitResult(
                allowed=True,
                rule_id="all_passed",
                action=RateLimitAction.LOG_ONLY,
                remaining_requests=100,
                reset_time=datetime.now(timezone.utc) + timedelta(minutes=1),
                violation=False,
            )

        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            # Fail open - allow request if rate limiting fails
            return RateLimitResult(
                allowed=True,
                rule_id="error",
                action=RateLimitAction.LOG_ONLY,
                remaining_requests=999,
                reset_time=datetime.now(timezone.utc) + timedelta(hours=1),
                violation=False,
                metadata={"error": str(e)},
            )

    async def _get_applicable_rules(
        self, request: RateLimitRequest
    ) -> List[RateLimitRule]:
        """Get applicable rules for the request"""
        try:
            applicable_rules = []

            for rule in self.rules.values():
                if not rule.enabled:
                    continue

                # Check if rule conditions are met
                if await self._check_rule_conditions(rule, request):
                    applicable_rules.append(rule)

            # Sort by priority (lower number = higher priority)
            applicable_rules.sort(key=lambda r: r.priority)

            return applicable_rules

        except Exception as e:
            logger.error(f"Failed to get applicable rules: {e}")
            return []

    async def _check_rule_conditions(
        self, rule: RateLimitRule, request: RateLimitRequest
    ) -> bool:
        """Check if rule conditions are met"""
        try:
            if not rule.conditions:
                return True

            # Check endpoint pattern
            if "endpoint_pattern" in rule.conditions:
                pattern = rule.conditions["endpoint_pattern"]
                if not self._match_endpoint_pattern(pattern, request.endpoint):
                    return False

            # Check user role
            if "user_role" in rule.conditions:
                required_roles = rule.conditions["user_role"]
                if isinstance(required_roles, list):
                    if request.user_role not in required_roles:
                        return False
                else:
                    if request.user_role != required_roles:
                        return False

            # Check HTTP method
            if "method" in rule.conditions:
                required_methods = rule.conditions["method"]
                if isinstance(required_methods, list):
                    if request.method not in required_methods:
                        return False
                else:
                    if request.method != required_methods:
                        return False

            return True

        except Exception as e:
            logger.error(f"Failed to check rule conditions: {e}")
            return True  # Default to allowing

    def _match_endpoint_pattern(self, pattern: str, endpoint: str) -> bool:
        """Match endpoint pattern"""
        try:
            # Simple pattern matching (can be enhanced with regex)
            if pattern.endswith("*"):
                return endpoint.startswith(pattern[:-1])
            else:
                return endpoint == pattern
        except Exception as e:
            logger.error(f"Failed to match endpoint pattern: {e}")
            return False

    async def _check_rule(
        self, request: RateLimitRequest, rule: RateLimitRule
    ) -> RateLimitResult:
        """Check specific rate limiting rule"""
        try:
            # Get key for rate limiting
            key = await self._get_rate_limit_key(request, rule)

            # Get current count
            current_count = await self._get_request_count(key, rule.window_seconds)

            # Check if limit exceeded
            if current_count >= rule.requests_per_window:
                return RateLimitResult(
                    allowed=False,
                    rule_id=rule.rule_id,
                    action=rule.action,
                    remaining_requests=0,
                    reset_time=datetime.now(timezone.utc)
                    + timedelta(seconds=rule.window_seconds),
                    violation=True,
                    metadata={
                        "current_count": current_count,
                        "limit": rule.requests_per_window,
                    },
                )

            # Increment count
            await self._increment_request_count(key)

            return RateLimitResult(
                allowed=True,
                rule_id=rule.rule_id,
                action=rule.action,
                remaining_requests=rule.requests_per_window - current_count - 1,
                reset_time=datetime.now(timezone.utc)
                + timedelta(seconds=rule.window_seconds),
                violation=False,
                metadata={
                    "current_count": current_count + 1,
                    "limit": rule.requests_per_window,
                },
            )

        except Exception as e:
            logger.error(f"Failed to check rule {rule.rule_id}: {e}")
            return RateLimitResult(
                allowed=True,
                rule_id=rule.rule_id,
                action=RateLimitAction.LOG_ONLY,
                remaining_requests=999,
                reset_time=datetime.now(timezone.utc) + timedelta(hours=1),
                violation=False,
                metadata={"error": str(e)},
            )

    async def _get_rate_limit_key(
        self, request: RateLimitRequest, rule: RateLimitRule
    ) -> str:
        """Get rate limiting key for request and rule"""
        try:
            if rule.rate_limit_type == RateLimitType.GLOBAL:
                return f"rate_limit:global:{rule.rule_id}"
            elif rule.rate_limit_type == RateLimitType.USER_BASED:
                user_id = request.user_id or "anonymous"
                return f"rate_limit:user:{user_id}:{rule.rule_id}"
            elif rule.rate_limit_type == RateLimitType.IP_BASED:
                ip_address = request.ip_address or "unknown"
                return f"rate_limit:ip:{ip_address}:{rule.rule_id}"
            elif rule.rate_limit_type == RateLimitType.ENDPOINT_BASED:
                endpoint_hash = hashlib.sha256(request.endpoint.encode()).hexdigest()[
                    :16
                ]
                return f"rate_limit:endpoint:{endpoint_hash}:{rule.rule_id}"
            elif rule.rate_limit_type == RateLimitType.ROLE_BASED:
                user_role = request.user_role or "none"
                return f"rate_limit:role:{user_role}:{rule.rule_id}"
            else:
                return f"rate_limit:default:{rule.rule_id}"

        except Exception as e:
            logger.error(f"Failed to get rate limit key: {e}")
            return f"rate_limit:error:{rule.rule_id}"

    async def _get_request_count(self, key: str, window_seconds: int) -> int:
        """Get current request count for key"""
        try:
            if self.redis_client:
                # Use Redis for distributed rate limiting
                count = await self.redis_client.get(key)
                return int(count) if count else 0
            else:
                # Fallback to in-memory storage
                current_time = time.time()
                window_start = current_time - window_seconds

                # Clean old entries
                if key in self.request_history:
                    while (
                        self.request_history[key]
                        and self.request_history[key][0] < window_start
                    ):
                        self.request_history[key].popleft()

                return len(self.request_history[key])

        except Exception as e:
            logger.error(f"Failed to get request count: {e}")
            return 0

    async def _increment_request_count(self, key: str):
        """Increment request count for key"""
        try:
            if self.redis_client:
                # Use Redis with expiration
                pipe = self.redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, 3600)  # 1 hour expiration
                await pipe.execute()
            else:
                # Fallback to in-memory storage
                current_time = time.time()
                if key not in self.request_history:
                    self.request_history[key] = deque()
                self.request_history[key].append(current_time)

        except Exception as e:
            logger.error(f"Failed to increment request count: {e}")

    async def _log_violation(
        self, request: RateLimitRequest, rule: RateLimitRule, result: RateLimitResult
    ):
        """Log rate limit violation"""
        try:
            violation = RateLimitViolation(
                violation_id=str(int(time.time() * 1000000)),  # Unique ID
                rule_id=rule.rule_id,
                request_id=request.request_id,
                user_id=request.user_id,
                ip_address=request.ip_address,
                endpoint=request.endpoint,
                timestamp=datetime.now(timezone.utc),
                action_taken=result.action,
                metadata=result.metadata,
            )

            self.violations.append(violation)

            # Keep only recent violations (last 1000)
            if len(self.violations) > 1000:
                self.violations = self.violations[-1000:]

            logger.warning(
                f"Rate limit violation: {rule.rule_id} for user {request.user_id} on {request.endpoint}"
            )

        except Exception as e:
            logger.error(f"Failed to log violation: {e}")

    async def _take_action(
        self, request: RateLimitRequest, rule: RateLimitRule, result: RateLimitResult
    ):
        """Take action based on rate limit rule"""
        try:
            if result.action == RateLimitAction.REJECT:
                # Reject request - handled by caller
                pass
            elif result.action == RateLimitAction.THROTTLE:
                # Throttle request - add delay
                await asyncio.sleep(1)
            elif result.action == RateLimitAction.QUEUE:
                # Queue request - not implemented yet
                logger.info(f"Request {request.request_id} queued due to rate limiting")
            elif result.action == RateLimitAction.LOG_ONLY:
                # Only log - no action taken
                pass

        except Exception as e:
            logger.error(f"Failed to take action {result.action}: {e}")

    async def add_rule(self, rule: RateLimitRule) -> bool:
        """Add new rate limiting rule"""
        try:
            self.rules[rule.rule_id] = rule
            logger.info(f"Added rate limiting rule: {rule.rule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add rule {rule.rule_id}: {e}")
            return False

    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing rate limiting rule"""
        try:
            if rule_id not in self.rules:
                return False

            rule = self.rules[rule_id]

            # Update rule properties
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)

            logger.info(f"Updated rate limiting rule: {rule_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update rule {rule_id}: {e}")
            return False

    async def delete_rule(self, rule_id: str) -> bool:
        """Delete rate limiting rule"""
        try:
            if rule_id in self.rules:
                del self.rules[rule_id]
                logger.info(f"Deleted rate limiting rule: {rule_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete rule {rule_id}: {e}")
            return False

    async def enable_rule(self, rule_id: str) -> bool:
        """Enable rate limiting rule"""
        try:
            if rule_id in self.rules:
                self.rules[rule_id].enabled = True
                logger.info(f"Enabled rate limiting rule: {rule_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to enable rule {rule_id}: {e}")
            return False

    async def disable_rule(self, rule_id: str) -> bool:
        """Disable rate limiting rule"""
        try:
            if rule_id in self.rules:
                self.rules[rule_id].enabled = False
                logger.info(f"Disabled rate limiting rule: {rule_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to disable rule {rule_id}: {e}")
            return False

    async def get_rate_limit_status(
        self, user_id: Optional[str] = None, ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current rate limiting status"""
        try:
            status = {
                "total_rules": len(self.rules),
                "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
                "recent_violations": len(
                    [
                        v
                        for v in self.violations
                        if v.timestamp > datetime.now(timezone.utc) - timedelta(hours=1)
                    ]
                ),
                "redis_connected": self.redis_client is not None,
            }

            if user_id:
                # Get user-specific status
                user_status = {}
                for rule in self.rules.values():
                    if (
                        rule.enabled
                        and rule.rate_limit_type == RateLimitType.USER_BASED
                    ):
                        key = f"rate_limit:user:{user_id}:{rule.rule_id}"
                        current_count = await self._get_request_count(
                            key, rule.window_seconds
                        )
                        user_status[rule.rule_id] = {
                            "current_count": current_count,
                            "limit": rule.requests_per_window,
                            "remaining": max(
                                0, rule.requests_per_window - current_count
                            ),
                            "reset_time": datetime.now(timezone.utc)
                            + timedelta(seconds=rule.window_seconds),
                        }
                status["user_status"] = user_status

            if ip_address:
                # Get IP-specific status
                ip_status = {}
                for rule in self.rules.values():
                    if rule.enabled and rule.rate_limit_type == RateLimitType.IP_BASED:
                        key = f"rate_limit:ip:{ip_address}:{rule.rule_id}"
                        current_count = await self._get_request_count(
                            key, rule.window_seconds
                        )
                        ip_status[rule.rule_id] = {
                            "current_count": current_count,
                            "limit": rule.requests_per_window,
                            "remaining": max(
                                0, rule.requests_per_window - current_count
                            ),
                            "reset_time": datetime.now(timezone.utc)
                            + timedelta(seconds=rule.window_seconds),
                        }
                status["ip_status"] = ip_status

            return status

        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {"error": str(e)}

    async def get_violations(
        self, limit: int = 100, user_id: Optional[str] = None
    ) -> List[RateLimitViolation]:
        """Get recent rate limit violations"""
        try:
            violations = self.violations

            # Filter by user if specified
            if user_id:
                violations = [v for v in violations if v.user_id == user_id]

            # Sort by timestamp (newest first)
            violations.sort(key=lambda v: v.timestamp, reverse=True)

            return violations[:limit]

        except Exception as e:
            logger.error(f"Failed to get violations: {e}")
            return []

    async def clear_violations(self, older_than_hours: int = 24) -> int:
        """Clear old violations"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            original_count = len(self.violations)

            self.violations = [v for v in self.violations if v.timestamp > cutoff_time]

            cleared_count = original_count - len(self.violations)

            logger.info(f"Cleared {cleared_count} old violations")
            return cleared_count

        except Exception as e:
            logger.error(f"Failed to clear violations: {e}")
            return 0

    async def get_rate_limit_statistics(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        try:
            now = datetime.now(timezone.utc)

            # Calculate statistics
            total_violations = len(self.violations)
            recent_violations = len(
                [v for v in self.violations if v.timestamp > now - timedelta(hours=1)]
            )
            daily_violations = len(
                [v for v in self.violations if v.timestamp > now - timedelta(days=1)]
            )

            # Violations by rule
            violations_by_rule = defaultdict(int)
            for violation in self.violations:
                violations_by_rule[violation.rule_id] += 1

            # Violations by action
            violations_by_action = defaultdict(int)
            for violation in self.violations:
                violations_by_action[violation.action_taken.value] += 1

            # Top violators
            user_violations = defaultdict(int)
            ip_violations = defaultdict(int)

            for violation in self.violations:
                if violation.user_id:
                    user_violations[violation.user_id] += 1
                if violation.ip_address:
                    ip_violations[violation.ip_address] += 1

            top_users = sorted(
                user_violations.items(), key=lambda x: x[1], reverse=True
            )[:10]
            top_ips = sorted(ip_violations.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]

            return {
                "total_violations": total_violations,
                "recent_violations_1h": recent_violations,
                "daily_violations": daily_violations,
                "violations_by_rule": dict(violations_by_rule),
                "violations_by_action": dict(violations_by_action),
                "top_user_violators": top_users,
                "top_ip_violators": top_ips,
                "total_rules": len(self.rules),
                "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
                "redis_connected": self.redis_client is not None,
            }

        except Exception as e:
            logger.error(f"Failed to get rate limit statistics: {e}")
            return {"error": str(e)}


# Global rate limiting engine instance
compliance_rate_limiting_engine = ComplianceRateLimitingEngine()
