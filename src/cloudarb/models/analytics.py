"""
Analytics models for CloudArb platform.
"""

from sqlalchemy import Column, String, Float, Boolean, Integer, ForeignKey, Text, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from .base import Base


class CostSavings(Base):
    """Cost savings analytics model."""

    __tablename__ = "cost_savings"

    # Time period
    date = Column(Date, nullable=False, index=True)
    hour = Column(Integer, nullable=True)  # 0-23 for hourly data

    # Organization and workload context
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    workload_id = Column(Integer, ForeignKey("workloads.id"), nullable=True)
    optimization_run_id = Column(Integer, ForeignKey("optimization_runs.id"), nullable=True)

    # Cost metrics
    original_cost_per_hour = Column(Float, nullable=False)
    optimized_cost_per_hour = Column(Float, nullable=False)
    cost_savings_per_hour = Column(Float, nullable=False)
    cost_savings_percentage = Column(Float, nullable=False)

    # Cumulative metrics
    total_original_cost = Column(Float, nullable=False)
    total_optimized_cost = Column(Float, nullable=False)
    total_cost_savings = Column(Float, nullable=False)

    # Provider breakdown
    provider_breakdown = Column(JSONB, nullable=True)  # Cost breakdown by provider
    instance_type_breakdown = Column(JSONB, nullable=True)  # Cost breakdown by instance type

    # Metadata
    optimization_type = Column(String(50), nullable=True)
    risk_level = Column(String(20), nullable=True)  # low, medium, high

    # Relationships
    organization = relationship("Organization")
    workload = relationship("Workload")
    optimization_run = relationship("OptimizationRun")

    def __repr__(self):
        return f"<CostSavings(id={self.id}, date='{self.date}', savings_percentage={self.cost_savings_percentage:.2f}%)>"

    @property
    def roi_percentage(self) -> float:
        """Calculate return on investment percentage."""
        if self.total_original_cost > 0:
            return (self.total_cost_savings / self.total_original_cost) * 100
        return 0.0


class UtilizationMetrics(Base):
    """GPU and resource utilization metrics."""

    __tablename__ = "utilization_metrics"

    # Time period
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Resource context
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    workload_id = Column(Integer, ForeignKey("workloads.id"), nullable=True)
    allocation_id = Column(Integer, ForeignKey("allocations.id"), nullable=True)

    # GPU utilization
    gpu_utilization_percentage = Column(Float, nullable=False)
    gpu_memory_utilization_percentage = Column(Float, nullable=False)
    gpu_temperature_celsius = Column(Float, nullable=True)
    gpu_power_watts = Column(Float, nullable=True)

    # CPU and memory utilization
    cpu_utilization_percentage = Column(Float, nullable=False)
    memory_utilization_percentage = Column(Float, nullable=False)
    memory_used_gb = Column(Float, nullable=False)
    memory_total_gb = Column(Float, nullable=False)

    # Storage utilization
    storage_utilization_percentage = Column(Float, nullable=True)
    storage_used_gb = Column(Float, nullable=True)
    storage_total_gb = Column(Float, nullable=True)

    # Network utilization
    network_in_mbps = Column(Float, nullable=True)
    network_out_mbps = Column(Float, nullable=True)

    # Performance metrics
    throughput_score = Column(Float, nullable=True)  # 0-1 scale
    latency_ms = Column(Float, nullable=True)

    # Relationships
    organization = relationship("Organization")
    workload = relationship("Workload")
    allocation = relationship("Allocation")

    def __repr__(self):
        return f"<UtilizationMetrics(id={self.id}, timestamp='{self.timestamp}', gpu_util={self.gpu_utilization_percentage:.1f}%)>"

    @property
    def overall_utilization_percentage(self) -> float:
        """Calculate overall resource utilization percentage."""
        metrics = [
            self.gpu_utilization_percentage,
            self.cpu_utilization_percentage,
            self.memory_utilization_percentage,
        ]
        if self.storage_utilization_percentage:
            metrics.append(self.storage_utilization_percentage)

        return sum(metrics) / len(metrics)


class PerformanceMetrics(Base):
    """Performance benchmarking and comparison metrics."""

    __tablename__ = "performance_metrics"

    # Test context
    benchmark_name = Column(String(100), nullable=False, index=True)
    benchmark_version = Column(String(50), nullable=False)
    test_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Resource context
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    workload_id = Column(Integer, ForeignKey("workloads.id"), nullable=True)
    allocation_id = Column(Integer, ForeignKey("allocations.id"), nullable=True)

    # Hardware details
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    instance_type_id = Column(Integer, ForeignKey("instance_types.id"), nullable=False)
    gpu_type = Column(String(50), nullable=False)
    gpu_count = Column(Integer, nullable=False)

    # Performance scores
    overall_score = Column(Float, nullable=False)  # 0-100 scale
    gpu_score = Column(Float, nullable=False)
    cpu_score = Column(Float, nullable=False)
    memory_score = Column(Float, nullable=False)
    storage_score = Column(Float, nullable=True)
    network_score = Column(Float, nullable=True)

    # Benchmark-specific metrics
    benchmark_metrics = Column(JSONB, nullable=False)  # Raw benchmark results
    normalized_metrics = Column(JSONB, nullable=True)  # Normalized scores

    # Comparison data
    baseline_score = Column(Float, nullable=True)  # Comparison baseline
    improvement_percentage = Column(Float, nullable=True)
    percentile_rank = Column(Float, nullable=True)  # Rank among similar instances

    # Relationships
    organization = relationship("Organization")
    workload = relationship("Workload")
    allocation = relationship("Allocation")
    provider = relationship("Provider")
    instance_type = relationship("InstanceType")

    def __repr__(self):
        return f"<PerformanceMetrics(id={self.id}, benchmark='{self.benchmark_name}', score={self.overall_score:.1f})>"

    @property
    def is_above_baseline(self) -> bool:
        """Check if performance is above baseline."""
        return self.baseline_score is not None and self.overall_score > self.baseline_score


