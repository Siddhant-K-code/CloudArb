"""
Monitoring and metrics for CloudArb platform.
"""

import time
from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest
from prometheus_client.registry import CollectorRegistry

# Create a custom registry
registry = CollectorRegistry()

# Request metrics
REQUEST_COUNT = Counter(
    'cloudarb_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

REQUEST_DURATION = Histogram(
    'cloudarb_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

# Business metrics
OPTIMIZATION_COUNT = Counter(
    'cloudarb_optimizations_total',
    'Total number of optimization runs',
    ['type', 'status'],
    registry=registry
)

OPTIMIZATION_DURATION = Histogram(
    'cloudarb_optimization_duration_seconds',
    'Optimization duration in seconds',
    ['type'],
    registry=registry
)

COST_SAVINGS = Counter(
    'cloudarb_cost_savings_total',
    'Total cost savings achieved',
    ['provider', 'instance_type'],
    registry=registry
)

WORKLOAD_COUNT = Gauge(
    'cloudarb_active_workloads',
    'Number of active workloads',
    ['status', 'type'],
    registry=registry
)

# System metrics
DATABASE_CONNECTIONS = Gauge(
    'cloudarb_database_connections',
    'Number of active database connections',
    registry=registry
)

REDIS_CONNECTIONS = Gauge(
    'cloudarb_redis_connections',
    'Number of active Redis connections',
    registry=registry
)

API_RESPONSE_TIME = Summary(
    'cloudarb_api_response_time_seconds',
    'API response time in seconds',
    ['endpoint'],
    registry=registry
)

# Error metrics
ERROR_COUNT = Counter(
    'cloudarb_errors_total',
    'Total number of errors',
    ['type', 'endpoint'],
    registry=registry
)

# Market data metrics
PRICING_UPDATES = Counter(
    'cloudarb_pricing_updates_total',
    'Total number of pricing data updates',
    ['provider', 'instance_type'],
    registry=registry
)

ARBITRAGE_OPPORTUNITIES = Gauge(
    'cloudarb_arbitrage_opportunities',
    'Number of current arbitrage opportunities',
    ['provider_from', 'provider_to'],
    registry=registry
)


class MetricsCollector:
    """Metrics collector for CloudArb platform."""

    def __init__(self):
        self.start_time = time.time()

    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics."""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

    def record_optimization(self, opt_type: str, status: str, duration: float):
        """Record optimization metrics."""
        OPTIMIZATION_COUNT.labels(type=opt_type, status=status).inc()
        OPTIMIZATION_DURATION.labels(type=opt_type).observe(duration)

    def record_cost_savings(self, provider: str, instance_type: str, amount: float):
        """Record cost savings metrics."""
        COST_SAVINGS.labels(provider=provider, instance_type=instance_type).inc(amount)

    def update_workload_count(self, status: str, workload_type: str, count: int):
        """Update workload count metrics."""
        WORKLOAD_COUNT.labels(status=status, type=workload_type).set(count)

    def record_error(self, error_type: str, endpoint: str):
        """Record error metrics."""
        ERROR_COUNT.labels(type=error_type, endpoint=endpoint).inc()

    def record_pricing_update(self, provider: str, instance_type: str):
        """Record pricing update metrics."""
        PRICING_UPDATES.labels(provider=provider, instance_type=instance_type).inc()

    def update_arbitrage_opportunities(self, provider_from: str, provider_to: str, count: int):
        """Update arbitrage opportunities metrics."""
        ARBITRAGE_OPPORTUNITIES.labels(
            provider_from=provider_from,
            provider_to=provider_to
        ).set(count)

    def update_database_connections(self, count: int):
        """Update database connection count."""
        DATABASE_CONNECTIONS.set(count)

    def update_redis_connections(self, count: int):
        """Update Redis connection count."""
        REDIS_CONNECTIONS.set(count)

    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time


# Global metrics collector instance
metrics_collector = MetricsCollector()


def setup_metrics():
    """Setup monitoring metrics."""
    # This function can be used to initialize any additional metrics setup
    pass


def get_metrics():
    """Get all metrics in Prometheus format."""
    return generate_latest(registry)


class MetricsMiddleware:
    """Middleware for collecting request metrics."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        # Create a custom send function to capture response status
        async def send_with_metrics(message):
            if message["type"] == "http.response.start":
                # Record metrics after response is sent
                duration = time.time() - start_time
                method = scope.get("method", "UNKNOWN")
                path = scope.get("path", "/")
                status = message.get("status", 500)

                metrics_collector.record_request(method, path, status, duration)

            await send(message)

        await self.app(scope, receive, send_with_metrics)


# Health check metrics
HEALTH_CHECK_COUNT = Counter(
    'cloudarb_health_checks_total',
    'Total number of health checks',
    ['status'],
    registry=registry
)

HEALTH_CHECK_DURATION = Histogram(
    'cloudarb_health_check_duration_seconds',
    'Health check duration in seconds',
    registry=registry
)


def record_health_check(status: str, duration: float):
    """Record health check metrics."""
    HEALTH_CHECK_COUNT.labels(status=status).inc()
    HEALTH_CHECK_DURATION.observe(duration)


# Performance metrics
MEMORY_USAGE = Gauge(
    'cloudarb_memory_usage_bytes',
    'Memory usage in bytes',
    registry=registry
)

CPU_USAGE = Gauge(
    'cloudarb_cpu_usage_percent',
    'CPU usage percentage',
    registry=registry
)

DISK_USAGE = Gauge(
    'cloudarb_disk_usage_bytes',
    'Disk usage in bytes',
    registry=registry
)


def update_system_metrics(memory_bytes: int, cpu_percent: float, disk_bytes: int):
    """Update system resource metrics."""
    MEMORY_USAGE.set(memory_bytes)
    CPU_USAGE.set(cpu_percent)
    DISK_USAGE.set(disk_bytes)


# Business intelligence metrics
USER_COUNT = Gauge(
    'cloudarb_active_users',
    'Number of active users',
    registry=registry
)

ORGANIZATION_COUNT = Gauge(
    'cloudarb_organizations',
    'Number of organizations',
    registry=registry
)

TOTAL_COST_SAVED = Counter(
    'cloudarb_total_cost_saved',
    'Total cost saved across all users',
    registry=registry
)

AVERAGE_SAVINGS_PERCENT = Gauge(
    'cloudarb_average_savings_percent',
    'Average savings percentage',
    registry=registry
)


def update_business_metrics(
    active_users: int,
    organizations: int,
    total_saved: float,
    avg_savings_percent: float
):
    """Update business intelligence metrics."""
    USER_COUNT.set(active_users)
    ORGANIZATION_COUNT.set(organizations)
    TOTAL_COST_SAVED.inc(total_saved)
    AVERAGE_SAVINGS_PERCENT.set(avg_savings_percent)