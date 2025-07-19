"""
Optimization API routes for CloudArb platform.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import User, OptimizationRun, OptimizationResult, Allocation
from ...api.dependencies import get_current_user
from ...optimization.solver import OptimizationSolver, SolverConfig
from ...optimization.models import (
    OptimizationRequest, OptimizationResponse, OptimizationProblem,
    OptimizationObjective, InstanceOption, ResourceRequirement, GPURequirement
)
from ...services.optimization_service import OptimizationService
from ...services.pricing_service import PricingService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=OptimizationResponse)
async def create_optimization(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create and run a new optimization.

    This endpoint creates an optimization problem and runs it in the background.
    Returns immediately with a result ID that can be used to check status.
    """
    try:
        # Create optimization service
        optimization_service = OptimizationService(db)
        pricing_service = PricingService(db)

        # Get available instance options
        instance_options = await pricing_service.get_available_instances(
            gpu_types=[req.get("gpu_type", "a100") for req in request.workloads],
            regions=request.constraints.get("regions", []) if request.constraints else []
        )

        if not instance_options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No suitable instance options found for the specified requirements"
            )

        # Create optimization problem
        problem = OptimizationProblem(
            name=request.name,
            description=request.description,
            workloads=request.workloads,
            objective=request.objective,
            risk_tolerance=request.risk_tolerance,
            time_horizon_hours=request.time_horizon_hours,
            timeout_seconds=request.timeout_seconds,
            organization_id=current_user.organization_id,
            created_by=current_user.id,
        )

        # Add instance options to problem
        for option_data in instance_options:
            option = InstanceOption(
                provider_id=option_data["provider_id"],
                instance_type_id=option_data["instance_type_id"],
                provider_name=option_data["provider_name"],
                instance_name=option_data["instance_name"],
                region=option_data["region"],
                cpu_cores=option_data["cpu_cores"],
                memory_gb=option_data["memory_gb"],
                gpu_count=option_data["gpu_count"],
                gpu_type=option_data["gpu_type"],
                gpu_memory_gb=option_data["gpu_memory_gb"],
                storage_gb=option_data["storage_gb"],
                on_demand_price_per_hour=option_data["on_demand_price_per_hour"],
                spot_price_per_hour=option_data.get("spot_price_per_hour"),
                performance_score=option_data.get("performance_score"),
            )
            problem.add_instance_option(option)

        # Add constraints
        for constraint_data in request.constraints:
            from ...optimization.models import OptimizationConstraint
            constraint = OptimizationConstraint(
                name=constraint_data["name"],
                constraint_type=constraint_data["type"],
                operator=constraint_data["operator"],
                value=constraint_data["value"],
                weight=constraint_data.get("weight", 1.0),
                is_hard_constraint=constraint_data.get("is_hard_constraint", True),
            )
            problem.add_constraint(constraint)

        # Create optimization run in database
        optimization_run = optimization_service.create_optimization_run(
            problem=problem,
            user_id=current_user.id
        )

        # Run optimization in background
        background_tasks.add_task(
            optimization_service.run_optimization,
            optimization_run.id
        )

        return OptimizationResponse(
            result_id=optimization_run.run_id,
            status="pending",
            message="Optimization started successfully"
        )

    except Exception as e:
        logger.error(f"Failed to create optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create optimization: {str(e)}"
        )


