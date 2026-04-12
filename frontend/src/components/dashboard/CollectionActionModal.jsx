import React from 'react';
import { LoaderCircle, Trash2 } from 'lucide-react';

const CollectionActionModal = ({
  isOpen,
  title,
  description,
  confirmLabel,
  onCancel,
  onConfirm,
  loading,
  error,
}) => {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[75] flex items-center justify-center bg-slate-900/45 px-4 py-8 backdrop-blur-sm">
      <div className="w-full max-w-md overflow-hidden rounded-lg bg-white shadow-2xl">
        <div className="border-b border-red-100 bg-red-50/80 px-6 py-5">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-white text-alert-red shadow-sm">
              <Trash2 className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-dark-slate">{title}</h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
            </div>
          </div>
        </div>

        <div className="space-y-4 px-6 py-6">
          {error ? (
            <div className="rounded-lg border border-alert-red/20 bg-alert-red/10 px-4 py-3 text-sm text-alert-red">
              {error}
            </div>
          ) : null}

          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="rounded-lg border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-alert-red px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CollectionActionModal;
