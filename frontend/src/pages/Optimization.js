import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { Helmet } from 'react-helmet-async';
import {
  Plus,
  Play,
  BarChart3,
  TrendingUp,
  DollarSign,
  Clock,
  CheckCircle,
  AlertCircle,
  XCircle,
  Zap,
  Target,
  Settings,
  Download,
  Upload,
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import toast from 'react-hot-toast';

import { optimizationAPI } from '../services/api';

const Optimization = () => {
  const [selectedOptimization, setSelectedOptimization] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showResultsModal, setShowResultsModal] = useState(false);
  const [showDeployModal, setShowDeployModal] = useState(false);
  const queryClient = useQueryClient();

  // Fetch optimizations
  const { data: optimizations, isLoading, error } = useQuery(
    ['optimizations'],
    () => optimizationAPI.getOptimizations(),
    { refetchInterval: 30000 } // Refetch every 30 seconds
  );

  // Mutations
  const createOptimizationMutation = useMutation(
    (optimizationData) => optimizationAPI.createOptimization(optimizationData),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['optimizations']);
        setShowCreateModal(false);
        toast.success('Optimization created successfully!');
      },
      onError: (error) => {
        toast.error(error.response?.data?.detail || 'Failed to create optimization');
      },
    }
  );

  const runOptimizationMutation = useMutation(
    (id) => optimizationAPI.runOptimization(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['optimizations']);
        toast.success('Optimization started successfully!');
      },
      onError: (error) => {
        toast.error(error.response?.data?.detail || 'Failed to start optimization');
      },
    }
  );

  const deployOptimizationMutation = useMutation(
    (id) => optimizationAPI.deployOptimization(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['optimizations']);
        setShowDeployModal(false);
        toast.success('Optimization deployed successfully!');
      },
      onError: (error) => {
        toast.error(error.response?.data?.detail || 'Failed to deploy optimization');
      },
    }
  );

  // Status badge component
  const StatusBadge = ({ status }) => {
    const statusConfig = {
      completed: { color: 'bg-green-100 text-green-800', icon: CheckCircle },
      running: { color: 'bg-blue-100 text-blue-800', icon: Play },
      pending: { color: 'bg-yellow-100 text-yellow-800', icon: Clock },
      failed: { color: 'bg-red-100 text-red-800', icon: XCircle },
      deployed: { color: 'bg-purple-100 text-purple-800', icon: Zap },
    };

    const config = statusConfig[status] || statusConfig.pending;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
        <Icon className="w-3 h-3 mr-1" />
        {status}
      </span>
    );
  };

  // Action handlers
  const handleCreateOptimization = (optimizationData) => {
    createOptimizationMutation.mutate(optimizationData);
  };

  const handleRunOptimization = (id) => {
    runOptimizationMutation.mutate(id);
  };

  const handleViewResults = (optimization) => {
    setSelectedOptimization(optimization);
    setShowResultsModal(true);
  };

  const handleDeployOptimization = (id) => {
    setSelectedOptimization(optimizations.find(o => o.id === id));
    setShowDeployModal(true);
  };

  const handleConfirmDeploy = () => {
    if (selectedOptimization) {
      deployOptimizationMutation.mutate(selectedOptimization.id);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Optimizations</h2>
          <p className="text-gray-600">{error.message}</p>
        </div>
      </div>
    );
  }

  // Calculate metrics
  const totalOptimizations = optimizations?.length || 0;
  const completedOptimizations = optimizations?.filter(o => o.status === 'completed').length || 0;
  const runningOptimizations = optimizations?.filter(o => o.status === 'running').length || 0;
  const totalSavings = optimizations?.reduce((sum, o) => sum + (o.savings_amount || 0), 0) || 0;

  // Sample data for charts
  const savingsTrendData = [
    { date: '2024-01-01', savings: 1200 },
    { date: '2024-01-02', savings: 1350 },
    { date: '2024-01-03', savings: 1100 },
    { date: '2024-01-04', savings: 1600 },
    { date: '2024-01-05', savings: 1400 },
    { date: '2024-01-06', savings: 1800 },
    { date: '2024-01-07', savings: 2000 },
  ];

  const providerBreakdownData = [
    { name: 'AWS', value: 35 },
    { name: 'GCP', value: 25 },
    { name: 'Azure', value: 20 },
    { name: 'Lambda Labs', value: 15 },
    { name: 'RunPod', value: 5 },
  ];

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  return (
    <>
      <Helmet>
        <title>Optimization - CloudArb</title>
        <meta name="description" content="GPU cost optimization and arbitrage management" />
      </Helmet>

      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8 flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Optimization</h1>
              <p className="mt-2 text-gray-600">
                Create and manage GPU cost optimizations using advanced arbitrage algorithms.
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Optimization
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Target className="h-8 w-8 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Optimizations</p>
                  <p className="text-2xl font-bold text-gray-900">{totalOptimizations}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Completed</p>
                  <p className="text-2xl font-bold text-gray-900">{completedOptimizations}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Play className="h-8 w-8 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Running</p>
                  <p className="text-2xl font-bold text-gray-900">{runningOptimizations}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <TrendingUp className="h-8 w-8 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Savings</p>
                  <p className="text-2xl font-bold text-gray-900">${totalSavings.toFixed(2)}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Savings Trend Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Savings Trend</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={savingsTrendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="savings" stroke="#10B981" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Provider Breakdown Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Provider Breakdown</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={providerBreakdownData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {providerBreakdownData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Optimizations Table */}
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900">Optimization History</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Objective
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Savings
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {optimizations?.map((optimization) => (
                    <tr key={optimization.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">{optimization.name}</div>
                          <div className="text-sm text-gray-500">{optimization.description}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <StatusBadge status={optimization.status} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {optimization.objective}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${optimization.savings_amount?.toFixed(2) || '0.00'}
                        {optimization.savings_percentage && (
                          <span className="text-green-600 ml-1">
                            ({optimization.savings_percentage.toFixed(1)}%)
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(optimization.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end space-x-2">
                          {optimization.status === 'pending' && (
                            <button
                              onClick={() => handleRunOptimization(optimization.id)}
                              className="text-green-600 hover:text-green-900"
                              title="Run Optimization"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}
                          {optimization.status === 'completed' && (
                            <>
                              <button
                                onClick={() => handleViewResults(optimization)}
                                className="text-blue-600 hover:text-blue-900"
                                title="View Results"
                              >
                                <BarChart3 className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleDeployOptimization(optimization.id)}
                                className="text-purple-600 hover:text-purple-900"
                                title="Deploy"
                              >
                                <Zap className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {optimizations?.length === 0 && (
            <div className="text-center py-12">
              <Target className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No optimizations</h3>
              <p className="mt-1 text-sm text-gray-500">
                Get started by creating your first optimization.
              </p>
              <div className="mt-6">
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create Optimization
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Optimization Modal */}
      {showCreateModal && (
        <CreateOptimizationModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateOptimization}
          isLoading={createOptimizationMutation.isLoading}
        />
      )}

      {/* Results Modal */}
      {showResultsModal && selectedOptimization && (
        <OptimizationResultsModal
          optimization={selectedOptimization}
          onClose={() => {
            setShowResultsModal(false);
            setSelectedOptimization(null);
          }}
        />
      )}

      {/* Deploy Modal */}
      {showDeployModal && selectedOptimization && (
        <DeployOptimizationModal
          optimization={selectedOptimization}
          onClose={() => {
            setShowDeployModal(false);
            setSelectedOptimization(null);
          }}
          onConfirm={handleConfirmDeploy}
          isLoading={deployOptimizationMutation.isLoading}
        />
      )}
    </>
  );
};

// Modal Components
const CreateOptimizationModal = ({ onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    objective: 'minimize_cost',
    workloads: [
      {
        gpu_type: 'a100',
        min_count: 1,
        max_count: 4,
        workload_type: 'training',
      }
    ],
    constraints: [
      {
        name: 'budget',
        type: 'budget',
        operator: '<=',
        value: 100,
      }
    ],
    risk_tolerance: 0.1,
    time_horizon_hours: 24,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const addWorkload = () => {
    setFormData({
      ...formData,
      workloads: [
        ...formData.workloads,
        {
          gpu_type: 'a100',
          min_count: 1,
          max_count: 4,
          workload_type: 'training',
        }
      ]
    });
  };

  const removeWorkload = (index) => {
    setFormData({
      ...formData,
      workloads: formData.workloads.filter((_, i) => i !== index)
    });
  };

  const updateWorkload = (index, field, value) => {
    const updatedWorkloads = [...formData.workloads];
    updatedWorkloads[index] = { ...updatedWorkloads[index], [field]: value };
    setFormData({ ...formData, workloads: updatedWorkloads });
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-10 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Optimization</h3>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  rows={3}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Objective</label>
                <select
                  value={formData.objective}
                  onChange={(e) => setFormData({ ...formData, objective: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="minimize_cost">Minimize Cost</option>
                  <option value="maximize_performance">Maximize Performance</option>
                  <option value="balance_cost_performance">Balance Cost & Performance</option>
                </select>
              </div>

              {/* Workloads Section */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Workloads</label>
                {formData.workloads.map((workload, index) => (
                  <div key={index} className="border border-gray-200 rounded-md p-4 mb-4">
                    <div className="flex justify-between items-center mb-3">
                      <h4 className="text-sm font-medium text-gray-900">Workload {index + 1}</h4>
                      {formData.workloads.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeWorkload(index)}
                          className="text-red-600 hover:text-red-900 text-sm"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-700">GPU Type</label>
                        <select
                          value={workload.gpu_type}
                          onChange={(e) => updateWorkload(index, 'gpu_type', e.target.value)}
                          className="mt-1 block w-full border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="a100">A100</option>
                          <option value="v100">V100</option>
                          <option value="h100">H100</option>
                          <option value="rtx4090">RTX 4090</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700">Workload Type</label>
                        <select
                          value={workload.workload_type}
                          onChange={(e) => updateWorkload(index, 'workload_type', e.target.value)}
                          className="mt-1 block w-full border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="training">Training</option>
                          <option value="inference">Inference</option>
                          <option value="development">Development</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700">Min GPU Count</label>
                        <input
                          type="number"
                          min="1"
                          value={workload.min_count}
                          onChange={(e) => updateWorkload(index, 'min_count', parseInt(e.target.value))}
                          className="mt-1 block w-full border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700">Max GPU Count</label>
                        <input
                          type="number"
                          min="1"
                          value={workload.max_count}
                          onChange={(e) => updateWorkload(index, 'max_count', parseInt(e.target.value))}
                          className="mt-1 block w-full border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addWorkload}
                  className="text-blue-600 hover:text-blue-900 text-sm font-medium"
                >
                  + Add Workload
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Risk Tolerance</label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={formData.risk_tolerance}
                    onChange={(e) => setFormData({ ...formData, risk_tolerance: parseFloat(e.target.value) })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Time Horizon (hours)</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.time_horizon_hours}
                    onChange={(e) => setFormData({ ...formData, time_horizon_hours: parseInt(e.target.value) })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {isLoading ? 'Creating...' : 'Create Optimization'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

const OptimizationResultsModal = ({ optimization, onClose }) => {
  // Sample results data
  const allocationData = [
    { provider: 'AWS', instances: 2, cost: 45.60, savings: 12.40 },
    { provider: 'GCP', instances: 1, cost: 32.80, savings: 8.20 },
    { provider: 'Lambda Labs', instances: 1, cost: 28.40, savings: 15.60 },
  ];

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-10 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Optimization Results</h3>
          <div className="space-y-6">
            {/* Summary */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="text-md font-medium text-gray-900 mb-2">Summary</h4>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Total Savings</p>
                  <p className="text-lg font-bold text-green-600">
                    ${optimization.savings_amount?.toFixed(2) || '0.00'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Savings Percentage</p>
                  <p className="text-lg font-bold text-green-600">
                    {optimization.savings_percentage?.toFixed(1) || '0'}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Solve Time</p>
                  <p className="text-lg font-bold text-gray-900">
                    {optimization.solve_time || '2.3'}s
                  </p>
                </div>
              </div>
            </div>

            {/* Allocation Chart */}
            <div>
              <h4 className="text-md font-medium text-gray-900 mb-2">Resource Allocation</h4>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={allocationData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="provider" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="cost" fill="#3B82F6" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Detailed Results */}
            <div>
              <h4 className="text-md font-medium text-gray-900 mb-2">Detailed Results</h4>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Instances</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Cost/Hour</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Savings</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {allocationData.map((item, index) => (
                      <tr key={index}>
                        <td className="px-4 py-2 text-sm text-gray-900">{item.provider}</td>
                        <td className="px-4 py-2 text-sm text-gray-900">{item.instances}</td>
                        <td className="px-4 py-2 text-sm text-gray-900">${item.cost.toFixed(2)}</td>
                        <td className="px-4 py-2 text-sm text-green-600">${item.savings.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div className="mt-6 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const DeployOptimizationModal = ({ optimization, onClose, onConfirm, isLoading }) => {
  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Deploy Optimization</h3>
          <div className="space-y-4">
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
              <div className="flex">
                <AlertCircle className="h-5 w-5 text-yellow-400" />
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-yellow-800">Deployment Warning</h3>
                  <div className="mt-2 text-sm text-yellow-700">
                    <p>This will deploy the optimized resource allocation across all cloud providers. This action cannot be undone.</p>
                  </div>
                </div>
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-600">
                Are you sure you want to deploy the optimization "{optimization.name}"?
              </p>
            </div>
          </div>
          <div className="mt-6 flex justify-end space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={isLoading}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50"
            >
              {isLoading ? 'Deploying...' : 'Deploy'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Optimization;