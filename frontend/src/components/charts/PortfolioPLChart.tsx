import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { formatCurrency, formatCurrencyForChart, formatDateForChart } from '../../shared/formatters';

interface PortfolioPLChartProps {
  data: Array<{
    date: string;
    unrealized_pl: number;
    realized_pl: number;
    total_pl: number;
  }>;
  currency: string;
  isLarge?: boolean;
  timePeriod?: '30D' | '1Y' | '1W' | '1D' | 'ALL';
}

export const PortfolioPLChart: React.FC<PortfolioPLChartProps> = ({
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
          <p className="tooltip-value total-pl">
            Total P&L: {formatCurrency(payload[0].value, currency)}
          </p>
          <p className="tooltip-value unrealized-pl">
            Unrealized: {formatCurrency(payload[1].value, currency)}
          </p>
          <p className="tooltip-value realized-pl">
            Realized: {formatCurrency(payload[2].value, currency)}
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
        <ReferenceLine y={0} stroke="var(--color-border)" strokeWidth={2} />
        <Line
          type="monotone"
          dataKey="total_pl"
          stroke="var(--color-primary)"
          strokeWidth={3}
          dot={{ fill: 'var(--color-primary)', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6, stroke: 'var(--color-primary)', strokeWidth: 2 }}
        />
        <Line
          type="monotone"
          dataKey="unrealized_pl"
          stroke="var(--color-success)"
          strokeWidth={2}
          strokeDasharray="5 5"
          dot={{ fill: 'var(--color-success)', strokeWidth: 2, r: 3 }}
          activeDot={{ r: 5, stroke: 'var(--color-success)', strokeWidth: 2 }}
        />
        <Line
          type="monotone"
          dataKey="realized_pl"
          stroke="var(--color-secondary)"
          strokeWidth={2}
          strokeDasharray="3 3"
          dot={{ fill: 'var(--color-secondary)', strokeWidth: 2, r: 3 }}
          activeDot={{ r: 5, stroke: 'var(--color-secondary)', strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};