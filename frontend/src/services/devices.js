import api from './api';

export const devicesService = {
  getDevices: async () => {
    const response = await api.get('/devices');
    return response.data;
  },
  
  updateDevice: async (deviceId, payload) => {
    const response = await api.put(`/devices/${deviceId}`, payload);
    return response.data;
  },

  toggleDeviceConfig: async (deviceId, isConfigActive) => {
    const response = await api.put(`/devices/${deviceId}/config`, {
      is_active: isConfigActive
    });
    return response.data;
  }
};
