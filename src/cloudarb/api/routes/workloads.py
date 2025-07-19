from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ...database import get_db
from ...models.workload import Workload
from ...models.user import User
from .auth import get_current_active_user
from ...optimization.solver import OptimizationSolver
from ...optimization.models import OptimizationRequest, OptimizationResult

router = APIRouter(prefix="/workloads", tags=["workloads"])

# Pydantic models
class WorkloadCreate(BaseModel):
    name: str
    description: Optional[str] = None
    workload_type: str  # training, inference, fine-tuning
    gpu_count: int
    gpu_memory_gb: int
    cpu_count: int
    memory_gb: int
    storage_gb: int
    estimated_duration_hours: float
    priority: int = 1  # 1-5, 5 being highest
    budget_per_hour: float
    deadline: Optional[datetime] = None
    requirements: Optional[dict] = None

class WorkloadUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    workload_type: Optional[str] = None
    gpu_count: Optional[int] = None
    gpu_memory_gb: Optional[int] = None
    cpu_count: Optional[int] = None
    memory_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    estimated_duration_hours: Optional[float] = None
    priority: Optional[int] = None
    budget_per_hour: Optional[float] = None
    deadline: Optional[datetime] = None
    requirements: Optional[dict] = None

class WorkloadResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    workload_type: str
    gpu_count: int
    gpu_memory_gb: int
    cpu_count: int
    memory_gb: int
    storage_gb: int
    estimated_duration_hours: float
    priority: int
    budget_per_hour: float
    deadline: Optional[datetime]
    requirements: Optional[dict]
    status: str
    user_id: int
    organization_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WorkloadOptimizationRequest(BaseModel):
    workload_ids: List[int]
    optimization_type: str = "cost"  # cost, performance, balanced
    constraints: Optional[dict] = None

@router.post("/", response_model=WorkloadResponse)
async def create_workload(
    workload_data: WorkloadCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_workload = Workload(
        **workload_data.dict(),
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        status="pending"
    )

    db.add(db_workload)
    db.commit()
    db.refresh(db_workload)

    return db_workload

@router.get("/", response_model=List[WorkloadResponse])
async def list_workloads(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    workload_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(Workload).filter(Workload.user_id == current_user.id)

    if status:
        query = query.filter(Workload.status == status)
    if workload_type:
        query = query.filter(Workload.workload_type == workload_type)

    workloads = query.offset(skip).limit(limit).all()
    return workloads

@router.get("/{workload_id}", response_model=WorkloadResponse)
async def get_workload(
    workload_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    workload = db.query(Workload).filter(
        Workload.id == workload_id,
        Workload.user_id == current_user.id
    ).first()

    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")

    return workload

@router.put("/{workload_id}", response_model=WorkloadResponse)
async def update_workload(
    workload_id: int,
    workload_data: WorkloadUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    workload = db.query(Workload).filter(
        Workload.id == workload_id,
        Workload.user_id == current_user.id
    ).first()

    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")

    # Only allow updates if workload is not running
    if workload.status in ["running", "completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot update workload in current status"
        )

    update_data = workload_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workload, field, value)

    workload.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(workload)

    return workload

@router.delete("/{workload_id}")
async def delete_workload(
    workload_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    workload = db.query(Workload).filter(
        Workload.id == workload_id,
        Workload.user_id == current_user.id
    ).first()

    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")

    # Only allow deletion if workload is not running
    if workload.status in ["running", "completed"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete workload in current status"
        )

    db.delete(workload)
    db.commit()

    return {"message": "Workload deleted successfully"}

@router.post("/{workload_id}/optimize")
async def optimize_workload(
    workload_id: int,
    optimization_request: WorkloadOptimizationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get the workload
    workload = db.query(Workload).filter(
        Workload.id == workload_id,
        Workload.user_id == current_user.id
    ).first()

    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")

    # Create optimization request
    opt_request = OptimizationRequest(
        workloads=[workload],
        optimization_type=optimization_request.optimization_type,
        constraints=optimization_request.constraints or {},
        user_id=current_user.id
    )

    # Run optimization
    solver = OptimizationSolver()
    try:
        result = solver.optimize(opt_request)
        return {
            "workload_id": workload_id,
            "optimization_result": result.dict(),
            "recommendations": result.recommendations
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Optimization failed: {str(e)}"
        )

@router.post("/batch-optimize")
async def batch_optimize_workloads(
    optimization_request: WorkloadOptimizationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get all workloads
    workloads = db.query(Workload).filter(
        Workload.id.in_(optimization_request.workload_ids),
        Workload.user_id == current_user.id
    ).all()

    if len(workloads) != len(optimization_request.workload_ids):
        raise HTTPException(
            status_code=404,
            detail="Some workloads not found or access denied"
        )

    # Create optimization request
    opt_request = OptimizationRequest(
        workloads=workloads,
        optimization_type=optimization_request.optimization_type,
        constraints=optimization_request.constraints or {},
        user_id=current_user.id
    )

    # Run optimization
    solver = OptimizationSolver()
    try:
        result = solver.optimize(opt_request)
        return {
            "optimization_result": result.dict(),
            "recommendations": result.recommendations,
            "workload_allocations": result.allocations
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Optimization failed: {str(e)}"
        )

@router.get("/{workload_id}/cost-analysis")
async def analyze_workload_cost(
    workload_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    workload = db.query(Workload).filter(
        Workload.id == workload_id,
        Workload.user_id == current_user.id
    ).first()

    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")

    # TODO: Implement cost analysis using CostCalculator
    # For now, return basic cost estimate
    estimated_total_cost = (
        workload.budget_per_hour *
        workload.estimated_duration_hours
    )

    return {
        "workload_id": workload_id,
        "estimated_total_cost": estimated_total_cost,
        "cost_per_hour": workload.budget_per_hour,
        "duration_hours": workload.estimated_duration_hours,
        "cost_breakdown": {
            "compute": estimated_total_cost * 0.7,
            "storage": estimated_total_cost * 0.2,
            "network": estimated_total_cost * 0.1
        }
    }