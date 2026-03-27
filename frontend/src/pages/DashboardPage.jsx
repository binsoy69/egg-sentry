import React, { useMemo, useState } from 'react';
import { Archive, BarChart3, CalendarDays, CalendarRange, Egg, HandCoins, TrendingUp } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

import AlertPanel from '../components/dashboard/AlertPanel';
import CameraCard from '../components/dashboard/CameraCard';
import CollectionHistoryPanel from '../components/dashboard/CollectionHistoryPanel';
import CollectEggsModal from '../components/dashboard/CollectEggsModal';
import DailyChart from '../components/dashboard/DailyChart';
import MetricCard from '../components/dashboard/MetricCard';
import PeriodCard from '../components/dashboard/PeriodCard';
import SizeDistChart from '../components/dashboard/SizeDistChart';
import ModifyCameraModal from '../components/settings/ModifyCameraModal';
import { useDashboard } from '../hooks/useDashboard';
import { useDevices } from '../hooks/useDevices';
import { collectionsService } from '../services/collections';

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
  const [collectModalOpen, setCollectModalOpen] = useState(false);
  const [collectionError, setCollectionError] = useState('');
  const [collectionMessage, setCollectionMessage] = useState('');
  const [collecting, setCollecting] = useState(false);
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
    updateDeviceChickenAge,
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
    refetch: refetchDashboard,
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

    const { age_of_chicken_days, age_of_chicken_weeks, ...devicePayload } = formData;

    await updateDevice(selectedDevice.device_id, devicePayload);
    updateDeviceChickenAge(selectedDevice.device_id, {
      weeks: age_of_chicken_weeks,
      days: age_of_chicken_days,
    });
    await Promise.all([refetchDevices(), refetchDashboard()]);
  };

  const cameraDevice = primaryDevice
    ? { ...(summary?.device ?? {}), ...primaryDevice }
    : null;
  const currentEggs = summary?.current_eggs ?? summary?.device?.current_count ?? primaryDevice?.current_count ?? 0;
  const collectedToday = summary?.collected_today ?? summary?.device?.collected_today ?? primaryDevice?.collected_today ?? 0;
  const totalToday = summary?.today_eggs ?? summary?.total_today ?? currentEggs + collectedToday;
  const allTimeEggs = summary?.all_time_eggs || 0;
  const bestDayLabel = summary?.best_day?.date
    ? `${summary.best_day.date} (${summary.best_day.count})`
    : 'No data';
  const topSizeLabel = summary?.top_size?.size_display
    ? `${summary.top_size.size_display} (${summary.top_size.count})`
    : 'No data';
  const collectionHistory = summary?.collection_history ?? [];
  const errorMessage = dashboardError || devicesError;

  const handleCollectEggs = async () => {
    if (!primaryDevice) {
      return;
    }

    setCollecting(true);
    setCollectionError('');
    setCollectionMessage('');
    try {
      const response = await collectionsService.collectEggs(primaryDevice.device_id);
      await Promise.all([refetchDashboard(), refetchDevices()]);
      setCollectionMessage(`Logged a collection entry for ${response.entry.count} eggs.`);
      setCollectModalOpen(false);
    } catch (err) {
      setCollectionError(err.response?.data?.detail || err.message || 'Failed to collect eggs.');
    } finally {
      setCollecting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-dark-slate sm:text-3xl">Dashboard</h1>
          <p className="mt-2 text-sm text-gray-500">Egg production overview, live nest count, and collection tracking</p>
        </div>

        <button
          type="button"
          onClick={() => {
            setCollectionError('');
            setCollectModalOpen(true);
          }}
          disabled={!primaryDevice || currentEggs <= 0 || dashLoading || devicesLoading}
          className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-yolk-yellow px-5 py-3 text-sm font-semibold text-white transition hover:bg-yolk-yellow/90 disabled:cursor-not-allowed disabled:bg-slate-300 sm:w-auto"
        >
          <HandCoins className="h-4 w-4" />
          Collect Eggs
        </button>
      </div>

      {errorMessage ? (
        <div className="rounded-xl border border-alert-red/20 bg-alert-red/10 px-4 py-3 text-sm text-alert-red">
          {errorMessage}
        </div>
      ) : null}

      {collectionMessage ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {collectionMessage}
        </div>
      ) : null}

      <AlertPanel
        alerts={alerts}
        loading={dashLoading || devicesLoading}
        dismissingAlertId={dismissingAlertId}
        onDismiss={dismissAlert}
      />

      {cameraDevice ? (
        <CameraCard
          device={cameraDevice}
          currentCount={currentEggs}
          collectedToday={collectedToday}
        />
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

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        <MetricCard title="Current Eggs" value={currentEggs} icon={Egg} color="yolk-yellow" />
        <MetricCard title="Today's Total" value={totalToday} icon={Archive} color="yolk-yellow" />
        <MetricCard title="Collected Today" value={collectedToday} icon={HandCoins} color="yolk-yellow" />
        <MetricCard title="All Time" value={allTimeEggs} icon={TrendingUp} color="yolk-yellow" />
        <MetricCard title="Best Day" value={bestDayLabel} icon={CalendarDays} color="yolk-yellow" />
        <MetricCard title="Top Size" value={topSizeLabel} icon={BarChart3} color="yolk-yellow" />
      </div>

      <CollectionHistoryPanel entries={collectionHistory} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2 rounded-xl border border-gray-100 bg-white p-4 shadow-sm sm:p-6">
          <h2 className="mb-4 text-lg font-semibold text-dark-slate">Daily Egg Production</h2>
          <div className="flex min-h-[16rem] items-center justify-center">
            {dashLoading || devicesLoading ? (
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-yolk-yellow border-t-transparent"></div>
            ) : (
              <DailyChart data={dailyChart} />
            )}
          </div>
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm sm:p-6">
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

      <CollectEggsModal
        isOpen={collectModalOpen}
        currentEggs={currentEggs}
        onCancel={() => setCollectModalOpen(false)}
        onConfirm={handleCollectEggs}
        loading={collecting}
        error={collectionError}
      />
    </div>
  );
};

export default DashboardPage;
