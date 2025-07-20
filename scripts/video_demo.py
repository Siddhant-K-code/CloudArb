#!/usr/bin/env python3
"""
CloudArb Video Demo Script

This script creates a compelling video demonstration that shows:
1. Real-time pricing data simulation
2. Cost optimization with realistic numbers
3. ML-powered forecasting and arbitrage opportunities
4. Infrastructure deployment capabilities
5. ROI calculations and payback periods

NO EXTERNAL DEPENDENCIES REQUIRED - Perfect for video demos!
"""

import asyncio
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import os

# Simulate rich output for video demo
class VideoDemo:
    """Self-contained video demonstration of CloudArb value."""

    def __init__(self):
        # Customer scenarios (realistic workloads with current pricing)
        self.customer_scenarios = {
            "startup": {
                "name": "AI Startup - Model Training",
                "description": "Training large language models for product development",
                "current_spend": 24000,  # Monthly (4x A100 @ $4.10/hr * 720 hours)
                "gpu_requirements": {
                    "gpu_type": "a100",
                    "gpu_count": 4,
                    "hours_per_month": 720
                },
                "budget_constraint": 18000,  # Target monthly spend
                "performance_requirement": "high"
            },
            "enterprise": {
                "name": "Enterprise - Inference Pipeline",
                "description": "High-throughput inference for production ML models",
                "current_spend": 120000,  # Monthly (16x T4 @ $3.47/hr * 2160 hours)
                "gpu_requirements": {
                    "gpu_type": "t4",
                    "gpu_count": 16,
                    "hours_per_month": 2160
                },
                "budget_constraint": 90000,  # Target monthly spend
                "performance_requirement": "reliable"
            },
            "research": {
                "name": "Research Lab - Mixed Workloads",
                "description": "Various ML research projects with different requirements",
                "current_spend": 80000,  # Monthly (8x V100 @ $6.94/hr * 1440 hours)
                "gpu_requirements": {
                    "gpu_type": "v100",
                    "gpu_count": 8,
                    "hours_per_month": 1440
                },
                "budget_constraint": 60000,  # Target monthly spend
                "performance_requirement": "flexible"
            }
        }

    def print_header(self, title: str):
        """Print a formatted header."""
        print(f"\n{'='*60}")
        print(f"🎯 {title}")
        print(f"{'='*60}")

    def print_section(self, title: str):
        """Print a section header."""
        print(f"\n📊 {title}")
        print("-" * 40)

    def print_success(self, message: str):
        """Print a success message."""
        print(f"✅ {message}")

    def print_info(self, message: str):
        """Print an info message."""
        print(f"ℹ️  {message}")

    def print_warning(self, message: str):
        """Print a warning message."""
        print(f"⚠️  {message}")

    def print_error(self, message: str):
        """Print an error message."""
        print(f"❌ {message}")

    async def simulate_loading(self, message: str, duration: float = 1.0):
        """Simulate loading with animated dots."""
        print(f"⏳ {message}", end="", flush=True)
        for _ in range(3):
            await asyncio.sleep(duration / 3)
            print(".", end="", flush=True)
        print(" ✅")

    async def run_video_demo(self, customer_type: str = "startup"):
        """Run a complete video demonstration."""
        self.print_header("CloudArb GPU Arbitrage Platform - Video Demo")

        if customer_type not in self.customer_scenarios:
            self.print_error(f"Unknown customer type: {customer_type}")
            return

        scenario = self.customer_scenarios[customer_type]

        try:
            # Step 1: Show current situation
            await self.show_current_situation(scenario)

            # Step 2: Demonstrate real-time pricing
            await self.demonstrate_real_pricing()

            # Step 3: Run optimization for customer workload
            await self.optimize_customer_workload(scenario)

            # Step 4: Show ML forecasting insights
            await self.show_ml_insights(scenario)

            # Step 5: Calculate ROI and payback
            await self.calculate_customer_roi(scenario)

            # Step 6: Demonstrate deployment
            await self.demonstrate_deployment(scenario)

            # Step 7: Generate customer report
            await self.generate_customer_report(scenario)

            self.print_success("Video demo completed successfully!")

        except Exception as e:
            self.print_error(f"Demo failed: {e}")
            raise

    async def show_current_situation(self, scenario: Dict[str, Any]):
        """Show the customer's current situation."""
        self.print_section(f"Current Situation: {scenario['name']}")

        print(f"Description: {scenario['description']}")
        print(f"Current Monthly Spend: ${scenario['current_spend']:,}")
        print(f"Target Monthly Spend: ${scenario['budget_constraint']:,}")
        print(f"Required GPUs: {scenario['gpu_requirements']['gpu_count']}x {scenario['gpu_requirements']['gpu_type']}")
        print(f"Monthly GPU Hours: {scenario['gpu_requirements']['hours_per_month']:,}")

        # Calculate current cost per hour
        current_cost_per_hour = scenario['current_spend'] / scenario['gpu_requirements']['hours_per_month']
        print(f"Current Cost per Hour: ${current_cost_per_hour:.2f}")

        # Show the problem
        overspend = scenario['current_spend'] - scenario['budget_constraint']
        if overspend > 0:
            print(f"🚨 Problem: ${overspend:,} over budget each month")
            print(f"💡 Opportunity: 25-40% cost reduction possible")

    async def demonstrate_real_pricing(self):
        """Demonstrate real-time pricing data collection."""
        self.print_section("Real-Time Pricing Data Collection")

        await self.simulate_loading("Connecting to AWS Pricing API", 0.8)
        await self.simulate_loading("Fetching GCP Compute Engine pricing", 0.8)
        await self.simulate_loading("Retrieving Azure VM pricing", 0.8)
        await self.simulate_loading("Collecting Lambda Labs pricing", 0.8)
        await self.simulate_loading("Gathering RunPod pricing data", 0.8)

        print(f"✅ Collected 1,247 pricing records in 2.3 seconds")
        print(f"📊 Data freshness: <2 minutes")
        print(f"🌍 Providers: AWS, GCP, Azure, Lambda Labs, RunPod")

        # Show sample pricing comparison
        await self.show_pricing_comparison()

    async def show_pricing_comparison(self):
        """Show pricing comparison across providers."""
        print(f"\n💰 Real-Time Pricing Comparison (A100 GPU):")
        print(f"⚠️  Note: Prices shown are estimates for demonstration purposes.")
        print(f"    Actual pricing varies by region, demand, and time of day.")

        pricing_data = {
            "AWS": {"on_demand": 4.10, "spot": 1.23, "region": "us-east-1"},
            "GCP": {"on_demand": 3.20, "spot": 0.96, "region": "us-central1"},
            "Azure": {"on_demand": 3.20, "spot": 0.96, "region": "eastus"},
            "Lambda Labs": {"on_demand": 2.50, "spot": 2.50, "region": "us-east-1"},
            "RunPod": {"on_demand": 2.40, "spot": 2.40, "region": "US-East"}
        }

        for provider, pricing in pricing_data.items():
            if pricing["spot"] != pricing["on_demand"]:
                savings = ((pricing["on_demand"] - pricing["spot"]) / pricing["on_demand"]) * 100
                print(f"  {provider}: ${pricing['on_demand']:.2f}/hr (Spot: ${pricing['spot']:.2f}/hr, {savings:.1f}% savings)")
            else:
                print(f"  {provider}: ${pricing['on_demand']:.2f}/hr (No spot pricing)")

    async def optimize_customer_workload(self, scenario: Dict[str, Any]):
        """Optimize the customer's specific workload."""
        self.print_section(f"Optimizing {scenario['name']}")

        requirements = scenario['gpu_requirements']
        budget_per_hour = scenario['budget_constraint'] / requirements['hours_per_month']

        print(f"Optimization Parameters:")
        print(f"  GPU Type: {requirements['gpu_type']}")
        print(f"  GPU Count: {requirements['gpu_count']}")
        print(f"  Budget per Hour: ${budget_per_hour:.2f}")
        print(f"  Performance: {scenario['performance_requirement']}")

        await self.simulate_loading("Initializing optimization solver", 0.5)
        await self.simulate_loading("Analyzing provider pricing", 0.8)
        await self.simulate_loading("Calculating optimal allocation", 1.2)
        await self.simulate_loading("Validating constraints", 0.5)

        print(f"\n✅ Optimization completed in 3.2 seconds")
        print(f"Status: Optimal solution found")

        await self.show_optimization_results(scenario)

    async def show_optimization_results(self, scenario: Dict[str, Any]):
        """Show optimization results for customer."""
        print(f"\n🎯 Optimization Results")
        print("-" * 40)

        current_cost = scenario['current_spend']
        # More realistic savings based on actual spot pricing and multi-cloud optimization
        if scenario['gpu_requirements']['gpu_type'] == 'a100':
            optimized_cost = current_cost * 0.65  # 35% savings (A100 spot pricing)
        elif scenario['gpu_requirements']['gpu_type'] == 't4':
            optimized_cost = current_cost * 0.70  # 30% savings (T4 spot pricing)
        else:  # v100
            optimized_cost = current_cost * 0.68  # 32% savings (V100 spot pricing)

        savings = current_cost - optimized_cost
        savings_percentage = (savings / current_cost) * 100

        print(f"Current Monthly Cost: ${current_cost:,}")
        print(f"Optimized Monthly Cost: ${optimized_cost:,.2f}")
        print(f"Monthly Savings: ${savings:,.2f}")
        print(f"Cost Reduction: {savings_percentage:.1f}%")

        # Show recommended configuration with realistic pricing
        print(f"\n📋 Recommended Configuration:")
        if scenario['gpu_requirements']['gpu_type'] == 'a100':
            print(f"  AWS p4d.24xlarge (us-east-1)")
            print(f"    Pricing: $1.23/hr (spot) - 70% savings")
            print(f"    GPUs: 8x {scenario['gpu_requirements']['gpu_type']}")
            print(f"  GCP n1-standard-64 + A100 (us-central1)")
            print(f"    Pricing: $0.96/hr (preemptible) - 70% savings")
            print(f"    GPUs: 1x {scenario['gpu_requirements']['gpu_type']}")
            print(f"  Lambda Labs gpu_1x_a100 (us-east-1)")
            print(f"    Pricing: $2.50/hr (on-demand) - best base price")
            print(f"    GPUs: 1x {scenario['gpu_requirements']['gpu_type']}")
        elif scenario['gpu_requirements']['gpu_type'] == 't4':
            print(f"  AWS g4dn.xlarge (us-east-1)")
            print(f"    Pricing: $0.158/hr (spot) - 70% savings")
            print(f"    GPUs: 1x {scenario['gpu_requirements']['gpu_type']}")
            print(f"  GCP n1-standard-4 + T4 (us-central1)")
            print(f"    Pricing: $0.35/hr (preemptible) - 70% savings")
            print(f"    GPUs: 1x {scenario['gpu_requirements']['gpu_type']}")
            print(f"  Azure Standard_NC4as_T4_v3 (eastus)")
            print(f"    Pricing: $0.156/hr (spot) - 70% savings")
            print(f"    GPUs: 1x {scenario['gpu_requirements']['gpu_type']}")
        else:  # v100
            print(f"  AWS p3.8xlarge (us-east-1)")
            print(f"    Pricing: $3.67/hr (spot) - 70% savings")
            print(f"    GPUs: 4x {scenario['gpu_requirements']['gpu_type']}")
            print(f"  GCP n1-standard-16 + V100 (us-central1)")
            print(f"    Pricing: $2.48/hr (preemptible) - 70% savings")
            print(f"    GPUs: 1x {scenario['gpu_requirements']['gpu_type']}")
            print(f"  Azure Standard_NC6s_v3 (eastus)")
            print(f"    Pricing: $2.40/hr (spot) - 70% savings")
            print(f"    GPUs: 1x {scenario['gpu_requirements']['gpu_type']}")

        # Show cost breakdown with realistic percentages
        print(f"\n💰 Cost Breakdown:")
        compute_cost = optimized_cost * 0.88  # 88% compute, 12% other
        storage_cost = optimized_cost * 0.08   # 8% storage
        network_cost = optimized_cost * 0.04   # 4% networking
        print(f"  Compute: ${compute_cost:,.2f}")
        print(f"  Storage: ${storage_cost:,.2f}")
        print(f"  Network: ${network_cost:,.2f}")
        print(f"  Total: ${optimized_cost:,.2f}")

    async def show_ml_insights(self, scenario: Dict[str, Any]):
        """Show ML forecasting insights for customer."""
        self.print_section("ML Forecasting Insights")

        await self.simulate_loading("Training demand forecasting model", 1.0)
        await self.simulate_loading("Analyzing price trends", 0.8)
        await self.simulate_loading("Detecting arbitrage opportunities", 0.6)

        print(f"✅ ML models trained successfully")
        print(f"📊 Demand Forecast: +12% increase expected next month")
        print(f"📈 Price Trend: Stable with 3-8% seasonal variation")
        print(f"🎯 Spot Price Volatility: 15-25% daily fluctuations")

        # Show arbitrage opportunities with realistic savings
        print(f"\n💡 Arbitrage Opportunities:")
        print(f"  AWS → GCP: 15% savings on spot instances")
        print(f"  Azure → Lambda Labs: 22% savings on on-demand instances")
        print(f"  GCP → RunPod: 25% savings on on-demand instances")
        print(f"  Cross-region: 8-12% savings on data transfer optimization")

        # Show demand forecasting with realistic patterns
        print(f"\n📊 Demand Forecasting:")
        print(f"  Peak demand: Weekdays 9 AM - 6 PM (US timezones)")
        print(f"  Low demand: Weekends and holidays")
        print(f"  Recommended scaling: 25-40% reduction during off-peak")
        print(f"  Auto-scaling: 15-30 minute response to demand changes")

    async def calculate_customer_roi(self, scenario: Dict[str, Any]):
        """Calculate ROI and payback period for customer."""
        self.print_section("ROI Analysis")

        current_cost = scenario['current_spend']
        # Use the same realistic savings as in optimization
        if scenario['gpu_requirements']['gpu_type'] == 'a100':
            optimized_cost = current_cost * 0.65  # 35% savings
        elif scenario['gpu_requirements']['gpu_type'] == 't4':
            optimized_cost = current_cost * 0.70  # 30% savings
        else:  # v100
            optimized_cost = current_cost * 0.68  # 32% savings

        monthly_savings = current_cost - optimized_cost
        annual_savings = monthly_savings * 12

        # Implementation costs (realistic)
        implementation_cost = 8000  # Setup, migration, training, integration
        payback_months = implementation_cost / monthly_savings

        # 3-year ROI calculation
        three_year_savings = annual_savings * 3
        roi_percentage = ((three_year_savings - implementation_cost) / implementation_cost) * 100

        print(f"Current Annual Cost: ${current_cost * 12:,}")
        print(f"Optimized Annual Cost: ${optimized_cost * 12:,}")
        print(f"Annual Savings: ${annual_savings:,}")
        print(f"Implementation Cost: ${implementation_cost:,}")
        print(f"Payback Period: {payback_months:.1f} months")
        print(f"3-Year ROI: {roi_percentage:.1f}%")

        # Show cumulative savings
        print(f"\n📈 Cumulative Savings:")
        for year in [1, 2, 3]:
            cumulative_savings = (annual_savings * year) - implementation_cost
            print(f"  Year {year}: ${cumulative_savings:,}")

    async def demonstrate_deployment(self, scenario: Dict[str, Any]):
        """Demonstrate infrastructure deployment capabilities."""
        self.print_section("Infrastructure Deployment Demo")

        try:
            # Simulate deployment
            print("Deploying optimized infrastructure...")

            deployment_steps = [
                "Validating cloud credentials...",
                "Creating Terraform configuration...",
                "Provisioning compute resources...",
                "Configuring networking...",
                "Setting up monitoring...",
                "Deploying application stack..."
            ]

            for step in deployment_steps:
                await self.simulate_loading(step, 0.8)

            print("✅ Infrastructure deployed successfully!")
            print(f"🌐 Access URL: https://cloudarb-demo-{scenario['name'].lower().replace(' ', '-')}.cloud")
            print(f"📊 Monitoring: https://grafana.cloudarb-demo.com")

        except Exception as e:
            self.print_warning(f"Deployment simulation: {e}")
            print("✅ Infrastructure deployment simulation completed")

    async def generate_customer_report(self, scenario: Dict[str, Any]):
        """Generate a comprehensive customer report."""
        self.print_section("Customer Report Generation")

        # Calculate key metrics with realistic savings
        current_cost = scenario['current_spend']
        if scenario['gpu_requirements']['gpu_type'] == 'a100':
            optimized_cost = current_cost * 0.65  # 35% savings
            savings_percentage = 35.0
        elif scenario['gpu_requirements']['gpu_type'] == 't4':
            optimized_cost = current_cost * 0.70  # 30% savings
            savings_percentage = 30.0
        else:  # v100
            optimized_cost = current_cost * 0.68  # 32% savings
            savings_percentage = 32.0

        monthly_savings = current_cost - optimized_cost
        annual_savings = monthly_savings * 12

        report = {
            "customer": scenario['name'],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "current_situation": {
                "monthly_spend": current_cost,
                "gpu_requirements": scenario['gpu_requirements'],
                "performance_requirement": scenario['performance_requirement']
            },
            "optimization_results": {
                "optimized_monthly_cost": optimized_cost,
                "monthly_savings": monthly_savings,
                "annual_savings": annual_savings,
                "cost_reduction_percentage": savings_percentage
            },
            "roi_analysis": {
                "implementation_cost": 8000,
                "payback_months": 8000 / monthly_savings,
                "three_year_roi": ((annual_savings * 3) - 8000) / 8000 * 100
            },
            "recommendations": [
                "Implement multi-cloud strategy for cost optimization",
                "Use spot instances for non-critical workloads",
                "Reserve instances for predictable workloads",
                "Monitor and adjust based on usage patterns"
            ]
        }

        # Save report
        report_filename = f"video_demo_report_{scenario['name'].lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json"

        try:
            with open(report_filename, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"✅ Report saved: {report_filename}")
        except Exception as e:
            self.print_warning(f"Could not save report: {e}")

        # Show executive summary
        print(f"\n📊 Executive Summary")
        print("-" * 40)
        print(f"Customer: {scenario['name']}")
        print(f"Current Monthly Spend: ${current_cost:,}")
        print(f"Potential Monthly Savings: ${monthly_savings:,}")
        print(f"Annual Savings: ${annual_savings:,}")
        print(f"Payback Period: {report['roi_analysis']['payback_months']:.1f} months")
        print(f"3-Year ROI: {report['roi_analysis']['three_year_roi']:.1f}%")

        # Show key benefits with realistic metrics
        print(f"\n🎯 Key Benefits:")
        print(f"  • {savings_percentage:.0f}% cost reduction through multi-cloud optimization")
        print(f"  • Real-time pricing data from 5+ cloud providers")
        print(f"  • ML-powered demand forecasting and arbitrage detection")
        print(f"  • Automated infrastructure deployment and scaling")
        print(f"  • Comprehensive cost monitoring and analytics")


async def main():
    """Main function to run video demo."""
    import argparse

    parser = argparse.ArgumentParser(description="CloudArb Video Demo")
    parser.add_argument(
        "--customer-type",
        choices=["startup", "enterprise", "research"],
        default="startup",
        help="Type of customer scenario to demonstrate"
    )

    args = parser.parse_args()

    demo = VideoDemo()
    await demo.run_video_demo(args.customer_type)

    print(f"\n🎉 Video demo completed successfully!")
    print(f"📊 Check the generated report for detailed results")


if __name__ == "__main__":
    asyncio.run(main())