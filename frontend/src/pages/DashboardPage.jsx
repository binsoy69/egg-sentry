import React, { useMemo, useState } from 'react';
import { BarChart3, CalendarDays, CalendarRange, Egg, TrendingUp } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

import AlertPanel from '../components/dashboard/AlertPanel';
import CameraCard from '../components/dashboard/CameraCard';
import DailyChart from '../components/dashboard/DailyChart';
import MetricCard from '../components/dashboard/MetricCard';
import PeriodCard from '../components/dashboard/PeriodCard';
import SizeDistChart from '../components/dashboard/SizeDistChart';
import ModifyCameraModal from '../components/settings/ModifyCameraModal';
import { useDashboard } from '../hooks/useDashboard';
import { useDevices } from '../hooks/useDevices';

const MONTH_OPTIONS = [
  { value: 1, label: 'January', shortLabel: 'Jan' },
  { value: 2, label: 'February', shortLabel: 'Feb' },
  { value: 3, label: 'March', shortLabel: 'Mar' },
  { value: 4, label: 'April', shortLabel: 'Apr' },
  { value: 5, label: 'May', shortLabel: 'May' },
  { value: 6, label: 'June', shortLabel: 'Jun' },
  { value: 7, label: 'July', shortLabel: 'Jul' },
  { value: 8, label: 'August', shortLabel: 'Aug' },
  { value: 9, label: 'September', shortLabel: 'Sep' },
  { value: 10, label: 'October', shortLabel: 'Oct' },
  { value: 11, label: 'November', shortLabel: 'Nov' },
  { value: 12, label: 'December', shortLabel: 'Dec' },
];

const buildYearOptions = (currentYear) =>
  Array.from({ length: 5 }, (_, index) => {
    const year = currentYear - 2 + index;
    return { value: year, label: String(year) };
  });

const buildWeekOptions = (year, month) => {
  const daysInMonth = new Date(year, month, 0).getDate();
  const weekCount = Math.ceil(daysInMonth / 7);

  return Array.from({ length: weekCount }, (_, index) => {
    const week = index + 1;
    const start = 1 + index * 7;
    const end = Math.min(start + 6, daysInMonth);
    return {
      value: week,
      label: `Week ${week} (${start}-${end})`,
    };
  });
};

const formatApiDate = (date) => date.toISOString().slice(0, 10);

