import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PortfolioValueChart } from '../components/charts/PortfolioValueChart';
import { PortfolioPLChart } from '../components/charts/PortfolioPLChart';
import { AssetAllocationChart } from '../components/charts/AssetAllocationChart';
import { PerformanceRankingChart } from '../components/charts/PerformanceRankingChart';
import { StockValueChart } from '../components/charts/StockValueChart';
import { StockPLChart } from '../components/charts/StockPLChart';
import { formatCurrency } from '../shared/formatters';
import { Portfolio, Position, PerformanceData } from '../shared/types';

interface AnalyticsData {
  portfolio: Portfolio;
  positions: Position[];
  performance_data: PerformanceData[];
}

const STOCK_COLORS = [
  '#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe',
  '#00c49f', '#ffbb28', '#ff8042', '#8dd1e1', '#d084d0',
  '#87ceeb', '#dda0dd', '#f0e68c', '#ff6347', '#40e0d0'
];

const CHARTS = [
  { id: 'portfolio-value', label: 'Portfolio Value' },
  { id: 'portfolio-pl', label: 'Portfolio P/L' },
  { id: 'stock-values', label: 'Stock Values' },
  { id: 'stock-pl', label: 'Stock P/L' },
  { id: 'allocation', label: 'Asset Allocation' },
  { id: 'performance-ranking', label: 'Performance Ranking' }
];

