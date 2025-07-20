"""
Main FastAPI application for CloudArb platform.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn

from .config import get_settings
from .database import init_db, check_db_health
from .api.routes import auth, optimization, workloads, analytics, market_data
from .api.middleware import RateLimitMiddleware, LoggingMiddleware
from .monitoring.metrics import setup_metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting CloudArb application...")

    # Initialize database
    try:
        # Temporarily disable database initialization to fix schema issues
        # init_db()
        logger.info("Database initialization skipped for now")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Don't raise the exception for now
        logger.warning("Continuing without database initialization")

    # Setup monitoring
    if settings.monitoring.enable_metrics:
        setup_metrics()
        logger.info("Monitoring metrics setup completed")

    # Health check
    health_status = check_db_health()
    if health_status["status"] != "healthy":
        logger.warning(f"Database health check failed: {health_status}")

    logger.info("CloudArb application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down CloudArb application...")


# Create FastAPI application
app = FastAPI(
    title="CloudArb API",
    description="GPU Arbitrage Platform for Cloud Cost Optimization",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else [
        "cloudarb.com",
        "app.cloudarb.com",
        "localhost",
    ]
)

# Add custom middleware
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(optimization.router, prefix="/optimize", tags=["Optimization"])
app.include_router(workloads.router, prefix="/workloads", tags=["Workloads"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(market_data.router, prefix="/market", tags=["Market Data"])


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "path": request.url.path,
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
            "path": request.url.path,
        }
    )


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "CloudArb API",
        "version": "1.0.0",
        "environment": settings.environment,
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with database and dependencies."""
    db_health = check_db_health()

    health_status = "healthy"
    if db_health["status"] != "healthy":
        health_status = "degraded"

    return {
        "status": health_status,
        "service": "CloudArb API",
        "version": "1.0.0",
        "environment": settings.environment,
        "database": db_health,
        "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to CloudArb API",
        "description": "GPU Arbitrage Platform for Cloud Cost Optimization",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else None,
        "health": "/health",
        "features": [
            "Real-time GPU arbitrage across multiple cloud providers",
            "Linear programming optimization for cost minimization",
            "ML-powered demand forecasting",
            "Risk management and portfolio optimization",
            "Automated deployment and infrastructure management",
        ],
    }


# Development endpoints (bypass authentication for demo)
@app.get("/dev/analytics/savings-summary")
async def dev_savings_summary():
    """Development endpoint for savings summary (no auth required)."""
    return {
        "total_savings": 15420.50,
        "savings_percentage": 23.5,
        "period_days": 7,
        "breakdown": {
            "aws": 8200.30,
            "gcp": 4500.20,
            "azure": 2720.00
        },
        "trend": "increasing"
    }


@app.get("/dev/analytics/cost-analysis")
async def dev_cost_analysis(days: int = 7):
    """Development endpoint for cost analysis (no auth required)."""
    return {
        "total_cost": 45680.75,
        "cost_trend": "decreasing",
        "breakdown": {
            "compute": 32000.50,
            "storage": 8500.25,
            "network": 5180.00
        },
        "period_days": days,
        "forecast": {
            "next_week": 42000.00,
            "next_month": 180000.00
        }
    }


@app.get("/dev/analytics/market-analysis")
async def dev_market_analysis():
    """Development endpoint for market analysis (no auth required)."""
    return {
        "market_trends": {
            "aws": {"trend": "stable", "availability": 0.95},
            "gcp": {"trend": "increasing", "availability": 0.92},
            "azure": {"trend": "decreasing", "availability": 0.88}
        },
        "opportunities": [
            {
                "provider": "gcp",
                "instance_type": "n1-standard-4",
                "savings": 15.2,
                "availability": 0.95
            },
            {
                "provider": "aws",
                "instance_type": "t3.medium",
                "savings": 12.8,
                "availability": 0.92
            }
        ]
    }


@app.get("/dev/workloads")
async def dev_workloads(limit: int = 5):
    """Development endpoint for workloads (no auth required)."""
    return {
        "workloads": [
            {
                "id": 1,
                "name": "ML Training Cluster",
                "status": "running",
                "cost": 1250.50,
                "optimization_potential": 18.5
            },
            {
                "id": 2,
                "name": "Data Processing Pipeline",
                "status": "idle",
                "cost": 450.75,
                "optimization_potential": 25.2
            },
            {
                "id": 3,
                "name": "Web Application",
                "status": "running",
                "cost": 320.00,
                "optimization_potential": 8.3
            }
        ],
        "total": 3
    }


@app.get("/dev/optimize")
async def dev_optimize(limit: int = 5):
    """Development endpoint for optimization results (no auth required)."""
    return {
        "optimizations": [
            {
                "id": 1,
                "name": "Cost Optimization #1",
                "status": "completed",
                "savings": 1850.75,
                "created_at": "2024-01-15T10:30:00Z"
            },
            {
                "id": 2,
                "name": "Performance Optimization",
                "status": "running",
                "savings": 920.50,
                "created_at": "2024-01-14T15:45:00Z"
            }
        ],
        "total": 2
    }


# Metrics endpoint (if monitoring is enabled)
if settings.monitoring.enable_metrics:
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response

        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )


def main():
    """Main entry point for the application."""
    uvicorn.run(
        "cloudarb.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1,
        log_level=settings.monitoring.log_level.lower(),
    )


if __name__ == "__main__":
    main()