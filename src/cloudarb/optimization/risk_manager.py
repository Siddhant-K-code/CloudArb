"""
Risk management component for GPU optimization.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

from .models import InstanceOption, PricingType

logger = logging.getLogger(__name__)


@dataclass
class RiskFactor:
    """Risk factor definition."""

    name: str
    weight: float  # 0-1 scale
    risk_score: float  # 0-1 scale
    description: str


class RiskManager:
    """Risk management and assessment for GPU allocations."""

    def __init__(self):
        """Initialize risk manager."""
        # Risk weights for different factors
        self.risk_weights = {
            "spot_interruption": 0.4,
            "provider_reliability": 0.2,
            "region_availability": 0.15,
            "price_volatility": 0.15,
            "performance_variance": 0.1,
        }

        # Provider reliability scores (based on historical data)
        self.provider_reliability = {
            "AWS": 0.95,
            "GCP": 0.93,
            "Azure": 0.91,
            "Lambda Labs": 0.88,
            "RunPod": 0.85,
        }

        # Region availability scores
        self.region_availability = {
            "us-east-1": 0.98,
            "us-west-2": 0.97,
            "eu-west-1": 0.96,
            "ap-southeast-1": 0.94,
            "us-central1": 0.97,
            "europe-west1": 0.96,
            "asia-east1": 0.94,
        }

    def calculate_instance_risk(self, instance: InstanceOption, pricing_type: PricingType) -> float:
        """
        Calculate risk score for a specific instance and pricing type.

        Args:
            instance: Instance option
            pricing_type: Pricing type (on-demand, spot, etc.)

        Returns:
            float: Risk score (0-1, higher = more risky)
        """
        risk_factors = []

        # Spot instance interruption risk
        if pricing_type == PricingType.SPOT:
            spot_risk = self._calculate_spot_interruption_risk(instance)
            risk_factors.append(RiskFactor(
                name="spot_interruption",
                weight=self.risk_weights["spot_interruption"],
                risk_score=spot_risk,
                description=f"Spot interruption risk: {spot_risk:.2f}"
            ))

        # Provider reliability risk
        provider_risk = self._calculate_provider_reliability_risk(instance)
        risk_factors.append(RiskFactor(
            name="provider_reliability",
            weight=self.risk_weights["provider_reliability"],
            risk_score=provider_risk,
            description=f"Provider reliability risk: {provider_risk:.2f}"
        ))

        # Region availability risk
        region_risk = self._calculate_region_availability_risk(instance)
        risk_factors.append(RiskFactor(
            name="region_availability",
            weight=self.risk_weights["region_availability"],
            risk_score=region_risk,
            description=f"Region availability risk: {region_risk:.2f}"
        ))

        # Price volatility risk
        price_risk = self._calculate_price_volatility_risk(instance, pricing_type)
        risk_factors.append(RiskFactor(
            name="price_volatility",
            weight=self.risk_weights["price_volatility"],
            risk_score=price_risk,
            description=f"Price volatility risk: {price_risk:.2f}"
        ))

        # Performance variance risk
        perf_risk = self._calculate_performance_variance_risk(instance)
        risk_factors.append(RiskFactor(
            name="performance_variance",
            weight=self.risk_weights["performance_variance"],
            risk_score=perf_risk,
            description=f"Performance variance risk: {perf_risk:.2f}"
        ))

        # Calculate weighted average risk score
        total_weight = sum(factor.weight for factor in risk_factors)
        weighted_risk = sum(factor.risk_score * factor.weight for factor in risk_factors)

        if total_weight > 0:
            final_risk = weighted_risk / total_weight
        else:
            final_risk = 0.0

        return min(1.0, max(0.0, final_risk))

    def _calculate_spot_interruption_risk(self, instance: InstanceOption) -> float:
        """Calculate spot instance interruption risk."""
        if not instance.spot_interruption_probability:
            # Estimate based on historical data and availability
            if instance.spot_availability:
                # Lower availability = higher interruption risk
                return 1.0 - instance.spot_availability
            else:
                # Default risk based on GPU type and region
                base_risk = 0.3  # 30% base risk

                # Adjust based on GPU type (newer GPUs may have higher demand)
                gpu_risk_multiplier = {
                    "v100": 0.8,
                    "a100": 1.2,
                    "h100": 1.5,
                    "rtx4090": 0.9,
                    "rtx3090": 0.7,
                }
                multiplier = gpu_risk_multiplier.get(instance.gpu_type, 1.0)

                return min(1.0, base_risk * multiplier)

        return instance.spot_interruption_probability

    def _calculate_provider_reliability_risk(self, instance: InstanceOption) -> float:
        """Calculate provider reliability risk."""
        provider_reliability = self.provider_reliability.get(instance.provider_name, 0.85)
        return 1.0 - provider_reliability

    def _calculate_region_availability_risk(self, instance: InstanceOption) -> float:
        """Calculate region availability risk."""
        region_availability = self.region_availability.get(instance.region, 0.90)
        return 1.0 - region_availability

    def _calculate_price_volatility_risk(self, instance: InstanceOption, pricing_type: PricingType) -> float:
        """Calculate price volatility risk."""
        if pricing_type == PricingType.SPOT:
            # Spot prices are more volatile
            return 0.6
        elif pricing_type == PricingType.ON_DEMAND:
            # On-demand prices are relatively stable
            return 0.1
        elif pricing_type in [PricingType.RESERVED_1Y, PricingType.RESERVED_3Y]:
            # Reserved instances have fixed pricing
            return 0.05
        else:
            return 0.2

    def _calculate_performance_variance_risk(self, instance: InstanceOption) -> float:
        """Calculate performance variance risk."""
        if instance.performance_score:
            # Higher performance scores indicate more consistent performance
            return max(0.0, (100 - instance.performance_score) / 100)
        else:
            # Default risk based on GPU type
            gpu_performance_risk = {
                "v100": 0.2,
                "a100": 0.15,
                "h100": 0.1,
                "rtx4090": 0.25,
                "rtx3090": 0.3,
            }
            return gpu_performance_risk.get(instance.gpu_type, 0.25)

    def assess_portfolio_risk(self, allocations: List[Tuple[InstanceOption, int, PricingType]]) -> Dict[str, float]:
        """
        Assess portfolio-level risk for multiple allocations.

        Args:
            allocations: List of (instance, count, pricing_type) tuples

        Returns:
            Dict containing portfolio risk metrics
        """
        if not allocations:
            return {"total_risk": 0.0, "diversification_score": 0.0}

        # Calculate individual risks
        individual_risks = []
        total_cost = 0.0

        for instance, count, pricing_type in allocations:
            risk = self.calculate_instance_risk(instance, pricing_type)
            cost = instance.get_price(pricing_type) * count if instance.get_price(pricing_type) else 0

            individual_risks.append((risk, cost))
            total_cost += cost

        if total_cost == 0:
            return {"total_risk": 0.0, "diversification_score": 0.0}

        # Calculate weighted average risk
        weighted_risk = sum(risk * cost for risk, cost in individual_risks) / total_cost

        # Calculate diversification score
        diversification_score = self._calculate_diversification_score(allocations)

        # Calculate concentration risk
        concentration_risk = self._calculate_concentration_risk(allocations)

        return {
            "total_risk": weighted_risk,
            "diversification_score": diversification_score,
            "concentration_risk": concentration_risk,
            "individual_risks": individual_risks,
        }

    def _calculate_diversification_score(self, allocations: List[Tuple[InstanceOption, int, PricingType]]) -> float:
        """Calculate diversification score (0-1, higher = more diversified)."""
        if len(allocations) <= 1:
            return 0.0

        # Count unique providers, regions, and GPU types
        providers = set(alloc[0].provider_name for alloc in allocations)
        regions = set(alloc[0].region for alloc in allocations)
        gpu_types = set(alloc[0].gpu_type for alloc in allocations)
        pricing_types = set(alloc[2] for alloc in allocations)

        # Calculate diversity metrics
        provider_diversity = len(providers) / 5.0  # Normalize to max 5 providers
        region_diversity = len(regions) / 10.0  # Normalize to max 10 regions
        gpu_diversity = len(gpu_types) / 5.0  # Normalize to max 5 GPU types
        pricing_diversity = len(pricing_types) / 4.0  # Normalize to max 4 pricing types

        # Weighted average
        diversification = (
            0.3 * provider_diversity +
            0.2 * region_diversity +
            0.2 * gpu_diversity +
            0.3 * pricing_diversity
        )

        return min(1.0, diversification)

    def _calculate_concentration_risk(self, allocations: List[Tuple[InstanceOption, int, PricingType]]) -> float:
        """Calculate concentration risk based on allocation distribution."""
        if not allocations:
            return 0.0

        # Calculate total cost for each allocation
        total_costs = []
        for instance, count, pricing_type in allocations:
            cost = instance.get_price(pricing_type) * count if instance.get_price(pricing_type) else 0
            total_costs.append(cost)

        total_cost = sum(total_costs)
        if total_cost == 0:
            return 0.0

        # Calculate concentration using Herfindahl-Hirschman Index (HHI)
        hhi = sum((cost / total_cost) ** 2 for cost in total_costs)

        # Convert HHI to risk score (0-1)
        # HHI ranges from 1/n (perfect diversification) to 1 (perfect concentration)
        n = len(allocations)
        min_hhi = 1.0 / n if n > 0 else 1.0
        concentration_risk = (hhi - min_hhi) / (1.0 - min_hhi) if n > 1 else 1.0

        return min(1.0, max(0.0, concentration_risk))

    def get_risk_recommendations(self, risk_assessment: Dict[str, float]) -> List[str]:
        """
        Get risk mitigation recommendations based on risk assessment.

        Args:
            risk_assessment: Risk assessment results

        Returns:
            List of recommendation strings
        """
        recommendations = []

        total_risk = risk_assessment.get("total_risk", 0.0)
        diversification_score = risk_assessment.get("diversification_score", 0.0)
        concentration_risk = risk_assessment.get("concentration_risk", 0.0)

        if total_risk > 0.7:
            recommendations.append("High overall risk detected. Consider reducing spot instance usage.")

        if total_risk > 0.5:
            recommendations.append("Moderate risk level. Consider adding on-demand instances for critical workloads.")

        if diversification_score < 0.3:
            recommendations.append("Low diversification. Consider spreading allocations across multiple providers.")

        if concentration_risk > 0.7:
            recommendations.append("High concentration risk. Consider distributing allocations more evenly.")

        if diversification_score < 0.5:
            recommendations.append("Medium diversification. Consider adding more regions or GPU types.")

        return recommendations

    def calculate_risk_adjusted_cost(self, instance: InstanceOption, pricing_type: PricingType,
                                   risk_tolerance: float = 0.5) -> float:
        """
        Calculate risk-adjusted cost for an instance.

        Args:
            instance: Instance option
            pricing_type: Pricing type
            risk_tolerance: Risk tolerance (0-1, higher = more risk tolerant)

        Returns:
            float: Risk-adjusted cost per hour
        """
        base_cost = instance.get_price(pricing_type)
        if base_cost is None:
            return float('inf')

        risk_score = self.calculate_instance_risk(instance, pricing_type)

        # Risk adjustment factor (higher risk = higher adjusted cost)
        risk_adjustment = 1.0 + (risk_score * (1.0 - risk_tolerance))

        return base_cost * risk_adjustment

    def get_risk_metrics(self, allocations: List[Tuple[InstanceOption, int, PricingType]]) -> Dict[str, Any]:
        """
        Get comprehensive risk metrics for a set of allocations.

        Args:
            allocations: List of allocations

        Returns:
            Dict containing detailed risk metrics
        """
        portfolio_risk = self.assess_portfolio_risk(allocations)
        recommendations = self.get_risk_recommendations(portfolio_risk)

        # Calculate additional metrics
        total_instances = sum(count for _, count, _ in allocations)
        spot_instances = sum(count for _, count, pricing_type in allocations
                           if pricing_type == PricingType.SPOT)
        spot_percentage = spot_instances / total_instances if total_instances > 0 else 0.0

        return {
            **portfolio_risk,
            "recommendations": recommendations,
            "total_instances": total_instances,
            "spot_instances": spot_instances,
            "spot_percentage": spot_percentage,
            "risk_level": self._get_risk_level(portfolio_risk["total_risk"]),
        }

    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level."""
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.6:
            return "medium"
        else:
            return "high"