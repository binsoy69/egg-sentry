import { useState, useEffect, useCallback } from 'react';
import { devicesService } from '../services/devices';

const CHICKEN_AGE_STORAGE_KEY = 'egg-sentry:device-chicken-age';

const readChickenAgeMap = () => {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const storedValue = window.localStorage.getItem(CHICKEN_AGE_STORAGE_KEY);
    if (!storedValue) {
      return {};
    }

    const parsedValue = JSON.parse(storedValue);
    return parsedValue && typeof parsedValue === 'object' ? parsedValue : {};
  } catch (error) {
    console.error('Failed to read stored chicken ages', error);
    return {};
  }
};

const writeChickenAgeMap = (ageMap) => {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.localStorage.setItem(CHICKEN_AGE_STORAGE_KEY, JSON.stringify(ageMap));
  } catch (error) {
    console.error('Failed to store chicken ages', error);
  }
};

const mergeChickenAge = (devices) => {
  const chickenAgeMap = readChickenAgeMap();

  return devices.map((device) => ({
    ...device,
    age_of_chicken: chickenAgeMap[device.device_id] ?? device.age_of_chicken ?? null,
  }));
};

export const useDevices = () => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    try {
      const data = await devicesService.getDevices();
      setDevices(mergeChickenAge(data));
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
            ? { ...updatedDevice, age_of_chicken: device.age_of_chicken ?? null }
            : device
        ))
      );
      return updatedDevice;
    } catch (err) {
      console.error('Failed to update device', err);
      throw err;
    }
  };

  const updateDeviceChickenAge = useCallback((deviceId, chickenAge) => {
    const nextChickenAgeMap = readChickenAgeMap();

    if (chickenAge === null || chickenAge === undefined || chickenAge === '') {
      delete nextChickenAgeMap[deviceId];
    } else {
      nextChickenAgeMap[deviceId] = chickenAge;
    }

    writeChickenAgeMap(nextChickenAgeMap);
    setDevices((prev) =>
      prev.map((device) => (
        device.device_id === deviceId
          ? { ...device, age_of_chicken: chickenAge === '' ? null : chickenAge }
          : device
      ))
    );
  }, []);

  const updateDeviceConfig = async (deviceId, isConfigActive) => {
    try {
      const updatedDevice = await devicesService.toggleDeviceConfig(deviceId, isConfigActive);
      setDevices((prev) =>
        prev.map((device) => (
          device.device_id === deviceId
            ? { ...updatedDevice, age_of_chicken: device.age_of_chicken ?? null }
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

  return {
    devices,
    loading,
    error,
    updateDevice,
    updateDeviceChickenAge,
    updateDeviceConfig,
    refetch: fetchDevices,
  };
};
