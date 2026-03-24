import React from 'react';
import { ChevronDown } from 'lucide-react';

const PeriodCard = ({ accentClass, averageClass, icon, title, controls = [], total = 0, average = 0 }) => {
  const Icon = icon;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${accentClass}`}>
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{title}</p>
            <p className="mt-3 text-2xl font-bold tracking-tight text-dark-slate sm:text-3xl">{total}</p>
          </div>
        </div>
        <div className="text-left sm:text-right">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Avg / Day</p>
          <p className={`mt-3 text-xl font-semibold ${averageClass || 'text-dark-slate'}`}>{average}</p>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        {controls.map((control) => (
          <label key={control.label} className="relative sm:min-w-0">
            <span className="sr-only">{control.label}</span>
            <select
              value={control.value}
              onChange={(event) => control.onChange(event.target.value)}
              className="w-full appearance-none rounded-lg border border-slate-200 bg-slate-50 py-2 pl-3 pr-9 text-sm font-medium text-dark-slate focus:outline-none focus:ring-2 focus:ring-yolk-yellow sm:w-auto"
            >
              {control.options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          </label>
        ))}
      </div>
    </div>
  );
};

export default PeriodCard;
