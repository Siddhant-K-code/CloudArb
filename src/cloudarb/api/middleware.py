"""
Middleware for CloudArb API.
"""

import time
import logging
from typing import Dict, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as redis

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis."""

    def __init__(self, app):
        super().__init__(app)
        self.redis_client: Optional[redis.Redis] = None
        self.rate_limits = {
            "default": {"requests": 100, "window": 60},  # 100 requests per minute
            "auth": {"requests": 10, "window": 60},      # 10 auth attempts per minute
            "optimization": {"requests": 20, "window": 60},  # 20 optimizations per minute
        }

    async def dispatch(self, request: Request, call_next):
        # Initialize Redis connection if not exists
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(settings.redis.url)
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for rate limiting: {e}")
                # Continue without rate limiting if Redis is unavailable
                return await call_next(request)

        # Get client identifier (IP address or user ID)
        client_id = self._get_client_id(request)

        # Determine rate limit based on endpoint
        rate_limit = self._get_rate_limit(request.url.path)

        # Check rate limit
        if not await self._check_rate_limit(client_id, rate_limit):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {rate_limit['requests']} requests per {rate_limit['window']} seconds"
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = await self._get_remaining_requests(client_id, rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(rate_limit["requests"])
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + rate_limit["window"])

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user ID from token if available
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # In a real implementation, you would decode the JWT token
            # For now, use IP address
            pass

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    def _get_rate_limit(self, path: str) -> Dict[str, int]:
        """Get rate limit configuration for the given path."""
        if path.startswith("/auth"):
            return self.rate_limits["auth"]
        elif path.startswith("/optimize"):
            return self.rate_limits["optimization"]
        else:
            return self.rate_limits["default"]

    async def _check_rate_limit(self, client_id: str, rate_limit: Dict[str, int]) -> bool:
        """Check if client has exceeded rate limit."""
        if not self.redis_client:
            return True  # Allow if Redis is unavailable

        try:
            key = f"rate_limit:{client_id}:{rate_limit['window']}"
            current = await self.redis_client.get(key)

            if current is None:
                # First request in window
                await self.redis_client.setex(key, rate_limit["window"], 1)
                return True

            current_count = int(current)
            if current_count >= rate_limit["requests"]:
                return False

            # Increment counter
            await self.redis_client.incr(key)
            return True

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow if rate limiting fails

    async def _get_remaining_requests(self, client_id: str, rate_limit: Dict[str, int]) -> int:
        """Get remaining requests for client."""
        if not self.redis_client:
            return rate_limit["requests"]

        try:
            key = f"rate_limit:{client_id}:{rate_limit['window']}"
            current = await self.redis_client.get(key)
            if current is None:
                return rate_limit["requests"]

            remaining = rate_limit["requests"] - int(current)
            return max(0, remaining)

        except Exception as e:
            logger.error(f"Failed to get remaining requests: {e}")
            return rate_limit["requests"]


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logging middleware for request/response tracking."""

    async def dispatch(self, request: Request, call_next):
        # Log request start
        start_time = time.time()

        # Get request details
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")

        # Log request
        logger.info(
            f"Request started: {method} {url} from {client_ip} "
            f"(User-Agent: {user_agent[:100]})"
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed: {method} {url} - "
                f"Status: {response.status_code} - "
                f"Duration: {duration:.3f}s"
            )

            # Add response time header
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            logger.error(
                f"Request failed: {method} {url} - "
                f"Error: {str(e)} - "
                f"Duration: {duration:.3f}s"
            )

            raise


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for adding security headers."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # Add HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware."""

    def __init__(self, app, allow_origins=None, allow_methods=None, allow_headers=None):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["*"]
        self.allow_headers = allow_headers or ["*"]

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add CORS headers
        origin = request.headers.get("Origin")
        if origin in self.allow_origins or "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin or "*"

        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        response.headers["Access-Control-Allow-Credentials"] = "true"

        return response