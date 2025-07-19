"""
Optimization models and problem definitions for CloudArb platform.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from pydantic import BaseModel, Field, validator


class OptimizationObjective(Enum):
    """Optimization objectives."""
    MINIMIZE_COST = "minimize_cost"
    MAXIMIZE_PERFORMANCE = "maximize_performance"
    BALANCE_COST_PERFORMANCE = "balance_cost_performance"
    MINIMIZE_RISK = "minimize_risk"
    MAXIMIZE_AVAILABILITY = "maximize_availability"


class PricingType(Enum):
    """Pricing types for GPU instances."""
    ON_DEMAND = "on_demand"
    SPOT = "spot"
    RESERVED_1Y = "reserved_1y"
    RESERVED_3Y = "reserved_3y"


@dataclass
class GPURequirement:
    """GPU requirement specification."""

    gpu_type: str  # v100, a100, h100, etc.
    min_count: int
    max_count: int
    min_memory_gb: float
    priority: int = 1  # Lower number = higher priority

    def __post_init__(self):
        if self.min_count > self.max_count:
            raise ValueError("min_count cannot be greater than max_count")
        if self.min_count < 0:
            raise ValueError("min_count cannot be negative")


@dataclass
class ResourceRequirement:
    """Resource requirement specification."""

    cpu_cores: int
    memory_gb: float
    storage_gb: float
    network_bandwidth_gbps: Optional[float] = None
    gpu_requirements: List[GPURequirement] = field(default_factory=list)

    def __post_init__(self):
        if self.cpu_cores < 1:
            raise ValueError("cpu_cores must be at least 1")
        if self.memory_gb < 1:
            raise ValueError("memory_gb must be at least 1")
        if self.storage_gb < 1:
            raise ValueError("storage_gb must be at least 1")


@dataclass
class InstanceOption:
    """Available instance option for optimization."""

    provider_id: int
    instance_type_id: int
    provider_name: str
    instance_name: str
    region: str
    zone: Optional[str] = None

    # Resource specifications
    cpu_cores: int
    memory_gb: float
    gpu_count: int
    gpu_type: str
    gpu_memory_gb: float
    storage_gb: float
    network_bandwidth_gbps: Optional[float] = None

    # Pricing information
    on_demand_price_per_hour: float
    spot_price_per_hour: Optional[float] = None
    reserved_1y_price_per_hour: Optional[float] = None
    reserved_3y_price_per_hour: Optional[float] = None

    # Availability and risk
    spot_availability: Optional[float] = None  # 0-1 scale
    on_demand_availability: Optional[float] = None  # 0-1 scale
    spot_interruption_probability: Optional[float] = None

    # Performance metrics
    performance_score: Optional[float] = None  # 0-100 scale
    latency_ms: Optional[float] = None

    def get_price(self, pricing_type: PricingType) -> Optional[float]:
        """Get price for specific pricing type."""
        price_map = {
            PricingType.ON_DEMAND: self.on_demand_price_per_hour,
            PricingType.SPOT: self.spot_price_per_hour,
            PricingType.RESERVED_1Y: self.reserved_1y_price_per_hour,
            PricingType.RESERVED_3Y: self.reserved_3y_price_per_hour,
        }
        return price_map.get(pricing_type)

    def get_availability(self, pricing_type: PricingType) -> Optional[float]:
        """Get availability for specific pricing type."""
        if pricing_type == PricingType.SPOT:
            return self.spot_availability
        elif pricing_type == PricingType.ON_DEMAND:
            return self.on_demand_availability
        return 1.0  # Reserved instances are always available

    @property
    def total_gpu_memory_gb(self) -> float:
        """Get total GPU memory across all GPUs."""
        return self.gpu_count * self.gpu_memory_gb


@dataclass
class OptimizationConstraint:
    """Optimization constraint definition."""

    name: str
    constraint_type: str  # budget, performance, availability, risk
    operator: str  # <=, >=, ==, !=
    value: float
    weight: float = 1.0
    is_hard_constraint: bool = True
    description: Optional[str] = None

    def __post_init__(self):
        if self.operator not in ["<=", ">=", "==", "!="]:
            raise ValueError("Invalid operator. Must be one of: <=, >=, ==, !=")
        if self.weight < 0:
            raise ValueError("Weight cannot be negative")


@dataclass
class OptimizationProblem:
    """Complete optimization problem definition."""

    problem_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "GPU Optimization Problem"
    description: Optional[str] = None

    # Workload requirements
    workloads: List[Dict[str, Any]] = field(default_factory=list)
    resource_requirements: List[ResourceRequirement] = field(default_factory=list)

    # Available options
    instance_options: List[InstanceOption] = field(default_factory=list)

    # Optimization configuration
    objective: OptimizationObjective = OptimizationObjective.MINIMIZE_COST
    constraints: List[OptimizationConstraint] = field(default_factory=list)
    risk_tolerance: float = 0.1  # 0-1 scale
    time_horizon_hours: float = 24.0

    # Solver configuration
    solver_name: str = "ortools"
    solver_parameters: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    max_iterations: int = 10000

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    organization_id: Optional[int] = None
    created_by: Optional[int] = None

    def __post_init__(self):
        if self.risk_tolerance < 0 or self.risk_tolerance > 1:
            raise ValueError("risk_tolerance must be between 0 and 1")
        if self.time_horizon_hours <= 0:
            raise ValueError("time_horizon_hours must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    def add_constraint(self, constraint: OptimizationConstraint) -> None:
        """Add constraint to the problem."""
        self.constraints.append(constraint)

    def add_instance_option(self, option: InstanceOption) -> None:
        """Add instance option to the problem."""
        self.instance_options.append(option)

    def get_total_resource_requirements(self) -> ResourceRequirement:
        """Get aggregated resource requirements across all workloads."""
        total_cpu = sum(req.cpu_cores for req in self.resource_requirements)
        total_memory = sum(req.memory_gb for req in self.resource_requirements)
        total_storage = sum(req.storage_gb for req in self.resource_requirements)

        # Aggregate GPU requirements
        gpu_requirements = {}
        for req in self.resource_requirements:
            for gpu_req in req.gpu_requirements:
                if gpu_req.gpu_type not in gpu_requirements:
                    gpu_requirements[gpu_req.gpu_type] = GPURequirement(
                        gpu_type=gpu_req.gpu_type,
                        min_count=0,
                        max_count=0,
                        min_memory_gb=0
                    )

                gpu_requirements[gpu_req.gpu_type].min_count += gpu_req.min_count
                gpu_requirements[gpu_req.gpu_type].max_count += gpu_req.max_count
                gpu_requirements[gpu_req.gpu_type].min_memory_gb = max(
                    gpu_requirements[gpu_req.gpu_type].min_memory_gb,
                    gpu_req.min_memory_gb
                )

        return ResourceRequirement(
            cpu_cores=total_cpu,
            memory_gb=total_memory,
            storage_gb=total_storage,
            gpu_requirements=list(gpu_requirements.values())
        )


@dataclass
class AllocationDecision:
    """Individual allocation decision."""

    workload_id: Optional[int]
    instance_option: InstanceOption
    instance_count: int
    pricing_type: PricingType
    cost_per_hour: float
    performance_score: Optional[float] = None
    risk_score: Optional[float] = None

    def __post_init__(self):
        if self.instance_count < 0:
            raise ValueError("instance_count cannot be negative")
        if self.cost_per_hour < 0:
            raise ValueError("cost_per_hour cannot be negative")

    @property
    def total_cost_per_hour(self) -> float:
        """Get total cost per hour for this allocation."""
        return self.cost_per_hour * self.instance_count

    @property
    def total_gpu_count(self) -> int:
        """Get total GPU count for this allocation."""
        return self.instance_option.gpu_count * self.instance_count


@dataclass
class OptimizationResult:
    """Complete optimization result."""

    problem_id: str
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Solution status
    status: str = "pending"  # pending, running, completed, failed
    is_optimal: bool = False
    solve_time_seconds: Optional[float] = None
    iteration_count: Optional[int] = None

    # Solution quality
    objective_value: Optional[float] = None
    solution_quality: Optional[float] = None  # 0-1 scale
    confidence_score: Optional[float] = None  # 0-1 scale

    # Allocation decisions
    allocations: List[AllocationDecision] = field(default_factory=list)

    # Cost analysis
    total_cost_per_hour: Optional[float] = None
    cost_breakdown: Dict[str, float] = field(default_factory=dict)
    cost_savings_percentage: Optional[float] = None
    cost_savings_amount: Optional[float] = None

    # Performance analysis
    total_performance_score: Optional[float] = None
    performance_breakdown: Dict[str, float] = field(default_factory=dict)

    # Risk analysis
    total_risk_score: Optional[float] = None
    risk_factors: Dict[str, float] = field(default_factory=dict)

    # Error information
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.solve_time_seconds is not None and self.solve_time_seconds < 0:
            raise ValueError("solve_time_seconds cannot be negative")

    @property
    def total_instances(self) -> int:
        """Get total number of instances allocated."""
        return sum(alloc.instance_count for alloc in self.allocations)

    @property
    def total_gpus(self) -> int:
        """Get total number of GPUs allocated."""
        return sum(alloc.total_gpu_count for alloc in self.allocations)

    @property
    def provider_breakdown(self) -> Dict[str, int]:
        """Get breakdown of instances by provider."""
        breakdown = {}
        for alloc in self.allocations:
            provider = alloc.instance_option.provider_name
            breakdown[provider] = breakdown.get(provider, 0) + alloc.instance_count
        return breakdown

    def get_cost_by_provider(self) -> Dict[str, float]:
        """Get cost breakdown by provider."""
        breakdown = {}
        for alloc in self.allocations:
            provider = alloc.instance_option.provider_name
            breakdown[provider] = breakdown.get(provider, 0) + alloc.total_cost_per_hour
        return breakdown

    def get_cost_by_gpu_type(self) -> Dict[str, float]:
        """Get cost breakdown by GPU type."""
        breakdown = {}
        for alloc in self.allocations:
            gpu_type = alloc.instance_option.gpu_type
            breakdown[gpu_type] = breakdown.get(gpu_type, 0) + alloc.total_cost_per_hour
        return breakdown


# Pydantic models for API serialization
class OptimizationRequest(BaseModel):
    """API request model for optimization."""

    name: str = Field(..., description="Optimization name")
    description: Optional[str] = Field(None, description="Optimization description")
    workloads: List[Dict[str, Any]] = Field(..., description="List of workload definitions")
    objective: OptimizationObjective = Field(OptimizationObjective.MINIMIZE_COST, description="Optimization objective")
    constraints: List[Dict[str, Any]] = Field(default_factory=list, description="Optimization constraints")
    risk_tolerance: float = Field(0.1, ge=0, le=1, description="Risk tolerance (0-1)")
    time_horizon_hours: float = Field(24.0, gt=0, description="Time horizon for optimization")
    timeout_seconds: int = Field(30, gt=0, description="Solver timeout in seconds")

    class Config:
        use_enum_values = True


class OptimizationResponse(BaseModel):
    """API response model for optimization results."""

    result_id: str
    status: str
    objective_value: Optional[float] = None
    total_cost_per_hour: Optional[float] = None
    cost_savings_percentage: Optional[float] = None
    total_performance_score: Optional[float] = None
    total_risk_score: Optional[float] = None
    solve_time_seconds: Optional[float] = None
    allocations: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "result_id": "opt_123456",
                "status": "completed",
                "objective_value": 45.67,
                "total_cost_per_hour": 12.34,
                "cost_savings_percentage": 35.2,
                "total_performance_score": 85.5,
                "total_risk_score": 0.15,
                "solve_time_seconds": 2.34,
                "allocations": [
                    {
                        "provider": "AWS",
                        "instance_type": "g4dn.xlarge",
                        "count": 2,
                        "cost_per_hour": 6.17,
                        "gpu_count": 2
                    }
                ]
            }
        }