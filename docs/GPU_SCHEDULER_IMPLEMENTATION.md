# GPU Scheduler Implementation Architecture

## Technical Implementation Overview

This document provides detailed technical implementation details for CloudArb's GPU scheduler, complementing the core logic summary with specific algorithms, data structures, and implementation patterns.

## Core Data Structures

### OptimizationProblem
```python
@dataclass
class OptimizationProblem:
    problem_id: str
    instance_options: List[InstanceOption]
    resource_requirements: List[ResourceRequirement]
    constraints: List[Constraint]
    objective: OptimizationObjective
    risk_tolerance: float = 0.1
    time_horizon_hours: int = 24
    baseline_cost: Optional[float] = None
```

### InstanceOption
```python
@dataclass
class InstanceOption:
    provider_name: str
    instance_name: str
    region: str
    gpu_type: str
    gpu_count: int
    gpu_memory_gb: float
    cpu_cores: int
    memory_gb: float
    on_demand_price_per_hour: float
    spot_price_per_hour: Optional[float]
    reserved_1y_price_per_hour: Optional[float]
    reserved_3y_price_per_hour: Optional[float]
    performance_score: Optional[float]
    spot_availability: Optional[float]
    spot_interruption_probability: Optional[float]
```

### AllocationDecision
```python
@dataclass
class AllocationDecision:
    workload_id: Optional[str]
    instance_option: InstanceOption
    instance_count: int
    pricing_type: PricingType
    cost_per_hour: float
    performance_score: float
    risk_score: float
    deployment_config: Optional[Dict]
    terraform_config: Optional[Dict]
    kubernetes_config: Optional[Dict]
```

## Algorithm Implementation Details

### 1. Linear Programming Model Construction

```python
def _build_model(self, problem: OptimizationProblem) -> Tuple[Dict[str, Any], List]:
    """Build the linear programming model with detailed constraint formulation."""
    
    # Decision Variables: x_{i}_{p} = number of instances of type i with pricing p
    model_vars = {}
    for i, option in enumerate(problem.instance_options):
        for pricing_type in PricingType:
            if option.get_price(pricing_type) is not None:
                var_name = f"x_{i}_{pricing_type.value}"
                model_vars[var_name] = self.solver.IntVar(
                    0, self.solver.infinity(), var_name
                )
    
    # Constraint Categories
    constraints = []
    
    # Resource Constraints
    constraints.extend(self._add_resource_constraints(problem, model_vars))
    
    # Budget Constraints  
    constraints.extend(self._add_budget_constraints(problem, model_vars))
    
    # Risk Constraints
    constraints.extend(self._add_risk_constraints(problem, model_vars))
    
    # Performance Constraints
    constraints.extend(self._add_performance_constraints(problem, model_vars))
    
    return model_vars, constraints
```

### 2. Resource Constraint Implementation

```python
def _add_resource_constraints(self, problem: OptimizationProblem, model_vars: Dict[str, Any]) -> List:
    """Implement detailed resource constraints with GPU type matching."""
    constraints = []
    total_requirements = problem.get_total_resource_requirements()
    
    # GPU constraints by type (most critical)
    for gpu_req in total_requirements.gpu_requirements:
        gpu_constraint = self.solver.Constraint(
            gpu_req.min_count, 
            gpu_req.max_count if gpu_req.max_count != -1 else self.solver.infinity(),
            f"gpu_{gpu_req.gpu_type}"
        )
        
        # Only include instances that match the GPU type
        for i, option in enumerate(problem.instance_options):
            if option.gpu_type == gpu_req.gpu_type:
                for pricing_type in PricingType:
                    if option.get_price(pricing_type) is not None:
                        var_name = f"x_{i}_{pricing_type.value}"
                        if var_name in model_vars:
                            # Coefficient = number of GPUs per instance
                            gpu_constraint.SetCoefficient(
                                model_vars[var_name], option.gpu_count
                            )
        
        constraints.append(gpu_constraint)
    
    # Memory constraints (ensure sufficient GPU memory)
    memory_constraint = self.solver.Constraint(
        total_requirements.memory_gb, 
        self.solver.infinity(), 
        "memory"
    )
    
    for i, option in enumerate(problem.instance_options):
        for pricing_type in PricingType:
            if option.get_price(pricing_type) is not None:
                var_name = f"x_{i}_{pricing_type.value}"
                if var_name in model_vars:
                    # Total memory = instance memory + GPU memory
                    total_memory = option.memory_gb + (option.gpu_memory_gb * option.gpu_count)
                    memory_constraint.SetCoefficient(
                        model_vars[var_name], total_memory
                    )
    
    constraints.append(memory_constraint)
    return constraints
```

