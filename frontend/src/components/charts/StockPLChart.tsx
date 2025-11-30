import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Brush } from 'recharts';
import { formatCurrency, formatCurrencyForChart, formatDateForChart } from '../../shared/formatters';

interface StockPLChartProps {
  data: Array<{
    date: string;
    [key: string]: number | string;
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

export const StockPLChart: React.FC<StockPLChartProps> = ({
  data,
  stocks,
  currency,
  isLarge = false,
  timePeriod
}) => {
  const [visibleStocks, setVisibleStocks] = useState<Set<string>>(
    new Set(stocks.map(s => s.symbol))
  );
  const [hoverData, setHoverData] = useState<any>(null);

  const toggleStock = (symbol: string) => {
    setVisibleStocks(prev => {
      const next = new Set(prev);
      if (next.has(symbol)) {
        next.delete(symbol);
      } else {
        next.add(symbol);
      }
      return next;
    });
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      setHoverData({ label, payload });
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

  const visibleStocksList = stocks.filter(s => visibleStocks.has(s.symbol));

  return (
    <div>
      {/* Stock toggles */}
      <div style={{ marginBottom: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
        {stocks.map(stock => (
          <label key={stock.symbol} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={visibleStocks.has(stock.symbol)}
              onChange={() => toggleStock(stock.symbol)}
            />
            <span style={{ color: stock.color, fontSize: '0.875rem' }}>{stock.symbol}</span>
          </label>
        ))}
      </div>

      <ResponsiveContainer width="100%" aspect={isLarge ? 16/9 : 2/1}>
        <LineChart
          data={data}
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
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'var(--color-border)', strokeWidth: 1 }} />
          <ReferenceLine y={0} stroke="var(--color-border)" strokeWidth={2} />
          {visibleStocksList.map((stock) => (
            <Line
              key={`${stock.symbol}_pl`}
              type="monotone"
              dataKey={`${stock.symbol}_pl`}
              stroke={stock.color}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
          <Brush dataKey="date" height={30} stroke="var(--color-primary)" />
        </LineChart>
      </ResponsiveContainer>

      {/* Fixed tooltip display */}
      {hoverData && (
        <div style={{ marginTop: '0.5rem', padding: '0.5rem', border: '1px solid var(--color-border)', fontSize: '0.875rem' }}>
          <strong>{formatDateForChart(hoverData.label, timePeriod)}</strong>
          {hoverData.payload.map((entry: any, index: number) => (
            <div key={index} style={{ color: entry.color }}>
              {entry.dataKey} P&L: {formatCurrency(entry.value, currency)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};