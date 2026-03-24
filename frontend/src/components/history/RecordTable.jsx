import React from 'react';

import SizeBadge from './SizeBadge';

const RecordTable = ({ records, loading }) => {
  if (loading && records.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex items-center gap-3 text-gray-500">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-yolk-yellow border-t-transparent"></div>
          <span>Loading records...</span>
        </div>
      </div>
    );
  }

  if (records.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-gray-500 shadow-sm">
        <p className="mb-2 text-lg font-medium text-dark-slate">No records found</p>
        <p className="text-sm">Try adjusting your filters to see more results.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="divide-y divide-slate-100 md:hidden">
        {records.map((record) => (
          <div key={record.id} className="space-y-3 px-4 py-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-dark-slate">{record.date}</p>
                <p className="mt-1 text-sm text-slate-500">{record.detected_at}</p>
              </div>
              <SizeBadge size={record.size_display} />
            </div>
          </div>
        ))}
      </div>

      <div className="hidden overflow-x-auto md:block">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th scope="col" className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Date
              </th>
              <th scope="col" className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Size
              </th>
              <th scope="col" className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Date &amp; Time
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {records.map((record) => (
              <tr key={record.id} className="transition-colors hover:bg-slate-50/70">
                <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-dark-slate">
                  {record.date}
                </td>
                <td className="whitespace-nowrap px-6 py-4">
                  <SizeBadge size={record.size_display} />
                </td>
                <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">
                  {record.detected_at}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RecordTable;
