import React, { useState } from 'react';
import * as XLSX from 'xlsx';

import FilterBar from '../components/history/FilterBar';
import HistoryCollectionManager from '../components/history/HistoryCollectionManager';
import RecordTable from '../components/history/RecordTable';
import { useHistory } from '../hooks/useHistory';
import { useAuth } from '../hooks/useAuth';
import { historyService } from '../services/history';

const EXPORT_HEADERS = ['Record ID', 'Date', 'Size', 'Collected At', 'Device ID', 'Timestamp'];

const buildExportFilename = ({ start_date: startDate, end_date: endDate }) => {
  if (startDate && endDate) {
    return `egg-history-${startDate}-to-${endDate}.xlsx`;
  }
  if (startDate) {
    return `egg-history-${startDate}-to-latest.xlsx`;
  }
  if (endDate) {
    return `egg-history-through-${endDate}.xlsx`;
  }
  return 'egg-history.xlsx';
};

const buildExportRows = (records) => (
  records.map((record) => [
    record.id,
    record.date,
    record.size_display || record.size,
    record.detected_at,
    record.device_id,
    record.timestamp,
  ])
);

const HistoryPage = () => {
  const { user } = useAuth();
  const { records, totalRecords, hasMore, loading, error, params, updateParams, loadMore, refetch } = useHistory();
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  const canManageHistory = user?.role === 'history_editor';

  const handleExport = async () => {
    setExporting(true);
    setExportError(null);

    try {
      const data = await historyService.getAllRecords(params);
      const worksheet = XLSX.utils.aoa_to_sheet([
        EXPORT_HEADERS,
        ...buildExportRows(data.records),
      ]);
      const workbook = XLSX.utils.book_new();

      XLSX.utils.book_append_sheet(workbook, worksheet, 'History');
      XLSX.writeFile(workbook, buildExportFilename(params));
    } catch (err) {
      setExportError(err.message || 'Failed to export records');
      console.error(err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-dark-slate sm:text-3xl">History</h1>
          <p className="text-sm text-gray-500">Browse collected egg records with filters</p>
        </div>
      </div>

      <FilterBar
        params={params}
        totalRecords={totalRecords}
        onUpdate={updateParams}
        onExport={handleExport}
        exporting={exporting}
      />

      {canManageHistory ? (
        <HistoryCollectionManager params={params} onChanged={refetch} />
      ) : null}

      {error ? (
        <div className="rounded-xl border border-alert-red/20 bg-alert-red/10 px-4 py-3 text-sm text-alert-red">
          {error}
        </div>
      ) : null}

      {exportError ? (
        <div className="rounded-xl border border-alert-red/20 bg-alert-red/10 px-4 py-3 text-sm text-alert-red">
          {exportError}
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
