import React from 'react';

import SizeBadge from './SizeBadge';

const SIZE_FIELDS = [
  { key: 'small', label: 'S' },
  { key: 'medium', label: 'M' },
  { key: 'large', label: 'L' },
  { key: 'extra-large', label: 'XL' },
  { key: 'jumbo', label: 'Jumbo' },
  { key: 'unknown', label: 'Unknown' },
];

const formatPercentage = (value) => `${Number(value || 0).toFixed(1)}%`;

const SizeSummary = ({ breakdown }) => (
  <div className="flex flex-wrap gap-1.5">
    {SIZE_FIELDS.map((field) => (
      <span key={field.key} className="inline-flex items-center gap-1 rounded-full bg-slate-50 pr-2">
        <SizeBadge size={field.label} />
        <span className="text-xs font-semibold text-slate-600">
          {Number(breakdown?.[field.key] || 0)}
        </span>
      </span>
    ))}
  </div>
);

const RecordTable = ({ records, loading }) => {
  if (loading && records.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex items-center gap-3 text-gray-500">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-yolk-yellow border-t-transparent"></div>
          <span>Loading eggs...</span>
        </div>
      </div>
    );
  }

  if (records.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-gray-500 shadow-sm">
        <p className="mb-2 text-lg font-medium text-dark-slate">No eggs found</p>
        <p className="text-sm">Try adjusting your filters to see more results.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="divide-y divide-slate-100 md:hidden">
        {records.map((record) => (
          <div key={record.date} className="space-y-4 px-4 py-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-dark-slate">{record.date_display || record.date}</p>
                <p className="mt-1 text-sm text-slate-500">
                  {record.eggs} eggs / {record.num_chickens} hens
                </p>
              </div>
              <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-bold text-alert-red">
                {formatPercentage(record.laying_percentage)}
              </span>
            </div>
            <SizeSummary breakdown={record.size_breakdown} />
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
                Eggs
              </th>
              <th scope="col" className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Hens
              </th>
              <th scope="col" className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Laying %
              </th>
              <th scope="col" className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Sizes
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {records.map((record) => (
              <tr key={record.date} className="transition-colors hover:bg-slate-50/70">
                <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-dark-slate">
                  {record.date_display || record.date}
                </td>
                <td className="whitespace-nowrap px-6 py-4 text-sm font-bold text-dark-slate">
                  {record.eggs}
                </td>
                <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">
                  {record.num_chickens}
                </td>
                <td className="whitespace-nowrap px-6 py-4 text-sm font-semibold text-alert-red">
                  {formatPercentage(record.laying_percentage)}
                </td>
                <td className="min-w-80 px-6 py-4">
                  <SizeSummary breakdown={record.size_breakdown} />
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
