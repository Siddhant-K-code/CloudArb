import React, { useState, useEffect } from 'react';
import { useQuery } from 'react-query';
import { Helmet } from 'react-helmet-async';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Cpu,
  Zap,
  Activity,
  Clock,
  Users,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import toast from 'react-hot-toast';

import { analyticsAPI, workloadsAPI, optimizationAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const Dashboard = () => {
  const { user } = useAuth();
  const [timeRange, setTimeRange] = useState('7d');

  // Fetch dashboard data
  const { data: costAnalysis, isLoading: costLoading } = useQuery(
    ['cost-analysis', timeRange],
    () => analyticsAPI.getCostAnalysis({ days: timeRange === '7d' ? 7 : 30 }),
    { refetchInterval: 300000 } // Refetch every 5 minutes
  );

  const { data: savingsSummary, isLoading: savingsLoading } = useQuery(
    ['savings-summary', timeRange],
    () => analyticsAPI.getSavingsSummary({ period_days: timeRange === '7d' ? 7 : 30 }),
    { refetchInterval: 300000 }
  );

  const { data: workloads, isLoading: workloadsLoading } = useQuery(
    ['workloads', 'dashboard'],
    () => workloadsAPI.getWorkloads({ limit: 5 }),
    { refetchInterval: 60000 } // Refetch every minute
  );

  const { data: optimizations, isLoading: optimizationsLoading } = useQuery(
    ['optimizations', 'dashboard'],
    () => optimizationAPI.getOptimizations({ limit: 5 }),
    { refetchInterval: 60000 }
  );

  const { data: marketStats, isLoading: marketLoading } = useQuery(
    ['market-stats'],
    () => analyticsAPI.getMarketAnalysis(),
    { refetchInterval: 300000 }
  );

  // Calculate metrics
  const totalCost = costAnalysis?.total_cost || 0;
  const totalSavings = savingsSummary?.total_savings || 0;
  const savingsPercentage = savingsSummary?.savings_percentage || 0;
  const activeWorkloads = workloads?.filter(w => w.status === 'running').length || 0;
  const pendingWorkloads = workloads?.filter(w => w.status === 'pending').length || 0;

  // Cost trend data for chart
  const costTrendData = costAnalysis?.cost_trend?.map(item => ({
    date: new Date(item.date).toLocaleDateString(),
    cost: item.cost,
  })) || [];

  // Cost breakdown data for pie chart
  const costBreakdownData = costAnalysis?.cost_breakdown ?
    Object.entries(costAnalysis.cost_breakdown).map(([provider, cost]) => ({
      name: provider,
      value: cost,
    })) : [];

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  // Quick action handlers
  const handleQuickOptimize = () => {
    toast.success('Quick optimization started!');
    // Navigate to optimization page
  };

  const handleCreateWorkload = () => {
    toast.success('Redirecting to workload creation...');
    // Navigate to workload creation
  };

  const handleViewAnalytics = () => {
    toast.success('Opening detailed analytics...');
    // Navigate to analytics page
  };

  return (
    <>
      <Helmet>
        <title>Dashboard - CloudArb</title>
        <meta name="description" content="CloudArb GPU Arbitrage Dashboard" />
      </Helmet>

      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">
              Welcome back, {user?.first_name || user?.email}!
            </h1>
            <p className="mt-2 text-gray-600">
              Here's what's happening with your GPU workloads and cost optimization.
            </p>
          </div>

          {/* Time Range Selector */}
          <div className="mb-6">
            <div className="flex space-x-2">
              <button
                onClick={() => setTimeRange('7d')}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${
                  timeRange === '7d'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                Last 7 days
              </button>
              <button
                onClick={() => setTimeRange('30d')}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${
                  timeRange === '30d'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                Last 30 days
              </button>
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {/* Total Cost */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <DollarSign className="h-8 w-8 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Cost</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${totalCost.toFixed(2)}
                  </p>
                </div>
              </div>
              <div className="mt-4 flex items-center">
                <TrendingUp className="h-4 w-4 text-green-500" />
                <span className="ml-1 text-sm text-green-600">+12.5%</span>
                <span className="ml-2 text-sm text-gray-500">vs last period</span>
              </div>
            </div>

            {/* Total Savings */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <TrendingDown className="h-8 w-8 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Savings</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${totalSavings.toFixed(2)}
                  </p>
                </div>
              </div>
              <div className="mt-4 flex items-center">
                <ArrowUpRight className="h-4 w-4 text-blue-500" />
                <span className="ml-1 text-sm text-blue-600">{savingsPercentage.toFixed(1)}%</span>
                <span className="ml-2 text-sm text-gray-500">savings rate</span>
              </div>
            </div>

            {/* Active Workloads */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Cpu className="h-8 w-8 text-purple-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Active Workloads</p>
                  <p className="text-2xl font-bold text-gray-900">{activeWorkloads}</p>
                </div>
              </div>
              <div className="mt-4 flex items-center">
                <Activity className="h-4 w-4 text-purple-500" />
                <span className="ml-1 text-sm text-purple-600">{pendingWorkloads}</span>
                <span className="ml-2 text-sm text-gray-500">pending</span>
              </div>
            </div>

            {/* Optimization Runs */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Zap className="h-8 w-8 text-yellow-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Optimizations</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {optimizations?.length || 0}
                  </p>
                </div>
              </div>
              <div className="mt-4 flex items-center">
                <Clock className="h-4 w-4 text-yellow-500" />
                <span className="ml-1 text-sm text-yellow-600">Last 24h</span>
              </div>
            </div>
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            {/* Cost Trend Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost Trend</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={costTrendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip formatter={(value) => [`$${value}`, 'Cost']} />
                  <Line
                    type="monotone"
                    dataKey="cost"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Cost Breakdown Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost by Provider</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={costBreakdownData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {costBreakdownData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`$${value}`, 'Cost']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                onClick={handleQuickOptimize}
                className="flex items-center justify-center px-4 py-3 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <Zap className="h-5 w-5 mr-2" />
                Quick Optimize
              </button>
              <button
                onClick={handleCreateWorkload}
                className="flex items-center justify-center px-4 py-3 border border-transparent text-sm font-medium rounded-lg text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
              >
                <Cpu className="h-5 w-5 mr-2" />
                Create Workload
              </button>
              <button
                onClick={handleViewAnalytics}
                className="flex items-center justify-center px-4 py-3 border border-transparent text-sm font-medium rounded-lg text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
              >
                <BarChart3 className="h-5 w-5 mr-2" />
                View Analytics
              </button>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Recent Workloads */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Workloads</h3>
              {workloadsLoading ? (
                <div className="animate-pulse space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-16 bg-gray-200 rounded"></div>
                  ))}
                </div>
              ) : workloads?.length > 0 ? (
                <div className="space-y-3">
                  {workloads.slice(0, 5).map((workload) => (
                    <div key={workload.id} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">{workload.name}</p>
                        <p className="text-sm text-gray-500">{workload.workload_type}</p>
                      </div>
                      <div className="text-right">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          workload.status === 'running' ? 'bg-green-100 text-green-800' :
                          workload.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {workload.status}
                        </span>
                        <p className="text-sm text-gray-500 mt-1">${workload.budget_per_hour}/hr</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">No workloads found</p>
              )}
            </div>

            {/* Recent Optimizations */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Optimizations</h3>
              {optimizationsLoading ? (
                <div className="animate-pulse space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-16 bg-gray-200 rounded"></div>
                  ))}
                </div>
              ) : optimizations?.length > 0 ? (
                <div className="space-y-3">
                  {optimizations.slice(0, 5).map((optimization) => (
                    <div key={optimization.id} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">{optimization.optimization_type}</p>
                        <p className="text-sm text-gray-500">
                          {new Date(optimization.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          optimization.status === 'completed' ? 'bg-green-100 text-green-800' :
                          optimization.status === 'running' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {optimization.status}
                        </span>
                        <p className="text-sm text-green-600 mt-1">
                          Saved ${optimization.total_savings?.toFixed(2) || '0.00'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">No optimizations found</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Dashboard;