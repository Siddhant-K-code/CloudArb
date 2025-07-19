"""
Performance analyzer component for GPU optimization.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

from .models import InstanceOption, PricingType

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for GPU instances."""

    gpu_utilization: float  # 0-100%
    memory_utilization: float  # 0-100%
    throughput_score: float  # 0-100
    latency_ms: float
    power_efficiency: float  # Performance per watt
    thermal_score: float  # 0-100, higher is better


@dataclass
class BenchmarkResult:
    """Benchmark result for a specific workload."""

    workload_name: str
    instance_type: str
    gpu_type: str
    provider: str
    benchmark_score: float  # 0-100
    execution_time_seconds: float
    throughput: float  # Operations per second
    memory_usage_gb: float
    power_consumption_watts: float
    cost_performance_ratio: float


class PerformanceAnalyzer:
    """Performance analysis and benchmarking for GPU instances."""

    def __init__(self):
        """Initialize performance analyzer."""
        # GPU performance benchmarks (normalized scores)
        self.gpu_benchmarks = {
            "v100": {
                "fp32_performance": 112,  # TFLOPS
                "fp16_performance": 224,  # TFLOPS
                "memory_bandwidth": 900,  # GB/s
                "memory_size": 32,  # GB
                "power_consumption": 300,  # Watts
            },
            "a100": {
                "fp32_performance": 312,  # TFLOPS
                "fp16_performance": 624,  # TFLOPS
                "memory_bandwidth": 1555,  # GB/s
                "memory_size": 80,  # GB
                "power_consumption": 400,  # Watts
            },
            "h100": {
                "fp32_performance": 989,  # TFLOPS
                "fp16_performance": 1979,  # TFLOPS
                "memory_bandwidth": 3350,  # GB/s
                "memory_size": 80,  # GB
                "power_consumption": 700,  # Watts
            },
            "rtx4090": {
                "fp32_performance": 83,  # TFLOPS
                "fp16_performance": 166,  # TFLOPS
                "memory_bandwidth": 1008,  # GB/s
                "memory_size": 24,  # GB
                "power_consumption": 450,  # Watts
            },
            "rtx3090": {
                "fp32_performance": 36,  # TFLOPS
                "fp16_performance": 72,  # TFLOPS
                "memory_bandwidth": 936,  # GB/s
                "memory_size": 24,  # GB
                "power_consumption": 350,  # Watts
            },
        }

        # Workload-specific performance characteristics
        self.workload_characteristics = {
            "training": {
                "fp16_heavy": True,
                "memory_intensive": True,
                "network_bound": False,
                "io_bound": False,
            },
            "inference": {
                "fp16_heavy": False,
                "memory_intensive": False,
                "network_bound": True,
                "io_bound": False,
            },
            "data_processing": {
                "fp16_heavy": False,
                "memory_intensive": True,
                "network_bound": False,
                "io_bound": True,
            },
        }

    def calculate_performance_score(self, instance: InstanceOption, workload_type: str = "training") -> float:
        """
        Calculate overall performance score for an instance.

        Args:
            instance: Instance option
            workload_type: Type of workload (training, inference, data_processing)

        Returns:
            float: Performance score (0-100)
        """
        if not instance.gpu_type or instance.gpu_count == 0:
            return 0.0

        # Get GPU benchmarks
        gpu_specs = self.gpu_benchmarks.get(instance.gpu_type)
        if not gpu_specs:
            return 50.0  # Default score for unknown GPU types

        # Get workload characteristics
        workload_specs = self.workload_characteristics.get(workload_type, self.workload_characteristics["training"])

        # Calculate component scores
        compute_score = self._calculate_compute_score(gpu_specs, workload_specs, instance.gpu_count)
        memory_score = self._calculate_memory_score(gpu_specs, workload_specs, instance)
        network_score = self._calculate_network_score(instance, workload_specs)
        efficiency_score = self._calculate_efficiency_score(gpu_specs, instance)

        # Weight scores based on workload type
        if workload_type == "training":
            weights = {"compute": 0.4, "memory": 0.3, "network": 0.2, "efficiency": 0.1}
        elif workload_type == "inference":
            weights = {"compute": 0.3, "memory": 0.2, "network": 0.4, "efficiency": 0.1}
        else:  # data_processing
            weights = {"compute": 0.2, "memory": 0.4, "network": 0.1, "efficiency": 0.3}

        # Calculate weighted average
        total_score = (
            compute_score * weights["compute"] +
            memory_score * weights["memory"] +
            network_score * weights["network"] +
            efficiency_score * weights["efficiency"]
        )

        return min(100.0, max(0.0, total_score))

    def _calculate_compute_score(self, gpu_specs: Dict[str, float], workload_specs: Dict[str, bool], gpu_count: int) -> float:
        """Calculate compute performance score."""
        if workload_specs.get("fp16_heavy", False):
            performance = gpu_specs.get("fp16_performance", 0)
        else:
            performance = gpu_specs.get("fp32_performance", 0)

        # Normalize to 100 (using H100 as reference)
        max_performance = self.gpu_benchmarks["h100"]["fp32_performance"]
        normalized_performance = (performance * gpu_count) / max_performance

        return min(100.0, normalized_performance * 100)

    def _calculate_memory_score(self, gpu_specs: Dict[str, float], workload_specs: Dict[str, bool], instance: InstanceOption) -> float:
        """Calculate memory performance score."""
        if not workload_specs.get("memory_intensive", False):
            return 80.0  # Good baseline for non-memory-intensive workloads

        # Consider memory size and bandwidth
        memory_size = gpu_specs.get("memory_size", 0) * instance.gpu_count
        memory_bandwidth = gpu_specs.get("memory_bandwidth", 0) * instance.gpu_count

        # Normalize memory size (using H100 as reference)
        max_memory = self.gpu_benchmarks["h100"]["memory_size"] * instance.gpu_count
        memory_size_score = min(100.0, (memory_size / max_memory) * 100)

        # Normalize memory bandwidth
        max_bandwidth = self.gpu_benchmarks["h100"]["memory_bandwidth"] * instance.gpu_count
        bandwidth_score = min(100.0, (memory_bandwidth / max_bandwidth) * 100)

        # Weighted average
        return (memory_size_score * 0.6 + bandwidth_score * 0.4)

    def _calculate_network_score(self, instance: InstanceOption, workload_specs: Dict[str, bool]) -> float:
        """Calculate network performance score."""
        if not workload_specs.get("network_bound", False):
            return 80.0  # Good baseline for non-network-bound workloads

        # Use network bandwidth if available
        if instance.network_bandwidth_gbps:
            # Normalize to 100 (assuming 100 Gbps is excellent)
            return min(100.0, (instance.network_bandwidth_gbps / 100.0) * 100)

        # Estimate based on provider and instance type
        provider_network_scores = {
            "AWS": 85,
            "GCP": 80,
            "Azure": 75,
            "Lambda Labs": 70,
            "RunPod": 65,
        }

        return provider_network_scores.get(instance.provider_name, 70)

    def _calculate_efficiency_score(self, gpu_specs: Dict[str, float], instance: InstanceOption) -> float:
        """Calculate power efficiency score."""
        power_consumption = gpu_specs.get("power_consumption", 300) * instance.gpu_count

        # Calculate performance per watt
        fp32_performance = gpu_specs.get("fp32_performance", 0) * instance.gpu_count
        performance_per_watt = fp32_performance / power_consumption if power_consumption > 0 else 0

        # Normalize to 100 (using H100 as reference)
        max_efficiency = self.gpu_benchmarks["h100"]["fp32_performance"] / self.gpu_benchmarks["h100"]["power_consumption"]
        efficiency_score = min(100.0, (performance_per_watt / max_efficiency) * 100)

        return efficiency_score

    def compare_performance(self, instances: List[InstanceOption], workload_type: str = "training") -> Dict[str, Any]:
        """
        Compare performance across multiple instances.

        Args:
            instances: List of instances to compare
            workload_type: Type of workload

        Returns:
            Dict containing performance comparison results
        """
        if not instances:
            return {"error": "No instances provided"}

        comparisons = []
        performance_scores = []

        for instance in instances:
            score = self.calculate_performance_score(instance, workload_type)

            comparison = {
                "provider": instance.provider_name,
                "instance_type": instance.instance_name,
                "gpu_type": instance.gpu_type,
                "gpu_count": instance.gpu_count,
                "region": instance.region,
                "performance_score": score,
                "compute_score": self._calculate_compute_score(
                    self.gpu_benchmarks.get(instance.gpu_type, {}),
                    self.workload_characteristics.get(workload_type, {}),
                    instance.gpu_count
                ),
                "memory_score": self._calculate_memory_score(
                    self.gpu_benchmarks.get(instance.gpu_type, {}),
                    self.workload_characteristics.get(workload_type, {}),
                    instance
                ),
                "network_score": self._calculate_network_score(
                    instance,
                    self.workload_characteristics.get(workload_type, {})
                ),
                "efficiency_score": self._calculate_efficiency_score(
                    self.gpu_benchmarks.get(instance.gpu_type, {}),
                    instance
                ),
            }

            comparisons.append(comparison)
            performance_scores.append(score)

        # Find best and worst performers
        best_idx = np.argmax(performance_scores)
        worst_idx = np.argmin(performance_scores)

        return {
            "comparisons": comparisons,
            "best_performer": comparisons[best_idx],
            "worst_performer": comparisons[worst_idx],
            "performance_range": {
                "min": min(performance_scores),
                "max": max(performance_scores),
                "mean": np.mean(performance_scores),
                "std": np.std(performance_scores),
            },
            "recommendations": self._get_performance_recommendations(comparisons, workload_type)
        }

    def _get_performance_recommendations(self, comparisons: List[Dict[str, Any]], workload_type: str) -> List[str]:
        """Get performance optimization recommendations."""
        recommendations = []

        # Find performance differences
        scores = [comp["performance_score"] for comp in comparisons]
        max_score = max(scores)
        min_score = min(scores)

        if max_score > min_score * 1.3:
            recommendations.append(f"Performance varies significantly ({min_score:.1f} - {max_score:.1f}). Consider higher-performing options.")

        # Workload-specific recommendations
        if workload_type == "training":
            # Find best compute performers
            compute_scores = [comp["compute_score"] for comp in comparisons]
            best_compute_idx = np.argmax(compute_scores)
            best_compute = comparisons[best_compute_idx]
            recommendations.append(f"Best compute performance: {best_compute['provider']} {best_compute['instance_type']}")

            # Check memory scores
            memory_scores = [comp["memory_score"] for comp in comparisons]
            if any(score < 60 for score in memory_scores):
                recommendations.append("Some instances have low memory scores. Consider instances with more GPU memory.")

        elif workload_type == "inference":
            # Find best network performers
            network_scores = [comp["network_score"] for comp in comparisons]
            best_network_idx = np.argmax(network_scores)
            best_network = comparisons[best_network_idx]
            recommendations.append(f"Best network performance: {best_network['provider']} {best_network['instance_type']}")

        # Efficiency recommendations
        efficiency_scores = [comp["efficiency_score"] for comp in comparisons]
        best_efficiency_idx = np.argmax(efficiency_scores)
        best_efficiency = comparisons[best_efficiency_idx]
        recommendations.append(f"Most power efficient: {best_efficiency['provider']} {best_efficiency['instance_type']}")

        return recommendations

    def estimate_workload_performance(self, instance: InstanceOption, workload_type: str,
                                    workload_size: str = "medium") -> Dict[str, Any]:
        """
        Estimate performance for a specific workload.

        Args:
            instance: Instance option
            workload_type: Type of workload
            workload_size: Size of workload (small, medium, large)

        Returns:
            Dict containing performance estimates
        """
        base_score = self.calculate_performance_score(instance, workload_type)

        # Workload size multipliers
        size_multipliers = {
            "small": 1.0,
            "medium": 0.9,
            "large": 0.8,
        }

        adjusted_score = base_score * size_multipliers.get(workload_size, 0.9)

        # Estimate execution time (relative to a baseline)
        baseline_time = {
            "training": {"small": 3600, "medium": 7200, "large": 14400},  # seconds
            "inference": {"small": 60, "medium": 300, "large": 900},
            "data_processing": {"small": 1800, "medium": 3600, "large": 7200},
        }

        base_time = baseline_time.get(workload_type, {}).get(workload_size, 3600)
        estimated_time = base_time * (100 / adjusted_score) if adjusted_score > 0 else float('inf')

        return {
            "performance_score": adjusted_score,
            "estimated_execution_time_seconds": estimated_time,
            "estimated_execution_time_hours": estimated_time / 3600,
            "throughput_estimate": adjusted_score / 100,  # Normalized throughput
            "recommendations": self._get_workload_recommendations(instance, workload_type, adjusted_score)
        }

    def _get_workload_recommendations(self, instance: InstanceOption, workload_type: str, performance_score: float) -> List[str]:
        """Get workload-specific recommendations."""
        recommendations = []

        if performance_score < 50:
            recommendations.append("Low performance score. Consider upgrading to a more powerful GPU.")

        if workload_type == "training" and instance.gpu_count < 2:
            recommendations.append("Training workloads benefit from multiple GPUs. Consider multi-GPU instances.")

        if workload_type == "inference" and instance.network_bandwidth_gbps and instance.network_bandwidth_gbps < 10:
            recommendations.append("Inference workloads benefit from high network bandwidth. Consider instances with faster networking.")

        gpu_specs = self.gpu_benchmarks.get(instance.gpu_type, {})
        if workload_type == "training" and gpu_specs.get("memory_size", 0) < 32:
            recommendations.append("Training workloads benefit from more GPU memory. Consider instances with larger GPU memory.")

        return recommendations

    def get_performance_benchmarks(self, gpu_type: str) -> Dict[str, float]:
        """
        Get performance benchmarks for a specific GPU type.

        Args:
            gpu_type: GPU type (v100, a100, h100, etc.)

        Returns:
            Dict containing benchmark data
        """
        return self.gpu_benchmarks.get(gpu_type, {})

    def calculate_performance_cost_ratio(self, instance: InstanceOption, cost_per_hour: float,
                                       workload_type: str = "training") -> float:
        """
        Calculate performance-cost ratio (higher is better).

        Args:
            instance: Instance option
            cost_per_hour: Cost per hour
            workload_type: Type of workload

        Returns:
            float: Performance-cost ratio
        """
        if cost_per_hour <= 0:
            return 0.0

        performance_score = self.calculate_performance_score(instance, workload_type)
        return performance_score / cost_per_hour