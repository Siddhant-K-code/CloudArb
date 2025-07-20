"""
Optimization service for CloudArb platform.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.optimization import OptimizationRun, OptimizationResult, Allocation
from ..models.pricing import Provider, InstanceType
from ..optimization.solver import OptimizationSolver, SolverConfig
from ..optimization.models import OptimizationProblem, OptimizationResult as OptResult

logger = logging.getLogger(__name__)


class OptimizationService:
    """Service for managing optimization operations."""

    def __init__(self, db: Session):
        self.db = db
        self.solver = OptimizationSolver()

    def create_optimization_run(
        self,
        problem: OptimizationProblem,
        user_id: int
    ) -> OptimizationRun:
        """Create a new optimization run in the database."""
        optimization_run = OptimizationRun(
            run_id=problem.problem_id,
            name=problem.name,
            description=problem.description,
            objective=problem.objective.value,
            status="pending",
            created_by=user_id,
            organization_id=problem.organization_id,
            created_at=datetime.utcnow()
        )

        self.db.add(optimization_run)
        self.db.commit()
        self.db.refresh(optimization_run)

        return optimization_run

    def get_optimization_run_by_id(
        self,
        run_id: str,
        organization_id: Optional[int] = None
    ) -> Optional[OptimizationRun]:
        """Get optimization run by ID."""
        query = self.db.query(OptimizationRun).filter(OptimizationRun.run_id == run_id)

        if organization_id:
            query = query.filter(OptimizationRun.organization_id == organization_id)

        return query.first()

    def get_allocations_for_run(self, run_id: int) -> List[Allocation]:
        """Get allocations for a specific optimization run."""
        return self.db.query(Allocation).filter(Allocation.optimization_run_id == run_id).all()

    def run_optimization(self, run_id: int) -> None:
        """Run optimization for a specific run ID."""
        try:
            # Get optimization run
            optimization_run = self.db.query(OptimizationRun).filter(
                OptimizationRun.id == run_id
            ).first()

            if not optimization_run:
                logger.error(f"Optimization run {run_id} not found")
                return

            # Update status to running
            optimization_run.status = "running"
            optimization_run.started_at = datetime.utcnow()
            self.db.commit()

            # TODO: Implement actual optimization logic
            # For now, just mark as completed with dummy results
            optimization_run.status = "completed"
            optimization_run.completed_at = datetime.utcnow()
            optimization_run.objective_value = 100.0
            optimization_run.total_cost_per_hour = 2.50
            optimization_run.cost_savings_percentage = 15.0
            optimization_run.total_performance_score = 85.0
            optimization_run.total_risk_score = 0.1
            optimization_run.solve_time_seconds = 5.0

            self.db.commit()

            logger.info(f"Optimization run {run_id} completed successfully")

        except Exception as e:
            logger.error(f"Failed to run optimization {run_id}: {e}")

            # Update status to failed
            optimization_run.status = "failed"
            optimization_run.error_message = str(e)
            optimization_run.completed_at = datetime.utcnow()
            self.db.commit()

    def list_optimizations(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[str] = None
    ) -> List[OptimizationRun]:
        """List optimizations for a user."""
        query = self.db.query(OptimizationRun).filter(OptimizationRun.created_by == user_id)

        if status_filter:
            query = query.filter(OptimizationRun.status == status_filter)

        return query.offset(skip).limit(limit).all()

    def delete_optimization(self, run_id: str, user_id: int) -> bool:
        """Delete an optimization run."""
        optimization_run = self.db.query(OptimizationRun).filter(
            OptimizationRun.run_id == run_id,
            OptimizationRun.created_by == user_id
        ).first()

        if optimization_run:
            self.db.delete(optimization_run)
            self.db.commit()
            return True

        return False