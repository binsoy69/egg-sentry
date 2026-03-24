import React from 'react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 rounded-lg shadow-md border border-gray-100 text-sm">
        <p className="font-semibold text-dark-slate">{`Size ${payload[0].payload.display}`}</p>
        <p className="text-gray-600">
          Count: <span className="font-bold text-dark-slate">{payload[0].value}</span>
        </p>
      </div>
    );
  }
  return null;
};

const SizeDistChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-400 border border-dashed border-gray-200 rounded-lg">
        No size distribution data available.
      </div>
    );
  }

  const COLORS = {
    small: '#3B82F6',
    medium: '#22C55E',
    large: '#F59E0B',
    'extra-large': '#8B5CF6',
    jumbo: '#EF4444',
  };

  return (
    <div className="h-64 w-full sm:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 6, left: -18, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
          <XAxis dataKey="display" axisLine={false} tickLine={false} tick={{ fill: '#6B7280', fontSize: 11 }} />
          <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6B7280', fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="count" radius={[8, 8, 0, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.size}
                fill={COLORS[entry.size] || '#9CA3AF'}
                stroke="transparent"
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default SizeDistChart;
