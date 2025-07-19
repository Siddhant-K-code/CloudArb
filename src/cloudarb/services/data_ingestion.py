"""
Data ingestion service for collecting pricing data from cloud providers.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
import boto3
from google.cloud import compute_v1
from azure.mgmt.compute import ComputeManagementClient
from azure.identity import DefaultAzureCredential
import json

from ..config import get_settings
from ..database import get_db
from ..models.pricing import Provider, InstanceType, PricingData
from ..monitoring.metrics import metrics_collector

logger = logging.getLogger(__name__)
settings = get_settings()


class PricingDataCollector:
    """Collects pricing data from various cloud providers."""

    def __init__(self):
        self.session = None
        self.providers = {
            "aws": AWSPriceCollector(),
            "gcp": GCPPriceCollector(),
            "azure": AzurePriceCollector(),
            "lambda": LambdaPriceCollector(),
            "runpod": RunPodPriceCollector(),
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def collect_all_pricing_data(self):
        """Collect pricing data from all providers."""
        tasks = []
        for provider_name, collector in self.providers.items():
            task = asyncio.create_task(
                self._collect_provider_data(provider_name, collector)
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for provider_name, result in zip(self.providers.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to collect data from {provider_name}: {result}")
            else:
                logger.info(f"Successfully collected data from {provider_name}: {result} records")

    async def _collect_provider_data(self, provider_name: str, collector):
        """Collect data from a specific provider."""
        try:
            start_time = datetime.utcnow()

            # Get pricing data from provider
            pricing_data = await collector.collect_pricing_data(self.session)

            # Store in database
            db = next(get_db())
            try:
                stored_count = await self._store_pricing_data(db, provider_name, pricing_data)

                # Record metrics
                duration = (datetime.utcnow() - start_time).total_seconds()
                metrics_collector.record_pricing_update(provider_name, "all")

                logger.info(f"Stored {stored_count} pricing records for {provider_name}")
                return stored_count

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error collecting data from {provider_name}: {e}")
            raise

    async def _store_pricing_data(self, db, provider_name: str, pricing_data: List[Dict]):
        """Store pricing data in the database."""
        stored_count = 0

        for data in pricing_data:
            try:
                # Get or create provider
                provider = db.query(Provider).filter(Provider.name == provider_name).first()
                if not provider:
                    provider = Provider(
                        name=provider_name,
                        display_name=data.get("provider_display_name", provider_name.title()),
                        is_active=True
                    )
                    db.add(provider)
                    db.commit()
                    db.refresh(provider)

                # Get or create instance type
                instance_type = db.query(InstanceType).filter(
                    InstanceType.name == data["instance_type"],
                    InstanceType.provider_id == provider.id
                ).first()

                if not instance_type:
                    instance_type = InstanceType(
                        name=data["instance_type"],
                        display_name=data.get("instance_display_name", data["instance_type"]),
                        provider_id=provider.id,
                        gpu_count=data.get("gpu_count", 0),
                        gpu_memory_gb=data.get("gpu_memory_gb", 0),
                        cpu_count=data.get("cpu_count", 0),
                        memory_gb=data.get("memory_gb", 0),
                        storage_gb=data.get("storage_gb", 0),
                        is_active=True
                    )
                    db.add(instance_type)
                    db.commit()
                    db.refresh(instance_type)

                # Create pricing data record
                pricing_record = PricingData(
                    provider_id=provider.id,
                    instance_type_id=instance_type.id,
                    region=data["region"],
                    price_per_hour=data["price_per_hour"],
                    spot_price=data.get("spot_price"),
                    timestamp=datetime.utcnow()
                )

                db.add(pricing_record)
                stored_count += 1

            except Exception as e:
                logger.error(f"Error storing pricing data: {e}")
                db.rollback()
                continue

        db.commit()
        return stored_count


class AWSPriceCollector:
    """Collects pricing data from AWS."""

    async def collect_pricing_data(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Collect pricing data from AWS."""
        pricing_data = []

        # AWS Pricing API endpoint
        base_url = "https://pricing.us-east-1.amazonaws.com"

        # Common AWS GPU instance types
        instance_types = [
            "p3.2xlarge", "p3.8xlarge", "p3.16xlarge", "p3dn.24xlarge",
            "p4d.24xlarge", "g4dn.xlarge", "g4dn.2xlarge", "g4dn.4xlarge",
            "g4dn.8xlarge", "g4dn.16xlarge", "g4dn.12xlarge",
            "g5.xlarge", "g5.2xlarge", "g5.4xlarge", "g5.8xlarge", "g5.16xlarge",
            "g5.12xlarge", "g5.24xlarge", "g5.48xlarge"
        ]

        regions = [
            "us-east-1", "us-west-2", "us-west-1", "eu-west-1",
            "eu-central-1", "ap-southeast-1", "ap-northeast-1"
        ]

        for instance_type in instance_types:
            for region in regions:
                try:
                    # Get on-demand pricing
                    on_demand_price = await self._get_aws_on_demand_price(
                        session, base_url, instance_type, region
                    )

                    # Get spot pricing
                    spot_price = await self._get_aws_spot_price(
                        session, instance_type, region
                    )

                    if on_demand_price:
                        pricing_data.append({
                            "instance_type": instance_type,
                            "instance_display_name": f"AWS {instance_type}",
                            "provider_display_name": "Amazon Web Services",
                            "region": region,
                            "price_per_hour": on_demand_price,
                            "spot_price": spot_price,
                            "gpu_count": self._get_gpu_count(instance_type),
                            "gpu_memory_gb": self._get_gpu_memory(instance_type),
                            "cpu_count": self._get_cpu_count(instance_type),
                            "memory_gb": self._get_memory_gb(instance_type),
                            "storage_gb": self._get_storage_gb(instance_type)
                        })

                except Exception as e:
                    logger.error(f"Error collecting AWS pricing for {instance_type} in {region}: {e}")
                    continue

        return pricing_data

    async def _get_aws_on_demand_price(self, session, base_url: str, instance_type: str, region: str) -> Optional[float]:
        """Get AWS on-demand pricing."""
        # This is a simplified implementation
        # In production, you would use the AWS Pricing API
        pricing_map = {
            "p3.2xlarge": 3.06,
            "p3.8xlarge": 12.24,
            "p3.16xlarge": 24.48,
            "p3dn.24xlarge": 31.212,
            "p4d.24xlarge": 32.7726,
            "g4dn.xlarge": 0.526,
            "g4dn.2xlarge": 0.752,
            "g4dn.4xlarge": 1.204,
            "g4dn.8xlarge": 2.176,
            "g4dn.16xlarge": 4.352,
            "g4dn.12xlarge": 3.912,
            "g5.xlarge": 1.006,
            "g5.2xlarge": 1.212,
            "g5.4xlarge": 1.624,
            "g5.8xlarge": 2.448,
            "g5.16xlarge": 4.096,
            "g5.12xlarge": 3.672,
            "g5.24xlarge": 5.672,
            "g5.48xlarge": 8.144
        }

        return pricing_map.get(instance_type)

    async def _get_aws_spot_price(self, session, instance_type: str, region: str) -> Optional[float]:
        """Get AWS spot pricing."""
        # This is a simplified implementation
        # In production, you would use the AWS Spot Instance API
        on_demand_price = await self._get_aws_on_demand_price(session, "", instance_type, region)
        if on_demand_price:
            # Spot prices are typically 50-90% of on-demand
            import random
            discount = random.uniform(0.5, 0.9)
            return on_demand_price * discount
        return None

    def _get_gpu_count(self, instance_type: str) -> int:
        """Get GPU count for instance type."""
        gpu_map = {
            "p3.2xlarge": 1, "p3.8xlarge": 4, "p3.16xlarge": 8, "p3dn.24xlarge": 8,
            "p4d.24xlarge": 8, "g4dn.xlarge": 1, "g4dn.2xlarge": 1, "g4dn.4xlarge": 1,
            "g4dn.8xlarge": 1, "g4dn.16xlarge": 1, "g4dn.12xlarge": 4,
            "g5.xlarge": 1, "g5.2xlarge": 1, "g5.4xlarge": 1, "g5.8xlarge": 1,
            "g5.16xlarge": 1, "g5.12xlarge": 4, "g5.24xlarge": 4, "g5.48xlarge": 8
        }
        return gpu_map.get(instance_type, 0)

    def _get_gpu_memory(self, instance_type: str) -> int:
        """Get GPU memory for instance type."""
        memory_map = {
            "p3.2xlarge": 16, "p3.8xlarge": 64, "p3.16xlarge": 128, "p3dn.24xlarge": 256,
            "p4d.24xlarge": 320, "g4dn.xlarge": 16, "g4dn.2xlarge": 16, "g4dn.4xlarge": 16,
            "g4dn.8xlarge": 16, "g4dn.16xlarge": 16, "g4dn.12xlarge": 64,
            "g5.xlarge": 24, "g5.2xlarge": 24, "g5.4xlarge": 24, "g5.8xlarge": 24,
            "g5.16xlarge": 24, "g5.12xlarge": 96, "g5.24xlarge": 96, "g5.48xlarge": 192
        }
        return memory_map.get(instance_type, 0)

    def _get_cpu_count(self, instance_type: str) -> int:
        """Get CPU count for instance type."""
        cpu_map = {
            "p3.2xlarge": 8, "p3.8xlarge": 32, "p3.16xlarge": 64, "p3dn.24xlarge": 96,
            "p4d.24xlarge": 96, "g4dn.xlarge": 4, "g4dn.2xlarge": 8, "g4dn.4xlarge": 16,
            "g4dn.8xlarge": 32, "g4dn.16xlarge": 64, "g4dn.12xlarge": 48,
            "g5.xlarge": 4, "g5.2xlarge": 8, "g5.4xlarge": 16, "g5.8xlarge": 32,
            "g5.16xlarge": 64, "g5.12xlarge": 48, "g5.24xlarge": 96, "g5.48xlarge": 192
        }
        return cpu_map.get(instance_type, 0)

    def _get_memory_gb(self, instance_type: str) -> int:
        """Get memory for instance type."""
        memory_map = {
            "p3.2xlarge": 61, "p3.8xlarge": 244, "p3.16xlarge": 488, "p3dn.24xlarge": 768,
            "p4d.24xlarge": 1152, "g4dn.xlarge": 16, "g4dn.2xlarge": 32, "g4dn.4xlarge": 64,
            "g4dn.8xlarge": 128, "g4dn.16xlarge": 256, "g4dn.12xlarge": 192,
            "g5.xlarge": 16, "g5.2xlarge": 32, "g5.4xlarge": 64, "g5.8xlarge": 128,
            "g5.16xlarge": 256, "g5.12xlarge": 192, "g5.24xlarge": 384, "g5.48xlarge": 768
        }
        return memory_map.get(instance_type, 0)

    def _get_storage_gb(self, instance_type: str) -> int:
        """Get storage for instance type."""
        storage_map = {
            "p3.2xlarge": 0, "p3.8xlarge": 0, "p3.16xlarge": 0, "p3dn.24xlarge": 1800,
            "p4d.24xlarge": 4000, "g4dn.xlarge": 125, "g4dn.2xlarge": 225, "g4dn.4xlarge": 225,
            "g4dn.8xlarge": 900, "g4dn.16xlarge": 900, "g4dn.12xlarge": 900,
            "g5.xlarge": 0, "g5.2xlarge": 0, "g5.4xlarge": 0, "g5.8xlarge": 0,
            "g5.16xlarge": 0, "g5.12xlarge": 0, "g5.24xlarge": 0, "g5.48xlarge": 0
        }
        return storage_map.get(instance_type, 0)


