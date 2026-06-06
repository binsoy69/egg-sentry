import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Check, Clock3, LoaderCircle, Pencil, Plus, Trash2, X } from 'lucide-react';

import CollectionActionModal from '../dashboard/CollectionActionModal';
import { useDevices } from '../../hooks/useDevices';
import { historyService } from '../../services/history';
import SizeBadge from './SizeBadge';

const PAGE_LIMIT = 20;

const SIZE_FIELDS = [
  { key: 'small', label: 'S', badge: 'S' },
  { key: 'medium', label: 'M', badge: 'M' },
  { key: 'large', label: 'L', badge: 'L' },
  { key: 'extra-large', label: 'XL', badge: 'XL' },
  { key: 'jumbo', label: 'Jumbo', badge: 'Jumbo' },
  { key: 'unknown', label: 'Unknown', badge: 'Unknown' },
];

const emptyBreakdown = () => (
  SIZE_FIELDS.reduce((current, field) => ({ ...current, [field.key]: '0' }), {})
);

const toDateTimeInput = (value) => {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) {
    return '';
  }

  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return localDate.toISOString().slice(0, 16);
};

const buildDefaultForm = (deviceId = '') => ({
  device_id: deviceId,
  collected_at: toDateTimeInput(),
  size_breakdown: emptyBreakdown(),
});

const sizeTotal = (breakdown) => (
  SIZE_FIELDS.reduce((total, field) => total + Number(breakdown?.[field.key] || 0), 0)
);

const sizeSummary = (breakdown) => {
  const items = SIZE_FIELDS.filter((field) => Number(breakdown?.[field.key] || 0) > 0);

  if (!items.length) {
    return <span className="text-sm text-slate-400">No sizes</span>;
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((field) => (
        <span key={field.key} className="inline-flex items-center gap-1 rounded-full bg-slate-50 pr-2">
          <SizeBadge size={field.badge} />
          <span className="text-xs font-semibold text-slate-600">{breakdown[field.key]}</span>
        </span>
      ))}
    </div>
  );
};

