import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Brush } from 'recharts';
import { formatCurrency, formatCurrencyForChart, formatDateForChart } from '../../shared/formatters';

interface PortfolioPLChartProps {
  data: Array<{
    date: string;
    unrealized_pl: number;
    realized_pl: number;
    total_return: number;
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
  const [zeroAtStart, setZeroAtStart] = React.useState(false);

  const chartData = React.useMemo(() => {
    if (!zeroAtStart || !data || data.length === 0) return data;

    const firstPoint = data[0];
    return data.map(point => ({
      ...point,
      total_return: point.total_return - firstPoint.total_return,
      unrealized_pl: point.unrealized_pl - firstPoint.unrealized_pl,
      realized_pl: point.realized_pl - firstPoint.realized_pl
    }));
  }, [data, zeroAtStart]);

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
    <div>
      <div style={{ marginBottom: '0.5rem' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={zeroAtStart}
            onChange={(e) => setZeroAtStart(e.target.checked)}
          />
          <span style={{ fontSize: '0.875rem' }}>Zero at Start</span>
        </label>
      </div>

      <ResponsiveContainer width="90%" aspect={isLarge ? 16/9 : 2/1}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 50, left: 20, bottom: 5 }}
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
        <Tooltip content={<CustomTooltip />} wrapperStyle={{ bottom: -60, top: 'auto' }} cursor={{ stroke: 'var(--color-border)', strokeWidth: 1 }} />
        <ReferenceLine y={0} stroke="var(--color-border)" strokeWidth={2} />
        <Line
          type="monotone"
          dataKey="total_return"
          stroke="var(--color-primary)"
          strokeWidth={3}
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="unrealized_pl"
          stroke="var(--color-success)"
          strokeWidth={2}
          strokeDasharray="5 5"
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="realized_pl"
          stroke="var(--color-secondary)"
          strokeWidth={2}
          strokeDasharray="3 3"
          dot={false}
          isAnimationActive={false}
        />
        <Brush dataKey="date" height={30} stroke="var(--color-primary)" />
      </LineChart>
    </ResponsiveContainer>
    </div>
  );
};