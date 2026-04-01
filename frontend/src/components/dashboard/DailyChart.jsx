import React from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { format, parseISO } from 'date-fns';

const DailyChart = ({ data }) => {
  const formatXAxis = (tickItem) => {
    try {
      return format(parseISO(tickItem), 'MMM dd');
    } catch {
      return tickItem;
    }
  };

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-400 border border-dashed border-gray-200 rounded-lg">
        No daily data available for this period.
      </div>
    );
  }

  return (
    <div className="h-64 w-full sm:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 8, left: -18, bottom: 5 }}>
          <defs>
            <linearGradient id="egg-production-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#FDB813" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#FDB813" stopOpacity={0.04} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
          <XAxis
            dataKey="date"
            tickFormatter={formatXAxis}
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#6B7280', fontSize: 11 }}
            dy={10}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#6B7280', fontSize: 11 }}
            dx={-10}
          />
          <Tooltip
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
            labelFormatter={(label) => {
              try {
                return format(parseISO(label), 'MMMM dd, yyyy');
              } catch {
                return label;
              }
            }}
          />
          <Area
            type="monotone"
            dataKey="count"
            name="Eggs Collected"
            stroke="#FDB813"
            fill="url(#egg-production-fill)"
            strokeWidth={3}
            dot={{ r: 4, fill: '#FDB813', strokeWidth: 0 }}
            activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DailyChart;
