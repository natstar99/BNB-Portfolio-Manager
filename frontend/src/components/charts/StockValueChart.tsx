import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { formatCurrency, formatCurrencyForChart, formatDateForChart } from '../../shared/formatters';

interface StockValueChartProps {
  data: Array<{
    date: string;
    [key: string]: number | string; // Dynamic stock symbols as keys
  }>;
  stocks: Array<{
    symbol: string;
    company_name?: string;
    color: string;
  }>;
  currency: string;
  isLarge?: boolean;
  timePeriod?: '30D' | '1Y' | '1W' | '1D' | 'ALL';
}

export const StockValueChart: React.FC<StockValueChartProps> = ({
  data,
  stocks,
  currency,
  isLarge = false,
  timePeriod
}) => {
  const formatCurrencyLocal = (value: number): string => {
    return formatCurrencyForChart(value, currency);
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{formatDateForChart(label, timePeriod)}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="tooltip-value" style={{ color: entry.color }}>
              {entry.dataKey}: {formatCurrency(entry.value, currency)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (!data || data.length === 0 || !stocks || stocks.length === 0) {
    return (
      <div className="chart-placeholder">
        <div className="chart-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
            <path d="M3 3v18h18"/>
            <path d="M7 16l4-4 4 4 6-6"/>
          </svg>
        </div>
        <p>No data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={isLarge ? 400 : 200}>
      <LineChart
        data={data}
        margin={{
          top: 5,
          right: 30,
          left: 20,
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis 
          dataKey="date" 
          tickFormatter={(value) => formatDateForChart(value, timePeriod)}
          stroke="var(--color-text-secondary)"
          fontSize={12}
        />
        <YAxis 
          tickFormatter={formatCurrencyLocal}
          stroke="var(--color-text-secondary)"
          fontSize={12}
        />
        <Tooltip content={<CustomTooltip />} />
        {isLarge && <Legend />}
        {stocks.map((stock, index) => (
          <Line
            key={stock.symbol}
            type="monotone"
            dataKey={stock.symbol}
            stroke={stock.color}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
};