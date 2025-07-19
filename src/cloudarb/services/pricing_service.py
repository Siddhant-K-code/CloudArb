"""
Pricing service for CloudArb platform.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..models.pricing import Provider, InstanceType, PricingData

logger = logging.getLogger(__name__)


class PricingService:
    """Service for managing pricing data and operations."""

    def __init__(self, db: Session):
        self.db = db

    async def get_available_instances(
        self,
        gpu_types: List[str] = None,
        regions: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available instance options for optimization."""
        try:
            # Query for available instances
            query = self.db.query(InstanceType).join(Provider)

            if gpu_types:
                query = query.filter(InstanceType.gpu_type.in_(gpu_types))

            if regions:
                query = query.filter(InstanceType.region.in_(regions))

            instances = query.all()

            # Convert to dictionary format
            instance_options = []
            for instance in instances:
                # Get latest pricing data
                latest_pricing = self.db.query(PricingData).filter(
                    PricingData.instance_type_id == instance.id
                ).order_by(PricingData.created_at.desc()).first()

                if latest_pricing:
                    instance_options.append({
                        "provider_id": instance.provider.id,
                        "instance_type_id": instance.id,
                        "provider_name": instance.provider.name,
                        "instance_name": instance.name,
                        "region": instance.region,
                        "cpu_cores": instance.cpu_cores,
                        "memory_gb": instance.memory_gb,
                        "gpu_count": instance.gpu_count,
                        "gpu_type": instance.gpu_type,
                        "gpu_memory_gb": instance.gpu_memory_gb,
                        "storage_gb": instance.storage_gb,
                        "on_demand_price_per_hour": latest_pricing.on_demand_price_per_hour,
                        "spot_price_per_hour": latest_pricing.spot_price_per_hour,
                        "performance_score": instance.performance_score,
                    })

            return instance_options

        except Exception as e:
            logger.error(f"Failed to get available instances: {e}")
            return []

    def get_providers(self) -> List[Provider]:
        """Get all available providers."""
        return self.db.query(Provider).all()

    def get_instance_types(
        self,
        provider_id: Optional[int] = None,
        gpu_type: Optional[str] = None
    ) -> List[InstanceType]:
        """Get instance types with optional filtering."""
        query = self.db.query(InstanceType)

        if provider_id:
            query = query.filter(InstanceType.provider_id == provider_id)

        if gpu_type:
            query = query.filter(InstanceType.gpu_type == gpu_type)

        return query.all()

    def get_latest_pricing(
        self,
        instance_type_id: int,
        hours_back: int = 24
    ) -> Optional[PricingData]:
        """Get latest pricing data for an instance type."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        return self.db.query(PricingData).filter(
            PricingData.instance_type_id == instance_type_id,
            PricingData.created_at >= cutoff_time
        ).order_by(PricingData.created_at.desc()).first()

    def get_price_history(
        self,
        instance_type_id: int,
        days_back: int = 7
    ) -> List[PricingData]:
        """Get price history for an instance type."""
        cutoff_time = datetime.utcnow() - timedelta(days=days_back)

        return self.db.query(PricingData).filter(
            PricingData.instance_type_id == instance_type_id,
            PricingData.created_at >= cutoff_time
        ).order_by(PricingData.created_at.asc()).all()

    def compare_prices(
        self,
        gpu_type: str,
        region: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Compare prices across providers for a specific GPU type."""
        query = self.db.query(InstanceType).join(Provider).filter(
            InstanceType.gpu_type == gpu_type
        )

        if region:
            query = query.filter(InstanceType.region == region)

        instances = query.all()

        comparisons = []
        for instance in instances:
            latest_pricing = self.get_latest_pricing(instance.id)

            if latest_pricing:
                comparisons.append({
                    "provider": instance.provider.name,
                    "instance_name": instance.name,
                    "region": instance.region,
                    "gpu_count": instance.gpu_count,
                    "on_demand_price": latest_pricing.on_demand_price_per_hour,
                    "spot_price": latest_pricing.spot_price_per_hour,
                    "performance_score": instance.performance_score,
                })

        return comparisons