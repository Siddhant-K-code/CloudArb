"""
API routes package for CloudArb platform.
"""

from . import auth, optimization, workloads, analytics, market_data

__all__ = [
    "auth",
    "optimization",
    "workloads",
    "analytics",
    "market_data",
]