### 3. Risk-Adjusted Objective Function

```python
def _create_objective(self, problem: OptimizationProblem, model_vars: Dict[str, Any]) -> Any:
    """Create sophisticated multi-objective function with risk adjustment."""
    objective = self.solver.Objective()
    
    if problem.objective == OptimizationObjective.BALANCE_COST_PERFORMANCE:
        # Multi-objective with risk adjustment
        for i, option in enumerate(problem.instance_options):
            for pricing_type in PricingType:
                price = option.get_price(pricing_type)
                if price is not None:
                    var_name = f"x_{i}_{pricing_type.value}"
                    if var_name in model_vars:
                        # Risk-adjusted cost
                        risk_score = self.risk_manager.calculate_instance_risk(
                            option, pricing_type
                        )
                        risk_adjusted_price = price * (1.0 + risk_score * self.config.risk_weight)
                        
                        # Performance penalty (invert to minimize)
                        perf_score = option.performance_score or 50.0
                        performance_penalty = (100 - perf_score) / 100.0
                        
                        # Combined objective coefficient
                        combined_coefficient = (
                            self.config.cost_weight * (risk_adjusted_price / 10.0) +
                            self.config.performance_weight * performance_penalty
                        )
                        
                        objective.SetCoefficient(model_vars[var_name], combined_coefficient)
    
    return objective
```

## Performance Analysis Implementation

### 1. GPU Performance Benchmarking

```python
def _calculate_compute_score(self, gpu_specs: Dict[str, float], 
                           workload_specs: Dict[str, bool], gpu_count: int) -> float:
    """Detailed compute performance calculation."""
    
    # Select appropriate performance metric based on workload
    if workload_specs.get("fp16_heavy", False):
        # AI/ML training typically uses FP16
        raw_performance = gpu_specs.get("fp16_performance", 0)
    elif workload_specs.get("fp32_heavy", False):
        # Scientific computing often requires FP32
        raw_performance = gpu_specs.get("fp32_performance", 0)
    else:
        # Mixed workloads - use weighted average
        fp32_perf = gpu_specs.get("fp32_performance", 0)
        fp16_perf = gpu_specs.get("fp16_performance", 0)
        raw_performance = (fp32_perf * 0.3 + fp16_perf * 0.7)
    
    # Scale by GPU count (with diminishing returns for very large counts)
    if gpu_count <= 8:
        scaling_factor = gpu_count
    else:
        # Diminishing returns due to communication overhead
        scaling_factor = 8 + (gpu_count - 8) * 0.9
    
    scaled_performance = raw_performance * scaling_factor
    
    # Normalize against H100 baseline (989 TFLOPS FP32)
    max_performance = self.gpu_benchmarks["h100"]["fp32_performance"]
    normalized_score = (scaled_performance / max_performance) * 100
    
    return min(100.0, normalized_score)
```

### 2. Memory Performance Assessment

