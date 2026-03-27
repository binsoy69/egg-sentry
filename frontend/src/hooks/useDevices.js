import { useState, useEffect, useCallback } from 'react';
import { devicesService } from '../services/devices';

const DAY_IN_MS = 24 * 60 * 60 * 1000;
const APP_TIMEZONE = 'Asia/Manila';
const APP_DATE_FORMATTER = new Intl.DateTimeFormat('en-CA', {
  timeZone: APP_TIMEZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

const normalizeAgeUnit = (value) => {
  if (value === '' || value === null || value === undefined) {
    return null;
  }

  const parsedValue = Number(value);
  if (!Number.isFinite(parsedValue)) {
    return null;
  }

  return Math.max(0, Math.trunc(parsedValue));
};

const normalizeChickenAge = (value) => {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  if (typeof value === 'number' || typeof value === 'string') {
    const normalizedValue = normalizeAgeUnit(value);
    if (normalizedValue === null) {
      return null;
    }

    return {
      weeks: Math.floor(normalizedValue / 7),
      days: normalizedValue % 7,
    };
  }

  if (typeof value !== 'object') {
    return null;
  }

  const weeks = normalizeAgeUnit(value.weeks);
  const days = normalizeAgeUnit(value.days);

  if (weeks === null && days === null) {
    return null;
  }

  const totalDays = (weeks ?? 0) * 7 + (days ?? 0);

  return {
    weeks: Math.floor(totalDays / 7),
    days: totalDays % 7,
  };
};

const buildChickenAgeRecord = (value, fallbackSetAt = new Date().toISOString()) => {
  const normalizedAge = normalizeChickenAge(value);
  if (!normalizedAge) {
    return null;
  }

  const rawSetAt =
    typeof value === 'object' && value !== null ? value.set_at ?? value.setAt ?? null : null;
  const parsedSetAt = rawSetAt ? Date.parse(rawSetAt) : Number.NaN;

  return {
    weeks: normalizedAge.weeks,
    days: normalizedAge.days,
    set_at: Number.isNaN(parsedSetAt) ? fallbackSetAt : new Date(parsedSetAt).toISOString(),
  };
};

const getTimezoneDateKey = (value) => {
  const parts = APP_DATE_FORMATTER.formatToParts(new Date(value));
  const year = Number(parts.find((part) => part.type === 'year')?.value);
  const month = Number(parts.find((part) => part.type === 'month')?.value);
  const day = Number(parts.find((part) => part.type === 'day')?.value);

  return { year, month, day };
};

const getElapsedCalendarDays = (start, end) => {
  const startDateKey = getTimezoneDateKey(start);
  const endDateKey = getTimezoneDateKey(end);
  const startUtcDay = Date.UTC(startDateKey.year, startDateKey.month - 1, startDateKey.day);
  const endUtcDay = Date.UTC(endDateKey.year, endDateKey.month - 1, endDateKey.day);

  return Math.max(0, Math.floor((endUtcDay - startUtcDay) / DAY_IN_MS));
};

const resolveChickenAge = (value, now = Date.now()) => {
  const record = buildChickenAgeRecord(value);
  if (!record) {
    return null;
  }

  const elapsedDays = getElapsedCalendarDays(record.set_at, now);
  const totalDays = record.weeks * 7 + record.days + elapsedDays;

  return {
    weeks: Math.floor(totalDays / 7),
    days: totalDays % 7,
  };
};

const mapDeviceChickenAge = (device) => {
  const ageRecord = buildChickenAgeRecord(device.age_of_chicken);

  return {
    ...device,
    age_of_chicken: resolveChickenAge(ageRecord),
    age_of_chicken_record: ageRecord,
  };
};

export const useDevices = () => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refreshDisplayedChickenAges = useCallback(() => {
    setDevices((prev) =>
      prev.map((device) => {
        const nextAge = resolveChickenAge(device.age_of_chicken_record);
        const currentAge = device.age_of_chicken;

        if (currentAge?.weeks === nextAge?.weeks && currentAge?.days === nextAge?.days) {
          return device;
        }

        return {
          ...device,
          age_of_chicken: nextAge,
        };
      })
    );
  }, []);

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    try {
      const data = await devicesService.getDevices();
      setDevices(data.map(mapDeviceChickenAge));
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to fetch devices');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const updateDevice = async (deviceId, payload) => {
    try {
      const updatedDevice = await devicesService.updateDevice(deviceId, payload);
      setDevices((prev) =>
        prev.map((device) => (
          device.device_id === deviceId
            ? mapDeviceChickenAge(updatedDevice)
            : device
        ))
      );
      return updatedDevice;
    } catch (err) {
      console.error('Failed to update device', err);
      throw err;
    }
  };

  const updateDeviceConfig = async (deviceId, isConfigActive) => {
    try {
      const updatedDevice = await devicesService.toggleDeviceConfig(deviceId, isConfigActive);
      setDevices((prev) =>
        prev.map((device) => (
          device.device_id === deviceId
            ? mapDeviceChickenAge(updatedDevice)
            : device
        ))
      );
      return updatedDevice;
    } catch (err) {
      console.error('Failed to update device config', err);
      fetchDevices();
      throw err;
    }
  };

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  useEffect(() => {
    refreshDisplayedChickenAges();

    const intervalId = window.setInterval(refreshDisplayedChickenAges, 60 * 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [refreshDisplayedChickenAges]);

  return {
    devices,
    loading,
    error,
    updateDevice,
    updateDeviceConfig,
    refetch: fetchDevices,
  };
};
