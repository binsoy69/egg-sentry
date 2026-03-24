import api from './api';

export const collectionsService = {
  collectEggs: async (deviceId) => {
    const response = await api.post('/collections', {
      device_id: deviceId,
    });
    return response.data;
  },
};
