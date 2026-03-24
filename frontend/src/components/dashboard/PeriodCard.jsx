import React from 'react';
import { ChevronDown } from 'lucide-react';

const PeriodCard = ({ accentClass, averageClass, icon, title, controls = [], total = 0, average = 0 }) => {
  const Icon = icon;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${accentClass}`}>
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{title}</p>
            <p className="mt-3 text-3xl font-bold tracking-tight text-dark-slate">{total}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Avg / Day</p>
          <p className={`mt-3 text-xl font-semibold ${averageClass || 'text-dark-slate'}`}>{average}</p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {controls.map((control) => (
          <label key={control.label} className="relative">
            <span className="sr-only">{control.label}</span>
            <select
              value={control.value}
              onChange={(event) => control.onChange(event.target.value)}
              className="appearance-none rounded-lg border border-slate-200 bg-slate-50 py-2 pl-3 pr-9 text-sm font-medium text-dark-slate focus:outline-none focus:ring-2 focus:ring-yolk-yellow"
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
