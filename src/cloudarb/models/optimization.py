"""
Optimization models for CloudArb platform.
"""

from sqlalchemy import Column, String, Float, Boolean, Integer, ForeignKey, Text, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from .base import Base


class OptimizationStatus(enum.Enum):
    """Optimization status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OptimizationType(enum.Enum):
    """Optimization type enumeration."""
    COST_MINIMIZATION = "cost_minimization"
    PERFORMANCE_MAXIMIZATION = "performance_maximization"
    BALANCED = "balanced"
    CUSTOM = "custom"


class OptimizationRun(Base):
    """Optimization run model for tracking optimization executions."""

    __tablename__ = "optimization_runs"

    run_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(OptimizationStatus), default=OptimizationStatus.PENDING, nullable=False, index=True)
    optimization_type = Column(Enum(OptimizationType), nullable=False)

    # Input parameters
    workloads = Column(JSONB, nullable=False)  # List of workload IDs
    constraints = Column(JSONB, nullable=True)  # Optimization constraints
    objectives = Column(JSONB, nullable=False)  # Optimization objectives
    risk_tolerance = Column(Float, default=0.1, nullable=False)

    # Solver configuration
    solver_name = Column(String(50), nullable=False, default="ortools")
    solver_parameters = Column(JSONB, nullable=True)
    timeout_seconds = Column(Integer, default=30, nullable=False)
    max_iterations = Column(Integer, default=10000, nullable=False)

    # Results
    objective_value = Column(Float, nullable=True)
    solve_time_seconds = Column(Float, nullable=True)
    iteration_count = Column(Integer, nullable=True)
    solution_quality = Column(Float, nullable=True)  # 0-1 scale
    confidence_score = Column(Float, nullable=True)  # 0-1 scale

    # Cost analysis
    total_cost_per_hour = Column(Float, nullable=True)
    cost_savings_percentage = Column(Float, nullable=True)
    cost_savings_amount = Column(Float, nullable=True)

    # Performance analysis
    total_performance_score = Column(Float, nullable=True)
    performance_improvement_percentage = Column(Float, nullable=True)

    # Risk analysis
    risk_score = Column(Float, nullable=True)
    risk_factors = Column(JSONB, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    error_code = Column(String(100), nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign keys
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    organization = relationship("Organization")
    creator = relationship("User")
    results = relationship("OptimizationResult", back_populates="optimization_run")
    allocations = relationship("Allocation", back_populates="optimization_run")

    def __repr__(self):
        return f"<OptimizationRun(id={self.id}, run_id='{self.run_id}', status='{self.status.value}')>"

    @property
    def duration_seconds(self) -> float:
        """Calculate optimization duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def is_successful(self) -> bool:
        """Check if optimization was successful."""
        return self.status == OptimizationStatus.COMPLETED and self.objective_value is not None


class OptimizationResult(Base):
    """Detailed optimization result model."""

    __tablename__ = "optimization_results"

    result_type = Column(String(50), nullable=False)  # allocation, cost, performance, risk
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)  # dollars, percentage, score, etc.
    confidence_interval_lower = Column(Float, nullable=True)
    confidence_interval_upper = Column(Float, nullable=True)
    meta_data = Column(JSONB, nullable=True)  # Additional result details

    # Foreign keys
    optimization_run_id = Column(Integer, ForeignKey("optimization_runs.id"), nullable=False)

    # Relationships
    optimization_run = relationship("OptimizationRun", back_populates="results")

    def __repr__(self):
        return f"<OptimizationResult(id={self.id}, type='{self.result_type}', value={self.value})>"


class Allocation(Base):
    """Resource allocation model for optimization results."""

    __tablename__ = "allocations"

    allocation_id = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(20), default="proposed", nullable=False, index=True)  # proposed, approved, deployed, cancelled

    # Resource allocation
    gpu_count = Column(Integer, nullable=False)
    cpu_count = Column(Integer, nullable=False)
    memory_gb = Column(Float, nullable=False)
    storage_gb = Column(Float, nullable=False)

    # Provider details
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    instance_type_id = Column(Integer, ForeignKey("instance_types.id"), nullable=False)
    region = Column(String(100), nullable=False)
    zone = Column(String(100), nullable=True)

    # Pricing
    cost_per_hour = Column(Float, nullable=False)
    pricing_type = Column(String(20), nullable=False)  # on_demand, spot, reserved
    spot_interruption_probability = Column(Float, nullable=True)

    # Performance
    expected_performance_score = Column(Float, nullable=True)
    performance_benchmarks = Column(JSONB, nullable=True)

    # Risk assessment
    risk_score = Column(Float, nullable=True)
    risk_factors = Column(JSONB, nullable=True)

    # Deployment
    deployment_config = Column(JSONB, nullable=True)
    terraform_config = Column(JSONB, nullable=True)
    kubernetes_config = Column(JSONB, nullable=True)

    # Timestamps
    proposed_at = Column(DateTime(timezone=True), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign keys
    optimization_run_id = Column(Integer, ForeignKey("optimization_runs.id"), nullable=False)
    workload_id = Column(Integer, ForeignKey("workloads.id"), nullable=False)

    # Relationships
    optimization_run = relationship("OptimizationRun", back_populates="allocations")
    workload = relationship("Workload", back_populates="allocations")
    provider = relationship("Provider")
    instance_type = relationship("InstanceType")

    def __repr__(self):
        return f"<Allocation(id={self.id}, allocation_id='{self.allocation_id}', status='{self.status}')>"

    @property
    def total_cost_per_hour(self) -> float:
        """Calculate total cost per hour for this allocation."""
        return self.cost_per_hour * self.gpu_count

    @property
    def is_deployed(self) -> bool:
        """Check if allocation has been deployed."""
        return self.status == "deployed" and self.deployed_at is not None

    @property
    def can_deploy(self) -> bool:
        """Check if allocation can be deployed."""
        return self.status in ["proposed", "approved"] and self.deployment_config is not None


class OptimizationConstraint(Base):
    """Constraint model for optimization problems."""

    __tablename__ = "optimization_constraints"

    constraint_type = Column(String(50), nullable=False)  # budget, performance, availability, risk
    constraint_name = Column(String(100), nullable=False)
    constraint_value = Column(Float, nullable=False)
    constraint_operator = Column(String(10), nullable=False)  # <=, >=, ==, !=
    weight = Column(Float, default=1.0, nullable=False)  # Constraint weight in multi-objective optimization
    is_hard_constraint = Column(Boolean, default=True, nullable=False)

    # Foreign keys
    optimization_run_id = Column(Integer, ForeignKey("optimization_runs.id"), nullable=False)

    # Relationships
    optimization_run = relationship("OptimizationRun")

    def __repr__(self):
        return f"<OptimizationConstraint(id={self.id}, type='{self.constraint_type}', name='{self.constraint_name}')>"