```python
def _calculate_memory_score(self, gpu_specs: Dict[str, float], 
                          workload_specs: Dict[str, bool], instance: InstanceOption) -> float:
    """Advanced memory performance scoring with bandwidth consideration."""
    
    if not workload_specs.get("memory_intensive", False):
        return 80.0  # Good baseline for non-memory-intensive workloads
    
    # Memory capacity score
    total_gpu_memory = gpu_specs.get("memory_size", 0) * instance.gpu_count
    max_memory = self.gpu_benchmarks["h100"]["memory_size"] * instance.gpu_count
    memory_capacity_score = min(100.0, (total_gpu_memory / max_memory) * 100)
    
    # Memory bandwidth score
    total_bandwidth = gpu_specs.get("memory_bandwidth", 0) * instance.gpu_count
    max_bandwidth = self.gpu_benchmarks["h100"]["memory_bandwidth"] * instance.gpu_count
    bandwidth_score = min(100.0, (total_bandwidth / max_bandwidth) * 100)
    
    # Memory access pattern consideration
    if workload_specs.get("sequential_access", True):
        # Sequential access patterns are more bandwidth-friendly
        bandwidth_weight = 0.4
        capacity_weight = 0.6
    else:
        # Random access patterns need more capacity
        bandwidth_weight = 0.3
        capacity_weight = 0.7
    
    return (memory_capacity_score * capacity_weight + 
            bandwidth_score * bandwidth_weight)
```

## Risk Management Implementation

### 1. Comprehensive Risk Calculation

```python
def calculate_instance_risk(self, instance: InstanceOption, pricing_type: PricingType) -> float:
    """Multi-factor risk assessment with dynamic weighting."""
    
    risk_factors = []
    
    # Spot interruption risk (most critical for spot instances)
    if pricing_type == PricingType.SPOT:
        spot_risk = self._calculate_spot_interruption_risk(instance)
        # Higher weight for spot instances
        weight = self.risk_weights["spot_interruption"] * 1.5
        risk_factors.append(RiskFactor(
            name="spot_interruption",
            weight=weight,
            risk_score=spot_risk,
            description=f"Spot interruption probability: {spot_risk:.2f}"
        ))
    
    # Provider reliability (historical uptime)
    provider_risk = self._calculate_provider_reliability_risk(instance)
    risk_factors.append(RiskFactor(
        name="provider_reliability",
        weight=self.risk_weights["provider_reliability"],
        risk_score=provider_risk,
        description=f"Provider {instance.provider_name} reliability: {1-provider_risk:.2f}"
    ))
    
    # Regional availability risk
    region_risk = self._calculate_region_availability_risk(instance)
    risk_factors.append(RiskFactor(
        name="region_availability", 
        weight=self.risk_weights["region_availability"],
        risk_score=region_risk,
        description=f"Region {instance.region} availability: {1-region_risk:.2f}"
    ))
    
    # Price volatility risk
    price_volatility = self._calculate_price_volatility_risk(instance, pricing_type)
    risk_factors.append(RiskFactor(
        name="price_volatility",
        weight=self.risk_weights["price_volatility"], 
        risk_score=price_volatility,
        description=f"Price volatility risk: {price_volatility:.2f}"
    ))
    
    # Performance variance risk
    perf_variance = self._calculate_performance_variance_risk(instance)
    risk_factors.append(RiskFactor(
        name="performance_variance",
        weight=self.risk_weights["performance_variance"],
        risk_score=perf_variance,
        description=f"Performance consistency: {1-perf_variance:.2f}"
    ))
    
    # Calculate weighted risk score
    total_weight = sum(factor.weight for factor in risk_factors)
    if total_weight > 0:
        weighted_risk = sum(factor.risk_score * factor.weight for factor in risk_factors) / total_weight
    else:
        weighted_risk = 0.0
    
    return min(1.0, max(0.0, weighted_risk))
```

### 2. Portfolio Risk Assessment

