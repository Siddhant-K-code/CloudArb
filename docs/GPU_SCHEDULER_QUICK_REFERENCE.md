# GPU Scheduler Quick Reference

## Core Algorithms & Formulas

### Optimization Objective Functions

#### 1. Cost Minimization
```
minimize: ∑(x_{i,p} × price_{i,p})
```
Where:
- `x_{i,p}` = number of instances of type i with pricing p
- `price_{i,p}` = cost per hour for instance i with pricing p

#### 2. Performance Maximization
```
maximize: ∑(x_{i,p} × performance_score_{i})
```

#### 3. Balanced Cost-Performance
```
minimize: ∑(x_{i,p} × (α × normalized_cost_{i,p} + β × normalized_performance_penalty_{i}))
```
Where:
- `α` = cost weight (default: 0.6)
- `β` = performance weight (default: 0.4)

### Constraint Formulations

#### Resource Constraints
```
∑(x_{i,p} × gpu_count_i) ≥ min_gpu_requirement     [GPU constraint]
∑(x_{i,p} × memory_i) ≥ min_memory_requirement     [Memory constraint]
∑(x_{i,p} × cpu_i) ≥ min_cpu_requirement           [CPU constraint]
```

#### Budget Constraint
```
∑(x_{i,p} × price_{i,p}) ≤ budget_limit
```

#### Risk Constraint
```
∑(x_{i,p} × risk_score_{i,p}) ≤ risk_tolerance
```

### Performance Scoring

#### Overall Performance Score
```
performance_score = w₁×compute_score + w₂×memory_score + w₃×network_score + w₄×efficiency_score
```

**Workload-specific weights:**
- Training: [0.4, 0.3, 0.2, 0.1]
- Inference: [0.3, 0.2, 0.4, 0.1]  
- Data Processing: [0.2, 0.4, 0.1, 0.3]

#### Compute Score
```
compute_score = min(100, (performance × gpu_count × scaling_factor) / baseline_performance × 100)
```

#### Memory Score
```
memory_score = capacity_score × 0.6 + bandwidth_score × 0.4
capacity_score = min(100, (total_gpu_memory / max_memory) × 100)
bandwidth_score = min(100, (total_bandwidth / max_bandwidth) × 100)
```

### Risk Assessment

#### Multi-factor Risk Score
```
risk_score = ∑(risk_factor_i × weight_i) / ∑(weight_i)
```

**Risk factor weights:**
- Spot interruption: 0.4
- Provider reliability: 0.2
- Region availability: 0.15
- Price volatility: 0.15
- Performance variance: 0.1

#### Spot Interruption Risk
```
spot_risk = min(1.0, base_risk × gpu_demand_multiplier)
```

#### Portfolio Risk (HHI-based)
```
concentration_risk = ∑(allocation_share_i²)
diversification_score = 1 - concentration_risk
```

### ML Forecasting Features

#### Time-based Features
```
features = [hour_of_day, day_of_week, month, is_weekend, is_holiday]
```

#### Price Trend Features
```
price_trend_Nh = (price_t - price_{t-N}) / price_{t-N}  [N ∈ {1,6,24}]
price_volatility_Nh = std(price_{t-N:t})
```

#### Market Indicators
```
spot_discount = (on_demand_price - spot_price) / on_demand_price
market_stress = std(spot_price_24h) / mean(spot_price_24h)
```

## Key Decision Points

### Instance Selection Priority
1. **Cost-Performance Ratio**: `performance_score / cost_per_hour`
2. **Risk-Adjusted Cost**: `cost × (1 + risk_score × risk_weight)`
3. **Availability Score**: Based on current capacity and historical availability

### Pricing Type Selection Logic
```python
if workload.fault_tolerance == "high" and spot_price < on_demand_price × 0.7:
    return SPOT
elif workload.duration > 8760:  # > 1 year
    return RESERVED_1Y
else:
    return ON_DEMAND
```

### Multi-Provider Distribution
- Maximum single provider: 60% of total allocation
- Minimum providers: 3 (if available)
- Regional distribution: Based on latency and availability requirements

## Performance Thresholds

### Solution Quality Metrics
```
solution_quality = 0.4×cost_efficiency + 0.4×performance_efficiency + 0.2×risk_efficiency

cost_efficiency = min(1.0, 50.0 / total_cost_per_hour)
performance_efficiency = total_performance_score / 100.0
risk_efficiency = 1.0 - total_risk_score
```

### Confidence Score Calculation
```
confidence = (optimality_factor + problem_size_factor + solve_time_factor + data_quality_factor) / 4

optimality_factor = 1.0 if optimal else 0.7
problem_size_factor = 1.0 if size < 100 else (0.9 if size < 500 else 0.8)
solve_time_factor = 1.0 if time < 5s else (0.9 if time < 15s else 0.8)
```

## Optimization Parameters

### Solver Configuration
- **Default Solver**: SCIP (fallback: CBC)
- **Timeout**: 30 seconds
- **Tolerance**: 1e-6
- **Max Iterations**: 10,000

### Risk Management
- **Default Risk Tolerance**: 0.1 (10%)
- **Spot Instance Limit**: 70% of total allocation
- **Provider Concentration Limit**: 60% of total cost

### Performance Benchmarks
- **Solve Time Target**: <30 seconds
- **API Response Time**: <200ms (95th percentile)
- **Pricing Data Freshness**: <2 minutes

## Common Optimization Patterns

### Cost-Optimized Pattern
```yaml
objective: minimize_cost
risk_tolerance: 0.3
spot_percentage: 60-80%
provider_diversification: medium
```

### Performance-Optimized Pattern
```yaml
objective: maximize_performance
risk_tolerance: 0.1
spot_percentage: 0-20%
provider_diversification: low
gpu_preference: h100 > a100 > v100
```

### Balanced Pattern
```yaml
objective: balance_cost_performance
risk_tolerance: 0.2
spot_percentage: 30-50%
provider_diversification: high
cost_weight: 0.6
performance_weight: 0.4
```

## Troubleshooting Quick Checks

### Infeasible Solutions
1. Check GPU availability: `available_gpus >= required_gpus`
2. Check budget constraints: `min_cost <= budget`
3. Check risk tolerance: `min_risk <= risk_tolerance`

### Poor Performance
1. Increase solver timeout: `timeout_seconds > 30`
2. Reduce problem size: Filter dominated instances
3. Use warm start: Initialize with heuristic solution

### High Risk Scores
1. Increase on-demand percentage
2. Improve provider diversification
3. Avoid high-demand GPU types in spot pricing

This quick reference provides the essential formulas and decision logic for understanding and troubleshooting CloudArb's GPU scheduler.