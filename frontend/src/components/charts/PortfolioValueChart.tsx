import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { formatCurrency, formatCurrencyForChart, formatDateForChart } from '../../shared/formatters';

interface PortfolioValueChartProps {
  data: Array<{
    date: string;
    total_value: number;
    total_cost: number;
  }>;
  currency: string;
  isLarge?: boolean;
  timePeriod?: '30D' | '1Y' | '1W' | '1D' | 'ALL';
}

export const PortfolioValueChart: React.FC<PortfolioValueChartProps> = ({
  data,
  currency,
  isLarge = false,
  timePeriod
}) => {

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{formatDateForChart(label, timePeriod)}</p>
          <p className="tooltip-value portfolio-value">
            Portfolio Value: {formatCurrency(payload[0].value, currency)}
          </p>
          <p className="tooltip-value cost-basis">
            Cost Basis: {formatCurrency(payload[1].value, currency)}
          </p>
        </div>
      );
    }
    return null;
  };

  if (!data || data.length === 0) {
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
          tickFormatter={(value) => formatCurrencyForChart(value, currency)}
          stroke="var(--color-text-secondary)"
          fontSize={12}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="total_value"
          stroke="var(--color-primary)"
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="total_cost"
          stroke="var(--color-text-secondary)"
          strokeWidth={2}
          strokeDasharray="5 5"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};