import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { Helmet } from 'react-helmet-async';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  Activity,
  Clock,
  RefreshCw,
  Filter,
  Search,
  AlertCircle,
  CheckCircle,
  XCircle,
  Zap,
  Globe,
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, HeatMap } from 'recharts';
import toast from 'react-hot-toast';

import { marketDataAPI } from '../services/api';

const MarketData = () => {
  const [selectedGPU, setSelectedGPU] = useState('all');
  const [selectedProvider, setSelectedProvider] = useState('all');
  const [timeRange, setTimeRange] = useState('24h');
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch market data
  const { data: providers, isLoading: providersLoading } = useQuery(
    ['providers'],
    () => marketDataAPI.getProviders(),
    { refetchInterval: 300000 } // Refetch every 5 minutes
  );

  const { data: instanceTypes, isLoading: instancesLoading } = useQuery(
    ['instance-types'],
    () => marketDataAPI.getInstanceTypes(),
    { refetchInterval: 300000 }
  );

  const { data: pricingData, isLoading: pricingLoading } = useQuery(
    ['pricing-data', selectedGPU, selectedProvider, timeRange],
    () => marketDataAPI.getPricingData({
      gpu_type: selectedGPU === 'all' ? undefined : selectedGPU,
      provider: selectedProvider === 'all' ? undefined : selectedProvider,
      time_range: timeRange
    }),
    { refetchInterval: 60000 } // Refetch every minute
  );

  const { data: marketTrends, isLoading: trendsLoading } = useQuery(
    ['market-trends'],
    () => marketDataAPI.getMarketTrends(),
    { refetchInterval: 300000 }
  );

  const { data: availabilityData, isLoading: availabilityLoading } = useQuery(
    ['availability-data'],
    () => marketDataAPI.getAvailabilityData(),
    { refetchInterval: 120000 } // Refetch every 2 minutes
  );

  // Sample data for charts
  const priceTrendData = [
    { time: '00:00', aws: 2.45, gcp: 2.32, azure: 2.58, lambda: 1.89, runpod: 1.95 },
    { time: '04:00', aws: 2.38, gcp: 2.28, azure: 2.52, lambda: 1.85, runpod: 1.92 },
    { time: '08:00', aws: 2.52, gcp: 2.45, azure: 2.65, lambda: 1.95, runpod: 2.02 },
    { time: '12:00', aws: 2.68, gcp: 2.58, azure: 2.72, lambda: 2.05, runpod: 2.15 },
    { time: '16:00', aws: 2.55, gcp: 2.42, azure: 2.60, lambda: 1.98, runpod: 2.08 },
    { time: '20:00', aws: 2.42, gcp: 2.35, azure: 2.55, lambda: 1.91, runpod: 1.98 },
    { time: '24:00', aws: 2.45, gcp: 2.32, azure: 2.58, lambda: 1.89, runpod: 1.95 },
  ];

  const gpuComparisonData = [
    { gpu: 'A100', aws: 2.45, gcp: 2.32, azure: 2.58, lambda: 1.89, runpod: 1.95 },
    { gpu: 'H100', aws: 4.12, gcp: 3.98, azure: 4.25, lambda: 3.45, runpod: 3.65 },
    { gpu: 'V100', aws: 1.85, gcp: 1.72, azure: 1.95, lambda: 1.45, runpod: 1.52 },
    { gpu: 'RTX 4090', aws: 0.95, gcp: 0.88, azure: 1.02, lambda: 0.75, runpod: 0.82 },
  ];

  const availabilityHeatmapData = [
    { region: 'US East', aws: 95, gcp: 92, azure: 88, lambda: 85, runpod: 82 },
    { region: 'US West', aws: 92, gcp: 95, azure: 90, lambda: 88, runpod: 85 },
    { region: 'Europe', aws: 88, gcp: 90, azure: 95, lambda: 82, runpod: 80 },
    { region: 'Asia', aws: 85, gcp: 88, azure: 92, lambda: 80, runpod: 78 },
  ];

  // Filter data based on search
  const filteredInstances = instanceTypes?.filter(instance =>
    instance.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    instance.gpu_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
    instance.provider.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  // Calculate metrics
  const totalProviders = providers?.length || 0;
  const totalInstances = instanceTypes?.length || 0;
  const avgPrice = pricingData?.average_price || 0;
  const priceVolatility = pricingData?.volatility || 0;

  // Status badge component
  const StatusBadge = ({ status }) => {
    const statusConfig = {
      available: { color: 'bg-green-100 text-green-800', icon: CheckCircle },
      limited: { color: 'bg-yellow-100 text-yellow-800', icon: AlertCircle },
      unavailable: { color: 'bg-red-100 text-red-800', icon: XCircle },
    };

    const config = statusConfig[status] || statusConfig.unavailable;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
        <Icon className="w-3 h-3 mr-1" />
        {status}
      </span>
    );
  };

  // Refresh function
  const handleRefresh = () => {
    toast.success('Market data refreshed!');
  };

  if (providersLoading || instancesLoading || pricingLoading || trendsLoading || availabilityLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <>
      <Helmet>
        <title>Market Data - CloudArb</title>
        <meta name="description" content="Real-time GPU pricing and market data across cloud providers" />
      </Helmet>

      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8 flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Market Data</h1>
              <p className="mt-2 text-gray-600">
                Real-time GPU pricing, availability, and market trends across all cloud providers.
              </p>
            </div>
            <button
              onClick={handleRefresh}
              className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh Data
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Globe className="h-8 w-8 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Active Providers</p>
                  <p className="text-2xl font-bold text-gray-900">{totalProviders}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Zap className="h-8 w-8 text-purple-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Instance Types</p>
                  <p className="text-2xl font-bold text-gray-900">{totalInstances}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <DollarSign className="h-8 w-8 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Avg Price/Hour</p>
                  <p className="text-2xl font-bold text-gray-900">${avgPrice.toFixed(2)}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Activity className="h-8 w-8 text-orange-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Price Volatility</p>
                  <p className="text-2xl font-bold text-gray-900">{priceVolatility.toFixed(1)}%</p>
                </div>
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="mb-6 bg-white rounded-lg shadow p-4">
            <div className="flex flex-wrap items-center space-x-4">
              <div className="flex-1 min-w-0">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <input
                    type="text"
                    placeholder="Search instances, GPUs, or providers..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">GPU Type</label>
                <select
                  value={selectedGPU}
                  onChange={(e) => setSelectedGPU(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">All GPUs</option>
                  <option value="a100">A100</option>
                  <option value="h100">H100</option>
                  <option value="v100">V100</option>
                  <option value="rtx4090">RTX 4090</option>
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
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Time Range</label>
                <select
                  value={timeRange}
                  onChange={(e) => setTimeRange(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="1h">Last Hour</option>
                  <option value="24h">Last 24 Hours</option>
                  <option value="7d">Last 7 Days</option>
                  <option value="30d">Last 30 Days</option>
                </select>
              </div>
            </div>
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Price Trend Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Price Trends (24h)</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={priceTrendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="aws" stroke="#FF9900" strokeWidth={2} name="AWS" />
                  <Line type="monotone" dataKey="gcp" stroke="#4285F4" strokeWidth={2} name="GCP" />
                  <Line type="monotone" dataKey="azure" stroke="#00A4EF" strokeWidth={2} name="Azure" />
                  <Line type="monotone" dataKey="lambda" stroke="#FF6B35" strokeWidth={2} name="Lambda" />
                  <Line type="monotone" dataKey="runpod" stroke="#6366F1" strokeWidth={2} name="RunPod" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* GPU Comparison Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">GPU Price Comparison</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={gpuComparisonData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="gpu" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="aws" fill="#FF9900" name="AWS" />
                  <Bar dataKey="gcp" fill="#4285F4" name="GCP" />
                  <Bar dataKey="azure" fill="#00A4EF" name="Azure" />
                  <Bar dataKey="lambda" fill="#FF6B35" name="Lambda" />
                  <Bar dataKey="runpod" fill="#6366F1" name="RunPod" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Availability Heatmap */}
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Regional Availability (%)</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Region
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      AWS
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      GCP
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Azure
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Lambda
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      RunPod
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {availabilityHeatmapData.map((region, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {region.region}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="flex items-center">
                          <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="bg-orange-500 h-2 rounded-full"
                              style={{ width: `${region.aws}%` }}
                            ></div>
                          </div>
                          {region.aws}%
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="flex items-center">
                          <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="bg-blue-500 h-2 rounded-full"
                              style={{ width: `${region.gcp}%` }}
                            ></div>
                          </div>
                          {region.gcp}%
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="flex items-center">
                          <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="bg-cyan-500 h-2 rounded-full"
                              style={{ width: `${region.azure}%` }}
                            ></div>
                          </div>
                          {region.azure}%
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="flex items-center">
                          <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="bg-red-500 h-2 rounded-full"
                              style={{ width: `${region.lambda}%` }}
                            ></div>
                          </div>
                          {region.lambda}%
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="flex items-center">
                          <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="bg-indigo-500 h-2 rounded-full"
                              style={{ width: `${region.runpod}%` }}
                            ></div>
                          </div>
                          {region.runpod}%
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Instance Types Table */}
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <div className="px-4 py-5 sm:px-6 flex justify-between items-center">
              <h3 className="text-lg leading-6 font-medium text-gray-900">Instance Types & Pricing</h3>
              <div className="text-sm text-gray-500">
                Last updated: {new Date().toLocaleTimeString()}
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Instance
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Provider
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      GPU Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Price/Hour
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Availability
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Region
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Updated
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredInstances?.map((instance) => (
                    <tr key={instance.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">{instance.name}</div>
                          <div className="text-sm text-gray-500">{instance.description}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          instance.provider === 'aws' ? 'bg-orange-100 text-orange-800' :
                          instance.provider === 'gcp' ? 'bg-blue-100 text-blue-800' :
                          instance.provider === 'azure' ? 'bg-cyan-100 text-cyan-800' :
                          instance.provider === 'lambda' ? 'bg-red-100 text-red-800' :
                          'bg-indigo-100 text-indigo-800'
                        }`}>
                          {instance.provider.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {instance.gpu_type}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="flex items-center">
                          <DollarSign className="w-4 h-4 text-green-600 mr-1" />
                          {instance.price_per_hour?.toFixed(2) || '0.00'}
                          {instance.price_change && (
                            <span className={`ml-2 text-xs ${
                              instance.price_change > 0 ? 'text-red-600' : 'text-green-600'
                            }`}>
                              {instance.price_change > 0 ? '+' : ''}{instance.price_change.toFixed(2)}%
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <StatusBadge status={instance.availability} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {instance.region}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(instance.last_updated).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {filteredInstances?.length === 0 && (
            <div className="text-center py-12">
              <Globe className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No instances found</h3>
              <p className="mt-1 text-sm text-gray-500">
                Try adjusting your search criteria or filters.
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default MarketData;