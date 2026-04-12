import React, { useState } from 'react';
import { Archive, Check, Clock3, LoaderCircle, Pencil, Trash2, X } from 'lucide-react';

const sourceClassMap = {
  manual: 'bg-amber-100 text-amber-700',
  automatic: 'bg-sky-100 text-sky-700',
};

const CollectionHistoryPanel = ({
  entries,
  onUpdateEntry,
  onDeleteEntry,
  onClearToday,
  actionLoading,
}) => {
  const [editingId, setEditingId] = useState(null);
  const [draftCount, setDraftCount] = useState('');

  const isLoading = (type, id) =>
    actionLoading?.type === type && (id === undefined || actionLoading?.id === id);
  const anyLoading = Boolean(actionLoading);

  const startEdit = (entry) => {
    setEditingId(entry.id);
    setDraftCount(String(entry.count));
  };

  const cancelEdit = () => {
    setEditingId(null);
    setDraftCount('');
  };

  const submitEdit = async (event, entry) => {
    event.preventDefault();
    const count = Number(draftCount);
    if (!Number.isInteger(count) || count < 1) {
      return;
    }

    const updated = await onUpdateEntry(entry.id, count);
    if (updated) {
      cancelEdit();
    }
  };

  if (!entries.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center shadow-sm">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-yolk-yellow">
          <Archive className="h-6 w-6" />
        </div>
        <h2 className="mt-4 text-lg font-semibold text-dark-slate">No collections logged today</h2>
        <p className="mt-2 text-sm text-slate-500">
          Use the collect button whenever eggs are removed so the collection log stays accurate.
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
        <div className="flex flex-wrap items-center gap-2">
          <div className="w-fit rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-yolk-yellow">
            {entries.length} entries
          </div>
          <button
            type="button"
            onClick={onClearToday}
            disabled={anyLoading}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-semibold text-alert-red transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading('clear') ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
            Clear today
          </button>
        </div>
      </div>

      <div className="divide-y divide-slate-100">
        {entries.map((entry) => {
          const isEditing = editingId === entry.id;
          const updateLoading = isLoading('update', entry.id);
          const deleteLoading = isLoading('delete', entry.id);

          return (
            <div key={entry.id} className="flex flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  {isEditing ? (
                    <form onSubmit={(event) => submitEdit(event, entry)} className="flex flex-wrap items-center gap-2">
                      <label className="sr-only" htmlFor={`collection-count-${entry.id}`}>
                        Egg count
                      </label>
                      <input
                        id={`collection-count-${entry.id}`}
                        type="number"
                        min="1"
                        step="1"
                        value={draftCount}
                        onChange={(event) => setDraftCount(event.target.value)}
                        disabled={updateLoading}
                        className="w-24 rounded-lg border border-slate-200 px-3 py-2 text-lg font-bold text-dark-slate outline-none transition focus:border-yolk-yellow focus:ring-2 focus:ring-yolk-yellow/20 disabled:cursor-not-allowed disabled:bg-slate-100"
                      />
                      <span className="text-lg font-bold text-dark-slate">eggs</span>
                      <button
                        type="submit"
                        disabled={updateLoading}
                        className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-yolk-yellow text-white transition hover:bg-yolk-yellow/90 disabled:cursor-not-allowed disabled:bg-slate-300"
                        aria-label="Save collection count"
                      >
                        {updateLoading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                      </button>
                      <button
                        type="button"
                        onClick={cancelEdit}
                        disabled={updateLoading}
                        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                        aria-label="Cancel editing collection count"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </form>
                  ) : (
                    <p className="text-2xl font-bold text-dark-slate">{entry.count} eggs</p>
                  )}
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${sourceClassMap[entry.source] || 'bg-slate-100 text-slate-600'}`}>
                    {entry.source === 'manual' ? 'Manual' : 'Automatic'}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-500">
                  Count changed from {entry.before_count} to {entry.after_count}.
                </p>
              </div>

              <div className="flex flex-col gap-3 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between lg:justify-end">
                <div className="inline-flex items-center gap-2">
                  <Clock3 className="h-4 w-4" />
                  {entry.collected_at_display}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => startEdit(entry)}
                    disabled={anyLoading || isEditing}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => onDeleteEntry(entry)}
                    disabled={anyLoading}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-alert-red transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {deleteLoading ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                    Delete
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CollectionHistoryPanel;
