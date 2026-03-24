import React from 'react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

const MetricCard = ({ title, value, icon, trend, className, color = 'yolk-yellow' }) => {
  const Icon = icon;
  const colorMap = {
    'yolk-yellow': 'text-yolk-yellow bg-amber-50',
    'sage-green': 'text-sage-green bg-emerald-50',
    'coop-brown': 'text-coop-brown bg-violet-50',
    'alert-red': 'text-alert-red bg-red-50',
    'dark-slate': 'text-dark-slate bg-slate-100',
  };

  const iconClasses = colorMap[color] || colorMap['yolk-yellow'];

  return (
    <div className={twMerge(clsx('flex items-center rounded-2xl border border-slate-200 bg-white p-5 shadow-sm', className))}>
      <div className={clsx('mr-4 rounded-xl p-3', iconClasses)}>
        <Icon className="h-6 w-6" />
      </div>
      <div>
        <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{title}</p>
        <div className="flex items-baseline gap-2">
          <h3 className="text-2xl font-bold tracking-tight text-dark-slate">{value}</h3>
          {trend ? (
            <span className={clsx('text-sm font-medium', trend.isPositive ? 'text-sage-green' : 'text-alert-red')}>
              {trend.isPositive ? '+' : '-'}{trend.value}%
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default MetricCard;
