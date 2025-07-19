import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { Helmet } from 'react-helmet-async';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  PieChart,
  Activity,
  Clock,
  Target,
  AlertCircle,
  Download,
  Calendar,
  Filter,
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart as RechartsPieChart, Pie, Cell, AreaChart, Area } from 'recharts';
import toast from 'react-hot-toast';

import { analyticsAPI } from '../services/api';

const Analytics = () => {
  const [timeRange, setTimeRange] = useState('30d');
  const [selectedMetric, setSelectedMetric] = useState('cost');
  const [selectedProvider, setSelectedProvider] = useState('all');

  // Fetch analytics data
  const { data: costAnalysis, isLoading: costLoading } = useQuery(
    ['cost-analysis', timeRange],
    () => analyticsAPI.getCostAnalysis({ days: timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90 }),
    { refetchInterval: 300000 } // Refetch every 5 minutes
  );

  const { data: savingsSummary, isLoading: savingsLoading } = useQuery(
    ['savings-summary', timeRange],
    () => analyticsAPI.getSavingsSummary({ period_days: timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90 }),
    { refetchInterval: 300000 }
  );

  const { data: performanceMetrics, isLoading: performanceLoading } = useQuery(
    ['performance-metrics', timeRange],
    () => analyticsAPI.getPerformanceMetrics({ period_days: timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90 }),
    { refetchInterval: 300000 }
  );

  const { data: marketAnalysis, isLoading: marketLoading } = useQuery(
    ['market-analysis'],
    () => analyticsAPI.getMarketAnalysis(),
    { refetchInterval: 600000 } // Refetch every 10 minutes
  );

  const { data: arbitrageOpportunities, isLoading: opportunitiesLoading } = useQuery(
    ['arbitrage-opportunities'],
    () => analyticsAPI.getArbitrageOpportunities(),
    { refetchInterval: 300000 }
  );

  // Sample data for charts
  const costTrendData = [
    { date: '2024-01-01', cost: 1250, savings: 320 },
    { date: '2024-01-02', cost: 1180, savings: 390 },
    { date: '2024-01-03', cost: 1320, savings: 280 },
    { date: '2024-01-04', cost: 1150, savings: 420 },
    { date: '2024-01-05', cost: 1280, savings: 290 },
    { date: '2024-01-06', cost: 1100, savings: 470 },
    { date: '2024-01-07', cost: 1350, savings: 220 },
  ];

  const providerCostData = [
    { provider: 'AWS', cost: 450, percentage: 35 },
    { provider: 'GCP', cost: 320, percentage: 25 },
    { provider: 'Azure', cost: 260, percentage: 20 },
    { provider: 'Lambda Labs', cost: 195, percentage: 15 },
    { provider: 'RunPod', cost: 65, percentage: 5 },
  ];

  const performanceData = [
    { provider: 'AWS', throughput: 95, latency: 12, availability: 99.9 },
    { provider: 'GCP', throughput: 92, latency: 15, availability: 99.8 },
    { provider: 'Azure', throughput: 88, latency: 18, availability: 99.7 },
    { provider: 'Lambda Labs', throughput: 85, latency: 22, availability: 99.5 },
    { provider: 'RunPod', throughput: 82, latency: 25, availability: 99.3 },
  ];

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  // Calculate metrics
  const totalCost = costAnalysis?.total_cost || 0;
  const totalSavings = savingsSummary?.total_savings || 0;
  const savingsPercentage = savingsSummary?.savings_percentage || 0;
  const avgPerformance = performanceMetrics?.average_performance || 0;

  // Export functions
  const handleExportData = (type) => {
    toast.success(`${type} data exported successfully!`);
    // In a real implementation, this would trigger a download
  };

  if (costLoading || savingsLoading || performanceLoading || marketLoading || opportunitiesLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <>
      <Helmet>
        <title>Analytics - CloudArb</title>
        <meta name="description" content="Comprehensive analytics and cost optimization insights" />
      </Helmet>

      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8 flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
              <p className="mt-2 text-gray-600">
                Comprehensive insights into your GPU costs, performance, and optimization opportunities.
              </p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => handleExportData('Cost')}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <Download className="w-4 h-4 mr-2" />
                Export
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="mb-6 bg-white rounded-lg shadow p-4">
            <div className="flex flex-wrap items-center space-x-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Time Range</label>
                <select
                  value={timeRange}
                  onChange={(e) => setTimeRange(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="7d">Last 7 days</option>
                  <option value="30d">Last 30 days</option>
                  <option value="90d">Last 90 days</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Metric</label>
                <select
                  value={selectedMetric}
                  onChange={(e) => setSelectedMetric(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="cost">Cost</option>
                  <option value="savings">Savings</option>
                  <option value="performance">Performance</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
                <select
                  value={selectedProvider}
                  onChange={(e) => setSelectedProvider(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">All Providers</option>
                  <option value="aws">AWS</option>
                  <option value="gcp">GCP</option>
                  <option value="azure">Azure</option>
                  <option value="lambda">Lambda Labs</option>
                  <option value="runpod">RunPod</option>
                </select>
              </div>
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {/* Total Cost */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <DollarSign className="h-8 w-8 text-red-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Cost</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${totalCost.toFixed(2)}
                  </p>
                </div>
              </div>
              <div className="mt-4 flex items-center">
                <TrendingUp className="h-4 w-4 text-red-500" />
                <span className="ml-1 text-sm text-red-600">+8.2%</span>
                <span className="ml-2 text-sm text-gray-500">vs last period</span>
              </div>
            </div>

            {/* Total Savings */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <TrendingDown className="h-8 w-8 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Savings</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${totalSavings.toFixed(2)}
                  </p>
                </div>
              </div>
              <div className="mt-4 flex items-center">
                <TrendingDown className="h-4 w-4 text-green-500" />
                <span className="ml-1 text-sm text-green-600">{savingsPercentage.toFixed(1)}%</span>
                <span className="ml-2 text-sm text-gray-500">savings rate</span>
              </div>
            </div>

            {/* Average Performance */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Activity className="h-8 w-8 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Avg Performance</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {avgPerformance.toFixed(1)}%
                  </p>
                </div>
              </div>
              <div className="mt-4 flex items-center">
                <TrendingUp className="h-4 w-4 text-blue-500" />
                <span className="ml-1 text-sm text-blue-600">+2.1%</span>
                <span className="ml-2 text-sm text-gray-500">vs last period</span>
              </div>
            </div>

            {/* Optimization Success Rate */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Target className="h-8 w-8 text-purple-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Success Rate</p>
                  <p className="text-2xl font-bold text-gray-900">94.2%</p>
                </div>
              </div>
              <div className="mt-4 flex items-center">
                <TrendingUp className="h-4 w-4 text-purple-500" />
                <span className="ml-1 text-sm text-purple-600">+1.8%</span>
                <span className="ml-2 text-sm text-gray-500">vs last period</span>
              </div>
            </div>
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Cost Trend Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Cost & Savings Trend</h3>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={costTrendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Area type="monotone" dataKey="cost" stackId="1" stroke="#EF4444" fill="#FEE2E2" />
                  <Area type="monotone" dataKey="savings" stackId="2" stroke="#10B981" fill="#D1FAE5" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Provider Cost Breakdown */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Provider Cost Breakdown</h3>
              <ResponsiveContainer width="100%" height={300}>
                <RechartsPieChart>
                  <Pie
                    data={providerCostData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ provider, percentage }) => `${provider} ${percentage}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="cost"
                  >
                    {providerCostData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </RechartsPieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Performance Analysis */}
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Performance Analysis by Provider</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Provider
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Throughput (%)
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Latency (ms)
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Availability (%)
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Performance Score
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {performanceData.map((provider, index) => {
                    const performanceScore = (provider.throughput * 0.4 + (100 - provider.latency) * 0.3 + provider.availability * 0.3).toFixed(1);
                    return (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {provider.provider}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          <div className="flex items-center">
                            <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                              <div
                                className="bg-blue-600 h-2 rounded-full"
                                style={{ width: `${provider.throughput}%` }}
                              ></div>
                            </div>
                            {provider.throughput}%
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {provider.latency}ms
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {provider.availability}%
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            performanceScore >= 90 ? 'bg-green-100 text-green-800' :
                            performanceScore >= 80 ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {performanceScore}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Arbitrage Opportunities */}
          {arbitrageOpportunities && arbitrageOpportunities.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6 mb-8">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Arbitrage Opportunities</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {arbitrageOpportunities.slice(0, 6).map((opportunity, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-gray-900">{opportunity.gpu_type}</h4>
                      <span className="text-xs text-green-600 font-medium">
                        {opportunity.savings_percentage?.toFixed(1)}% savings
                      </span>
                    </div>
                    <div className="space-y-1 text-xs text-gray-600">
                      <p>From: {opportunity.from_provider} (${opportunity.from_cost}/hr)</p>
                      <p>To: {opportunity.to_provider} (${opportunity.to_cost}/hr)</p>
                      <p>Potential Savings: ${opportunity.potential_savings?.toFixed(2)}/hr</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Market Analysis */}
          {marketAnalysis && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Market Analysis</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="text-center">
                  <p className="text-sm text-gray-500">Average A100 Price</p>
                  <p className="text-lg font-bold text-gray-900">$2.45/hr</p>
                  <p className="text-xs text-green-600">↓ 3.2% this week</p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-gray-500">Average H100 Price</p>
                  <p className="text-lg font-bold text-gray-900">$4.12/hr</p>
                  <p className="text-xs text-red-600">↑ 1.8% this week</p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-gray-500">Market Volatility</p>
                  <p className="text-lg font-bold text-gray-900">Low</p>
                  <p className="text-xs text-green-600">Stable pricing</p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-gray-500">Best Value</p>
                  <p className="text-lg font-bold text-gray-900">Lambda Labs</p>
                  <p className="text-xs text-blue-600">A100 @ $1.89/hr</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default Analytics;