class GCPPriceCollector:
    """Collects pricing data from Google Cloud Platform."""

    async def collect_pricing_data(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Collect pricing data from GCP."""
        # Simplified implementation
        pricing_data = []

        instance_types = [
            "n1-standard-4", "n1-standard-8", "n1-standard-16", "n1-standard-32",
            "n1-standard-64", "n1-highmem-4", "n1-highmem-8", "n1-highmem-16",
            "n1-highmem-32", "n1-highmem-64", "n1-highcpu-4", "n1-highcpu-8",
            "n1-highcpu-16", "n1-highcpu-32", "n1-highcpu-64"
        ]

        regions = ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"]

        for instance_type in instance_types:
            for region in regions:
                # Simplified pricing
                base_price = 0.1  # $0.10 per hour base
                pricing_data.append({
                    "instance_type": instance_type,
                    "instance_display_name": f"GCP {instance_type}",
                    "provider_display_name": "Google Cloud Platform",
                    "region": region,
                    "price_per_hour": base_price,
                    "spot_price": base_price * 0.7,
                    "gpu_count": 0,
                    "gpu_memory_gb": 0,
                    "cpu_count": 4,
                    "memory_gb": 15,
                    "storage_gb": 0
                })

        return pricing_data


class AzurePriceCollector:
    """Collects pricing data from Microsoft Azure."""

    async def collect_pricing_data(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Collect pricing data from Azure."""
        # Simplified implementation
        pricing_data = []

        instance_types = [
            "Standard_NC6", "Standard_NC12", "Standard_NC24", "Standard_NC24r",
            "Standard_ND6", "Standard_ND12", "Standard_ND24", "Standard_ND24r"
        ]

        regions = ["eastus", "westus2", "westeurope", "southeastasia"]

        for instance_type in instance_types:
            for region in regions:
                # Simplified pricing
                base_price = 0.9  # $0.90 per hour base
                pricing_data.append({
                    "instance_type": instance_type,
                    "instance_display_name": f"Azure {instance_type}",
                    "provider_display_name": "Microsoft Azure",
                    "region": region,
                    "price_per_hour": base_price,
                    "spot_price": base_price * 0.6,
                    "gpu_count": 1,
                    "gpu_memory_gb": 16,
                    "cpu_count": 6,
                    "memory_gb": 56,
                    "storage_gb": 0
                })

        return pricing_data


class LambdaPriceCollector:
    """Collects pricing data from Lambda Labs."""

    async def collect_pricing_data(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Collect pricing data from Lambda Labs."""
        # Simplified implementation
        pricing_data = []

        instance_types = [
            "gpu_1x_a100", "gpu_2x_a100", "gpu_4x_a100", "gpu_8x_a100"
        ]

        regions = ["us-east-1", "us-west-1", "us-south-1"]

        for instance_type in instance_types:
            for region in regions:
                # Simplified pricing
                base_price = 1.2  # $1.20 per hour base
                pricing_data.append({
                    "instance_type": instance_type,
                    "instance_display_name": f"Lambda {instance_type}",
                    "provider_display_name": "Lambda Labs",
                    "region": region,
                    "price_per_hour": base_price,
                    "spot_price": None,  # Lambda doesn't have spot instances
                    "gpu_count": 1,
                    "gpu_memory_gb": 40,
                    "cpu_count": 8,
                    "memory_gb": 64,
                    "storage_gb": 0
                })

        return pricing_data


class RunPodPriceCollector:
    """Collects pricing data from RunPod."""

    async def collect_pricing_data(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Collect pricing data from RunPod."""
        # Simplified implementation
        pricing_data = []

        instance_types = [
            "RTX 4090", "RTX 3090", "RTX 3080", "RTX 3070"
        ]

        regions = ["US-East", "US-West", "EU-West"]

        for instance_type in instance_types:
            for region in regions:
                # Simplified pricing
                base_price = 0.8  # $0.80 per hour base
                pricing_data.append({
                    "instance_type": instance_type,
                    "instance_display_name": f"RunPod {instance_type}",
                    "provider_display_name": "RunPod",
                    "region": region,
                    "price_per_hour": base_price,
                    "spot_price": None,  # RunPod doesn't have spot instances
                    "gpu_count": 1,
                    "gpu_memory_gb": 24,
                    "cpu_count": 6,
                    "memory_gb": 32,
                    "storage_gb": 0
                })

        return pricing_data


async def run_data_ingestion():
    """Run the data ingestion process."""
    async with PricingDataCollector() as collector:
        await collector.collect_all_pricing_data()


def start_data_ingestion_scheduler():
    """Start the data ingestion scheduler."""
    async def scheduler():
        while True:
            try:
                await run_data_ingestion()
                logger.info("Data ingestion completed successfully")
            except Exception as e:
                logger.error(f"Data ingestion failed: {e}")

            # Wait for next collection cycle (every hour)
            await asyncio.sleep(3600)

    # Run the scheduler
    asyncio.run(scheduler())


if __name__ == "__main__":
    # Run data ingestion once
    asyncio.run(run_data_ingestion())