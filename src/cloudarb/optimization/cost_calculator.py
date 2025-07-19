"""
Cost calculator component for GPU optimization.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

from .models import InstanceOption, PricingType

logger = logging.getLogger(__name__)


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for an allocation."""

    compute_cost: float
    storage_cost: float
    network_cost: float
    data_transfer_cost: float
    total_cost: float
    cost_per_gpu_hour: float
    cost_performance_ratio: float


class CostCalculator:
    """Cost calculation and analysis for GPU allocations."""

    def __init__(self):
        """Initialize cost calculator."""
        # Storage costs per GB per month (approximate)
        self.storage_costs = {
            "AWS": 0.08,  # EBS gp3
            "GCP": 0.04,  # Standard persistent disk
            "Azure": 0.05,  # Premium SSD
            "Lambda Labs": 0.05,
            "RunPod": 0.05,
        }

        # Network costs per GB (approximate)
        self.network_costs = {
            "AWS": 0.09,  # Outbound data transfer
            "GCP": 0.12,  # Outbound data transfer
            "Azure": 0.087,  # Outbound data transfer
            "Lambda Labs": 0.10,
            "RunPod": 0.10,
        }

        # Data transfer costs between regions (per GB)
        self.cross_region_transfer_costs = {
            "AWS": 0.02,
            "GCP": 0.02,
            "Azure": 0.02,
        }

    def calculate_total_cost(
        self,
        instance: InstanceOption,
        pricing_type: PricingType,
        duration_hours: float = 1.0,
        storage_gb: Optional[float] = None,
        data_transfer_gb: Optional[float] = None,
        network_bandwidth_gbps: Optional[float] = None
    ) -> CostBreakdown:
        """
        Calculate total cost for an instance allocation.

        Args:
            instance: Instance option
            pricing_type: Pricing type
            duration_hours: Duration in hours
            storage_gb: Storage usage in GB
            data_transfer_gb: Data transfer in GB
            network_bandwidth_gbps: Network bandwidth usage

        Returns:
            CostBreakdown: Detailed cost breakdown
        """
        # Base compute cost
        compute_cost = self._calculate_compute_cost(instance, pricing_type, duration_hours)

        # Storage cost
        storage_cost = self._calculate_storage_cost(instance, storage_gb, duration_hours)

        # Network cost
        network_cost = self._calculate_network_cost(instance, network_bandwidth_gbps, duration_hours)

        # Data transfer cost
        data_transfer_cost = self._calculate_data_transfer_cost(instance, data_transfer_gb)

        # Total cost
        total_cost = compute_cost + storage_cost + network_cost + data_transfer_cost

        # Cost per GPU hour
        cost_per_gpu_hour = total_cost / (instance.gpu_count * duration_hours) if instance.gpu_count > 0 else 0

        # Cost-performance ratio
        cost_performance_ratio = self._calculate_cost_performance_ratio(instance, total_cost, duration_hours)

        return CostBreakdown(
            compute_cost=compute_cost,
            storage_cost=storage_cost,
            network_cost=network_cost,
            data_transfer_cost=data_transfer_cost,
            total_cost=total_cost,
            cost_per_gpu_hour=cost_per_gpu_hour,
            cost_performance_ratio=cost_performance_ratio
        )

    def _calculate_compute_cost(self, instance: InstanceOption, pricing_type: PricingType, duration_hours: float) -> float:
        """Calculate compute cost for the instance."""
        base_price = instance.get_price(pricing_type)
        if base_price is None:
            return 0.0

        # Apply pricing type multipliers
        if pricing_type == PricingType.SPOT:
            # Spot instances may have additional overhead for interruption handling
            multiplier = 1.05  # 5% overhead
        elif pricing_type in [PricingType.RESERVED_1Y, PricingType.RESERVED_3Y]:
            # Reserved instances have upfront costs amortized over time
            multiplier = 1.0
        else:
            multiplier = 1.0

        return base_price * duration_hours * multiplier

    def _calculate_storage_cost(self, instance: InstanceOption, storage_gb: Optional[float], duration_hours: float) -> float:
        """Calculate storage cost."""
        if storage_gb is None:
            storage_gb = instance.storage_gb or 100.0  # Default storage

        provider = instance.provider_name
        storage_cost_per_gb_month = self.storage_costs.get(provider, 0.05)

        # Convert monthly cost to hourly
        storage_cost_per_gb_hour = storage_cost_per_gb_month / (30 * 24)

        return storage_gb * storage_cost_per_gb_hour * duration_hours

    def _calculate_network_cost(self, instance: InstanceOption, network_bandwidth_gbps: Optional[float], duration_hours: float) -> float:
        """Calculate network bandwidth cost."""
        if network_bandwidth_gbps is None:
            network_bandwidth_gbps = instance.network_bandwidth_gbps or 10.0  # Default bandwidth

        # Convert GBps to GB for the duration
        network_gb = network_bandwidth_gbps * 3600 * duration_hours  # GBps * seconds

        provider = instance.provider_name
        network_cost_per_gb = self.network_costs.get(provider, 0.10)

        return network_gb * network_cost_per_gb

    def _calculate_data_transfer_cost(self, instance: InstanceOption, data_transfer_gb: Optional[float]) -> float:
        """Calculate data transfer cost."""
        if data_transfer_gb is None:
            return 0.0

        provider = instance.provider_name
        transfer_cost_per_gb = self.network_costs.get(provider, 0.10)

        return data_transfer_gb * transfer_cost_per_gb

    def _calculate_cost_performance_ratio(self, instance: InstanceOption, total_cost: float, duration_hours: float) -> float:
        """Calculate cost-performance ratio (lower is better)."""
        if total_cost <= 0:
            return float('inf')

        # Use performance score if available, otherwise estimate based on GPU type
        if instance.performance_score:
            performance = instance.performance_score
        else:
            # Estimate performance based on GPU type
            gpu_performance = {
                "v100": 70,
                "a100": 90,
                "h100": 95,
                "rtx4090": 85,
                "rtx3090": 75,
            }
            performance = gpu_performance.get(instance.gpu_type, 60)

        # Calculate cost per performance point per hour
        total_performance = performance * instance.gpu_count * duration_hours
        return total_cost / total_performance if total_performance > 0 else float('inf')

    def compare_costs(self, instances: List[InstanceOption], pricing_type: PricingType = PricingType.ON_DEMAND) -> Dict[str, Any]:
        """
        Compare costs across multiple instances.

        Args:
            instances: List of instances to compare
            pricing_type: Pricing type to use for comparison

        Returns:
            Dict containing cost comparison results
        """
        if not instances:
            return {"error": "No instances provided"}

        comparisons = []
        costs_per_gpu = []

        for instance in instances:
            breakdown = self.calculate_total_cost(instance, pricing_type)

            comparison = {
                "provider": instance.provider_name,
                "instance_type": instance.instance_name,
                "gpu_type": instance.gpu_type,
                "gpu_count": instance.gpu_count,
                "region": instance.region,
                "total_cost_per_hour": breakdown.total_cost,
                "cost_per_gpu_hour": breakdown.cost_per_gpu_hour,
                "cost_performance_ratio": breakdown.cost_performance_ratio,
                "performance_score": instance.performance_score or 60,
                "breakdown": {
                    "compute": breakdown.compute_cost,
                    "storage": breakdown.storage_cost,
                    "network": breakdown.network_cost,
                    "data_transfer": breakdown.data_transfer_cost,
                }
            }

            comparisons.append(comparison)
            costs_per_gpu.append(breakdown.cost_per_gpu_hour)

        # Find best and worst options
        best_idx = np.argmin(costs_per_gpu)
        worst_idx = np.argmax(costs_per_gpu)

        return {
            "comparisons": comparisons,
            "best_option": comparisons[best_idx],
            "worst_option": comparisons[worst_idx],
            "cost_range": {
                "min": min(costs_per_gpu),
                "max": max(costs_per_gpu),
                "mean": np.mean(costs_per_gpu),
                "std": np.std(costs_per_gpu),
            },
            "recommendations": self._get_cost_recommendations(comparisons)
        }

    def _get_cost_recommendations(self, comparisons: List[Dict[str, Any]]) -> List[str]:
        """Get cost optimization recommendations."""
        recommendations = []

        # Find cost differences
        costs = [comp["cost_per_gpu_hour"] for comp in comparisons]
        min_cost = min(costs)
        max_cost = max(costs)

        if max_cost > min_cost * 1.5:
            recommendations.append(f"Cost varies significantly (${min_cost:.2f} - ${max_cost:.2f} per GPU hour). Consider cheaper alternatives.")

        # Check for spot instance opportunities
        spot_instances = [comp for comp in comparisons if "spot" in comp.get("pricing_type", "").lower()]
        if spot_instances:
            spot_savings = [(comp["cost_per_gpu_hour"], comp["provider"]) for comp in spot_instances]
            best_spot = min(spot_savings, key=lambda x: x[0])
            recommendations.append(f"Spot instances available from {best_spot[1]} at ${best_spot[0]:.2f}/GPU hour.")

        # Performance-cost ratio recommendations
        ratios = [comp["cost_performance_ratio"] for comp in comparisons]
        best_ratio_idx = np.argmin(ratios)
        best_ratio_comp = comparisons[best_ratio_idx]

        recommendations.append(f"Best cost-performance ratio: {best_ratio_comp['provider']} {best_ratio_comp['instance_type']}")

        return recommendations

    def calculate_savings_potential(self, current_allocation: Dict[str, Any], optimized_allocation: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate potential savings between current and optimized allocations.

        Args:
            current_allocation: Current allocation details
            optimized_allocation: Optimized allocation details

        Returns:
            Dict containing savings metrics
        """
        current_cost = current_allocation.get("total_cost_per_hour", 0)
        optimized_cost = optimized_allocation.get("total_cost_per_hour", 0)

        if current_cost <= 0:
            return {"error": "Invalid current cost"}

        absolute_savings = current_cost - optimized_cost
        percentage_savings = (absolute_savings / current_cost) * 100

        # Calculate annual savings
        annual_savings = absolute_savings * 24 * 365

        return {
            "current_cost_per_hour": current_cost,
            "optimized_cost_per_hour": optimized_cost,
            "absolute_savings_per_hour": absolute_savings,
            "percentage_savings": percentage_savings,
            "annual_savings": annual_savings,
            "roi_multiplier": annual_savings / 1000 if annual_savings > 0 else 0,  # Assuming $1000 setup cost
        }

    def estimate_monthly_cost(self, allocations: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Estimate monthly cost for a set of allocations.

        Args:
            allocations: List of allocation details

        Returns:
            Dict containing monthly cost breakdown
        """
        total_cost = 0.0
        breakdown = {
            "compute": 0.0,
            "storage": 0.0,
            "network": 0.0,
            "data_transfer": 0.0,
        }

        for allocation in allocations:
            cost_per_hour = allocation.get("total_cost_per_hour", 0)
            monthly_cost = cost_per_hour * 24 * 30

            total_cost += monthly_cost

            # Add breakdown if available
            if "breakdown" in allocation:
                for category, cost in allocation["breakdown"].items():
                    if category in breakdown:
                        breakdown[category] += cost * 24 * 30

        return {
            "total_monthly_cost": total_cost,
            "breakdown": breakdown,
            "daily_cost": total_cost / 30,
            "hourly_cost": total_cost / (30 * 24),
        }

    def get_cost_optimization_tips(self, allocation: Dict[str, Any]) -> List[str]:
        """
        Get cost optimization tips for a specific allocation.

        Args:
            allocation: Allocation details

        Returns:
            List of optimization tips
        """
        tips = []

        cost_per_gpu = allocation.get("cost_per_gpu_hour", 0)
        provider = allocation.get("provider", "")
        gpu_type = allocation.get("gpu_type", "")

        # High cost warnings
        if cost_per_gpu > 2.0:
            tips.append("High GPU cost detected. Consider spot instances or different providers.")

        if cost_per_gpu > 1.5:
            tips.append("Consider reserved instances for long-running workloads.")

        # Provider-specific tips
        if provider == "AWS":
            tips.append("AWS offers Spot Fleet for better spot instance management.")
        elif provider == "GCP":
            tips.append("GCP preemptible instances can provide significant savings.")
        elif provider == "Azure":
            tips.append("Azure Spot instances offer up to 90% savings vs on-demand.")

        # GPU-specific tips
        if gpu_type in ["h100", "a100"]:
            tips.append("Premium GPUs are expensive. Consider if your workload requires this performance.")

        # General tips
        tips.append("Monitor utilization to ensure you're not over-provisioning.")
        tips.append("Use auto-scaling to match demand and reduce costs.")

        return tips