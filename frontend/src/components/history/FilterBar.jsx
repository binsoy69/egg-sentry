import React from 'react';
import { Calendar, CalendarDays, Funnel } from 'lucide-react';

const SIZE_OPTIONS = [
  { value: 'all', label: 'All Sizes' },
  { value: 'small', label: 'S' },
  { value: 'medium', label: 'M' },
  { value: 'large', label: 'L' },
  { value: 'extra-large', label: 'XL' },
  { value: 'jumbo', label: 'Jumbo' },
  { value: 'unknown', label: 'Unknown' },
];

const formatDateInputValue = (date) => {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const FilterBar = ({ params, totalRecords, onUpdate }) => {
  const today = formatDateInputValue(new Date());
  const isTodayFilterActive = params.start_date === today && params.end_date === today;

  const handleTodayFilter = () => {
    if (isTodayFilterActive) {
      onUpdate({ start_date: '', end_date: '' });
      return;
    }

    onUpdate({ start_date: today, end_date: today });
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 text-dark-slate">
          <Funnel className="h-4 w-4 text-yolk-yellow" />
          <span className="text-sm font-semibold">Filters</span>
        </div>
        <span className="inline-flex items-center rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-yolk-yellow">
          {totalRecords} records
        </span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={handleTodayFilter}
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-semibold transition-colors ${
            isTodayFilterActive
              ? 'border-yolk-yellow bg-amber-50 text-yolk-yellow'
              : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-dark-slate'
          }`}
        >
          <CalendarDays className="h-4 w-4" />
          Today
        </button>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <select
          value={params.size}
          onChange={(event) => onUpdate({ size: event.target.value })}
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-dark-slate focus:outline-none focus:ring-2 focus:ring-yolk-yellow"
        >
          {SIZE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <div className="relative flex items-center">
          <Calendar className="pointer-events-none absolute left-3 h-4 w-4 text-slate-400" />
          <input
            type="date"
            value={params.start_date || ''}
            onChange={(event) => onUpdate({ start_date: event.target.value })}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 pl-9 pr-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-yolk-yellow"
          />
        </div>
        <div className="relative flex items-center">
          <Calendar className="pointer-events-none absolute left-3 h-4 w-4 text-slate-400" />
          <input
            type="date"
            value={params.end_date || ''}
            onChange={(event) => onUpdate({ end_date: event.target.value })}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 pl-9 pr-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-yolk-yellow"
          />
        </div>
      </div>

      <button
        type="button"
        onClick={() => onUpdate({ size: 'all', start_date: '', end_date: '' })}
        className="mt-4 text-sm font-medium text-slate-500 transition-colors hover:text-dark-slate"
      >
        Clear filters
      </button>
    </div>
  );
};

export default FilterBar;
