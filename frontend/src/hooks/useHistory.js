import { useEffect, useMemo, useState } from 'react';
import { historyService } from '../services/history';

export const useHistory = (initialParams = { page: 1, limit: 20, size: 'all', start_date: '', end_date: '' }) => {
  const [records, setRecords] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [params, setParams] = useState(initialParams);

  const requestParams = useMemo(() => {
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
  }, [params.end_date, params.limit, params.page, params.size, params.start_date]);

  useEffect(() => {
    let isMounted = true;

    const fetchRecords = async () => {
      setLoading(true);
      try {
        const data = await historyService.getRecords(requestParams);
        if (!isMounted) {
          return;
        }

        setRecords((prev) => (
          params.page === 1 ? data.records : [...prev, ...data.records]
        ));
        setTotalRecords(data.total_records);
        setError(null);
      } catch (err) {
        if (!isMounted) {
          return;
        }
        setError(err.message || 'Failed to fetch records');
        console.error(err);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchRecords();
    return () => {
      isMounted = false;
    };
  }, [params.page, requestParams]);

  const updateParams = (newParams) => {
    setParams((prev) => ({ ...prev, ...newParams, page: 1 }));
  };

  const loadMore = () => {
    setParams((prev) => ({ ...prev, page: prev.page + 1 }));
  };

  const hasMore = records.length < totalRecords;

  return { records, totalRecords, hasMore, loading, error, params, updateParams, loadMore };
};
