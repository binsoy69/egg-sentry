import React from 'react';
import { Archive, Clock3 } from 'lucide-react';

const sourceClassMap = {
  manual: 'bg-amber-100 text-amber-700',
  automatic: 'bg-sky-100 text-sky-700',
};

const CollectionHistoryPanel = ({ entries }) => {
  if (!entries.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center shadow-sm">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-yolk-yellow">
          <Archive className="h-6 w-6" />
        </div>
        <h2 className="mt-4 text-lg font-semibold text-dark-slate">No collections logged today</h2>
        <p className="mt-2 text-sm text-slate-500">
          Use the collect button when eggs are removed, or let the system infer it from a large count drop.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-100 px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <h2 className="text-lg font-semibold text-dark-slate">Today&apos;s Collection Log</h2>
          <p className="mt-1 text-sm text-slate-500">Each entry preserves collected eggs without losing the running day total.</p>
        </div>
        <div className="w-fit rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-yolk-yellow">
          {entries.length} entries
        </div>
      </div>

      <div className="divide-y divide-slate-100">
        {entries.map((entry) => (
          <div key={entry.id} className="flex flex-col gap-4 px-4 py-4 sm:px-6 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-2xl font-bold text-dark-slate">{entry.count} eggs</p>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${sourceClassMap[entry.source] || 'bg-slate-100 text-slate-600'}`}>
                  {entry.source === 'manual' ? 'Manual' : 'Auto'}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-500">
                Count changed from {entry.before_count} to {entry.after_count}.
              </p>
            </div>

            <div className="inline-flex items-center gap-2 text-sm text-slate-500">
              <Clock3 className="h-4 w-4" />
              {entry.collected_at_display}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CollectionHistoryPanel;
