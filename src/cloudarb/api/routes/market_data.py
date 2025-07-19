from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from datetime import datetime, timedelta

from ..database import get_db
from ..models.user import User
from ..models.pricing import PricingData, Provider, InstanceType
from ..api.routes.auth import get_current_active_user

router = APIRouter(prefix="/market-data", tags=["market-data"])

# Pydantic models
class ProviderResponse(BaseModel):
    id: int
    name: str
    display_name: str
    is_active: bool
    regions: List[str]
    instance_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class InstanceTypeResponse(BaseModel):
    id: int
    name: str
    display_name: str
    provider_id: int
    provider_name: str
    gpu_count: int
    gpu_memory_gb: int
    cpu_count: int
    memory_gb: int
    storage_gb: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class PricingDataResponse(BaseModel):
    id: int
    provider_id: int
    provider_name: str
    instance_type_id: int
    instance_type_name: str
    region: str
    price_per_hour: float
    spot_price: Optional[float]
    timestamp: datetime

    class Config:
        from_attributes = True

class PriceComparisonResponse(BaseModel):
    instance_type: str
    region: str
    providers: Dict[str, Dict[str, float]]

@router.get("/providers", response_model=List[ProviderResponse])
async def list_providers(
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of available cloud providers"""

    query = db.query(Provider)

    if is_active is not None:
        query = query.filter(Provider.is_active == is_active)

    providers = query.all()

    # Add instance count for each provider
    result = []
    for provider in providers:
        instance_count = db.query(InstanceType).filter(
            InstanceType.provider_id == provider.id,
            InstanceType.is_active == True
        ).count()

        # Get unique regions for this provider
        regions = db.query(PricingData.region).filter(
            PricingData.provider_id == provider.id
        ).distinct().all()
        regions = [r[0] for r in regions]

        result.append(ProviderResponse(
            id=provider.id,
            name=provider.name,
            display_name=provider.display_name,
            is_active=provider.is_active,
            regions=regions,
            instance_count=instance_count,
            created_at=provider.created_at
        ))

    return result

@router.get("/providers/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific provider details"""

    provider = db.query(Provider).filter(Provider.id == provider_id).first()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Get instance count
    instance_count = db.query(InstanceType).filter(
        InstanceType.provider_id == provider.id,
        InstanceType.is_active == True
    ).count()

    # Get regions
    regions = db.query(PricingData.region).filter(
        PricingData.provider_id == provider.id
    ).distinct().all()
    regions = [r[0] for r in regions]

    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        display_name=provider.display_name,
        is_active=provider.is_active,
        regions=regions,
        instance_count=instance_count,
        created_at=provider.created_at
    )