```python
def assess_portfolio_risk(self, allocations: List[Tuple[InstanceOption, int, PricingType]]) -> Dict[str, float]:
    """Advanced portfolio risk analysis with correlation considerations."""
    
    if not allocations:
        return {"total_risk": 0.0, "diversification_score": 0.0}
    
    # Calculate value-weighted risk
    individual_risks = []
    total_value = 0.0
    
    for instance, count, pricing_type in allocations:
        individual_risk = self.calculate_instance_risk(instance, pricing_type)
        cost_per_hour = instance.get_price(pricing_type) or 0
        allocation_value = cost_per_hour * count
        
        individual_risks.append((individual_risk, allocation_value))
        total_value += allocation_value
    
    if total_value == 0:
        return {"total_risk": 0.0, "diversification_score": 0.0}
    
    # Value-weighted average risk
    weighted_risk = sum(risk * value for risk, value in individual_risks) / total_value
    
    # Diversification scoring
    diversification_score = self._calculate_advanced_diversification(allocations)
    
    # Correlation-adjusted risk (simplified correlation model)
    correlation_adjustment = self._calculate_correlation_adjustment(allocations)
    adjusted_risk = weighted_risk * correlation_adjustment
    
    # Concentration risk using Herfindahl-Hirschman Index
    concentration_risk = self._calculate_concentration_risk(allocations)
    
    return {
        "total_risk": adjusted_risk,
        "diversification_score": diversification_score,
        "concentration_risk": concentration_risk,
        "correlation_adjustment": correlation_adjustment,
        "individual_risks": individual_risks,
    }
```

## Machine Learning Integration

### 1. Feature Engineering Pipeline

```python
def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
    """Comprehensive feature engineering for ML models."""
    df = data.copy()
    
    # Temporal features
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour_of_day'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['day_of_month'] = df['timestamp'].dt.day
    df['month'] = df['timestamp'].dt.month
    df['quarter'] = df['timestamp'].dt.quarter
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['is_business_hours'] = df['hour_of_day'].between(9, 17).astype(int)
    
    # Holiday detection
    df['is_holiday'] = self._detect_holidays(df['timestamp'])
    df['days_to_holiday'] = self._days_to_next_holiday(df['timestamp'])
    
    # Price dynamics
    for window in [1, 6, 24, 168]:  # 1h, 6h, 1d, 1w
        df[f'price_trend_{window}h'] = df['price_per_hour'].pct_change(window)
        df[f'price_volatility_{window}h'] = df['price_per_hour'].rolling(window).std()
        df[f'price_ma_{window}h'] = df['price_per_hour'].rolling(window).mean()
    
    # Market indicators
    df['spot_discount'] = (df['on_demand_price'] - df['spot_price']) / df['on_demand_price']
    df['market_stress'] = df['spot_price'].rolling(24).std() / df['spot_price'].rolling(24).mean()
    
    # Provider-specific features
    df['provider_utilization'] = self._estimate_provider_utilization(df)
    df['regional_demand'] = self._estimate_regional_demand(df)
    
    return df.fillna(method='ffill').fillna(0)
```

### 2. Model Training and Validation

```python
def train_demand_model(self, data: pd.DataFrame, provider: str, instance_type: str) -> Dict[str, float]:
    """Train ML model with cross-validation and hyperparameter tuning."""
    
    # Feature preparation
    df = self.prepare_features(data)
    X = df[self.feature_columns].values
    y = df['demand'].values
    
    # Train-validation split with time awareness
    split_point = int(len(X) * 0.8)
    X_train, X_val = X[:split_point], X[split_point:]
    y_train, y_val = y[:split_point], y[split_point:]
    
    # Feature scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # Model ensemble
    models = {
        'rf': RandomForestRegressor(n_estimators=100, random_state=42),
        'gbm': GradientBoostingRegressor(n_estimators=100, random_state=42),
        'prophet': self._create_prophet_model(df)
    }
    
    # Train models
    ensemble_predictions = []
    model_weights = {}
    
    for name, model in models.items():
        if name != 'prophet':
            model.fit(X_train_scaled, y_train)
            val_pred = model.predict(X_val_scaled)
        else:
            prophet_pred = self._train_prophet_model(model, df, split_point)
            val_pred = prophet_pred
        
        # Calculate model weight based on validation performance
        val_mae = mean_absolute_error(y_val, val_pred)
        model_weights[name] = 1.0 / (val_mae + 1e-6)  # Inverse error weighting
        ensemble_predictions.append(val_pred)
    
    # Normalize weights
    total_weight = sum(model_weights.values())
    model_weights = {k: v/total_weight for k, v in model_weights.items()}
    
    # Store trained models and metadata
    model_key = f"{provider}_{instance_type}"
    self.models[model_key] = models
    self.scalers[model_key] = scaler
    self.model_weights[model_key] = model_weights
    
    # Return validation metrics
    ensemble_pred = np.average(ensemble_predictions, axis=0, weights=list(model_weights.values()))
    
    return {
        'mae': mean_absolute_error(y_val, ensemble_pred),
        'rmse': np.sqrt(mean_squared_error(y_val, ensemble_pred)),
        'r2': r2_score(y_val, ensemble_pred),
        'model_weights': model_weights
    }
```

