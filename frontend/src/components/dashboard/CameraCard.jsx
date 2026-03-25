import React from 'react';
import { Camera } from 'lucide-react';

const CameraCard = ({ device, currentCount = 0, collectedToday = 0 }) => {
  return (
    <div className="rounded-2xl border border-amber-100 bg-white shadow-sm">
      <div className="flex flex-col gap-5 border-l-4 border-l-yolk-yellow px-4 py-5 sm:px-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-50 text-yolk-yellow">
            <Camera className="h-6 w-6" />
          </div>
          <div className="min-w-0">
            <h3 className="text-lg font-bold text-dark-slate">{device.name}</h3>
            <p className="text-sm text-slate-500">{device.location || 'Primary coop device'}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 text-left sm:grid-cols-4 md:min-w-[26rem] md:gap-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Cages</p>
            <p className="mt-1 text-2xl font-bold text-dark-slate">{device.num_cages ?? 0}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Chickens</p>
            <p className="mt-1 text-2xl font-bold text-dark-slate">{device.num_chickens ?? 0}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Chicken Age</p>
            <p className="mt-1 text-2xl font-bold text-dark-slate">{device.age_of_chicken ?? '-'}</p>
          </div>
          <div className="col-span-2 sm:col-span-1">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Current</p>
            <p className="mt-1 text-2xl font-bold text-yolk-yellow">{currentCount}</p>
            <p className="mt-1 text-xs text-slate-500">Collected today: {collectedToday}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CameraCard;
