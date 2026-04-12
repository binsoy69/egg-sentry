import api from './api';

export const collectionsService = {
  collectEggs: async (deviceId) => {
    const response = await api.post('/collections', {
      device_id: deviceId,
    });
    return response.data;
  },

  updateCollection: async (collectionId, count) => {
    const response = await api.patch(`/collections/${collectionId}`, {
      count,
    });
    return response.data;
  },

  deleteCollection: async (collectionId) => {
    const response = await api.delete(`/collections/${collectionId}`);
    return response.data;
  },

  clearToday: async (deviceId) => {
    const response = await api.delete('/collections/today', {
      params: deviceId ? { device_id: deviceId } : undefined,
    });
    return response.data;
  },
};