export const Analytics: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const navigate = useNavigate();
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([]);
  const [stocksData, setStocksData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedChart, setSelectedChart] = useState<string>('portfolio-value');

  // Date range state
  const [useCustomRange, setUseCustomRange] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [quickPeriod, setQuickPeriod] = useState<'1D' | '1W' | '30D' | '1Y' | 'ALL'>('30D');

  useEffect(() => {
    if (!portfolioId) {
      navigate('/');
      return;
    }
    fetchAnalyticsData();
  }, [portfolioId, navigate]);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);
      setError(null);

      const analyticsResponse = await fetch(`/api/portfolios/${portfolioId}/analytics`);
      if (!analyticsResponse.ok) {
        if (analyticsResponse.status === 404) {
          navigate('/');
          return;
        }
        throw new Error('Failed to fetch analytics data');
      }

      const analyticsData = await analyticsResponse.json();
      if (analyticsData.success && analyticsData.data) {
        setAnalyticsData(analyticsData.data);
      } else {
        throw new Error(analyticsData.error || 'Invalid response format');
      }

      const performanceResponse = await fetch(`/api/analytics/portfolio/${portfolioId}/timeseries`);
      if (performanceResponse.ok) {
        const performanceData = await performanceResponse.json();
        if (performanceData.success && performanceData.data) {
          setPerformanceData(performanceData.data);
        }
      }

      const stocksResponse = await fetch(`/api/analytics/portfolio/${portfolioId}/stocks`);
      if (stocksResponse.ok) {
        const stocksData = await stocksResponse.json();
        if (stocksData.success && stocksData.data) {
          setStocksData(stocksData.data);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const filterDataByDate = (data: any[]) => {
    if (!data || data.length === 0) return [];

    if (useCustomRange && startDate && endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      return data.filter(item => {
        const itemDate = new Date(item.date);
        return itemDate >= start && itemDate <= end;
      });
    }

    if (quickPeriod === 'ALL') return data;

    const daysMap = { '1D': 1, '1W': 7, '30D': 30, '1Y': 365 };
    const days = daysMap[quickPeriod];
    const now = new Date();
    const cutoffDate = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);

    return data.filter(item => new Date(item.date) >= cutoffDate);
  };

  const prepareChartData = () => {
    if (!analyticsData) return null;

    const filteredPortfolioData = filterDataByDate(performanceData || []);

    const allocationData = analyticsData.positions.map(position => ({
      symbol: position.symbol,
      company_name: position.company_name,
      market_value: position.market_value,
      percentage: (position.market_value / (analyticsData.portfolio.total_value || 1)) * 100
    }));

    const rankingData = analyticsData.positions.map(position => ({
      symbol: position.symbol,
      company_name: position.company_name,
      avg_daily_return: position.day_change_percent || 0,
      trading_days: 30
    }));

    const stocksWithColors = analyticsData.positions.map((position, index) => ({
      symbol: position.symbol,
      company_name: position.company_name,
      color: STOCK_COLORS[index % STOCK_COLORS.length]
    }));

    const stockValueData: any[] = [];

    if (stocksData.length > 0 && filteredPortfolioData.length > 0) {
      const dateSet = new Set(filteredPortfolioData.map(item => item.date));
      const stocksByDate: { [date: string]: any } = {};

      stocksData.forEach(stock => {
        stock.timeseries.forEach((point: any) => {
          if (dateSet.has(point.date)) {
            if (!stocksByDate[point.date]) {
              stocksByDate[point.date] = { date: point.date };
            }
            stocksByDate[point.date][stock.symbol] = point.market_value;
            stocksByDate[point.date][`${stock.symbol}_pl`] = point.unrealized_pl;
          }
        });
      });

      stockValueData.push(...Object.values(stocksByDate).sort((a, b) =>
        new Date(a.date).getTime() - new Date(b.date).getTime()
      ));
    }

    return {
      portfolioData: filteredPortfolioData,
      allocationData,
      rankingData,
      stocksWithColors,
      filteredData: stockValueData
    };
  };

  const chartData = prepareChartData();

  const handleQuickPeriod = (period: typeof quickPeriod) => {
    setQuickPeriod(period);
    setUseCustomRange(false);
  };

  const handleCustomRange = () => {
    if (startDate && endDate) {
      setUseCustomRange(true);
    }
  };

  const renderChart = () => {
    if (!chartData) return <p>No data available</p>;

    switch (selectedChart) {
      case 'portfolio-value':
        return chartData.portfolioData.length > 0 ? (
          <PortfolioValueChart
            data={chartData.portfolioData}
            currency={analyticsData!.portfolio.currency}
            isLarge={true}
            timePeriod={quickPeriod}
          />
        ) : <p>No data available</p>;

      case 'portfolio-pl':
        return chartData.portfolioData.length > 0 ? (
          <PortfolioPLChart
            data={chartData.portfolioData}
            currency={analyticsData!.portfolio.currency}
            isLarge={true}
            timePeriod={quickPeriod}
          />
        ) : <p>No data available</p>;

      case 'stock-values':
        return chartData.filteredData.length > 0 && chartData.stocksWithColors.length > 0 ? (
          <StockValueChart
            data={chartData.filteredData}
            stocks={chartData.stocksWithColors}
            currency={analyticsData!.portfolio.currency}
            isLarge={true}
            timePeriod={quickPeriod}
          />
        ) : <p>No data available</p>;

      case 'stock-pl':
        return chartData.filteredData.length > 0 && chartData.stocksWithColors.length > 0 ? (
          <StockPLChart
            data={chartData.filteredData}
            stocks={chartData.stocksWithColors}
            currency={analyticsData!.portfolio.currency}
            isLarge={true}
            timePeriod={quickPeriod}
          />
        ) : <p>No data available</p>;

      case 'allocation':
        return chartData.allocationData.length > 0 ? (
          <AssetAllocationChart
            data={chartData.allocationData}
            currency={analyticsData!.portfolio.currency}
            isLarge={true}
          />
        ) : <p>No data available</p>;

      case 'performance-ranking':
        return chartData.rankingData.length > 0 ? (
          <PerformanceRankingChart data={chartData.rankingData} isLarge={true} />
        ) : <p>No data available</p>;

      default:
        return <p>Chart not found</p>;
    }
  };

  if (loading) {
    return <div className="page"><p>Loading...</p></div>;
  }

  if (error || !analyticsData) {
    return (
      <div className="page">
        <h1>Analytics</h1>
        <p>{error || 'Analytics data not found'}</p>
        <button onClick={() => navigate(`/portfolio/${portfolioId}/dashboard`)}>Back to Dashboard</button>
        <button onClick={fetchAnalyticsData}>Try Again</button>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>{analyticsData.portfolio.name} Analytics</h1>

      {/* Chart Selector */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
        {CHARTS.map(chart => (
          <button
            key={chart.id}
            className={selectedChart === chart.id ? 'active' : ''}
            onClick={() => setSelectedChart(chart.id)}
          >
            {chart.label}
          </button>
        ))}
      </div>

      {/* Date Range Controls */}
      <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid var(--color-border)' }}>
        <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>Date Range</h3>

        {/* Quick Period Buttons */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          {(['1D', '1W', '30D', '1Y', 'ALL'] as const).map((period) => (
            <button
              key={period}
              className={!useCustomRange && quickPeriod === period ? 'active' : ''}
              onClick={() => handleQuickPeriod(period)}
            >
              {period === 'ALL' ? 'All Time' : period}
            </button>
          ))}
        </div>

        {/* Custom Date Range */}
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <label htmlFor="start-date" style={{ marginRight: '0.5rem' }}>From:</label>
            <input
              type="date"
              id="start-date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="end-date" style={{ marginRight: '0.5rem' }}>To:</label>
            <input
              type="date"
              id="end-date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          <button
            onClick={handleCustomRange}
            disabled={!startDate || !endDate}
          >
            Apply Custom Range
          </button>
        </div>
      </div>

      {/* Chart Display */}
      <div style={{ width: '100%', minHeight: '400px' }}>
        {renderChart()}
      </div>
    </div>
  );
};
