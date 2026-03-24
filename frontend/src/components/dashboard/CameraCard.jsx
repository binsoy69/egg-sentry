import React from 'react';
import { Camera } from 'lucide-react';

const CameraCard = ({ device }) => {
  return (
    <div className="rounded-2xl border border-amber-100 bg-white shadow-sm">
      <div className="flex flex-col gap-5 border-l-4 border-l-yolk-yellow px-6 py-5 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-yolk-yellow">
            <Camera className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-dark-slate">{device.name}</h3>
            <p className="text-sm text-slate-500">{device.location || 'Primary coop device'}</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-5 text-left md:min-w-[20rem]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Cages</p>
            <p className="mt-1 text-2xl font-bold text-dark-slate">{device.num_cages ?? 0}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Chickens</p>
            <p className="mt-1 text-2xl font-bold text-dark-slate">{device.num_chickens ?? 0}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Today</p>
            <p className="mt-1 text-2xl font-bold text-yolk-yellow">{device.today_count ?? 0}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CameraCard;
