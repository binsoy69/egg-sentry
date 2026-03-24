import api from './api';

export const historyService = {
  getRecords: async (params) => {
    const response = await api.get('/history', { params });
    return response.data;
  }
};
