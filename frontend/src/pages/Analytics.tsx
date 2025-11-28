import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
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

export const Analytics: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const navigate = useNavigate();
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([]);
  const [stocksData, setStocksData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timePeriod, setTimePeriod] = useState<'30D' | '1Y' | '1W' | '1D' | 'ALL'>('30D');
  const [selectedChart, setSelectedChart] = useState<string | null>(null);

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

  const prepareChartData = () => {
    if (!analyticsData) return null;

    const dataToUse = performanceData || [];
    let filteredData = Array.isArray(dataToUse) ? dataToUse : [];

    if (timePeriod !== 'ALL' && filteredData.length > 0) {
      const daysMap = { '1D': 1, '1W': 7, '30D': 30, '1Y': 365 };
      const days = daysMap[timePeriod];
      const now = new Date();
      const startDate = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);

      filteredData = filteredData.filter(item =>
        new Date(item.date) >= startDate
      );
    }

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

    if (stocksData.length > 0 && filteredData.length > 0) {
      const dateSet = new Set(filteredData.map(item => item.date));
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
      portfolioData: filteredData,
      allocationData,
      rankingData,
      stocksWithColors,
      filteredData: stockValueData
    };
  };

  const chartData = prepareChartData();

  const renderEnlargedChart = () => {
    if (!chartData || !selectedChart) return null;

    switch (selectedChart) {
      case 'portfolio-value':
        return <PortfolioValueChart data={chartData.portfolioData} currency={analyticsData!.portfolio.currency} isLarge={true} timePeriod={timePeriod} />;
      case 'portfolio-pl':
        return <PortfolioPLChart data={chartData.portfolioData} currency={analyticsData!.portfolio.currency} isLarge={true} timePeriod={timePeriod} />;
      case 'stock-values':
        return <StockValueChart data={chartData.filteredData} stocks={chartData.stocksWithColors} currency={analyticsData!.portfolio.currency} isLarge={true} timePeriod={timePeriod} />;
      case 'stock-pl':
        return <StockPLChart data={chartData.filteredData} stocks={chartData.stocksWithColors} currency={analyticsData!.portfolio.currency} isLarge={true} timePeriod={timePeriod} />;
      case 'allocation':
        return <AssetAllocationChart data={chartData.allocationData} currency={analyticsData!.portfolio.currency} isLarge={true} />;
      case 'performance-ranking':
        return <PerformanceRankingChart data={chartData.rankingData} isLarge={true} />;
      default:
        return <p>Chart not found</p>;
    }
  };

  if (loading) {
    return (
      <div className="page">
        <p>Loading...</p>
      </div>
    );
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
    <div className="page analytics-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>{analyticsData.portfolio.name} Analytics</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {(['1D', '1W', '30D', '1Y', 'ALL'] as const).map((period) => (
            <button
              key={period}
              className={timePeriod === period ? 'active' : ''}
              onClick={() => setTimePeriod(period)}
            >
              {period === 'ALL' ? 'All Time' : period}
            </button>
          ))}
          <Link to={`/portfolio/${portfolioId}/dashboard`}>Back to Dashboard</Link>
        </div>
      </div>

      {/* Analytics Dashboard Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Portfolio Value */}
        <div onClick={() => setSelectedChart('portfolio-value')} style={{ cursor: 'pointer', border: '1px solid var(--color-border)', padding: '1rem' }}>
          <h3>Portfolio Value</h3>
          <p style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
            {formatCurrency(analyticsData.portfolio.total_value || 0, analyticsData?.portfolio?.currency)}
          </p>
          {chartData && chartData.portfolioData && chartData.portfolioData.length > 0 ? (
            <PortfolioValueChart data={chartData.portfolioData} currency={analyticsData.portfolio.currency} isLarge={false} timePeriod={timePeriod} />
          ) : (
            <p>No data available</p>
          )}
        </div>

        {/* Portfolio P&L */}
        <div onClick={() => setSelectedChart('portfolio-pl')} style={{ cursor: 'pointer', border: '1px solid var(--color-border)', padding: '1rem' }}>
          <h3>Portfolio P&L</h3>
          <p style={{ fontSize: '1.5rem', fontWeight: 'bold' }} className={(analyticsData.portfolio.total_pl || 0) >= 0 ? 'positive' : 'negative'}>
            {formatCurrency(analyticsData.portfolio.total_pl || 0, analyticsData?.portfolio?.currency)}
          </p>
          {chartData && chartData.portfolioData && chartData.portfolioData.length > 0 ? (
            <PortfolioPLChart data={chartData.portfolioData} currency={analyticsData.portfolio.currency} isLarge={false} timePeriod={timePeriod} />
          ) : (
            <p>No data available</p>
          )}
        </div>

        {/* Stock Values */}
        <div onClick={() => setSelectedChart('stock-values')} style={{ cursor: 'pointer', border: '1px solid var(--color-border)', padding: '1rem' }}>
          <h3>Stock Values</h3>
          <p>{analyticsData.positions.length} Active Positions</p>
          {chartData && chartData.filteredData && chartData.filteredData.length > 0 && chartData.stocksWithColors.length > 0 ? (
            <StockValueChart data={chartData.filteredData} stocks={chartData.stocksWithColors} currency={analyticsData.portfolio.currency} isLarge={false} timePeriod={timePeriod} />
          ) : (
            <p>No data available</p>
          )}
        </div>

        {/* Stock P&L */}
        <div onClick={() => setSelectedChart('stock-pl')} style={{ cursor: 'pointer', border: '1px solid var(--color-border)', padding: '1rem' }}>
          <h3>Stock P&L</h3>
          <p>Performance by Stock</p>
          {chartData && chartData.filteredData && chartData.filteredData.length > 0 && chartData.stocksWithColors.length > 0 ? (
            <StockPLChart data={chartData.filteredData} stocks={chartData.stocksWithColors} currency={analyticsData.portfolio.currency} isLarge={false} timePeriod={timePeriod} />
          ) : (
            <p>No data available</p>
          )}
        </div>

        {/* Asset Allocation */}
        <div onClick={() => setSelectedChart('allocation')} style={{ cursor: 'pointer', border: '1px solid var(--color-border)', padding: '1rem' }}>
          <h3>Asset Allocation</h3>
          <p>Distribution by Market Value</p>
          {chartData && chartData.allocationData && chartData.allocationData.length > 0 ? (
            <AssetAllocationChart data={chartData.allocationData} currency={analyticsData.portfolio.currency} isLarge={false} />
          ) : (
            <p>No data available</p>
          )}
        </div>

        {/* Performance Ranking */}
        <div onClick={() => setSelectedChart('performance-ranking')} style={{ cursor: 'pointer', border: '1px solid var(--color-border)', padding: '1rem' }}>
          <h3>Performance Ranking</h3>
          <p>Average Daily % Performance</p>
          {chartData && chartData.rankingData && chartData.rankingData.length > 0 ? (
            <PerformanceRankingChart data={chartData.rankingData} isLarge={false} />
          ) : (
            <p>No data available</p>
          )}
        </div>
      </div>

      {/* Modal for enlarged charts */}
      {selectedChart && (
        <div className="modal-overlay" onClick={() => setSelectedChart(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '1200px', width: '90%' }}>
            <h2>Chart Details</h2>
            <button onClick={() => setSelectedChart(null)} style={{ position: 'absolute', right: '1rem', top: '1rem' }}>Close</button>
            <div style={{ marginTop: '2rem' }}>
              {chartData && renderEnlargedChart()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
