import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';
import { formatCurrency, formatCurrencyForChart, formatDateForChart } from '../../shared/formatters';

interface StockPLChartProps {
  data: Array<{
    date: string;
    [key: string]: number | string; // Dynamic stock symbols as keys for P&L values
  }>;
  stocks: Array<{
    symbol: string;
    company_name?: string;
    color: string;
  }>;
  currency: string;
  isLarge?: boolean;
}

export const StockPLChart: React.FC<StockPLChartProps> = ({
  data,
  stocks,
  currency,
  isLarge = false
}) => {

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{formatDateForChart(label)}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="tooltip-value" style={{ color: entry.color }}>
              {entry.dataKey} P&L: {formatCurrency(entry.value, currency)}
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
          tickFormatter={formatDateForChart}
          stroke="var(--color-text-secondary)"
          fontSize={12}
        />
        <YAxis 
          tickFormatter={(value) => formatCurrencyForChart(value, currency)}
          stroke="var(--color-text-secondary)"
          fontSize={12}
        />
        <Tooltip content={<CustomTooltip />} />
        {isLarge && <Legend />}
        <ReferenceLine y={0} stroke="var(--color-border)" strokeWidth={2} />
        {stocks.map((stock, index) => (
          <Line
            key={`${stock.symbol}_pl`}
            type="monotone"
            dataKey={`${stock.symbol}_pl`}
            stroke={stock.color}
            strokeWidth={2}
            dot={{ fill: stock.color, strokeWidth: 2, r: 3 }}
            activeDot={{ r: 5, stroke: stock.color, strokeWidth: 2 }}
            connectNulls={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
};