import React from 'react';
import clsx from 'clsx';
import { AlertTriangle, BellRing, CheckCircle2, Info, ShieldAlert } from 'lucide-react';

const severityStyles = {
  critical: {
    accent: 'border-alert-red/20 bg-red-50 text-alert-red',
    badge: 'bg-alert-red text-white',
    icon: AlertTriangle,
  },
  warning: {
    accent: 'border-yolk-yellow/30 bg-amber-50 text-dark-slate',
    badge: 'bg-yolk-yellow text-white',
    icon: ShieldAlert,
  },
  info: {
    accent: 'border-sky-200 bg-sky-50 text-dark-slate',
    badge: 'bg-sky-500 text-white',
    icon: Info,
  },
};

const typeLabels = {
  device_offline: 'Device Offline',
  low_production: 'Low Production',
  uncertain_detection: 'Uncertain Detection',
  missing_data: 'Missing Data',
};

const formatTimestamp = (value) =>
  new Date(value).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

const AlertPanel = ({ alerts, loading, dismissingAlertId, onDismiss }) => {
  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 animate-pulse rounded-2xl bg-slate-100"></div>
          <div className="space-y-2">
            <div className="h-4 w-28 animate-pulse rounded bg-slate-100"></div>
            <div className="h-3 w-56 animate-pulse rounded bg-slate-100"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!alerts.length) {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-sage-green shadow-sm">
            <CheckCircle2 className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sage-green">Alerts</p>
            <h2 className="mt-1 text-lg font-semibold text-dark-slate">All monitoring checks are clear</h2>
            <p className="mt-1 text-sm text-slate-600">
              Heartbeats, production checks, and detection quality are currently within expected ranges.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-2 border-b border-slate-100 pb-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-yolk-yellow">
            <BellRing className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Alerts</p>
            <h2 className="text-lg font-semibold text-dark-slate">
              {alerts.length} active {alerts.length === 1 ? 'alert' : 'alerts'}
            </h2>
          </div>
        </div>
        <p className="text-sm text-slate-500">Dashboard-only operational alerts for the monitored coop.</p>
      </div>

      <div className="mt-4 space-y-3">
        {alerts.map((alert) => {
          const severity = severityStyles[alert.severity] || severityStyles.info;
          const Icon = severity.icon;

          return (
            <div key={alert.id} className={clsx('rounded-2xl border px-4 py-4', severity.accent)}>
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex gap-3">
                  <div className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-2xl bg-white/90 shadow-sm">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={clsx(
                          'rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]',
                          severity.badge
                        )}
                      >
                        {alert.severity}
                      </span>
                      <span className="text-sm font-semibold text-dark-slate">
                        {typeLabels[alert.type] || alert.type}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{alert.message}</p>
                    <p className="mt-2 text-xs font-medium uppercase tracking-[0.14em] text-slate-400">
                      {`${alert.device_id || 'System'} | ${formatTimestamp(alert.created_at)}`}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => onDismiss(alert.id)}
                  disabled={dismissingAlertId === alert.id}
                  className="inline-flex items-center justify-center rounded-xl border border-white/70 bg-white px-4 py-2 text-sm font-semibold text-dark-slate shadow-sm transition hover:border-slate-200 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {dismissingAlertId === alert.id ? 'Dismissing...' : 'Dismiss'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AlertPanel;
