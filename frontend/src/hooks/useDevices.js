import { useState, useEffect, useCallback } from 'react';
import { devicesService } from '../services/devices';

export const useDevices = () => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    try {
      const data = await devicesService.getDevices();
      setDevices(data);
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
        prev.map((device) => device.device_id === deviceId ? updatedDevice : device)
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
        prev.map((device) => device.device_id === deviceId ? updatedDevice : device)
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

  return { devices, loading, error, updateDevice, updateDeviceConfig, refetch: fetchDevices };
};
