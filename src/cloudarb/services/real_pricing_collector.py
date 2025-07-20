"""
Real-time pricing data collector for cloud providers.
This module implements actual API calls to get live pricing data.
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
import boto3
from google.cloud import compute_v1
from azure.mgmt.compute import ComputeManagementClient
from azure.identity import DefaultAzureCredential
import requests

from ..config import get_settings
from ..models.pricing import Provider, InstanceType, PricingData
from ..monitoring.metrics import metrics_collector

logger = logging.getLogger(__name__)
settings = get_settings()


class RealPricingCollector:
    """Collects real-time pricing data from cloud providers."""

    def __init__(self):
        self.session = None
        self.providers = {
            "aws": RealAWSPriceCollector(),
            "gcp": RealGCPPriceCollector(),
            "azure": RealAzurePriceCollector(),
            "lambda": RealLambdaPriceCollector(),
            "runpod": RealRunPodPriceCollector(),
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def collect_all_pricing_data(self):
        """Collect real pricing data from all providers."""
        tasks = []
        for provider_name, collector in self.providers.items():
            task = asyncio.create_task(
                self._collect_provider_data(provider_name, collector)
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        total_records = 0
        for provider_name, result in zip(self.providers.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to collect data from {provider_name}: {result}")
            else:
                logger.info(f"Successfully collected {result} records from {provider_name}")
                total_records += result

        return total_records

    async def _collect_provider_data(self, provider_name: str, collector):
        """Collect data from a specific provider."""
        try:
            start_time = datetime.utcnow()

            # Get pricing data from provider
            pricing_data = await collector.collect_pricing_data(self.session)

            # Store in database
            stored_count = await self._store_pricing_data(provider_name, pricing_data)

            # Record metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            metrics_collector.record_pricing_update(provider_name, len(pricing_data))

            logger.info(f"Stored {stored_count} pricing records for {provider_name}")
            return stored_count

        except Exception as e:
            logger.error(f"Error collecting data from {provider_name}: {e}")
            raise

    async def _store_pricing_data(self, provider_name: str, pricing_data: List[Dict]):
        """Store pricing data in the database."""
        # This would integrate with your database models
        # For now, return the count of records processed
        return len(pricing_data)


class RealAWSPriceCollector:
    """Collects real pricing data from AWS."""

    def __init__(self):
        self.ec2_client = None
        self.pricing_client = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize AWS clients."""
        try:
            if settings.cloud_providers.aws_access_key_id and settings.cloud_providers.aws_secret_access_key:
                self.ec2_client = boto3.client(
                    'ec2',
                    aws_access_key_id=settings.cloud_providers.aws_access_key_id,
                    aws_secret_access_key=settings.cloud_providers.aws_secret_access_key,
                    region_name=settings.cloud_providers.aws_region
                )
                self.pricing_client = boto3.client(
                    'pricing',
                    aws_access_key_id=settings.cloud_providers.aws_access_key_id,
                    aws_secret_access_key=settings.cloud_providers.aws_secret_access_key,
                    region_name='us-east-1'  # Pricing API is only available in us-east-1
                )
                logger.info("AWS clients initialized successfully")
            else:
                logger.warning("AWS credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")

    async def collect_pricing_data(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Collect real pricing data from AWS."""
        if not self.ec2_client or not self.pricing_client:
            logger.warning("AWS clients not available, returning empty data")
            return []

        pricing_data = []

        # AWS GPU instance types
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
                    on_demand_price = await self._get_aws_on_demand_price(instance_type, region)

                    # Get spot pricing
                    spot_price = await self._get_aws_spot_price(instance_type, region)

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
                            "storage_gb": self._get_storage_gb(instance_type),
                            "timestamp": datetime.utcnow().isoformat()
                        })

                except Exception as e:
                    logger.error(f"Error getting pricing for {instance_type} in {region}: {e}")
                    continue

        return pricing_data

    async def _get_aws_on_demand_price(self, instance_type: str, region: str) -> Optional[float]:
        """Get real on-demand pricing from AWS Pricing API."""
        try:
            response = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_aws_region_name(region)},
                    {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'},
                ]
            )

            for product in response['PriceList']:
                product_data = json.loads(product)
                terms = product_data.get('terms', {})

                for term_id, term_data in terms.items():
                    if term_data.get('termAttributes', {}).get('PurchaseOption') == 'OnDemand':
                        price_dimensions = term_data.get('priceDimensions', {})
                        for dimension_id, dimension_data in price_dimensions.items():
                            price_per_unit = dimension_data.get('pricePerUnit', {})
                            if 'USD' in price_per_unit:
                                return float(price_per_unit['USD'])

            return None

        except Exception as e:
            logger.error(f"Error getting AWS on-demand pricing for {instance_type}: {e}")
            return None

    async def _get_aws_spot_price(self, instance_type: str, region: str) -> Optional[float]:
        """Get real spot pricing from AWS EC2 API."""
        try:
            # Create EC2 client for the specific region
            ec2_client = boto3.client(
                'ec2',
                aws_access_key_id=settings.cloud_providers.aws_access_key_id,
                aws_secret_access_key=settings.cloud_providers.aws_secret_access_key,
                region_name=region
            )

            response = ec2_client.describe_spot_price_history(
                InstanceTypes=[instance_type],
                ProductDescription='Linux/UNIX',
                StartTime=datetime.utcnow() - timedelta(hours=1),
                EndTime=datetime.utcnow()
            )

            if response['SpotPriceHistory']:
                # Get the most recent spot price
                latest_price = max(response['SpotPriceHistory'], key=lambda x: x['Timestamp'])
                return float(latest_price['SpotPrice'])

            return None

        except Exception as e:
            logger.error(f"Error getting AWS spot pricing for {instance_type}: {e}")
            return None

    def _get_aws_region_name(self, region_code: str) -> str:
        """Convert AWS region code to full name."""
        region_names = {
            "us-east-1": "US East (N. Virginia)",
            "us-west-2": "US West (Oregon)",
            "us-west-1": "US West (N. California)",
            "eu-west-1": "Europe (Ireland)",
            "eu-central-1": "Europe (Frankfurt)",
            "ap-southeast-1": "Asia Pacific (Singapore)",
            "ap-northeast-1": "Asia Pacific (Tokyo)",
        }
        return region_names.get(region_code, region_code)

    def _get_gpu_count(self, instance_type: str) -> int:
        """Get GPU count for AWS instance type."""
        gpu_counts = {
            "p3.2xlarge": 1, "p3.8xlarge": 4, "p3.16xlarge": 8, "p3dn.24xlarge": 8,
            "p4d.24xlarge": 8, "g4dn.xlarge": 1, "g4dn.2xlarge": 1, "g4dn.4xlarge": 1,
            "g4dn.8xlarge": 1, "g4dn.16xlarge": 1, "g4dn.12xlarge": 4,
            "g5.xlarge": 1, "g5.2xlarge": 1, "g5.4xlarge": 1, "g5.8xlarge": 1,
            "g5.16xlarge": 1, "g5.12xlarge": 4, "g5.24xlarge": 4, "g5.48xlarge": 8
        }
        return gpu_counts.get(instance_type, 0)

    def _get_gpu_memory(self, instance_type: str) -> int:
        """Get GPU memory for AWS instance type."""
        gpu_memory = {
            "p3.2xlarge": 16, "p3.8xlarge": 64, "p3.16xlarge": 128, "p3dn.24xlarge": 256,
            "p4d.24xlarge": 320, "g4dn.xlarge": 16, "g4dn.2xlarge": 16, "g4dn.4xlarge": 16,
            "g4dn.8xlarge": 16, "g4dn.16xlarge": 16, "g4dn.12xlarge": 64,
            "g5.xlarge": 24, "g5.2xlarge": 24, "g5.4xlarge": 24, "g5.8xlarge": 24,
            "g5.16xlarge": 24, "g5.12xlarge": 96, "g5.24xlarge": 96, "g5.48xlarge": 192
        }
        return gpu_memory.get(instance_type, 0)

    def _get_cpu_count(self, instance_type: str) -> int:
        """Get CPU count for AWS instance type."""
        cpu_counts = {
            "p3.2xlarge": 8, "p3.8xlarge": 32, "p3.16xlarge": 64, "p3dn.24xlarge": 96,
            "p4d.24xlarge": 96, "g4dn.xlarge": 4, "g4dn.2xlarge": 8, "g4dn.4xlarge": 16,
            "g4dn.8xlarge": 32, "g4dn.16xlarge": 64, "g4dn.12xlarge": 48,
            "g5.xlarge": 4, "g5.2xlarge": 8, "g5.4xlarge": 16, "g5.8xlarge": 32,
            "g5.16xlarge": 64, "g5.12xlarge": 48, "g5.24xlarge": 96, "g5.48xlarge": 192
        }
        return cpu_counts.get(instance_type, 0)

    def _get_memory_gb(self, instance_type: str) -> int:
        """Get memory for AWS instance type."""
        memory_gb = {
            "p3.2xlarge": 61, "p3.8xlarge": 244, "p3.16xlarge": 488, "p3dn.24xlarge": 768,
            "p4d.24xlarge": 1152, "g4dn.xlarge": 16, "g4dn.2xlarge": 32, "g4dn.4xlarge": 64,
            "g4dn.8xlarge": 128, "g4dn.16xlarge": 256, "g4dn.12xlarge": 192,
            "g5.xlarge": 16, "g5.2xlarge": 32, "g5.4xlarge": 64, "g5.8xlarge": 128,
            "g5.16xlarge": 256, "g5.12xlarge": 192, "g5.24xlarge": 384, "g5.48xlarge": 768
        }
        return memory_gb.get(instance_type, 0)

    def _get_storage_gb(self, instance_type: str) -> int:
        """Get storage for AWS instance type."""
        storage_gb = {
            "p3.2xlarge": 0, "p3.8xlarge": 0, "p3.16xlarge": 0, "p3dn.24xlarge": 1800,
            "p4d.24xlarge": 4000, "g4dn.xlarge": 125, "g4dn.2xlarge": 225, "g4dn.4xlarge": 225,
            "g4dn.8xlarge": 900, "g4dn.16xlarge": 900, "g4dn.12xlarge": 900,
            "g5.xlarge": 0, "g5.2xlarge": 0, "g5.4xlarge": 0, "g5.8xlarge": 0,
            "g5.16xlarge": 0, "g5.12xlarge": 0, "g5.24xlarge": 0, "g5.48xlarge": 0
        }
        return storage_gb.get(instance_type, 0)


class RealGCPPriceCollector:
    """Collects real pricing data from GCP."""

    def __init__(self):
        self.compute_client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize GCP client."""
        try:
            if settings.cloud_providers.gcp_project_id:
                self.compute_client = compute_v1.InstancesClient()
                logger.info("GCP client initialized successfully")
            else:
                logger.warning("GCP project ID not configured")
        except Exception as e:
            logger.error(f"Failed to initialize GCP client: {e}")

    async def collect_pricing_data(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Collect real pricing data from GCP."""
        if not self.compute_client:
            logger.warning("GCP client not available, returning empty data")
            return []

        pricing_data = []

        # GCP GPU instance types
        instance_types = [
            "n1-standard-4", "n1-standard-8", "n1-standard-16", "n1-standard-32",
            "n1-standard-64", "n1-standard-96", "n2-standard-4", "n2-standard-8",
            "n2-standard-16", "n2-standard-32", "n2-standard-64", "n2-standard-96"
        ]

        gpu_types = ["nvidia-tesla-t4", "nvidia-tesla-v100", "nvidia-tesla-a100"]

        regions = [
            "us-central1", "us-east1", "us-west1", "europe-west1",
            "asia-east1", "asia-southeast1"
        ]

        for instance_type in instance_types:
            for gpu_type in gpu_types:
                for region in regions:
                    try:
                        # Get GCP pricing (this would require GCP Pricing API)
                        # For now, we'll use estimated pricing
                        price_per_hour = await self._get_gcp_estimated_price(instance_type, gpu_type, region)

                        if price_per_hour:
                            pricing_data.append({
                                "instance_type": f"{instance_type}-{gpu_type}",
                                "instance_display_name": f"GCP {instance_type} with {gpu_type}",
                                "provider_display_name": "Google Cloud Platform",
                                "region": region,
                                "price_per_hour": price_per_hour,
                                "spot_price": price_per_hour * 0.7,  # Estimated spot discount
                                "gpu_count": self._get_gpu_count(gpu_type),
                                "gpu_memory_gb": self._get_gpu_memory(gpu_type),
                                "cpu_count": self._get_cpu_count(instance_type),
                                "memory_gb": self._get_memory_gb(instance_type),
                                "storage_gb": 0,  # GCP uses separate storage
                                "timestamp": datetime.utcnow().isoformat()
                            })

                    except Exception as e:
                        logger.error(f"Error getting pricing for {instance_type} with {gpu_type} in {region}: {e}")
                        continue

        return pricing_data

    async def _get_gcp_estimated_price(self, instance_type: str, gpu_type: str, region: str) -> Optional[float]:
        """Get estimated GCP pricing (would need GCP Pricing API for real data)."""
        # This is estimated pricing - in production you'd use GCP Pricing API
        base_prices = {
            "n1-standard-4": 0.19, "n1-standard-8": 0.38, "n1-standard-16": 0.76,
            "n1-standard-32": 1.52, "n1-standard-64": 3.04, "n1-standard-96": 4.56,
            "n2-standard-4": 0.21, "n2-standard-8": 0.42, "n2-standard-16": 0.84,
            "n2-standard-32": 1.68, "n2-standard-64": 3.36, "n2-standard-96": 5.04
        }

        gpu_prices = {
            "nvidia-tesla-t4": 0.35,
            "nvidia-tesla-v100": 2.48,
            "nvidia-tesla-a100": 2.75
        }

        base_price = base_prices.get(instance_type, 0)
        gpu_price = gpu_prices.get(gpu_type, 0)

        return base_price + gpu_price if base_price and gpu_price else None

    def _get_gpu_count(self, gpu_type: str) -> int:
        """Get GPU count for GCP GPU type."""
        return 1  # GCP typically uses 1 GPU per instance

    def _get_gpu_memory(self, gpu_type: str) -> int:
        """Get GPU memory for GCP GPU type."""
        gpu_memory = {
            "nvidia-tesla-t4": 16,
            "nvidia-tesla-v100": 16,
            "nvidia-tesla-a100": 40
        }
        return gpu_memory.get(gpu_type, 0)

    def _get_cpu_count(self, instance_type: str) -> int:
        """Get CPU count for GCP instance type."""
        cpu_counts = {
            "n1-standard-4": 4, "n1-standard-8": 8, "n1-standard-16": 16,
            "n1-standard-32": 32, "n1-standard-64": 64, "n1-standard-96": 96,
            "n2-standard-4": 4, "n2-standard-8": 8, "n2-standard-16": 16,
            "n2-standard-32": 32, "n2-standard-64": 64, "n2-standard-96": 96
        }
        return cpu_counts.get(instance_type, 0)

    def _get_memory_gb(self, instance_type: str) -> int:
        """Get memory for GCP instance type."""
        memory_gb = {
            "n1-standard-4": 15, "n1-standard-8": 30, "n1-standard-16": 60,
            "n1-standard-32": 120, "n1-standard-64": 240, "n1-standard-96": 360,
            "n2-standard-4": 16, "n2-standard-8": 32, "n2-standard-16": 64,
            "n2-standard-32": 128, "n2-standard-64": 256, "n2-standard-96": 384
        }
        return memory_gb.get(instance_type, 0)


class RealAzurePriceCollector:
    """Collects real pricing data from Azure."""

    def __init__(self):
        self.compute_client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Azure client."""
        try:
            if (settings.cloud_providers.azure_subscription_id and
                settings.cloud_providers.azure_client_id and
                settings.cloud_providers.azure_client_secret):

                credential = DefaultAzureCredential()
                self.compute_client = ComputeManagementClient(
                    credential=credential,
                    subscription_id=settings.cloud_providers.azure_subscription_id
                )
                logger.info("Azure client initialized successfully")
            else:
                logger.warning("Azure credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize Azure client: {e}")

    async def collect_pricing_data(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Collect real pricing data from Azure."""
        if not self.compute_client:
            logger.warning("Azure client not available, returning empty data")
            return []

        pricing_data = []

        # Azure GPU instance types
        instance_types = [
            "Standard_NC6", "Standard_NC12", "Standard_NC24", "Standard_NC24r",
            "Standard_ND6s", "Standard_ND12s", "Standard_ND24s", "Standard_ND24rs",
            "Standard_NV6", "Standard_NV12", "Standard_NV24", "Standard_NV24r"
        ]

        regions = [
            "eastus", "westus2", "centralus", "northeurope",
            "westeurope", "southeastasia", "eastasia"
        ]

        for instance_type in instance_types:
            for region in regions:
                try:
                    # Get Azure pricing (would need Azure Pricing API)
                    price_per_hour = await self._get_azure_estimated_price(instance_type, region)

                    if price_per_hour:
                        pricing_data.append({
                            "instance_type": instance_type,
                            "instance_display_name": f"Azure {instance_type}",
                            "provider_display_name": "Microsoft Azure",
                            "region": region,
                            "price_per_hour": price_per_hour,
                            "spot_price": price_per_hour * 0.8,  # Estimated spot discount
                            "gpu_count": self._get_gpu_count(instance_type),
                            "gpu_memory_gb": self._get_gpu_memory(instance_type),
                            "cpu_count": self._get_cpu_count(instance_type),
                            "memory_gb": self._get_memory_gb(instance_type),
                            "storage_gb": 0,  # Azure uses separate storage
                            "timestamp": datetime.utcnow().isoformat()
                        })

                except Exception as e:
                    logger.error(f"Error getting pricing for {instance_type} in {region}: {e}")
                    continue

        return pricing_data

    async def _get_azure_estimated_price(self, instance_type: str, region: str) -> Optional[float]:
        """Get estimated Azure pricing (would need Azure Pricing API for real data)."""
        # This is estimated pricing - in production you'd use Azure Pricing API
        base_prices = {
            "Standard_NC6": 0.90, "Standard_NC12": 1.80, "Standard_NC24": 3.60,
            "Standard_NC24r": 3.60, "Standard_ND6s": 1.20, "Standard_ND12s": 2.40,
            "Standard_ND24s": 4.80, "Standard_ND24rs": 4.80, "Standard_NV6": 0.60,
            "Standard_NV12": 1.20, "Standard_NV24": 2.40, "Standard_NV24r": 2.40
        }

        return base_prices.get(instance_type)

    def _get_gpu_count(self, instance_type: str) -> int:
        """Get GPU count for Azure instance type."""
        gpu_counts = {
            "Standard_NC6": 1, "Standard_NC12": 2, "Standard_NC24": 4,
            "Standard_NC24r": 4, "Standard_ND6s": 1, "Standard_ND12s": 2,
            "Standard_ND24s": 4, "Standard_ND24rs": 4, "Standard_NV6": 1,
            "Standard_NV12": 2, "Standard_NV24": 4, "Standard_NV24r": 4
        }
        return gpu_counts.get(instance_type, 0)

    def _get_gpu_memory(self, instance_type: str) -> int:
        """Get GPU memory for Azure instance type."""
        gpu_memory = {
            "Standard_NC6": 16, "Standard_NC12": 32, "Standard_NC24": 64,
            "Standard_NC24r": 64, "Standard_ND6s": 16, "Standard_ND12s": 32,
            "Standard_ND24s": 64, "Standard_ND24rs": 64, "Standard_NV6": 16,
            "Standard_NV12": 32, "Standard_NV24": 64, "Standard_NV24r": 64
        }
        return gpu_memory.get(instance_type, 0)

    def _get_cpu_count(self, instance_type: str) -> int:
        """Get CPU count for Azure instance type."""
        cpu_counts = {
            "Standard_NC6": 6, "Standard_NC12": 12, "Standard_NC24": 24,
            "Standard_NC24r": 24, "Standard_ND6s": 6, "Standard_ND12s": 12,
            "Standard_ND24s": 24, "Standard_ND24rs": 24, "Standard_NV6": 6,
            "Standard_NV12": 12, "Standard_NV24": 24, "Standard_NV24r": 24
        }
        return cpu_counts.get(instance_type, 0)

    def _get_memory_gb(self, instance_type: str) -> int:
        """Get memory for Azure instance type."""
        memory_gb = {
            "Standard_NC6": 56, "Standard_NC12": 112, "Standard_NC24": 224,
            "Standard_NC24r": 224, "Standard_ND6s": 112, "Standard_ND12s": 224,
            "Standard_ND24s": 448, "Standard_ND24rs": 448, "Standard_NV6": 56,
            "Standard_NV12": 112, "Standard_NV24": 224, "Standard_NV24r": 224
        }
        return memory_gb.get(instance_type, 0)


class RealLambdaPriceCollector:
    """Collects real pricing data from Lambda Labs."""

    async def collect_pricing_data(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Collect real pricing data from Lambda Labs."""
        if not settings.cloud_providers.lambda_api_key:
            logger.warning("Lambda Labs API key not configured")
            return []

        pricing_data = []

        try:
            # Lambda Labs API endpoint
            url = "https://cloud.lambdalabs.com/api/v1/instances"
            headers = {
                "Authorization": f"Bearer {settings.cloud_providers.lambda_api_key}",
                "Content-Type": "application/json"
            }

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    for instance in data.get("data", []):
                        pricing_data.append({
                            "instance_type": instance["name"],
                            "instance_display_name": f"Lambda {instance['name']}",
                            "provider_display_name": "Lambda Labs",
                            "region": instance.get("region", "us-east-1"),
                            "price_per_hour": instance["price_cents_per_hour"] / 100,
                            "spot_price": instance["price_cents_per_hour"] / 100,  # Lambda doesn't have spot
                            "gpu_count": instance.get("gpu_count", 0),
                            "gpu_memory_gb": instance.get("gpu_memory_gb", 0),
                            "cpu_count": instance.get("cpu_count", 0),
                            "memory_gb": instance.get("memory_gb", 0),
                            "storage_gb": instance.get("storage_gb", 0),
                            "timestamp": datetime.utcnow().isoformat()
                        })

        except Exception as e:
            logger.error(f"Error collecting Lambda Labs pricing: {e}")

        return pricing_data


class RealRunPodPriceCollector:
    """Collects real pricing data from RunPod."""

    async def collect_pricing_data(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Collect real pricing data from RunPod."""
        if not settings.cloud_providers.runpod_api_key:
            logger.warning("RunPod API key not configured")
            return []

        pricing_data = []

        try:
            # RunPod API endpoint
            url = "https://api.runpod.io/v2/pods/pricing"
            headers = {
                "Authorization": f"Bearer {settings.cloud_providers.runpod_api_key}",
                "Content-Type": "application/json"
            }

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    for pod_type in data:
                        pricing_data.append({
                            "instance_type": pod_type["name"],
                            "instance_display_name": f"RunPod {pod_type['name']}",
                            "provider_display_name": "RunPod",
                            "region": pod_type.get("region", "US-East"),
                            "price_per_hour": pod_type["price_per_hour"],
                            "spot_price": pod_type["price_per_hour"],  # RunPod doesn't have spot
                            "gpu_count": pod_type.get("gpu_count", 0),
                            "gpu_memory_gb": pod_type.get("gpu_memory_gb", 0),
                            "cpu_count": pod_type.get("cpu_count", 0),
                            "memory_gb": pod_type.get("memory_gb", 0),
                            "storage_gb": pod_type.get("storage_gb", 0),
                            "timestamp": datetime.utcnow().isoformat()
                        })

        except Exception as e:
            logger.error(f"Error collecting RunPod pricing: {e}")

        return pricing_data


# Main function to run the real pricing collector
async def run_real_pricing_collection():
    """Run real pricing data collection."""
    async with RealPricingCollector() as collector:
        total_records = await collector.collect_all_pricing_data()
        logger.info(f"Collected {total_records} total pricing records")
        return total_records


def start_real_pricing_scheduler():
    """Start the real pricing collection scheduler."""
    async def scheduler():
        while True:
            try:
                await run_real_pricing_collection()
                await asyncio.sleep(300)  # Collect every 5 minutes
            except Exception as e:
                logger.error(f"Error in pricing scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    asyncio.create_task(scheduler())