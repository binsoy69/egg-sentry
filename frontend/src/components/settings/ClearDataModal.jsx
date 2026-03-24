import React, { useState } from 'react';
import { ShieldAlert, Trash2, X } from 'lucide-react';

const ClearDataModal = ({ onClose, onConfirm, loading, error }) => {
  const [password, setPassword] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onConfirm(password);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={loading ? undefined : onClose}
    >
      <div
        className="w-full max-w-md overflow-hidden rounded-[1.75rem] bg-white shadow-[0_28px_70px_rgba(15,23,42,0.16)] animate-in zoom-in-95 duration-200"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <div className="flex items-center gap-2 text-dark-slate">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-50 text-alert-red">
                <Trash2 className="h-5 w-5" />
              </div>
              <h2 className="text-lg font-bold text-dark-slate">Clear Runtime Data</h2>
            </div>
            <p className="mt-2 text-sm text-gray-500">
              This removes egg detections, live count snapshots, collections, and alerts while keeping user accounts and device records.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="p-1 text-gray-400 transition-colors hover:text-gray-600 disabled:cursor-not-allowed"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 p-6">
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-4">
            <p className="text-sm font-semibold text-red-700">Confirm destructive action</p>
            <p className="mt-2 text-sm leading-6 text-red-800">
              Enter your current password to start fresh. This action cannot be undone.
            </p>
          </div>

          {error ? (
            <div className="flex items-start gap-2 rounded-lg bg-alert-red/10 p-3 text-sm text-alert-red">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{error}</p>
            </div>
          ) : null}

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-dark-slate">Current password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              autoFocus
              className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-dark-slate outline-none transition focus:border-alert-red focus:ring-2 focus:ring-alert-red/20"
            />
          </label>

          <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-dark-slate disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-xl bg-alert-red px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading ? 'Clearing...' : 'Clear Data'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ClearDataModal;