const HistoryCollectionManager = ({ params, onChanged }) => {
  const { devices, loading: devicesLoading, error: devicesError } = useDevices();
  const editFormRef = useRef(null);
  const [records, setRecords] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState(buildDefaultForm());
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteError, setDeleteError] = useState('');
  const [deleting, setDeleting] = useState(false);

  const listParams = useMemo(() => ({
    size: params.size,
    start_date: params.start_date,
    end_date: params.end_date,
    page,
    limit: PAGE_LIMIT,
  }), [page, params.end_date, params.size, params.start_date]);

  useEffect(() => {
    setPage(1);
  }, [params.end_date, params.size, params.start_date]);

  useEffect(() => {
    if (!formData.device_id && devices.length > 0) {
      setFormData((current) => ({ ...current, device_id: devices[0].device_id }));
    }
  }, [devices, formData.device_id]);

  useEffect(() => {
    let isMounted = true;

    const fetchRecords = async () => {
      setLoading(true);
      try {
        const data = await historyService.getCollections(listParams);
        if (!isMounted) {
          return;
        }

        setRecords(data.records);
        setTotalRecords(data.total_records);
        setError('');
      } catch (err) {
        if (!isMounted) {
          return;
        }
        setError(err.response?.data?.detail || err.message || 'Failed to load editable history eggs.');
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchRecords();
    return () => {
      isMounted = false;
    };
  }, [listParams, reloadKey]);

  const resetForm = () => {
    setEditingId(null);
    setFormError('');
    setFormData(buildDefaultForm(devices[0]?.device_id || ''));
  };

  const refreshAfterMutation = () => {
    if (page !== 1) {
      setPage(1);
    }
    setReloadKey((current) => current + 1);
    onChanged?.();
  };

  const updateBreakdown = (key, value) => {
    if (!/^\d*$/.test(value)) {
      return;
    }

    setFormData((current) => ({
      ...current,
      size_breakdown: {
        ...current.size_breakdown,
        [key]: value,
      },
    }));
  };

  const buildPayload = () => {
    if (!formData.device_id) {
      throw new Error('Select a device.');
    }

    const collectedAt = new Date(formData.collected_at);
    if (!formData.collected_at || Number.isNaN(collectedAt.getTime())) {
      throw new Error('Choose a valid collection time.');
    }

    const size_breakdown = {};
    for (const field of SIZE_FIELDS) {
      const count = Number(formData.size_breakdown[field.key] || 0);
      if (!Number.isInteger(count) || count < 0) {
        throw new Error('Size counts must be whole numbers.');
      }
      size_breakdown[field.key] = count;
    }

    if (sizeTotal(size_breakdown) < 1) {
      throw new Error('Enter at least one egg.');
    }

    return {
      device_id: formData.device_id,
      collected_at: collectedAt.toISOString(),
      size_breakdown,
    };
  };

  const submitForm = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError('');

    try {
      const payload = buildPayload();
      if (editingId) {
        await historyService.updateCollection(editingId, payload);
      } else {
        await historyService.createCollection(payload);
      }
      resetForm();
      refreshAfterMutation();
    } catch (err) {
      setFormError(err.response?.data?.detail || err.message || 'Failed to save history entry.');
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (record) => {
    setEditingId(record.id);
    setFormError('');
    setFormData({
      device_id: record.device_id,
      collected_at: toDateTimeInput(record.collected_at),
      size_breakdown: SIZE_FIELDS.reduce(
        (current, field) => ({
          ...current,
          [field.key]: String(record.size_breakdown?.[field.key] || 0),
        }),
        {}
      ),
    });

    window.requestAnimationFrame(() => {
      editFormRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      editFormRef.current?.focus({ preventScroll: true });
    });
  };

  const confirmDelete = async () => {
    if (!deleteTarget) {
      return;
    }

    setDeleting(true);
    setDeleteError('');
    try {
      await historyService.deleteCollection(deleteTarget.id);
      setDeleteTarget(null);
      if (editingId === deleteTarget.id) {
        resetForm();
      }
      refreshAfterMutation();
    } catch (err) {
      setDeleteError(err.response?.data?.detail || err.message || 'Failed to delete history entry.');
    } finally {
      setDeleting(false);
    }
  };

  const currentTotal = sizeTotal(formData.size_breakdown);
  const hasPreviousPage = page > 1;
  const hasNextPage = page * PAGE_LIMIT < totalRecords;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-100 px-4 py-5 sm:flex-row sm:items-start sm:justify-between sm:px-6">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-yolk-yellow">
            <Pencil className="h-3.5 w-3.5" />
            Editor
          </div>
          <h2 className="mt-3 text-xl font-bold text-dark-slate">Manage History Eggs</h2>
        </div>
        <div className="rounded-full bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-600">
          {totalRecords} grouped eggs
        </div>
      </div>

      <form
        ref={editFormRef}
        onSubmit={submitForm}
        tabIndex={-1}
        aria-label="History egg editor"
        className="scroll-mt-24 border-b border-slate-100 px-4 py-5 outline-none sm:px-6"
      >
        <div className="grid gap-3 lg:grid-cols-[1fr,1fr,auto]">
          <label className="block">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Device</span>
            <select
              value={formData.device_id}
              onChange={(event) => setFormData((current) => ({ ...current, device_id: event.target.value }))}
              disabled={saving || devicesLoading}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-dark-slate outline-none transition focus:border-yolk-yellow focus:ring-2 focus:ring-yolk-yellow/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <option value="">Select device</option>
              {devices.map((device) => (
                <option key={device.device_id} value={device.device_id}>
                  {device.name || device.device_id}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Collected At</span>
            <input
              type="datetime-local"
              value={formData.collected_at}
              onChange={(event) => setFormData((current) => ({ ...current, collected_at: event.target.value }))}
              disabled={saving}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-dark-slate outline-none transition focus:border-yolk-yellow focus:ring-2 focus:ring-yolk-yellow/20 disabled:cursor-not-allowed disabled:opacity-60"
            />
          </label>

          <div className="flex items-end">
            <div className="w-full rounded-xl border border-amber-100 bg-amber-50 px-4 py-2">
              <span className="block text-xs font-semibold uppercase tracking-[0.14em] text-amber-700">Total</span>
              <span className="text-2xl font-bold text-dark-slate">{currentTotal}</span>
            </div>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {SIZE_FIELDS.map((field) => (
            <label key={field.key} className="block">
              <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
                {field.label}
              </span>
              <input
                type="number"
                min="0"
                step="1"
                value={formData.size_breakdown[field.key]}
                onChange={(event) => updateBreakdown(field.key, event.target.value)}
                disabled={saving}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-dark-slate outline-none transition focus:border-yolk-yellow focus:ring-2 focus:ring-yolk-yellow/20 disabled:cursor-not-allowed disabled:opacity-60"
              />
            </label>
          ))}
        </div>

        {formError || devicesError ? (
          <div className="mt-4 rounded-xl border border-alert-red/20 bg-alert-red/10 px-4 py-3 text-sm text-alert-red">
            {formError || devicesError}
          </div>
        ) : null}

        <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          {editingId ? (
            <button
              type="button"
              onClick={resetForm}
              disabled={saving}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <X className="h-4 w-4" />
              Cancel
            </button>
          ) : null}
          <button
            type="submit"
            disabled={saving || devicesLoading || !devices.length}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-yolk-yellow px-5 py-2 text-sm font-semibold text-white transition hover:bg-yolk-yellow/90 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : editingId ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {editingId ? 'Save Eggs' : 'Add Eggs'}
          </button>
        </div>
      </form>

      {error ? (
        <div className="mx-4 mt-4 rounded-xl border border-alert-red/20 bg-alert-red/10 px-4 py-3 text-sm text-alert-red sm:mx-6">
          {error}
        </div>
      ) : null}

      <div className="px-4 py-5 sm:px-6">
        {loading ? (
          <div className="flex items-center justify-center rounded-xl border border-slate-200 bg-slate-50 p-8 text-sm text-slate-500">
            <LoaderCircle className="mr-2 h-5 w-5 animate-spin text-yolk-yellow" />
            Loading grouped eggs...
          </div>
        ) : records.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-5 py-8 text-center text-sm text-slate-500">
            No editable eggs match the current filters.
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-200">
            <div className="divide-y divide-slate-100 md:hidden">
              {records.map((record) => (
                <div key={record.id} className="space-y-4 bg-white px-4 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-lg font-bold text-dark-slate">{record.count} eggs</p>
                      <p className="mt-1 inline-flex items-center gap-1.5 text-sm text-slate-500">
                        <Clock3 className="h-4 w-4" />
                        {record.collected_at_display}
                      </p>
                    </div>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                      {record.device_id}
                    </span>
                  </div>
                  {sizeSummary(record.size_breakdown)}
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => startEdit(record)}
                      className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setDeleteError('');
                        setDeleteTarget(record);
                      }}
                      className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-alert-red transition hover:bg-red-50"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="hidden overflow-x-auto md:block">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th scope="col" className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                      Collected At
                    </th>
                    <th scope="col" className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                      Device
                    </th>
                    <th scope="col" className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                      Total
                    </th>
                    <th scope="col" className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                      Sizes
                    </th>
                    <th scope="col" className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {records.map((record) => (
                    <tr key={record.id} className="transition-colors hover:bg-slate-50/70">
                      <td className="whitespace-nowrap px-5 py-4 text-sm font-medium text-dark-slate">
                        {record.collected_at_display}
                      </td>
                      <td className="whitespace-nowrap px-5 py-4 text-sm text-slate-600">{record.device_id}</td>
                      <td className="whitespace-nowrap px-5 py-4 text-sm font-bold text-dark-slate">{record.count}</td>
                      <td className="min-w-64 px-5 py-4">{sizeSummary(record.size_breakdown)}</td>
                      <td className="whitespace-nowrap px-5 py-4 text-right">
                        <div className="inline-flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => startEdit(record)}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setDeleteError('');
                              setDeleteTarget(record);
                            }}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-alert-red transition hover:bg-red-50"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {totalRecords > PAGE_LIMIT ? (
          <div className="mt-4 flex items-center justify-between gap-3">
            <span className="text-sm text-slate-500">
              Page {page} of {Math.ceil(totalRecords / PAGE_LIMIT)}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={!hasPreviousPage || loading}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => setPage((current) => current + 1)}
                disabled={!hasNextPage || loading}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        ) : null}
      </div>

      <CollectionActionModal
        isOpen={Boolean(deleteTarget)}
        title="Delete history eggs?"
        description={`This removes the ${deleteTarget?.count ?? ''} egg entry from history and reports.`}
        confirmLabel="Delete eggs"
        onCancel={() => {
          if (!deleting) {
            setDeleteError('');
            setDeleteTarget(null);
          }
        }}
        onConfirm={confirmDelete}
        loading={deleting}
        error={deleteError}
      />
    </section>
  );
};

export default HistoryCollectionManager;