## Optimization Performance Enhancements

### 1. Problem Preprocessing

```python
def preprocess_problem(self, problem: OptimizationProblem) -> OptimizationProblem:
    """Optimize problem structure for faster solving."""
    
    # Remove dominated instances (strictly worse in all dimensions)
    filtered_instances = self._remove_dominated_instances(problem.instance_options)
    
    # Precompute risk and performance scores
    for instance in filtered_instances:
        for pricing_type in PricingType:
            if instance.get_price(pricing_type) is not None:
                # Cache risk scores
                risk_key = f"{instance.provider_name}_{instance.instance_name}_{pricing_type.value}"
                if risk_key not in self._risk_cache:
                    self._risk_cache[risk_key] = self.risk_manager.calculate_instance_risk(
                        instance, pricing_type
                    )
                
                # Cache performance scores
                perf_key = f"{instance.gpu_type}_{instance.gpu_count}"
                if perf_key not in self._performance_cache:
                    self._performance_cache[perf_key] = self.performance_analyzer.calculate_performance_score(
                        instance, problem.workload_type
                    )
                    instance.performance_score = self._performance_cache[perf_key]
    
    return OptimizationProblem(
        problem_id=problem.problem_id,
        instance_options=filtered_instances,
        resource_requirements=problem.resource_requirements,
        constraints=problem.constraints,
        objective=problem.objective,
        risk_tolerance=problem.risk_tolerance
    )
```

### 2. Heuristic Initial Solutions

```python
def generate_initial_solution(self, problem: OptimizationProblem) -> List[AllocationDecision]:
    """Generate good initial solution using greedy heuristics."""
    
    # Sort instances by cost-performance ratio
    scored_instances = []
    for instance in problem.instance_options:
        for pricing_type in PricingType:
            price = instance.get_price(pricing_type)
            if price is not None:
                perf_score = instance.performance_score or 50.0
                risk_score = self._risk_cache.get(
                    f"{instance.provider_name}_{instance.instance_name}_{pricing_type.value}", 0.5
                )
                
                # Multi-criteria scoring
                if problem.objective == OptimizationObjective.MINIMIZE_COST:
                    score = -price  # Lower cost = higher score
                elif problem.objective == OptimizationObjective.MAXIMIZE_PERFORMANCE:
                    score = perf_score  # Higher performance = higher score
                else:  # BALANCE_COST_PERFORMANCE
                    normalized_cost = price / 10.0  # Assume max cost $10/hour
                    normalized_perf = perf_score / 100.0
                    score = normalized_perf - 0.5 * normalized_cost - 0.3 * risk_score
                
                scored_instances.append((score, instance, pricing_type))
    
    # Sort by score (descending)
    scored_instances.sort(key=lambda x: x[0], reverse=True)
    
    # Greedy allocation
    allocations = []
    remaining_requirements = problem.get_total_resource_requirements()
    
    for score, instance, pricing_type in scored_instances:
        if self._requirements_satisfied(remaining_requirements):
            break
        
        # Calculate how many instances we can afford/need
        max_instances = self._calculate_max_instances(
            instance, pricing_type, remaining_requirements, problem.constraints
        )
        
        if max_instances > 0:
            allocation = AllocationDecision(
                workload_id=None,
                instance_option=instance,
                instance_count=max_instances,
                pricing_type=pricing_type,
                cost_per_hour=instance.get_price(pricing_type) * max_instances,
                performance_score=instance.performance_score or 50.0,
                risk_score=self._risk_cache.get(
                    f"{instance.provider_name}_{instance.instance_name}_{pricing_type.value}", 0.5
                )
            )
            allocations.append(allocation)
            
            # Update remaining requirements
            remaining_requirements = self._update_requirements(
                remaining_requirements, instance, max_instances
            )
    
    return allocations
```