@router.get("/{result_id}", response_model=OptimizationResponse)
async def get_optimization_result(
    result_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get optimization result by ID.
    """
    try:
        optimization_service = OptimizationService(db)

        # Get optimization run
        optimization_run = optimization_service.get_optimization_run_by_id(
            result_id, current_user.organization_id
        )

        if not optimization_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Optimization result not found"
            )

        # Get allocations
        allocations = optimization_service.get_allocations_for_run(optimization_run.id)

        # Format allocations for response
        allocation_data = []
        for allocation in allocations:
            allocation_data.append({
                "provider": allocation.provider.name,
                "instance_type": allocation.instance_type.name,
                "count": allocation.instance_count,
                "cost_per_hour": allocation.cost_per_hour,
                "gpu_count": allocation.gpu_count,
                "region": allocation.region,
                "pricing_type": allocation.pricing_type,
                "performance_score": allocation.expected_performance_score,
                "risk_score": allocation.risk_score,
            })

        return OptimizationResponse(
            result_id=optimization_run.run_id,
            status=optimization_run.status.value,
            objective_value=optimization_run.objective_value,
            total_cost_per_hour=optimization_run.total_cost_per_hour,
            cost_savings_percentage=optimization_run.cost_savings_percentage,
            total_performance_score=optimization_run.total_performance_score,
            total_risk_score=optimization_run.total_risk_score,
            solve_time_seconds=optimization_run.solve_time_seconds,
            allocations=allocation_data,
            error_message=optimization_run.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get optimization result: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get optimization result: {str(e)}"
        )


@router.get("/", response_model=List[Dict[str, Any]])
async def list_optimizations(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List optimization runs for the current user's organization.
    """
    try:
        optimization_service = OptimizationService(db)

        optimizations = optimization_service.list_optimization_runs(
            organization_id=current_user.organization_id,
            skip=skip,
            limit=limit,
            status_filter=status_filter
        )

        return [
            {
                "id": opt.id,
                "run_id": opt.run_id,
                "name": opt.name,
                "status": opt.status.value,
                "objective_value": opt.objective_value,
                "total_cost_per_hour": opt.total_cost_per_hour,
                "cost_savings_percentage": opt.cost_savings_percentage,
                "solve_time_seconds": opt.solve_time_seconds,
                "created_at": opt.created_at.isoformat(),
                "completed_at": opt.completed_at.isoformat() if opt.completed_at else None,
            }
            for opt in optimizations
        ]

    except Exception as e:
        logger.error(f"Failed to list optimizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list optimizations: {str(e)}"
        )


@router.delete("/{result_id}")
async def delete_optimization(
    result_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an optimization run.
    """
    try:
        optimization_service = OptimizationService(db)

        # Get optimization run
        optimization_run = optimization_service.get_optimization_run_by_id(
            result_id, current_user.organization_id
        )

        if not optimization_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Optimization result not found"
            )

        # Delete optimization run
        optimization_service.delete_optimization_run(optimization_run.id)

        return {"message": "Optimization deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete optimization: {str(e)}"
        )


@router.post("/{result_id}/deploy")
async def deploy_optimization(
    result_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deploy the optimized allocation.
    """
    try:
        optimization_service = OptimizationService(db)

        # Get optimization run
        optimization_run = optimization_service.get_optimization_run_by_id(
            result_id, current_user.organization_id
        )

        if not optimization_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Optimization result not found"
            )

        if optimization_run.status.value != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only deploy completed optimizations"
            )

        # Deploy allocations
        deployment_result = await optimization_service.deploy_allocations(
            optimization_run.id, current_user.id
        )

        return {
            "message": "Deployment initiated successfully",
            "deployment_id": deployment_result["deployment_id"],
            "status": deployment_result["status"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deploy optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy optimization: {str(e)}"
        )


@router.get("/{result_id}/allocations")
async def get_optimization_allocations(
    result_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed allocation information for an optimization result.
    """
    try:
        optimization_service = OptimizationService(db)

        # Get optimization run
        optimization_run = optimization_service.get_optimization_run_by_id(
            result_id, current_user.organization_id
        )

        if not optimization_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Optimization result not found"
            )

        # Get allocations with detailed information
        allocations = optimization_service.get_detailed_allocations(optimization_run.id)

        return {
            "optimization_id": optimization_run.run_id,
            "status": optimization_run.status.value,
            "allocations": allocations,
            "summary": {
                "total_instances": sum(alloc["instance_count"] for alloc in allocations),
                "total_gpus": sum(alloc["gpu_count"] * alloc["instance_count"] for alloc in allocations),
                "total_cost_per_hour": sum(alloc["total_cost_per_hour"] for alloc in allocations),
                "providers": list(set(alloc["provider"] for alloc in allocations)),
                "regions": list(set(alloc["region"] for alloc in allocations)),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get optimization allocations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get optimization allocations: {str(e)}"
        )


@router.post("/quick-optimize")
async def quick_optimize(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick optimization with minimal parameters.
    """
    try:
        # Extract parameters
        gpu_type = request.get("gpu_type", "a100")
        gpu_count = request.get("gpu_count", 1)
        workload_type = request.get("workload_type", "training")
        budget_per_hour = request.get("budget_per_hour")
        risk_tolerance = request.get("risk_tolerance", 0.1)

        # Create simple optimization request
        optimization_request = OptimizationRequest(
            name=f"Quick optimization - {gpu_type} x{gpu_count}",
            workloads=[{
                "gpu_type": gpu_type,
                "min_count": gpu_count,
                "max_count": gpu_count,
                "workload_type": workload_type,
            }],
            objective=OptimizationObjective.MINIMIZE_COST,
            constraints=[
                {
                    "name": "budget",
                    "type": "budget",
                    "operator": "<=",
                    "value": budget_per_hour
                }
            ] if budget_per_hour else [],
            risk_tolerance=risk_tolerance,
            timeout_seconds=15,  # Quick optimization
        )

        # Use the main optimization endpoint
        return await create_optimization(
            optimization_request,
            BackgroundTasks(),
            current_user,
            db
        )

    except Exception as e:
        logger.error(f"Failed to perform quick optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform quick optimization: {str(e)}"
        )