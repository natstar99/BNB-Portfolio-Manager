import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface PortfolioValueChartProps {
  data: Array<{
    date: string;
    total_value: number;
    total_cost: number;
  }>;
  currency: string;
  isLarge?: boolean;
}

export const PortfolioValueChart: React.FC<PortfolioValueChartProps> = ({
  data,
  currency,
  isLarge = false
}) => {
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{formatDate(label)}</p>
          <p className="tooltip-value portfolio-value">
            Portfolio Value: {formatCurrency(payload[0].value)}
          </p>
          <p className="tooltip-value cost-basis">
            Cost Basis: {formatCurrency(payload[1].value)}
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
          tickFormatter={formatDate}
          stroke="var(--color-text-secondary)"
          fontSize={12}
        />
        <YAxis 
          tickFormatter={formatCurrency}
          stroke="var(--color-text-secondary)"
          fontSize={12}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="total_value"
          stroke="var(--color-primary)"
          strokeWidth={2}
          dot={{ fill: 'var(--color-primary)', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6, stroke: 'var(--color-primary)', strokeWidth: 2 }}
        />
        <Line
          type="monotone"
          dataKey="total_cost"
          stroke="var(--color-text-secondary)"
          strokeWidth={2}
          strokeDasharray="5 5"
          dot={{ fill: 'var(--color-text-secondary)', strokeWidth: 2, r: 3 }}
          activeDot={{ r: 5, stroke: 'var(--color-text-secondary)', strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};