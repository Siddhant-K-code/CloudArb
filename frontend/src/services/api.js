import axios from 'axios';

// Create axios instance
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refreshToken');
        if (refreshToken) {
          const response = await axios.post('/auth/refresh', {
            refresh_token: refreshToken,
          });

          const { access_token } = response.data;
          localStorage.setItem('token', access_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email, password) =>
    api.post('/auth/login', { username: email, password }),

  register: (userData) =>
    api.post('/auth/register', userData),

  getCurrentUser: () =>
    api.get('/auth/me'),

  refreshToken: () =>
    api.post('/auth/refresh'),

  logout: () =>
    api.post('/auth/logout'),

  requestPasswordReset: (email) =>
    api.post('/auth/password-reset', { email }),

  confirmPasswordReset: (token, newPassword) =>
    api.post('/auth/password-reset/confirm', { token, new_password: newPassword }),
};

// Workloads API
export const workloadsAPI = {
  getWorkloads: (params = {}) =>
    api.get('/workloads', { params }),

  getWorkload: (id) =>
    api.get(`/workloads/${id}`),

  createWorkload: (workloadData) =>
    api.post('/workloads', workloadData),

  updateWorkload: (id, workloadData) =>
    api.put(`/workloads/${id}`, workloadData),

  deleteWorkload: (id) =>
    api.delete(`/workloads/${id}`),

  optimizeWorkload: (id, optimizationData) =>
    api.post(`/workloads/${id}/optimize`, optimizationData),

  batchOptimize: (optimizationData) =>
    api.post('/workloads/batch-optimize', optimizationData),

  analyzeCost: (id) =>
    api.get(`/workloads/${id}/cost-analysis`),
};

// Optimization API
export const optimizationAPI = {
  createOptimization: (optimizationData) =>
    api.post('/optimize', optimizationData),

  getOptimization: (id) =>
    api.get(`/optimize/${id}`),

  getOptimizations: (params = {}) =>
    api.get('/optimize', { params }),

  deleteOptimization: (id) =>
    api.delete(`/optimize/${id}`),

  deployOptimization: (id) =>
    api.post(`/optimize/${id}/deploy`),

  runOptimization: (id) =>
    api.post(`/optimize/${id}/run`),

  quickOptimize: (optimizationData) =>
    api.post('/optimize/quick', optimizationData),
};

// Analytics API
export const analyticsAPI = {
  getCostAnalysis: (params = {}) =>
    api.get('/analytics/cost-analysis', { params }),

  getPerformanceMetrics: (params = {}) =>
    api.get('/analytics/performance-metrics', { params }),

  getArbitrageOpportunities: (params = {}) =>
    api.get('/analytics/arbitrage-opportunities', { params }),

  getMarketAnalysis: (params = {}) =>
    api.get('/analytics/market-analysis', { params }),

  getOptimizationHistory: (params = {}) =>
    api.get('/analytics/optimization-history', { params }),

  getSavingsSummary: (params = {}) =>
    api.get('/analytics/savings-summary', { params }),
};

// Market Data API
export const marketDataAPI = {
  getProviders: (params = {}) =>
    api.get('/market/providers', { params }),

  getProvider: (id) =>
    api.get(`/market/providers/${id}`),

  getInstanceTypes: (params = {}) =>
    api.get('/market/instance-types', { params }),

  getInstanceType: (id) =>
    api.get(`/market/instance-types/${id}`),

  getPricingData: (params = {}) =>
    api.get('/market/pricing', { params }),

  comparePrices: (params = {}) =>
    api.get('/market/pricing/compare', { params }),

  getPriceTrends: (providerId, instanceTypeId, region, params = {}) =>
    api.get(`/market/pricing/trends`, {
      params: { provider_id: providerId, instance_type_id: instanceTypeId, region, ...params }
    }),

  getRegions: (params = {}) =>
    api.get('/market/regions', { params }),

  getMarketStats: () =>
    api.get('/market/stats'),

  getMarketTrends: (params = {}) =>
    api.get('/market/trends', { params }),

  getAvailabilityData: (params = {}) =>
    api.get('/market/availability', { params }),
};

// User API
export const userAPI = {
  getProfile: () =>
    api.get('/users/profile'),

  updateProfile: (profileData) =>
    api.put('/users/profile', profileData),

  getActivity: (params = {}) =>
    api.get('/users/activity', { params }),

  changePassword: (passwordData) =>
    api.put('/users/password', passwordData),

  getPreferences: () =>
    api.get('/users/preferences'),

  updatePreferences: (preferences) =>
    api.put('/users/preferences', preferences),
};

// Settings API
export const settingsAPI = {
  getSettings: () =>
    api.get('/settings'),

  updateSettings: (settingsData) =>
    api.put('/settings', settingsData),

  updatePassword: (passwordData) =>
    api.put('/settings/password', passwordData),

  updateNotificationSettings: (notificationSettings) =>
    api.put('/settings/notifications', notificationSettings),

  updateApplicationSettings: (applicationSettings) =>
    api.put('/settings/application', applicationSettings),

  exportSettings: () =>
    api.get('/settings/export'),

  importSettings: (settingsFile) =>
    api.post('/settings/import', settingsFile),
};

// Health Check API
export const healthAPI = {
  getHealth: () =>
    api.get('/health'),

  getDetailedHealth: () =>
    api.get('/health/detailed'),
};

// WebSocket connection for real-time updates
export const createWebSocketConnection = (token) => {
  const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';
  const ws = new WebSocket(`${wsUrl}?token=${token}`);

  ws.onopen = () => {
    console.log('WebSocket connected');
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  return ws;
};

// Export the main api instance
export default api;