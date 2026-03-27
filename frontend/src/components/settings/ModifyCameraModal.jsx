import React, { useEffect, useState } from 'react';
import { Camera, ShieldAlert, X } from 'lucide-react';

const getAgeFormValues = (age) => ({
  age_of_chicken_weeks: age?.weeks ?? '',
  age_of_chicken_days: age?.days ?? '',
});

const ModifyCameraModal = ({ device, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    num_cages: 1,
    num_chickens: 1,
    age_of_chicken_weeks: '',
    age_of_chicken_days: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (device) {
      setFormData({
        num_cages: device.num_cages || 1,
        num_chickens: device.num_chickens || 1,
        ...getAgeFormValues(device.age_of_chicken),
      });
    }
  }, [device]);

  if (!device) return null;

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value === '' ? '' : Number(value),
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');

    try {
      await onSave(formData);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md overflow-hidden rounded-[1.75rem] bg-white shadow-[0_28px_70px_rgba(15,23,42,0.16)] animate-in zoom-in-95 duration-200"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <div className="flex items-center gap-2 text-dark-slate">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-50 text-yolk-yellow">
                <Camera className="h-5 w-5" />
              </div>
              <h2 className="text-lg font-bold text-dark-slate">Modify Camera</h2>
            </div>
            <p className="mt-2 text-sm text-gray-500">
              {device.name} - Update cage, chicken count, and chicken age
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-gray-400 transition-colors hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 p-6">
          {error ? (
            <div className="flex items-start gap-2 rounded-lg bg-alert-red/10 p-3 text-sm text-alert-red">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{error}</p>
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Number of Cages</label>
              <input
                type="number"
                name="num_cages"
                min="1"
                value={formData.num_cages}
                onChange={handleChange}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yolk-yellow"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Number of Chickens</label>
              <input
                type="number"
                name="num_chickens"
                min="1"
                value={formData.num_chickens}
                onChange={handleChange}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yolk-yellow"
                required
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium text-gray-700">Age of Chicken</label>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-[0.14em] text-slate-500">
                    Weeks
                  </label>
                  <input
                    type="number"
                    name="age_of_chicken_weeks"
                    min="0"
                    value={formData.age_of_chicken_weeks}
                    onChange={handleChange}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yolk-yellow"
                    placeholder="Weeks"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-[0.14em] text-slate-500">
                    Days
                  </label>
                  <input
                    type="number"
                    name="age_of_chicken_days"
                    min="0"
                    value={formData.age_of_chicken_days}
                    onChange={handleChange}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yolk-yellow"
                    placeholder="Days"
                  />
                </div>
              </div>
              <p className="mt-2 text-xs text-slate-500">Informational only. This value is shown on the dashboard camera card.</p>
            </div>
          </div>

          <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-dark-slate"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-yolk-yellow px-5 py-2 text-sm font-semibold text-white shadow-[0_14px_32px_rgba(245,158,11,0.28)] transition-colors hover:bg-amber-500 disabled:opacity-70"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ModifyCameraModal;