class ArbitrageOpportunity(Base):
    """Arbitrage opportunity detection and tracking."""

    __tablename__ = "arbitrage_opportunities"

    # Opportunity identification
    opportunity_id = Column(String(100), unique=True, nullable=False, index=True)
    opportunity_type = Column(String(50), nullable=False)  # price_difference, spot_discount, region_arbitrage
    severity = Column(String(20), nullable=False)  # low, medium, high, critical

    # Resource context
    gpu_type = Column(String(50), nullable=False)
    gpu_count = Column(Integer, nullable=False)
    region = Column(String(100), nullable=False)

    # Provider comparison
    source_provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    target_provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    source_instance_type_id = Column(Integer, ForeignKey("instance_types.id"), nullable=False)
    target_instance_type_id = Column(Integer, ForeignKey("instance_types.id"), nullable=False)

    # Cost analysis
    source_cost_per_hour = Column(Float, nullable=False)
    target_cost_per_hour = Column(Float, nullable=False)
    cost_difference_per_hour = Column(Float, nullable=False)
    cost_savings_percentage = Column(Float, nullable=False)

    # Risk assessment
    risk_score = Column(Float, nullable=False)  # 0-1 scale
    risk_factors = Column(JSONB, nullable=True)
    migration_complexity = Column(String(20), nullable=False)  # low, medium, high

    # Availability and timing
    estimated_availability_hours = Column(Float, nullable=True)
    best_execution_window = Column(JSONB, nullable=True)  # Optimal time to execute
    expiration_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Status tracking
    status = Column(String(20), default="detected", nullable=False)  # detected, analyzed, executed, expired
    executed_at = Column(DateTime(timezone=True), nullable=True)
    executed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    source_provider = relationship("Provider", foreign_keys=[source_provider_id])
    target_provider = relationship("Provider", foreign_keys=[target_provider_id])
    source_instance_type = relationship("InstanceType", foreign_keys=[source_instance_type_id])
    target_instance_type = relationship("InstanceType", foreign_keys=[target_instance_type_id])
    executor = relationship("User")

    def __repr__(self):
        return f"<ArbitrageOpportunity(id={self.id}, type='{self.opportunity_type}', savings={self.cost_savings_percentage:.1f}%)>"

    @property
    def is_active(self) -> bool:
        """Check if opportunity is still active."""
        if self.expiration_timestamp:
            from datetime import datetime
            return datetime.utcnow() < self.expiration_timestamp
        return self.status in ["detected", "analyzed"]

    @property
    def potential_savings_per_day(self) -> float:
        """Calculate potential daily savings."""
        return self.cost_difference_per_hour * 24


class MarketAnalysis(Base):
    """Market analysis and trend tracking."""

    __tablename__ = "market_analysis"

    # Analysis period
    analysis_date = Column(Date, nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)  # daily, weekly, monthly

    # Market metrics
    total_gpu_instances = Column(Integer, nullable=False)
    average_price_per_hour = Column(Float, nullable=False)
    price_volatility = Column(Float, nullable=False)  # Standard deviation of prices
    availability_score = Column(Float, nullable=False)  # 0-1 scale

    # Provider breakdown
    provider_market_share = Column(JSONB, nullable=False)  # Market share by provider
    provider_price_comparison = Column(JSONB, nullable=False)  # Price comparison by provider

    # GPU type analysis
    gpu_type_distribution = Column(JSONB, nullable=False)  # Distribution by GPU type
    gpu_type_pricing = Column(JSONB, nullable=False)  # Pricing by GPU type

    # Regional analysis
    regional_price_variation = Column(JSONB, nullable=False)  # Price variation by region
    regional_availability = Column(JSONB, nullable=False)  # Availability by region

    # Trend analysis
    price_trend = Column(String(20), nullable=False)  # increasing, decreasing, stable
    trend_strength = Column(Float, nullable=False)  # 0-1 scale
    trend_duration_days = Column(Integer, nullable=True)

    # Predictions
    predicted_price_change_percentage = Column(Float, nullable=True)
    prediction_confidence = Column(Float, nullable=True)  # 0-1 scale
    prediction_horizon_days = Column(Integer, nullable=True)

    # Metadata
    data_sources = Column(JSONB, nullable=True)
    analysis_parameters = Column(JSONB, nullable=True)

    def __repr__(self):
        return f"<MarketAnalysis(id={self.id}, date='{self.analysis_date}', avg_price=${self.average_price_per_hour:.2f})>"