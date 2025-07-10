import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';

interface PerformanceRankingChartProps {
  data: Array<{
    symbol: string;
    company_name?: string;
    avg_daily_return: number;
    trading_days: number;
  }>;
  isLarge?: boolean;
}

export const PerformanceRankingChart: React.FC<PerformanceRankingChartProps> = ({
  data,
  isLarge = false
}) => {
  const formatPercent = (value: number): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">
            {data.symbol} - {data.company_name || 'Unknown Company'}
          </p>
          <p className="tooltip-value avg-return">
            Avg Daily Return: {formatPercent(data.avg_daily_return)}
          </p>
          <p className="tooltip-value trading-days">
            Trading Days: {data.trading_days}
          </p>
        </div>
      );
    }
    return null;
  };

  // Sort data by average daily return: negative values (left) to positive values (right)
  const sortedData = [...data].sort((a, b) => a.avg_daily_return - b.avg_daily_return);

  if (!data || data.length === 0) {
    return (
      <div className="chart-placeholder">
        <div className="chart-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
            <path d="M3 12h18m-9-9v18"/>
            <path d="M8 8l4 4 4-4"/>
          </svg>
        </div>
        <p>No data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={isLarge ? 400 : 200}>
      <BarChart
        data={sortedData}
        margin={{
          top: 5,
          right: 30,
          left: 20,
          bottom: isLarge ? 60 : 40,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis 
          dataKey="symbol"
          stroke="var(--color-text-secondary)"
          fontSize={12}
          angle={isLarge ? -45 : -90}
          textAnchor="end"
          height={isLarge ? 60 : 40}
        />
        <YAxis 
          tickFormatter={formatPercent}
          stroke="var(--color-text-secondary)"
          fontSize={12}
          label={{ value: 'Daily Return %', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="var(--color-border)" strokeWidth={2} />
        <Bar dataKey="avg_daily_return">
          {sortedData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.avg_daily_return >= 0 ? 'var(--color-success)' : 'var(--color-error)'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};