## Monitoring and Feedback Integration

### 1. Real-time Performance Tracking

```python
def track_allocation_performance(self, allocation_id: str, metrics: Dict[str, float]):
    """Track actual performance vs predictions for continuous improvement."""
    
    allocation = self.get_allocation(allocation_id)
    
    # Compare predicted vs actual performance
    predicted_perf = allocation.performance_score
    actual_perf = metrics.get('performance_score', 0)
    
    performance_error = abs(predicted_perf - actual_perf) / predicted_perf
    
    # Update performance prediction models
    if performance_error > 0.1:  # >10% error threshold
        self.performance_analyzer.update_prediction_model(
            gpu_type=allocation.instance_option.gpu_type,
            workload_type=metrics.get('workload_type', 'training'),
            predicted_score=predicted_perf,
            actual_score=actual_perf,
            instance_config={
                'gpu_count': allocation.instance_option.gpu_count,
                'provider': allocation.instance_option.provider_name,
                'region': allocation.instance_option.region
            }
        )
    
    # Track cost accuracy
    predicted_cost = allocation.cost_per_hour
    actual_cost = metrics.get('actual_cost_per_hour', predicted_cost)
    
    cost_error = abs(predicted_cost - actual_cost) / predicted_cost
    
    # Update risk models with interruption data
    if allocation.pricing_type == PricingType.SPOT:
        interruption_occurred = metrics.get('interruption_occurred', False)
        self.risk_manager.update_interruption_model(
            provider=allocation.instance_option.provider_name,
            region=allocation.instance_option.region,
            gpu_type=allocation.instance_option.gpu_type,
            interruption_occurred=interruption_occurred
        )
    
    # Store feedback for model retraining
    feedback_data = {
        'allocation_id': allocation_id,
        'timestamp': datetime.utcnow(),
        'predicted_performance': predicted_perf,
        'actual_performance': actual_perf,
        'predicted_cost': predicted_cost,
        'actual_cost': actual_cost,
        'performance_error': performance_error,
        'cost_error': cost_error,
        'allocation_config': allocation.__dict__
    }
    
    self.feedback_store.append(feedback_data)
```

### 2. Model Retraining Pipeline

```python
async def retrain_models_periodic(self):
    """Periodic model retraining based on accumulated feedback."""
    
    # Collect feedback data from last training period
    recent_feedback = self.get_recent_feedback(days=7)
    
    if len(recent_feedback) < 100:  # Minimum samples for retraining
        return
    
    # Retrain performance prediction models
    performance_data = self.prepare_performance_training_data(recent_feedback)
    await self.performance_analyzer.retrain_models(performance_data)
    
    # Retrain risk models
    risk_data = self.prepare_risk_training_data(recent_feedback)
    await self.risk_manager.retrain_models(risk_data)
    
    # Update ML forecasting models
    pricing_data = await self.data_collector.get_recent_pricing_data(days=30)
    await self.ml_service.retrain_models(pricing_data)
    
    # Validate model improvements
    validation_results = await self.validate_model_improvements(recent_feedback)
    
    if validation_results['performance_improvement'] > 0.05:  # 5% improvement
        self.deploy_updated_models()
        logger.info(f"Models updated with {validation_results['performance_improvement']:.2%} improvement")
    else:
        self.rollback_models()
        logger.warning("Model update did not improve performance, rolling back")
```

This technical implementation document provides the detailed algorithms, data structures, and implementation patterns that make CloudArb's GPU scheduler effective and robust. The system's strength lies in its mathematical rigor combined with practical engineering considerations for real-world deployment.