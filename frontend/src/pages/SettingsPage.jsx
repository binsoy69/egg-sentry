import React, { useState } from 'react';
import { KeyRound, ShieldCheck } from 'lucide-react';

import { authService } from '../services/auth';

const SettingsPage = () => {
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    if (formData.newPassword !== formData.confirmPassword) {
      setError('New password and confirmation must match.');
      return;
    }

    setLoading(true);
    try {
      const response = await authService.changePassword(formData.currentPassword, formData.newPassword);
      setSuccess(response.message || 'Password updated successfully.');
      setFormData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
      });
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to update password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold text-dark-slate">Settings</h1>
        <p className="mt-2 text-sm text-gray-500">Manage account security for the authenticated user.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <form onSubmit={handleSubmit} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-yolk-yellow">
              <KeyRound className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-dark-slate">Change Password</h2>
              <p className="mt-1 text-sm text-slate-500">Update your login credentials without leaving the app.</p>
            </div>
          </div>

          <div className="mt-6 space-y-5">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-dark-slate">Current password</span>
              <input
                type="password"
                name="currentPassword"
                value={formData.currentPassword}
                onChange={handleChange}
                required
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-dark-slate outline-none transition focus:border-yolk-yellow focus:ring-2 focus:ring-yolk-yellow/20"
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-dark-slate">New password</span>
              <input
                type="password"
                name="newPassword"
                value={formData.newPassword}
                onChange={handleChange}
                required
                minLength={6}
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-dark-slate outline-none transition focus:border-yolk-yellow focus:ring-2 focus:ring-yolk-yellow/20"
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-dark-slate">Confirm new password</span>
              <input
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                minLength={6}
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-dark-slate outline-none transition focus:border-yolk-yellow focus:ring-2 focus:ring-yolk-yellow/20"
              />
            </label>
          </div>

          {error ? (
            <div className="mt-5 rounded-2xl border border-alert-red/20 bg-alert-red/10 px-4 py-3 text-sm text-alert-red">
              {error}
            </div>
          ) : null}

          {success ? (
            <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {success}
            </div>
          ) : null}

          <div className="mt-6 flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="rounded-full bg-yolk-yellow px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-yolk-yellow/90 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {loading ? 'Updating...' : 'Update Password'}
            </button>
          </div>
        </form>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-dark-slate">Account Security</h2>
              <p className="mt-1 text-sm text-slate-500">Keep access limited to trusted farm staff.</p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            <div className="rounded-2xl bg-slate-50 px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Guidance</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Use a password that is different from device API keys and avoid sharing it between accounts.
              </p>
            </div>

            <div className="rounded-2xl bg-amber-50 px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Minimum rule</p>
              <p className="mt-2 text-sm leading-6 text-amber-800">
                New passwords must be at least 6 characters and cannot match the current password.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
