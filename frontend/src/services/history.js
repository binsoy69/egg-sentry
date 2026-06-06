import api from './api';

const EXPORT_PAGE_LIMIT = 200;

const buildHistoryParams = (params = {}) => {
  const nextParams = {
    page: params.page,
    limit: params.limit,
  };

  if (params.size && params.size !== 'all') {
    nextParams.size = params.size;
  }
  if (params.start_date) {
    nextParams.start_date = params.start_date;
  }
  if (params.end_date) {
    nextParams.end_date = params.end_date;
  }

  return nextParams;
};

export const historyService = {
  getRecords: async (params) => {
    const response = await api.get('/history', { params: buildHistoryParams(params) });
    return response.data;
  },
  getDailyRecords: async (params) => {
    const response = await api.get('/history/daily', { params: buildHistoryParams(params) });
    return response.data;
  },
  getCollections: async (params) => {
    const response = await api.get('/history/collections', { params: buildHistoryParams(params) });
    return response.data;
  },
  createCollection: async (payload) => {
    const response = await api.post('/history/collections', payload);
    return response.data;
  },
  updateCollection: async (collectionId, payload) => {
    const response = await api.patch(`/history/collections/${collectionId}`, payload);
    return response.data;
  },
  deleteCollection: async (collectionId) => {
    const response = await api.delete(`/history/collections/${collectionId}`);
    return response.data;
  },
  getAllRecords: async (params = {}) => {
    let page = 1;
    let totalRecords = 0;
    const records = [];

    do {
      const data = await historyService.getRecords({
        ...params,
        page,
        limit: EXPORT_PAGE_LIMIT,
      });

      totalRecords = data.total_records;
      records.push(...data.records);
      page += 1;
    } while (records.length < totalRecords);

    return {
      total_records: totalRecords,
      records,
    };
  },
  getAllDailyRecords: async (params = {}) => {
    let page = 1;
    let totalRecords = 0;
    let totalEggs = 0;
    const records = [];

    do {
      const data = await historyService.getDailyRecords({
        ...params,
        page,
        limit: EXPORT_PAGE_LIMIT,
      });

      totalRecords = data.total_records;
      totalEggs = data.total_eggs;
      records.push(...data.records);
      page += 1;
    } while (records.length < totalRecords);

    return {
      total_records: totalRecords,
      total_eggs: totalEggs,
      records,
    };
  },
};
