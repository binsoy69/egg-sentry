import React from 'react';
import { AlertTriangle, LoaderCircle } from 'lucide-react';

const CollectEggsModal = ({ isOpen, currentEggs, onCancel, onConfirm, loading, error }) => {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/45 px-4 py-8 backdrop-blur-sm">
      <div className="w-full max-w-md overflow-hidden rounded-3xl bg-white shadow-2xl">
        <div className="border-b border-amber-100 bg-amber-50/70 px-6 py-5">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-yolk-yellow shadow-sm">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-dark-slate">Confirm Egg Collection</h2>
              <p className="mt-1 text-sm text-slate-600">
                This will create a collection log entry and reset the current nest count to zero.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-4 px-6 py-6">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Current Eggs</p>
            <p className="mt-2 text-4xl font-bold text-dark-slate">{currentEggs}</p>
            <p className="mt-2 text-sm text-slate-500">The same amount will be stored in today&apos;s collection history.</p>
          </div>

          {error ? (
            <div className="rounded-2xl border border-alert-red/20 bg-alert-red/10 px-4 py-3 text-sm text-alert-red">
              {error}
            </div>
          ) : null}

          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="rounded-full border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={loading || currentEggs <= 0}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-yolk-yellow px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-yolk-yellow/90 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
              Confirm Collection
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CollectEggsModal;
