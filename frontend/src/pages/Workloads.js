import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { Helmet } from 'react-helmet-async';
import {
  Plus,
  Play,
  Pause,
  Trash2,
  Edit,
  Eye,
  Clock,
  Cpu,
  DollarSign,
  AlertCircle,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';

import { workloadsAPI } from '../services/api';

const Workloads = () => {
  const [selectedWorkload, setSelectedWorkload] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const queryClient = useQueryClient();

  // Fetch workloads
  const { data: workloads, isLoading, error } = useQuery(
    ['workloads'],
    () => workloadsAPI.getWorkloads(),
    { refetchInterval: 30000 } // Refetch every 30 seconds
  );

  // Mutations
  const createWorkloadMutation = useMutation(
    (workloadData) => workloadsAPI.createWorkload(workloadData),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['workloads']);
        setShowCreateModal(false);
        toast.success('Workload created successfully!');
      },
      onError: (error) => {
        toast.error(error.response?.data?.detail || 'Failed to create workload');
      },
    }
  );

  const updateWorkloadMutation = useMutation(
    ({ id, data }) => workloadsAPI.updateWorkload(id, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['workloads']);
        setShowEditModal(false);
        setSelectedWorkload(null);
        toast.success('Workload updated successfully!');
      },
      onError: (error) => {
        toast.error(error.response?.data?.detail || 'Failed to update workload');
      },
    }
  );

  const deleteWorkloadMutation = useMutation(
    (id) => workloadsAPI.deleteWorkload(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['workloads']);
        toast.success('Workload deleted successfully!');
      },
      onError: (error) => {
        toast.error(error.response?.data?.detail || 'Failed to delete workload');
      },
    }
  );

  const startWorkloadMutation = useMutation(
    (id) => workloadsAPI.startWorkload(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['workloads']);
        toast.success('Workload started successfully!');
      },
      onError: (error) => {
        toast.error(error.response?.data?.detail || 'Failed to start workload');
      },
    }
  );

  const stopWorkloadMutation = useMutation(
    (id) => workloadsAPI.stopWorkload(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['workloads']);
        toast.success('Workload stopped successfully!');
      },
      onError: (error) => {
        toast.error(error.response?.data?.detail || 'Failed to stop workload');
      },
    }
  );

  // Status badge component
  const StatusBadge = ({ status }) => {
    const statusConfig = {
      running: { color: 'bg-green-100 text-green-800', icon: CheckCircle },
      stopped: { color: 'bg-gray-100 text-gray-800', icon: XCircle },
      pending: { color: 'bg-yellow-100 text-yellow-800', icon: Clock },
      error: { color: 'bg-red-100 text-red-800', icon: AlertCircle },
    };

    const config = statusConfig[status] || statusConfig.stopped;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
        <Icon className="w-3 h-3 mr-1" />
        {status}
      </span>
    );
  };

  // Action handlers
  const handleCreateWorkload = (workloadData) => {
    createWorkloadMutation.mutate(workloadData);
  };

  const handleEditWorkload = (workload) => {
    setSelectedWorkload(workload);
    setShowEditModal(true);
  };

  const handleUpdateWorkload = (workloadData) => {
    updateWorkloadMutation.mutate({ id: selectedWorkload.id, data: workloadData });
  };

  const handleDeleteWorkload = (id) => {
    if (window.confirm('Are you sure you want to delete this workload?')) {
      deleteWorkloadMutation.mutate(id);
    }
  };

  const handleStartWorkload = (id) => {
    startWorkloadMutation.mutate(id);
  };

  const handleStopWorkload = (id) => {
    stopWorkloadMutation.mutate(id);
  };

  const handleViewDetails = (workload) => {
    setSelectedWorkload(workload);
    setShowDetailsModal(true);
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
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Workloads</h2>
          <p className="text-gray-600">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <Helmet>
        <title>Workloads - CloudArb</title>
        <meta name="description" content="Manage your GPU workloads and deployments" />
      </Helmet>

      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8 flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Workloads</h1>
              <p className="mt-2 text-gray-600">
                Manage your GPU workloads and monitor their performance.
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Workload
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Cpu className="h-8 w-8 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Workloads</p>
                  <p className="text-2xl font-bold text-gray-900">{workloads?.length || 0}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Running</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {Array.isArray(workloads) ? workloads.filter(w => w.status === 'running').length : 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Clock className="h-8 w-8 text-yellow-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Pending</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {Array.isArray(workloads) ? workloads.filter(w => w.status === 'pending').length : 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <DollarSign className="h-8 w-8 text-purple-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Cost</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${Array.isArray(workloads) ? workloads.reduce((sum, w) => sum + (w.total_cost || 0), 0).toFixed(2) : '0.00'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Workloads Table */}
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900">Workload List</h3>
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
                      GPU Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Cost/Hour
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
                  {Array.isArray(workloads) ? workloads.map((workload) => (
                    <tr key={workload.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">{workload.name}</div>
                          <div className="text-sm text-gray-500">{workload.description}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <StatusBadge status={workload.status} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {workload.gpu_type} x {workload.gpu_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${workload.cost_per_hour?.toFixed(2) || '0.00'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(workload.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end space-x-2">
                          <button
                            onClick={() => handleViewDetails(workload)}
                            className="text-blue-600 hover:text-blue-900"
                            title="View Details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleEditWorkload(workload)}
                            className="text-indigo-600 hover:text-indigo-900"
                            title="Edit"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          {workload.status === 'stopped' && (
                            <button
                              onClick={() => handleStartWorkload(workload.id)}
                              className="text-green-600 hover:text-green-900"
                              title="Start"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}
                          {workload.status === 'running' && (
                            <button
                              onClick={() => handleStopWorkload(workload.id)}
                              className="text-yellow-600 hover:text-yellow-900"
                              title="Stop"
                            >
                              <Pause className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => handleDeleteWorkload(workload.id)}
                            className="text-red-600 hover:text-red-900"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )) : null}
                </tbody>
              </table>
            </div>
          </div>

          {Array.isArray(workloads) && workloads.length === 0 && (
            <div className="text-center py-12">
              <Cpu className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No workloads</h3>
              <p className="mt-1 text-sm text-gray-500">
                Get started by creating a new workload.
              </p>
              <div className="mt-6">
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create Workload
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Workload Modal */}
      {showCreateModal && (
        <CreateWorkloadModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateWorkload}
          isLoading={createWorkloadMutation.isLoading}
        />
      )}

      {/* Edit Workload Modal */}
      {showEditModal && selectedWorkload && (
        <EditWorkloadModal
          workload={selectedWorkload}
          onClose={() => {
            setShowEditModal(false);
            setSelectedWorkload(null);
          }}
          onSubmit={handleUpdateWorkload}
          isLoading={updateWorkloadMutation.isLoading}
        />
      )}

      {/* Workload Details Modal */}
      {showDetailsModal && selectedWorkload && (
        <WorkloadDetailsModal
          workload={selectedWorkload}
          onClose={() => {
            setShowDetailsModal(false);
            setSelectedWorkload(null);
          }}
        />
      )}
    </>
  );
};

// Modal Components (simplified for brevity)
const CreateWorkloadModal = ({ onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    gpu_type: 'a100',
    gpu_count: 1,
    workload_type: 'training',
    budget_per_hour: 10,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Workload</h3>
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
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">GPU Type</label>
                  <select
                    value={formData.gpu_type}
                    onChange={(e) => setFormData({ ...formData, gpu_type: e.target.value })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="a100">A100</option>
                    <option value="v100">V100</option>
                    <option value="h100">H100</option>
                    <option value="rtx4090">RTX 4090</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">GPU Count</label>
                  <input
                    type="number"
                    min="1"
                    max="8"
                    value={formData.gpu_count}
                    onChange={(e) => setFormData({ ...formData, gpu_count: parseInt(e.target.value) })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Workload Type</label>
                  <select
                    value={formData.workload_type}
                    onChange={(e) => setFormData({ ...formData, workload_type: e.target.value })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="training">Training</option>
                    <option value="inference">Inference</option>
                    <option value="development">Development</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Budget/Hour ($)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.budget_per_hour}
                    onChange={(e) => setFormData({ ...formData, budget_per_hour: parseFloat(e.target.value) })}
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
                {isLoading ? 'Creating...' : 'Create Workload'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

const EditWorkloadModal = ({ workload, onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    name: workload.name,
    description: workload.description,
    gpu_type: workload.gpu_type,
    gpu_count: workload.gpu_count,
    workload_type: workload.workload_type,
    budget_per_hour: workload.budget_per_hour,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Edit Workload</h3>
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
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">GPU Type</label>
                  <select
                    value={formData.gpu_type}
                    onChange={(e) => setFormData({ ...formData, gpu_type: e.target.value })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="a100">A100</option>
                    <option value="v100">V100</option>
                    <option value="h100">H100</option>
                    <option value="rtx4090">RTX 4090</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">GPU Count</label>
                  <input
                    type="number"
                    min="1"
                    max="8"
                    value={formData.gpu_count}
                    onChange={(e) => setFormData({ ...formData, gpu_count: parseInt(e.target.value) })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Workload Type</label>
                  <select
                    value={formData.workload_type}
                    onChange={(e) => setFormData({ ...formData, workload_type: e.target.value })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="training">Training</option>
                    <option value="inference">Inference</option>
                    <option value="development">Development</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Budget/Hour ($)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.budget_per_hour}
                    onChange={(e) => setFormData({ ...formData, budget_per_hour: parseFloat(e.target.value) })}
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
                {isLoading ? 'Updating...' : 'Update Workload'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

const WorkloadDetailsModal = ({ workload, onClose }) => {
  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Workload Details</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Name</label>
              <p className="mt-1 text-sm text-gray-900">{workload.name}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Description</label>
              <p className="mt-1 text-sm text-gray-900">{workload.description}</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Status</label>
                <p className="mt-1 text-sm text-gray-900">{workload.status}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">GPU Type</label>
                <p className="mt-1 text-sm text-gray-900">{workload.gpu_type} x {workload.gpu_count}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Workload Type</label>
                <p className="mt-1 text-sm text-gray-900">{workload.workload_type}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Cost/Hour</label>
                <p className="mt-1 text-sm text-gray-900">${workload.cost_per_hour?.toFixed(2) || '0.00'}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Total Cost</label>
                <p className="mt-1 text-sm text-gray-900">${workload.total_cost?.toFixed(2) || '0.00'}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Created</label>
                <p className="mt-1 text-sm text-gray-900">
                  {new Date(workload.created_at).toLocaleDateString()}
                </p>
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

export default Workloads;