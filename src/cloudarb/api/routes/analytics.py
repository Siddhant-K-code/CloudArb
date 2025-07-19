from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from pydantic import BaseModel
from datetime import datetime, timedelta
import json

from ..database import get_db
from ..models.user import User
from ..models.workload import Workload
from ..models.pricing import PricingData, Provider, InstanceType
from ..models.optimization import OptimizationRun, Allocation
from ..models.analytics import ArbitrageOpportunity
from ..api.routes.auth import get_current_active_user
from ..optimization.cost_calculator import CostCalculator
from ..optimization.performance_analyzer import PerformanceAnalyzer

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Pydantic models
class CostAnalysisResponse(BaseModel):
    total_cost: float
    cost_breakdown: Dict[str, float]
    cost_trend: List[Dict[str, Any]]
    savings_opportunities: List[Dict[str, Any]]
    recommendations: List[str]

class PerformanceMetricsResponse(BaseModel):
    average_performance_score: float
    performance_by_provider: Dict[str, float]
    performance_by_instance_type: Dict[str, float]
    bottlenecks: List[str]
    optimization_suggestions: List[str]

class ArbitrageOpportunityResponse(BaseModel):
    id: int
    provider_from: str
    provider_to: str
    instance_type: str
    region: str
    cost_savings_percent: float
    cost_savings_amount: float
    risk_score: float
    confidence_score: float
    created_at: datetime

    class Config:
        from_attributes = True

class MarketAnalysisResponse(BaseModel):
    provider_prices: Dict[str, Dict[str, float]]
    price_volatility: Dict[str, float]
    demand_trends: Dict[str, str]
    spot_vs_on_demand: Dict[str, Dict[str, float]]