@router.get("/instance-types", response_model=List[InstanceTypeResponse])
async def list_instance_types(
    provider_id: Optional[int] = Query(None),
    gpu_count: Optional[int] = Query(None),
    min_gpu_memory: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of available instance types"""

    query = db.query(InstanceType).join(Provider)

    if provider_id:
        query = query.filter(InstanceType.provider_id == provider_id)
    if gpu_count:
        query = query.filter(InstanceType.gpu_count == gpu_count)
    if min_gpu_memory:
        query = query.filter(InstanceType.gpu_memory_gb >= min_gpu_memory)
    if is_active is not None:
        query = query.filter(InstanceType.is_active == is_active)

    instance_types = query.all()

    return [
        InstanceTypeResponse(
            id=it.id,
            name=it.name,
            display_name=it.display_name,
            provider_id=it.provider_id,
            provider_name=it.provider.name,
            gpu_count=it.gpu_count,
            gpu_memory_gb=it.gpu_memory_gb,
            cpu_count=it.cpu_count,
            memory_gb=it.memory_gb,
            storage_gb=it.storage_gb,
            is_active=it.is_active,
            created_at=it.created_at
        )
        for it in instance_types
    ]

@router.get("/instance-types/{instance_type_id}", response_model=InstanceTypeResponse)
async def get_instance_type(
    instance_type_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific instance type details"""

    instance_type = db.query(InstanceType).join(Provider).filter(
        InstanceType.id == instance_type_id
    ).first()

    if not instance_type:
        raise HTTPException(status_code=404, detail="Instance type not found")

    return InstanceTypeResponse(
        id=instance_type.id,
        name=instance_type.name,
        display_name=instance_type.display_name,
        provider_id=instance_type.provider_id,
        provider_name=instance_type.provider.name,
        gpu_count=instance_type.gpu_count,
        gpu_memory_gb=instance_type.gpu_memory_gb,
        cpu_count=instance_type.cpu_count,
        memory_gb=instance_type.memory_gb,
        storage_gb=instance_type.storage_gb,
        is_active=instance_type.is_active,
        created_at=instance_type.created_at
    )

@router.get("/pricing", response_model=List[PricingDataResponse])
async def get_pricing_data(
    provider_id: Optional[int] = Query(None),
    instance_type_id: Optional[int] = Query(None),
    region: Optional[str] = Query(None),
    hours_ago: Optional[int] = Query(24, description="Get pricing data from last N hours"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current pricing data"""

    # Calculate time threshold
    time_threshold = datetime.utcnow() - timedelta(hours=hours_ago)

    query = db.query(PricingData).join(Provider).join(InstanceType).filter(
        PricingData.timestamp >= time_threshold
    )

    if provider_id:
        query = query.filter(PricingData.provider_id == provider_id)
    if instance_type_id:
        query = query.filter(PricingData.instance_type_id == instance_type_id)
    if region:
        query = query.filter(PricingData.region == region)

    # Get latest pricing for each combination
    pricing_data = query.order_by(
        PricingData.provider_id,
        PricingData.instance_type_id,
        PricingData.region,
        desc(PricingData.timestamp)
    ).all()

    # Group by provider/instance/region and take latest
    latest_pricing = {}
    for price in pricing_data:
        key = (price.provider_id, price.instance_type_id, price.region)
        if key not in latest_pricing or price.timestamp > latest_pricing[key].timestamp:
            latest_pricing[key] = price

    return [
        PricingDataResponse(
            id=price.id,
            provider_id=price.provider_id,
            provider_name=price.provider.name,
            instance_type_id=price.instance_type_id,
            instance_type_name=price.instance_type.name,
            region=price.region,
            price_per_hour=price.price_per_hour,
            spot_price=price.spot_price,
            timestamp=price.timestamp
        )
        for price in latest_pricing.values()
    ]

@router.get("/pricing/compare", response_model=List[PriceComparisonResponse])
async def compare_prices(
    instance_type: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    gpu_count: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Compare prices across providers for similar instance types"""

    # Get latest pricing data
    time_threshold = datetime.utcnow() - timedelta(hours=24)

    query = db.query(PricingData).join(Provider).join(InstanceType).filter(
        PricingData.timestamp >= time_threshold
    )

    if instance_type:
        query = query.filter(InstanceType.name == instance_type)
    if region:
        query = query.filter(PricingData.region == region)
    if gpu_count:
        query = query.filter(InstanceType.gpu_count == gpu_count)

    pricing_data = query.all()

    # Group by instance type and region
    comparisons = {}
    for price in pricing_data:
        key = (price.instance_type.name, price.region)
        if key not in comparisons:
            comparisons[key] = {
                "instance_type": price.instance_type.name,
                "region": price.region,
                "providers": {}
            }

        comparisons[key]["providers"][price.provider.name] = {
            "on_demand_price": price.price_per_hour,
            "spot_price": price.spot_price,
            "spot_discount": ((price.price_per_hour - price.spot_price) / price.price_per_hour * 100) if price.spot_price else None
        }

    return [PriceComparisonResponse(**comp) for comp in comparisons.values()]

@router.get("/pricing/trends")
async def get_price_trends(
    provider_id: int,
    instance_type_id: int,
    region: str,
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get price trends for a specific instance type"""

    start_date = datetime.utcnow() - timedelta(days=days)

    pricing_data = db.query(PricingData).filter(
        PricingData.provider_id == provider_id,
        PricingData.instance_type_id == instance_type_id,
        PricingData.region == region,
        PricingData.timestamp >= start_date
    ).order_by(PricingData.timestamp).all()

    if not pricing_data:
        raise HTTPException(status_code=404, detail="No pricing data found")

    # Group by date and calculate daily averages
    daily_prices = {}
    for price in pricing_data:
        date_key = price.timestamp.date().isoformat()
        if date_key not in daily_prices:
            daily_prices[date_key] = {
                "on_demand_prices": [],
                "spot_prices": []
            }

        daily_prices[date_key]["on_demand_prices"].append(price.price_per_hour)
        if price.spot_price:
            daily_prices[date_key]["spot_prices"].append(price.spot_price)

    # Calculate averages
    trends = []
    for date, prices in sorted(daily_prices.items()):
        avg_on_demand = sum(prices["on_demand_prices"]) / len(prices["on_demand_prices"])
        avg_spot = None
        if prices["spot_prices"]:
            avg_spot = sum(prices["spot_prices"]) / len(prices["spot_prices"])

        trends.append({
            "date": date,
            "avg_on_demand_price": avg_on_demand,
            "avg_spot_price": avg_spot,
            "spot_discount_percent": ((avg_on_demand - avg_spot) / avg_on_demand * 100) if avg_spot else None
        })

    return {
        "provider_id": provider_id,
        "instance_type_id": instance_type_id,
        "region": region,
        "trends": trends
    }

@router.get("/regions")
async def list_regions(
    provider_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of available regions"""

    query = db.query(PricingData.region).distinct()

    if provider_id:
        query = query.filter(PricingData.provider_id == provider_id)

    regions = query.all()

    return [region[0] for region in regions]

@router.get("/stats")
async def get_market_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get market statistics"""

    # Provider count
    provider_count = db.query(Provider).filter(Provider.is_active == True).count()

    # Instance type count
    instance_count = db.query(InstanceType).filter(InstanceType.is_active == True).count()

    # Region count
    region_count = db.query(PricingData.region).distinct().count()

    # Latest pricing data count
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    pricing_count = db.query(PricingData).filter(PricingData.timestamp >= time_threshold).count()

    # Average prices by provider
    avg_prices = db.query(
        Provider.name,
        func.avg(PricingData.price_per_hour).label('avg_price')
    ).join(PricingData).filter(
        PricingData.timestamp >= time_threshold
    ).group_by(Provider.name).all()

    avg_prices_dict = {row[0]: float(row[1]) for row in avg_prices}

    return {
        "provider_count": provider_count,
        "instance_type_count": instance_count,
        "region_count": region_count,
        "pricing_data_points_24h": pricing_count,
        "average_prices_by_provider": avg_prices_dict,
        "last_updated": datetime.utcnow().isoformat()
    }