const DashboardPage = () => {
  const today = useMemo(() => new Date(), []);
  const currentYear = today.getFullYear();
  const currentMonth = today.getMonth() + 1;
  const currentWeek = Math.floor((today.getDate() - 1) / 7) + 1;
  const [searchParams, setSearchParams] = useSearchParams();
  const [weekParams, setWeekParams] = useState({ month: currentMonth, year: currentYear, week: currentWeek });
  const [monthParams, setMonthParams] = useState({ month: currentMonth, year: currentYear });
  const [year, setYear] = useState(currentYear);
  const yearOptions = useMemo(() => buildYearOptions(currentYear), [currentYear]);
  const weekOptions = useMemo(
    () => buildWeekOptions(weekParams.year, weekParams.month),
    [weekParams.month, weekParams.year]
  );
  const resolvedWeek = weekOptions.some((option) => option.value === weekParams.week) ? weekParams.week : 1;
  const chartRange = useMemo(() => {
    const from = new Date(monthParams.year, monthParams.month - 1, 1);
    const to = new Date(monthParams.year, monthParams.month, 0);
    return {
      from: formatApiDate(from),
      to: formatApiDate(to),
    };
  }, [monthParams.month, monthParams.year]);

  const {
    devices,
    updateDevice,
    loading: devicesLoading,
    error: devicesError,
    refetch: refetchDevices,
  } = useDevices();
  const primaryDevice = devices[0] ?? null;
  const selectedDevice = searchParams.get('modifyCamera') === '1' ? primaryDevice : null;

  const {
    summary,
    weeklyStats,
    monthlyStats,
    yearlyStats,
    dailyChart,
    sizeDistribution,
    alerts,
    loading: dashLoading,
    error: dashboardError,
    dismissAlert,
    dismissingAlertId,
  } = useDashboard({
    weekParams: { ...weekParams, week: resolvedWeek },
    monthParams,
    year,
    chartRange,
    deviceId: primaryDevice?.device_id,
  });

  const closeModifyModal = () => {
    const nextSearch = new URLSearchParams(searchParams);
    nextSearch.delete('modifyCamera');
    setSearchParams(nextSearch);
  };

  const saveDeviceCounts = async (formData) => {
    if (!selectedDevice) {
      return;
    }
    await updateDevice(selectedDevice.device_id, formData);
    await refetchDevices();
  };

  const totalToday = summary?.today_eggs || 0;
  const allTimeEggs = summary?.all_time_eggs || 0;
  const bestDayLabel = summary?.best_day?.date
    ? `${summary.best_day.date} (${summary.best_day.count})`
    : 'No data';
  const topSizeLabel = summary?.top_size?.size_display
    ? `${summary.top_size.size_display} (${summary.top_size.count})`
    : 'No data';
  const errorMessage = dashboardError || devicesError;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold text-dark-slate">Dashboard</h1>
        <p className="mt-2 text-sm text-gray-500">Egg production overview and analytics</p>
      </div>

      {errorMessage ? (
        <div className="rounded-xl border border-alert-red/20 bg-alert-red/10 px-4 py-3 text-sm text-alert-red">
          {errorMessage}
        </div>
      ) : null}

      <AlertPanel
        alerts={alerts}
        loading={dashLoading || devicesLoading}
        dismissingAlertId={dismissingAlertId}
        onDismiss={dismissAlert}
      />

      {primaryDevice ? (
        <CameraCard device={summary?.device || primaryDevice} />
      ) : (
        <div className="rounded-xl border border-dashed border-gray-200 bg-white px-6 py-10 text-center text-gray-500">
          No camera device found.
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <PeriodCard
          title="Weekly"
          icon={CalendarDays}
          accentClass="bg-sky-100 text-sky-600"
          averageClass="text-sky-600"
          total={weeklyStats?.total_eggs ?? 0}
          average={weeklyStats?.avg_per_day ?? 0}
          controls={[
            {
              label: 'Week month',
              value: String(weekParams.month),
              onChange: (value) => setWeekParams((prev) => ({ ...prev, month: Number(value), week: 1 })),
              options: MONTH_OPTIONS.map((option) => ({ value: String(option.value), label: option.shortLabel })),
            },
            {
              label: 'Week',
              value: String(resolvedWeek),
              onChange: (value) => setWeekParams((prev) => ({ ...prev, week: Number(value) })),
              options: weekOptions.map((option) => ({ value: String(option.value), label: option.label })),
            },
          ]}
        />

        <PeriodCard
          title="Monthly"
          icon={CalendarRange}
          accentClass="bg-emerald-100 text-emerald-600"
          averageClass="text-emerald-600"
          total={monthlyStats?.total_eggs ?? 0}
          average={monthlyStats?.avg_per_day ?? 0}
          controls={[
            {
              label: 'Month',
              value: String(monthParams.month),
              onChange: (value) => setMonthParams((prev) => ({ ...prev, month: Number(value) })),
              options: MONTH_OPTIONS.map((option) => ({ value: String(option.value), label: option.label })),
            },
            {
              label: 'Month year',
              value: String(monthParams.year),
              onChange: (value) => setMonthParams((prev) => ({ ...prev, year: Number(value) })),
              options: yearOptions.map((option) => ({ value: String(option.value), label: option.label })),
            },
          ]}
        />

        <PeriodCard
          title="Yearly"
          icon={TrendingUp}
          accentClass="bg-violet-100 text-violet-600"
          averageClass="text-violet-600"
          total={yearlyStats?.total_eggs ?? 0}
          average={yearlyStats?.avg_per_day ?? 0}
          controls={[
            {
              label: 'Year',
              value: String(year),
              onChange: (value) => setYear(Number(value)),
              options: yearOptions.map((option) => ({ value: String(option.value), label: option.label })),
            },
          ]}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Today's Eggs" value={totalToday} icon={Egg} color="yolk-yellow" />
        <MetricCard title="All Time" value={allTimeEggs} icon={TrendingUp} color="yolk-yellow" />
        <MetricCard title="Best Day" value={bestDayLabel} icon={CalendarDays} color="yolk-yellow" />
        <MetricCard title="Top Size" value={topSizeLabel} icon={BarChart3} color="yolk-yellow" />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2 rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-dark-slate">Daily Egg Production</h2>
          <div className="flex min-h-[16rem] items-center justify-center">
            {dashLoading || devicesLoading ? (
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-yolk-yellow border-t-transparent"></div>
            ) : (
              <DailyChart data={dailyChart} />
            )}
          </div>
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-dark-slate">Egg Size Distribution</h2>
          <div className="flex min-h-[16rem] items-center justify-center">
            {dashLoading || devicesLoading ? (
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-sage-green border-t-transparent"></div>
            ) : (
              <SizeDistChart data={sizeDistribution} />
            )}
          </div>
        </div>
      </div>

      {selectedDevice ? (
        <ModifyCameraModal
          device={selectedDevice}
          onClose={closeModifyModal}
          onSave={saveDeviceCounts}
        />
      ) : null}
    </div>
  );
};

export default DashboardPage;
