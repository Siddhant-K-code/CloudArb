"""
Workload management models for CloudArb platform.
"""

from sqlalchemy import Column, String, Float, Boolean, Integer, ForeignKey, Text, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from .base import Base


class WorkloadStatus(enum.Enum):
    """Workload status enumeration."""
    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class WorkloadPriority(enum.Enum):
    """Workload priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Workload(Base):
    """Workload model for GPU compute jobs."""

    __tablename__ = "workloads"

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(WorkloadStatus), default=WorkloadStatus.DRAFT, nullable=False, index=True)
    priority = Column(Enum(WorkloadPriority), default=WorkloadPriority.NORMAL, nullable=False)

    # Resource requirements
    min_gpu_count = Column(Integer, nullable=False, default=1)
    max_gpu_count = Column(Integer, nullable=False, default=1)
    gpu_type = Column(String(50), nullable=False)  # v100, a100, h100, etc.
    min_gpu_memory_gb = Column(Float, nullable=False)
    min_cpu_count = Column(Integer, nullable=False, default=4)
    min_memory_gb = Column(Float, nullable=False, default=16.0)
    min_storage_gb = Column(Float, nullable=False, default=100.0)

    # Scheduling constraints
    estimated_duration_hours = Column(Float, nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    preferred_regions = Column(JSONB, nullable=True)  # List of preferred regions
    excluded_regions = Column(JSONB, nullable=True)  # List of excluded regions
    allow_spot_instances = Column(Boolean, default=True)
    allow_preemptible = Column(Boolean, default=True)

    # Budget constraints
    max_cost_per_hour = Column(Float, nullable=True)
    total_budget = Column(Float, nullable=True)
    cost_optimization_target = Column(Float, default=0.3)  # Target 30% cost reduction

    # Execution details
    container_image = Column(String(255), nullable=True)
    command = Column(Text, nullable=True)
    environment_variables = Column(JSONB, nullable=True)
    volume_mounts = Column(JSONB, nullable=True)
    resource_limits = Column(JSONB, nullable=True)

    # Metadata
    tags = Column(JSONB, nullable=True)
    metadata = Column(JSONB, nullable=True)

    # Timestamps
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign keys
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="workloads")
    creator = relationship("User")
    requirements = relationship("WorkloadRequirement", back_populates="workload")
    allocations = relationship("Allocation", back_populates="workload")

    def __repr__(self):
        return f"<Workload(id={self.id}, name='{self.name}', status='{self.status.value}')>"

    @property
    def is_active(self) -> bool:
        """Check if workload is currently active."""
        return self.status in [WorkloadStatus.PENDING, WorkloadStatus.RUNNING]

    @property
    def duration_hours(self) -> float:
        """Calculate actual duration in hours."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() / 3600
        return 0.0


class WorkloadRequirement(Base):
    """Detailed resource requirements for workloads."""

    __tablename__ = "workload_requirements"

    requirement_type = Column(String(50), nullable=False)  # gpu, cpu, memory, storage, network
    min_value = Column(Float, nullable=False)
    max_value = Column(Float, nullable=True)
    preferred_value = Column(Float, nullable=True)
    unit = Column(String(20), nullable=False)  # cores, gb, mbps, etc.
    is_required = Column(Boolean, default=True)
    priority = Column(Integer, default=1)  # Lower number = higher priority

    # Foreign keys
    workload_id = Column(Integer, ForeignKey("workloads.id"), nullable=False)

    # Relationships
    workload = relationship("Workload", back_populates="requirements")

    def __repr__(self):
        return f"<WorkloadRequirement(id={self.id}, type='{self.requirement_type}', min_value={self.min_value})>"


class WorkloadExecution(Base):
    """Execution history for workloads."""

    __tablename__ = "workload_executions"

    execution_id = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(Enum(WorkloadStatus), nullable=False, index=True)

    # Resource allocation
    allocated_gpu_count = Column(Integer, nullable=False)
    allocated_cpu_count = Column(Integer, nullable=False)
    allocated_memory_gb = Column(Float, nullable=False)
    allocated_storage_gb = Column(Float, nullable=False)

    # Provider details
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    instance_type_id = Column(Integer, ForeignKey("instance_types.id"), nullable=False)
    region = Column(String(100), nullable=False)
    zone = Column(String(100), nullable=True)

    # Pricing
    cost_per_hour = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=True)
    pricing_type = Column(String(20), nullable=False)  # on_demand, spot, reserved

    # Performance metrics
    gpu_utilization = Column(Float, nullable=True)
    cpu_utilization = Column(Float, nullable=True)
    memory_utilization = Column(Float, nullable=True)
    network_throughput = Column(Float, nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    error_code = Column(String(100), nullable=True)

    # Foreign keys
    workload_id = Column(Integer, ForeignKey("workloads.id"), nullable=False)

    # Relationships
    workload = relationship("Workload")
    provider = relationship("Provider")
    instance_type = relationship("InstanceType")

    def __repr__(self):
        return f"<WorkloadExecution(id={self.id}, execution_id='{self.execution_id}', status='{self.status.value}')>"

    @property
    def duration_hours(self) -> float:
        """Calculate execution duration in hours."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() / 3600
        return 0.0

    @property
    def estimated_total_cost(self) -> float:
        """Estimate total cost based on duration and hourly rate."""
        return self.duration_hours * self.cost_per_hour