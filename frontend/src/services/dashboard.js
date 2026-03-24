import api from './api';

export const dashboardService = {
  getSummary: async (deviceId) => {
    const response = await api.get('/dashboard/summary', {
      params: deviceId ? { device_id: deviceId } : undefined,
    });
    return response.data;
  },

  getWeekly: async ({ month, year, week, deviceId }) => {
    const response = await api.get('/dashboard/weekly', {
      params: {
        month,
        year,
        week,
        ...(deviceId ? { device_id: deviceId } : {}),
      },
    });
    return response.data;
  },

  getMonthly: async ({ month, year, deviceId }) => {
    const response = await api.get('/dashboard/monthly', {
      params: {
        month,
        year,
        ...(deviceId ? { device_id: deviceId } : {}),
      },
    });
    return response.data;
  },

  getYearly: async ({ year, deviceId }) => {
    const response = await api.get('/dashboard/yearly', {
      params: {
        year,
        ...(deviceId ? { device_id: deviceId } : {}),
      },
    });
    return response.data;
  },

  getDailyChart: async ({ from, to, deviceId }) => {
    const response = await api.get('/dashboard/daily-chart', {
      params: {
        from,
        to,
        ...(deviceId ? { device_id: deviceId } : {}),
      },
    });
    return response.data;
  },

  getSizeDistribution: async ({ from, to, deviceId }) => {
    const response = await api.get('/dashboard/size-distribution', {
      params: {
        from,
        to,
        ...(deviceId ? { device_id: deviceId } : {}),
      },
    });
    return response.data;
  },
};
