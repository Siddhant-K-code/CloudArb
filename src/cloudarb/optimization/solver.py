"""
Core optimization solver using Google OR-Tools for GPU resource allocation.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from ortools.linear_solver import pywraplp
from ortools.sat.python import cp_model
import numpy as np

from .models import (
    OptimizationProblem, OptimizationResult, AllocationDecision,
    InstanceOption, ResourceRequirement, OptimizationObjective, PricingType
)
from .risk_manager import RiskManager
from .cost_calculator import CostCalculator
from .performance_analyzer import PerformanceAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class SolverConfig:
    """Solver configuration parameters."""

    solver_name: str = "SCIP"  # SCIP, CBC, GLPK, CPLEX
    timeout_seconds: int = 30
    max_iterations: int = 10000
    tolerance: float = 1e-6
    enable_spot_instances: bool = True
    enable_reserved_instances: bool = True
    risk_weight: float = 0.1
    performance_weight: float = 0.3
    cost_weight: float = 0.6


class OptimizationSolver:
    """Main optimization solver for GPU resource allocation."""

    def __init__(self, config: Optional[SolverConfig] = None):
        """
        Initialize the optimization solver.

        Args:
            config: Solver configuration
        """
        self.config = config or SolverConfig()
        self.risk_manager = RiskManager()
        self.cost_calculator = CostCalculator()
        self.performance_analyzer = PerformanceAnalyzer()

        # Initialize solver
        self.solver = self._create_solver()

    def _create_solver(self) -> pywraplp.Solver:
        """Create and configure the OR-Tools solver."""
        try:
            solver = pywraplp.Solver.CreateSolver(self.config.solver_name)
            if not solver:
                logger.warning(f"Solver {self.config.solver_name} not available, falling back to CBC")
                solver = pywraplp.Solver.CreateSolver("CBC")

            # Configure solver parameters
            solver.set_time_limit(self.config.timeout_seconds * 1000)  # Convert to milliseconds
            solver.EnableOutput()

            return solver
        except Exception as e:
            logger.error(f"Failed to create solver: {e}")
            raise

    def solve(self, problem: OptimizationProblem) -> OptimizationResult:
        """
        Solve the optimization problem.

        Args:
            problem: Optimization problem definition

        Returns:
            OptimizationResult: Solution results
        """
        start_time = time.time()
        result = OptimizationResult(problem_id=problem.problem_id)

        try:
            logger.info(f"Starting optimization for problem {problem.problem_id}")
            result.status = "running"

            # Validate problem
            self._validate_problem(problem)

            # Build optimization model
            model_vars, constraints = self._build_model(problem)

            # Set objective function
            objective = self._create_objective(problem, model_vars)
            self.solver.Minimize(objective)

            # Solve the problem
            solve_status = self.solver.Solve()

            # Process results
            result = self._process_solution(
                problem, model_vars, solve_status, result, time.time() - start_time
            )

            logger.info(f"Optimization completed in {result.solve_time_seconds:.2f} seconds")

        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            result.status = "failed"
            result.error_message = str(e)
            result.error_code = "SOLVER_ERROR"

        return result

    def _validate_problem(self, problem: OptimizationProblem) -> None:
        """Validate optimization problem."""
        if not problem.instance_options:
            raise ValueError("No instance options provided")

        if not problem.resource_requirements:
            raise ValueError("No resource requirements provided")

        # Check if any instance options can satisfy requirements
        total_gpu_requirements = {}
        for req in problem.resource_requirements:
            for gpu_req in req.gpu_requirements:
                if gpu_req.gpu_type not in total_gpu_requirements:
                    total_gpu_requirements[gpu_req.gpu_type] = 0
                total_gpu_requirements[gpu_req.gpu_type] += gpu_req.min_count

        available_gpus = {}
        for option in problem.instance_options:
            if option.gpu_type not in available_gpus:
                available_gpus[option.gpu_type] = 0
            available_gpus[option.gpu_type] += option.gpu_count

        for gpu_type, required in total_gpu_requirements.items():
            if gpu_type not in available_gpus or available_gpus[gpu_type] < required:
                raise ValueError(f"Insufficient {gpu_type} GPUs available")

    def _build_model(self, problem: OptimizationProblem) -> Tuple[Dict[str, Any], List]:
        """
        Build the linear programming model.

        Returns:
            Tuple of (decision variables, constraints)
        """
        model_vars = {}
        constraints = []

        # Create decision variables for each instance option and pricing type
        for i, option in enumerate(problem.instance_options):
            for pricing_type in PricingType:
                if option.get_price(pricing_type) is not None:
                    var_name = f"x_{i}_{pricing_type.value}"
                    model_vars[var_name] = self.solver.IntVar(
                        0, self.solver.infinity(), var_name
                    )

        # Resource constraints
        constraints.extend(self._add_resource_constraints(problem, model_vars))

        # Budget constraints
        constraints.extend(self._add_budget_constraints(problem, model_vars))

        # Risk constraints
        constraints.extend(self._add_risk_constraints(problem, model_vars))

        # Performance constraints
        constraints.extend(self._add_performance_constraints(problem, model_vars))

        # Custom constraints
        constraints.extend(self._add_custom_constraints(problem, model_vars))

        return model_vars, constraints

    def _add_resource_constraints(self, problem: OptimizationProblem, model_vars: Dict[str, Any]) -> List:
        """Add resource requirement constraints."""
        constraints = []
        total_requirements = problem.get_total_resource_requirements()

        # GPU constraints by type
        for gpu_req in total_requirements.gpu_requirements:
            gpu_constraint = self.solver.Constraint(
                gpu_req.min_count, gpu_req.max_count, f"gpu_{gpu_req.gpu_type}"
            )

            for i, option in enumerate(problem.instance_options):
                if option.gpu_type == gpu_req.gpu_type:
                    for pricing_type in PricingType:
                        if option.get_price(pricing_type) is not None:
                            var_name = f"x_{i}_{pricing_type.value}"
                            if var_name in model_vars:
                                gpu_constraint.SetCoefficient(
                                    model_vars[var_name], option.gpu_count
                                )

            constraints.append(gpu_constraint)

        # CPU constraints
        cpu_constraint = self.solver.Constraint(
            total_requirements.cpu_cores, self.solver.infinity(), "cpu"
        )
        for i, option in enumerate(problem.instance_options):
            for pricing_type in PricingType:
                if option.get_price(pricing_type) is not None:
                    var_name = f"x_{i}_{pricing_type.value}"
                    if var_name in model_vars:
                        cpu_constraint.SetCoefficient(
                            model_vars[var_name], option.cpu_cores
                        )
        constraints.append(cpu_constraint)

        # Memory constraints
        memory_constraint = self.solver.Constraint(
            total_requirements.memory_gb, self.solver.infinity(), "memory"
        )
        for i, option in enumerate(problem.instance_options):
            for pricing_type in PricingType:
                if option.get_price(pricing_type) is not None:
                    var_name = f"x_{i}_{pricing_type.value}"
                    if var_name in model_vars:
                        memory_constraint.SetCoefficient(
                            model_vars[var_name], option.memory_gb
                        )
        constraints.append(memory_constraint)

        return constraints

    def _add_budget_constraints(self, problem: OptimizationProblem, model_vars: Dict[str, Any]) -> List:
        """Add budget constraints."""
        constraints = []

        # Find budget constraint
        budget_constraint = None
        for constraint in problem.constraints:
            if constraint.constraint_type == "budget":
                budget_constraint = constraint
                break

        if budget_constraint:
            budget_expr = self.solver.Constraint(
                0, budget_constraint.value, "budget"
            )

            for i, option in enumerate(problem.instance_options):
                for pricing_type in PricingType:
                    price = option.get_price(pricing_type)
                    if price is not None:
                        var_name = f"x_{i}_{pricing_type.value}"
                        if var_name in model_vars:
                            budget_expr.SetCoefficient(
                                model_vars[var_name], price
                            )

            constraints.append(budget_expr)

        return constraints

    def _add_risk_constraints(self, problem: OptimizationProblem, model_vars: Dict[str, Any]) -> List:
        """Add risk management constraints."""
        constraints = []

        # Risk tolerance constraint
        risk_expr = self.solver.Constraint(
            0, problem.risk_tolerance, "risk_tolerance"
        )

        for i, option in enumerate(problem.instance_options):
            for pricing_type in PricingType:
                if option.get_price(pricing_type) is not None:
                    risk_score = self.risk_manager.calculate_instance_risk(
                        option, pricing_type
                    )
                    var_name = f"x_{i}_{pricing_type.value}"
                    if var_name in model_vars:
                        risk_expr.SetCoefficient(
                            model_vars[var_name], risk_score
                        )

        constraints.append(risk_expr)

        return constraints

    def _add_performance_constraints(self, problem: OptimizationProblem, model_vars: Dict[str, Any]) -> List:
        """Add performance constraints."""
        constraints = []

        # Find performance constraint
        perf_constraint = None
        for constraint in problem.constraints:
            if constraint.constraint_type == "performance":
                perf_constraint = constraint
                break

        if perf_constraint:
            perf_expr = self.solver.Constraint(
                perf_constraint.value, self.solver.infinity(), "performance"
            )

            for i, option in enumerate(problem.instance_options):
                for pricing_type in PricingType:
                    if option.get_price(pricing_type) is not None:
                        perf_score = option.performance_score or 50.0  # Default score
                        var_name = f"x_{i}_{pricing_type.value}"
                        if var_name in model_vars:
                            perf_expr.SetCoefficient(
                                model_vars[var_name], perf_score
                            )

            constraints.append(perf_expr)

        return constraints

    def _add_custom_constraints(self, problem: OptimizationProblem, model_vars: Dict[str, Any]) -> List:
        """Add custom constraints from problem definition."""
        constraints = []

        for constraint in problem.constraints:
            if constraint.constraint_type not in ["budget", "performance", "risk"]:
                # Handle custom constraints based on constraint type
                if constraint.constraint_type == "provider_limit":
                    # Limit instances from specific provider
                    provider_expr = self.solver.Constraint(
                        0, constraint.value, f"provider_limit_{constraint.name}"
                    )

                    for i, option in enumerate(problem.instance_options):
                        if option.provider_name == constraint.name:
                            for pricing_type in PricingType:
                                if option.get_price(pricing_type) is not None:
                                    var_name = f"x_{i}_{pricing_type.value}"
                                    if var_name in model_vars:
                                        provider_expr.SetCoefficient(
                                            model_vars[var_name], 1
                                        )

                    constraints.append(provider_expr)

        return constraints

    def _create_objective(self, problem: OptimizationProblem, model_vars: Dict[str, Any]) -> Any:
        """Create the objective function."""
        objective = self.solver.Objective()

        if problem.objective == OptimizationObjective.MINIMIZE_COST:
            # Minimize total cost
            for i, option in enumerate(problem.instance_options):
                for pricing_type in PricingType:
                    price = option.get_price(pricing_type)
                    if price is not None:
                        var_name = f"x_{i}_{pricing_type.value}"
                        if var_name in model_vars:
                            objective.SetCoefficient(model_vars[var_name], price)

        elif problem.objective == OptimizationObjective.MAXIMIZE_PERFORMANCE:
            # Maximize total performance (minimize negative performance)
            for i, option in enumerate(problem.instance_options):
                for pricing_type in PricingType:
                    if option.get_price(pricing_type) is not None:
                        perf_score = option.performance_score or 50.0
                        var_name = f"x_{i}_{pricing_type.value}"
                        if var_name in model_vars:
                            objective.SetCoefficient(model_vars[var_name], -perf_score)

        elif problem.objective == OptimizationObjective.BALANCE_COST_PERFORMANCE:
            # Multi-objective: balance cost and performance
            for i, option in enumerate(problem.instance_options):
                for pricing_type in PricingType:
                    price = option.get_price(pricing_type)
                    if price is not None:
                        perf_score = option.performance_score or 50.0
                        var_name = f"x_{i}_{pricing_type.value}"
                        if var_name in model_vars:
                            # Normalize and weight the objectives
                            normalized_cost = price / 10.0  # Assume max cost is $10/hour
                            normalized_perf = (100 - perf_score) / 100.0  # Invert performance
                            combined_score = (
                                self.config.cost_weight * normalized_cost +
                                self.config.performance_weight * normalized_perf
                            )
                            objective.SetCoefficient(model_vars[var_name], combined_score)

        elif problem.objective == OptimizationObjective.MINIMIZE_RISK:
            # Minimize total risk
            for i, option in enumerate(problem.instance_options):
                for pricing_type in PricingType:
                    if option.get_price(pricing_type) is not None:
                        risk_score = self.risk_manager.calculate_instance_risk(
                            option, pricing_type
                        )
                        var_name = f"x_{i}_{pricing_type.value}"
                        if var_name in model_vars:
                            objective.SetCoefficient(model_vars[var_name], risk_score)

        return objective

    def _process_solution(
        self,
        problem: OptimizationProblem,
        model_vars: Dict[str, Any],
        solve_status: int,
        result: OptimizationResult,
        solve_time: float
    ) -> OptimizationResult:
        """Process the solver solution and create allocation decisions."""
        result.solve_time_seconds = solve_time

        if solve_status == pywraplp.Solver.OPTIMAL:
            result.status = "completed"
            result.is_optimal = True
            result.objective_value = self.solver.Objective().Value()

            # Extract allocation decisions
            allocations = []
            total_cost = 0.0
            total_performance = 0.0
            total_risk = 0.0

            for var_name, var in model_vars.items():
                if var.solution_value() > 0:
                    # Parse variable name to get option index and pricing type
                    parts = var_name.split('_')
                    option_idx = int(parts[1])
                    pricing_type = PricingType(parts[2])

                    option = problem.instance_options[option_idx]
                    instance_count = int(var.solution_value())
                    cost_per_hour = option.get_price(pricing_type)

                    # Calculate performance and risk scores
                    performance_score = option.performance_score or 50.0
                    risk_score = self.risk_manager.calculate_instance_risk(option, pricing_type)

                    allocation = AllocationDecision(
                        workload_id=None,  # Will be assigned later
                        instance_option=option,
                        instance_count=instance_count,
                        pricing_type=pricing_type,
                        cost_per_hour=cost_per_hour,
                        performance_score=performance_score,
                        risk_score=risk_score
                    )

                    allocations.append(allocation)

                    # Update totals
                    total_cost += allocation.total_cost_per_hour
                    total_performance += performance_score * instance_count
                    total_risk += risk_score * instance_count

            result.allocations = allocations
            result.total_cost_per_hour = total_cost
            result.total_performance_score = total_performance / max(1, result.total_instances)
            result.total_risk_score = total_risk / max(1, result.total_instances)

            # Calculate cost savings if baseline is available
            if hasattr(problem, 'baseline_cost') and problem.baseline_cost:
                result.cost_savings_amount = problem.baseline_cost - total_cost
                result.cost_savings_percentage = (
                    (problem.baseline_cost - total_cost) / problem.baseline_cost * 100
                )

            # Calculate solution quality
            result.solution_quality = self._calculate_solution_quality(problem, result)
            result.confidence_score = self._calculate_confidence_score(problem, result)

        elif solve_status == pywraplp.Solver.FEASIBLE:
            result.status = "completed"
            result.is_optimal = False
            result.objective_value = self.solver.Objective().Value()
            result.error_message = "Solver found feasible but not optimal solution"

        elif solve_status == pywraplp.Solver.INFEASIBLE:
            result.status = "failed"
            result.error_message = "Problem is infeasible - no solution exists"
            result.error_code = "INFEASIBLE"

        elif solve_status == pywraplp.Solver.UNBOUNDED:
            result.status = "failed"
            result.error_message = "Problem is unbounded"
            result.error_code = "UNBOUNDED"

        else:
            result.status = "failed"
            result.error_message = f"Solver failed with status: {solve_status}"
            result.error_code = "SOLVER_FAILED"

        return result

    def _calculate_solution_quality(self, problem: OptimizationProblem, result: OptimizationResult) -> float:
        """Calculate solution quality score (0-1)."""
        if not result.allocations:
            return 0.0

        # Calculate various quality metrics
        cost_efficiency = 1.0
        if result.total_cost_per_hour > 0:
            cost_efficiency = min(1.0, 50.0 / result.total_cost_per_hour)  # Normalize to $50/hour

        performance_efficiency = result.total_performance_score / 100.0 if result.total_performance_score else 0.5

        risk_efficiency = 1.0 - result.total_risk_score if result.total_risk_score else 0.8

        # Weighted average
        quality = (
            0.4 * cost_efficiency +
            0.4 * performance_efficiency +
            0.2 * risk_efficiency
        )

        return max(0.0, min(1.0, quality))

    def _calculate_confidence_score(self, problem: OptimizationProblem, result: OptimizationResult) -> float:
        """Calculate confidence score for the solution (0-1)."""
        if not result.allocations:
            return 0.0

        confidence_factors = []

        # Solution optimality
        if result.is_optimal:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.7)

        # Problem size (larger problems may have less confidence)
        problem_size = len(problem.instance_options) * len(problem.resource_requirements)
        if problem_size < 100:
            confidence_factors.append(1.0)
        elif problem_size < 500:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.8)

        # Solve time (faster solutions may be more reliable)
        if result.solve_time_seconds < 5:
            confidence_factors.append(1.0)
        elif result.solve_time_seconds < 15:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.8)

        # Data quality (availability of pricing and performance data)
        data_quality = 0.8  # Placeholder - could be calculated based on data freshness
        confidence_factors.append(data_quality)

        return sum(confidence_factors) / len(confidence_factors)