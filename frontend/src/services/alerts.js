import api from './api';

export const alertsService = {
  listAlerts: async ({ status = 'active', page = 1, limit = 5 } = {}) => {
    const response = await api.get('/alerts', {
      params: { status, page, limit },
    });
    return response.data;
  },

  dismissAlert: async (alertId) => {
    const response = await api.put(`/alerts/${alertId}/dismiss`);
    return response.data;
  },
};
