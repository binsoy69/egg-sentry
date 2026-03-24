import { useCallback, useEffect, useState } from 'react';

import { alertsService } from '../services/alerts';
import { dashboardService } from '../services/dashboard';

export const useDashboard = ({ weekParams, monthParams, year, chartRange, deviceId }) => {
  const weeklyMonth = weekParams.month;
  const weeklyYear = weekParams.year;
  const week = weekParams.week;
  const monthlyMonth = monthParams.month;
  const monthlyYear = monthParams.year;
  const fromDate = chartRange.from;
  const toDate = chartRange.to;
  const [summary, setSummary] = useState(null);
  const [weeklyStats, setWeeklyStats] = useState(null);
  const [monthlyStats, setMonthlyStats] = useState(null);
  const [yearlyStats, setYearlyStats] = useState(null);
  const [dailyChart, setDailyChart] = useState([]);
  const [sizeDistribution, setSizeDistribution] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dismissingAlertId, setDismissingAlertId] = useState(null);

  const fetchDashboardData = useCallback(async (isMounted = () => true) => {
    setLoading(true);
    try {
      const [summaryData, weeklyData, monthlyData, yearlyData, dailyData, sizeData, alertsData] = await Promise.all([
        dashboardService.getSummary(deviceId),
        dashboardService.getWeekly({ month: weeklyMonth, year: weeklyYear, week, deviceId }),
        dashboardService.getMonthly({ month: monthlyMonth, year: monthlyYear, deviceId }),
        dashboardService.getYearly({ year, deviceId }),
        dashboardService.getDailyChart({ from: fromDate, to: toDate, deviceId }),
        dashboardService.getSizeDistribution({ from: fromDate, to: toDate, deviceId }),
        alertsService.listAlerts({ status: 'active', limit: 5 }),
      ]);

      if (!isMounted()) {
        return;
      }

      setSummary(summaryData);
      setWeeklyStats(weeklyData);
      setMonthlyStats(monthlyData);
      setYearlyStats(yearlyData);
      setDailyChart(dailyData.data);
      setSizeDistribution(sizeData.data);
      setAlerts(alertsData.alerts);
      setError(null);
    } catch (err) {
      if (!isMounted()) {
        return;
      }
      setError(err.message || 'Failed to fetch dashboard data');
      console.error(err);
    } finally {
      if (isMounted()) {
        setLoading(false);
      }
    }
  }, [
    deviceId,
    fromDate,
    monthlyMonth,
    monthlyYear,
    toDate,
    week,
    weeklyMonth,
    weeklyYear,
    year,
  ]);

  useEffect(() => {
    let active = true;
    fetchDashboardData(() => active);
    return () => {
      active = false;
    };
  }, [fetchDashboardData]);

  const dismissAlert = async (alertId) => {
    setDismissingAlertId(alertId);
    try {
      await alertsService.dismissAlert(alertId);
      setAlerts((currentAlerts) => currentAlerts.filter((alert) => alert.id !== alertId));
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to dismiss alert');
      throw err;
    } finally {
      setDismissingAlertId(null);
    }
  };

  return {
    summary,
    weeklyStats,
    monthlyStats,
    yearlyStats,
    dailyChart,
    sizeDistribution,
    alerts,
    loading,
    error,
    refetch: () => fetchDashboardData(),
    dismissAlert,
    dismissingAlertId,
  };
};
