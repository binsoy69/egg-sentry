import React from 'react';

import FilterBar from '../components/history/FilterBar';
import RecordTable from '../components/history/RecordTable';
import { useHistory } from '../hooks/useHistory';

const HistoryPage = () => {
  const { records, totalRecords, hasMore, loading, error, params, updateParams, loadMore } = useHistory();

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-dark-slate">History</h1>
          <p className="text-sm text-gray-500">Browse all egg records with filters</p>
        </div>
      </div>

      <FilterBar params={params} totalRecords={totalRecords} onUpdate={updateParams} />

      {error ? (
        <div className="rounded-xl border border-alert-red/20 bg-alert-red/10 px-4 py-3 text-sm text-alert-red">
          {error}
        </div>
      ) : null}

      <RecordTable records={records} loading={loading} />

      {hasMore ? (
        <div className="mt-6 flex justify-center">
          <button
            onClick={loadMore}
            disabled={loading}
            className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-6 py-2 text-sm font-medium text-dark-slate shadow-sm transition-all hover:bg-slate-50 hover:shadow disabled:opacity-50"
          >
            {loading ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-dark-slate border-t-transparent"></div> : null}
            Load More Records
          </button>
        </div>
      ) : null}
    </div>
  );
};

export default HistoryPage;
