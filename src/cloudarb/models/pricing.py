"""
Pricing data models for CloudArb platform.
"""

from sqlalchemy import Column, String, Float, Boolean, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from .base import Base


class Provider(Base):
    """Cloud provider model."""

    __tablename__ = "providers"

    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)  # aws, gcp, azure, lambda, runpod
    display_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    api_endpoint = Column(String(255), nullable=True)
    credentials = Column(JSONB, nullable=True)  # Encrypted credentials
    rate_limits = Column(JSONB, nullable=True)  # API rate limits
    regions = Column(JSONB, nullable=True)  # Available regions

    # Relationships
    instance_types = relationship("InstanceType", back_populates="provider")
    pricing_data = relationship("PricingData", back_populates="provider")

    def __repr__(self):
        return f"<Provider(id={self.id}, name='{self.name}')>"


class InstanceType(Base):
    """GPU instance type model."""

    __tablename__ = "instance_types"

    name = Column(String(100), nullable=False, index=True)
    provider_instance_id = Column(String(100), nullable=False)  # Provider-specific ID
    cpu_count = Column(Integer, nullable=False)
    memory_gb = Column(Float, nullable=False)
    gpu_count = Column(Integer, nullable=False)
    gpu_type = Column(String(50), nullable=False)  # v100, a100, h100, etc.
    gpu_memory_gb = Column(Float, nullable=False)
    network_bandwidth_gbps = Column(Float, nullable=True)
    storage_gb = Column(Float, nullable=True)
    is_spot_available = Column(Boolean, default=False)
    is_preemptible = Column(Boolean, default=False)
    architecture = Column(String(50), nullable=True)  # x86_64, arm64
    virtualization_type = Column(String(50), nullable=True)  # hvm, pv

    # Foreign keys
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)

    # Relationships
    provider = relationship("Provider", back_populates="instance_types")
    pricing_data = relationship("PricingData", back_populates="instance_type")

    def __repr__(self):
        return f"<InstanceType(id={self.id}, name='{self.name}', gpu_type='{self.gpu_type}')>"

    @property
    def total_gpu_memory_gb(self) -> float:
        """Get total GPU memory across all GPUs."""
        return self.gpu_count * self.gpu_memory_gb


class PricingData(Base):
    """Real-time pricing data model with TimescaleDB hypertable support."""

    __tablename__ = "pricing_data"

    # Time-series fields
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    region = Column(String(100), nullable=False, index=True)
    zone = Column(String(100), nullable=True, index=True)

    # Pricing fields
    on_demand_price_per_hour = Column(Float, nullable=False)
    spot_price_per_hour = Column(Float, nullable=True)
    reserved_1y_price_per_hour = Column(Float, nullable=True)
    reserved_3y_price_per_hour = Column(Float, nullable=True)

    # Availability fields
    spot_availability = Column(Float, nullable=True)  # 0-1 scale
    on_demand_availability = Column(Float, nullable=True)  # 0-1 scale
    capacity_status = Column(String(50), nullable=True)  # available, limited, unavailable

    # Metadata
    data_source = Column(String(50), nullable=False)  # api, scraping, manual
    confidence_score = Column(Float, nullable=True)  # 0-1 scale for data quality
    metadata = Column(JSONB, nullable=True)  # Additional provider-specific data

    # Foreign keys
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    instance_type_id = Column(Integer, ForeignKey("instance_types.id"), nullable=False)

    # Relationships
    provider = relationship("Provider", back_populates="pricing_data")
    instance_type = relationship("InstanceType", back_populates="pricing_data")

    def __repr__(self):
        return f"<PricingData(id={self.id}, provider_id={self.provider_id}, instance_type_id={self.instance_type_id})>"

    @property
    def best_price_per_hour(self) -> float:
        """Get the best available price per hour."""
        prices = [
            self.on_demand_price_per_hour,
            self.spot_price_per_hour,
            self.reserved_1y_price_per_hour,
            self.reserved_3y_price_per_hour,
        ]
        valid_prices = [p for p in prices if p is not None]
        return min(valid_prices) if valid_prices else self.on_demand_price_per_hour

    @property
    def price_discount_vs_ondemand(self) -> float:
        """Get discount percentage vs on-demand pricing."""
        if self.spot_price_per_hour and self.on_demand_price_per_hour:
            return (self.on_demand_price_per_hour - self.spot_price_per_hour) / self.on_demand_price_per_hour
        return 0.0


class PricingAlert(Base):
    """Model for tracking significant pricing changes."""

    __tablename__ = "pricing_alerts"

    alert_type = Column(String(50), nullable=False)  # price_drop, price_spike, availability_change
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    message = Column(Text, nullable=False)
    old_value = Column(Float, nullable=True)
    new_value = Column(Float, nullable=True)
    change_percentage = Column(Float, nullable=True)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign keys
    pricing_data_id = Column(Integer, ForeignKey("pricing_data.id"), nullable=False)

    def __repr__(self):
        return f"<PricingAlert(id={self.id}, type='{self.alert_type}', severity='{self.severity}')>"