@router.get("/cost-analysis")
async def get_cost_analysis(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    provider: Optional[str] = Query(None),
    instance_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive cost analysis for the user's workloads"""

    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Get user's workloads and allocations
    query = db.query(Allocation).join(Workload).filter(
        Workload.user_id == current_user.id,
        Allocation.created_at >= start_date,
        Allocation.created_at <= end_date
    )

    if provider:
        query = query.filter(Allocation.provider == provider)
    if instance_type:
        query = query.filter(Allocation.instance_type == instance_type)

    allocations = query.all()

    if not allocations:
        return CostAnalysisResponse(
            total_cost=0.0,
            cost_breakdown={},
            cost_trend=[],
            savings_opportunities=[],
            recommendations=["No cost data available for the specified period"]
        )

    # Calculate total cost
    total_cost = sum(alloc.total_cost for alloc in allocations)

    # Cost breakdown by provider
    cost_breakdown = {}
    for alloc in allocations:
        provider = alloc.provider
        if provider not in cost_breakdown:
            cost_breakdown[provider] = 0.0
        cost_breakdown[provider] += alloc.total_cost

    # Cost trend over time
    cost_trend = []
    current_date = start_date
    while current_date <= end_date:
        daily_cost = sum(
            alloc.total_cost for alloc in allocations
            if alloc.created_at.date() == current_date.date()
        )
        cost_trend.append({
            "date": current_date.isoformat(),
            "cost": daily_cost
        })
        current_date += timedelta(days=1)

    # Find savings opportunities
    savings_opportunities = []
    cost_calculator = CostCalculator()

    for alloc in allocations:
        # Compare with other providers
        alternative_costs = cost_calculator.get_alternative_costs(
            alloc.instance_type, alloc.gpu_count, alloc.duration_hours
        )

        for alt_provider, alt_cost in alternative_costs.items():
            if alt_provider != alloc.provider and alt_cost < alloc.total_cost:
                savings = alloc.total_cost - alt_cost
                savings_opportunities.append({
                    "allocation_id": alloc.id,
                    "current_provider": alloc.provider,
                    "alternative_provider": alt_provider,
                    "potential_savings": savings,
                    "savings_percent": (savings / alloc.total_cost) * 100
                })

    # Sort by potential savings
    savings_opportunities.sort(key=lambda x: x["potential_savings"], reverse=True)

    # Generate recommendations
    recommendations = []
    if savings_opportunities:
        recommendations.append(
            f"Consider switching to {savings_opportunities[0]['alternative_provider']} "
            f"for potential savings of ${savings_opportunities[0]['potential_savings']:.2f}"
        )

    if total_cost > 1000:  # High cost threshold
        recommendations.append("Consider using spot instances for non-critical workloads")

    return CostAnalysisResponse(
        total_cost=total_cost,
        cost_breakdown=cost_breakdown,
        cost_trend=cost_trend,
        savings_opportunities=savings_opportunities[:5],  # Top 5
        recommendations=recommendations
    )

@router.get("/performance-metrics")
async def get_performance_metrics(
    workload_type: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get performance metrics and analysis"""

    # Get user's workloads
    query = db.query(Workload).filter(Workload.user_id == current_user.id)

    if workload_type:
        query = query.filter(Workload.workload_type == workload_type)

    workloads = query.all()

    if not workloads:
        return PerformanceMetricsResponse(
            average_performance_score=0.0,
            performance_by_provider={},
            performance_by_instance_type={},
            bottlenecks=[],
            optimization_suggestions=["No workload data available"]
        )

    # Analyze performance
    performance_analyzer = PerformanceAnalyzer()

    # Calculate performance scores
    performance_scores = []
    performance_by_provider = {}
    performance_by_instance_type = {}

    for workload in workloads:
        # Get allocations for this workload
        allocations = db.query(Allocation).filter(
            Allocation.workload_id == workload.id
        ).all()

        for alloc in allocations:
            score = performance_analyzer.calculate_performance_score(
                alloc.instance_type, workload.workload_type
            )
            performance_scores.append(score)

            # Aggregate by provider
            if alloc.provider not in performance_by_provider:
                performance_by_provider[alloc.provider] = []
            performance_by_provider[alloc.provider].append(score)

            # Aggregate by instance type
            if alloc.instance_type not in performance_by_instance_type:
                performance_by_instance_type[alloc.instance_type] = []
            performance_by_instance_type[alloc.instance_type].append(score)

    # Calculate averages
    average_performance_score = sum(performance_scores) / len(performance_scores) if performance_scores else 0.0

    for provider in performance_by_provider:
        performance_by_provider[provider] = sum(performance_by_provider[provider]) / len(performance_by_provider[provider])

    for instance_type in performance_by_instance_type:
        performance_by_instance_type[instance_type] = sum(performance_by_instance_type[instance_type]) / len(performance_by_instance_type[instance_type])

    # Identify bottlenecks
    bottlenecks = []
    if average_performance_score < 0.7:
        bottlenecks.append("Overall performance is below optimal levels")

    low_performance_providers = [
        provider for provider, score in performance_by_provider.items()
        if score < 0.6
    ]
    if low_performance_providers:
        bottlenecks.append(f"Low performance on providers: {', '.join(low_performance_providers)}")

    # Generate optimization suggestions
    optimization_suggestions = []
    if average_performance_score < 0.8:
        optimization_suggestions.append("Consider upgrading to higher-performance instance types")

    if len(performance_by_provider) > 1:
        best_provider = max(performance_by_provider.items(), key=lambda x: x[1])[0]
        optimization_suggestions.append(f"Consider migrating workloads to {best_provider} for better performance")

    return PerformanceMetricsResponse(
        average_performance_score=average_performance_score,
        performance_by_provider=performance_by_provider,
        performance_by_instance_type=performance_by_instance_type,
        bottlenecks=bottlenecks,
        optimization_suggestions=optimization_suggestions
    )

@router.get("/arbitrage-opportunities", response_model=List[ArbitrageOpportunityResponse])
async def get_arbitrage_opportunities(
    min_savings_percent: float = Query(10.0, description="Minimum savings percentage"),
    max_risk_score: float = Query(0.5, description="Maximum risk score"),
    provider: Optional[str] = Query(None),
    instance_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current arbitrage opportunities"""

    query = db.query(ArbitrageOpportunity).filter(
        ArbitrageOpportunity.cost_savings_percent >= min_savings_percent,
        ArbitrageOpportunity.risk_score <= max_risk_score
    )

    if provider:
        query = query.filter(
            (ArbitrageOpportunity.provider_from == provider) |
            (ArbitrageOpportunity.provider_to == provider)
        )

    if instance_type:
        query = query.filter(ArbitrageOpportunity.instance_type == instance_type)

    opportunities = query.order_by(desc(ArbitrageOpportunity.cost_savings_percent)).limit(20).all()

    return opportunities

@router.get("/market-analysis", response_model=MarketAnalysisResponse)
async def get_market_analysis(
    instance_type: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current market analysis and pricing trends"""

    # Get latest pricing data
    query = db.query(PricingData).join(InstanceType).join(Provider)

    if instance_type:
        query = query.filter(InstanceType.name == instance_type)
    if region:
        query = query.filter(PricingData.region == region)

    # Get latest prices for each provider/instance combination
    latest_prices = query.order_by(
        PricingData.provider_id,
        PricingData.instance_type_id,
        desc(PricingData.timestamp)
    ).all()

    # Group by provider
    provider_prices = {}
    price_volatility = {}
    spot_vs_on_demand = {}

    for price_data in latest_prices:
        provider_name = price_data.provider.name
        instance_name = price_data.instance_type.name

        if provider_name not in provider_prices:
            provider_prices[provider_name] = {}
            spot_vs_on_demand[provider_name] = {}

        provider_prices[provider_name][instance_name] = price_data.price_per_hour

        # Calculate spot vs on-demand ratio
        if price_data.spot_price:
            spot_vs_on_demand[provider_name][instance_name] = {
                "spot_price": price_data.spot_price,
                "on_demand_price": price_data.price_per_hour,
                "spot_discount": ((price_data.price_per_hour - price_data.spot_price) / price_data.price_per_hour) * 100
            }

    # Calculate price volatility (simplified)
    for provider_name in provider_prices:
        prices = list(provider_prices[provider_name].values())
        if len(prices) > 1:
            mean_price = sum(prices) / len(prices)
            variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
            price_volatility[provider_name] = (variance ** 0.5) / mean_price
        else:
            price_volatility[provider_name] = 0.0

    # Determine demand trends (simplified)
    demand_trends = {}
    for provider_name in provider_prices:
        # This would typically use historical data and ML models
        # For now, use a simple heuristic based on price volatility
        volatility = price_volatility.get(provider_name, 0.0)
        if volatility > 0.1:
            demand_trends[provider_name] = "high"
        elif volatility > 0.05:
            demand_trends[provider_name] = "medium"
        else:
            demand_trends[provider_name] = "low"

    return MarketAnalysisResponse(
        provider_prices=provider_prices,
        price_volatility=price_volatility,
        demand_trends=demand_trends,
        spot_vs_on_demand=spot_vs_on_demand
    )

@router.get("/optimization-history")
async def get_optimization_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's optimization history"""

    optimizations = db.query(OptimizationRun).filter(
        OptimizationRun.user_id == current_user.id
    ).order_by(desc(OptimizationRun.created_at)).offset(skip).limit(limit).all()

    return [
        {
            "id": opt.id,
            "optimization_type": opt.optimization_type,
            "status": opt.status,
            "total_cost": opt.total_cost,
            "total_savings": opt.total_savings,
            "created_at": opt.created_at,
            "workload_count": len(opt.workloads) if opt.workloads else 0
        }
        for opt in optimizations
    ]

@router.get("/savings-summary")
async def get_savings_summary(
    period_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get summary of cost savings achieved"""

    start_date = datetime.utcnow() - timedelta(days=period_days)

    # Get optimizations in the period
    optimizations = db.query(OptimizationRun).filter(
        OptimizationRun.user_id == current_user.id,
        OptimizationRun.created_at >= start_date
    ).all()

    total_savings = sum(opt.total_savings for opt in optimizations)
    total_cost = sum(opt.total_cost for opt in optimizations)
    savings_percentage = (total_savings / total_cost * 100) if total_cost > 0 else 0

    # Get allocations in the period
    allocations = db.query(Allocation).join(Workload).filter(
        Workload.user_id == current_user.id,
        Allocation.created_at >= start_date
    ).all()

    actual_cost = sum(alloc.total_cost for alloc in allocations)

    return {
        "period_days": period_days,
        "total_optimizations": len(optimizations),
        "total_savings": total_savings,
        "total_cost": total_cost,
        "actual_cost": actual_cost,
        "savings_percentage": savings_percentage,
        "average_savings_per_optimization": total_savings / len(optimizations) if optimizations else 0
    }