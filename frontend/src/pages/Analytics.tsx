import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { usePortfolios } from '../hooks/usePortfolios';
import { PortfolioValueChart } from '../components/charts/PortfolioValueChart';
import { PortfolioPLChart } from '../components/charts/PortfolioPLChart';
import { AssetAllocationChart } from '../components/charts/AssetAllocationChart';
import { PerformanceRankingChart } from '../components/charts/PerformanceRankingChart';
import { StockValueChart } from '../components/charts/StockValueChart';
import { StockPLChart } from '../components/charts/StockPLChart';
import { formatCurrency, formatDateWithYear } from '../shared/formatters';
import { Portfolio, Position, PerformanceData } from '../shared/types';
import '../styles/analytics.css';


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
  const { hasPortfolios, isNewUser } = usePortfolios();
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timePeriod, setTimePeriod] = useState<'30D' | '1Y' | '1W' | '1D' | 'ALL'>('30D');
  const [selectedChart, setSelectedChart] = useState<string | null>(null);

  useEffect(() => {
    if (!portfolioId) {
      // If no portfolio ID, redirect to portfolio selection
      navigate('/');
      return;
    }
    fetchAnalyticsData();
  }, [portfolioId, navigate]);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch portfolio analytics data
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

      // Fetch performance data
      const performanceResponse = await fetch(`/api/analytics/portfolio/${portfolioId}/performance`);
      if (performanceResponse.ok) {
        const performanceData = await performanceResponse.json();
        if (performanceData.success && performanceData.data) {
          setPerformanceData(performanceData.data);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };


  // Prepare chart data
  const prepareChartData = () => {
    if (!analyticsData) return null;

    // Only use real performance data - no mock data
    const dataToUse = performanceData || [];

    // Filter data based on time period - ensure filteredData is always an array
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

    // Prepare asset allocation data
    const allocationData = analyticsData.positions.map(position => ({
      symbol: position.symbol,
      company_name: position.company_name,
      market_value: position.market_value,
      percentage: (position.market_value / (analyticsData.portfolio.total_value || 1)) * 100
    }));

    // Prepare performance ranking data
    const rankingData = analyticsData.positions.map(position => ({
      symbol: position.symbol,
      company_name: position.company_name,
      avg_daily_return: position.day_change_percent || 0,
      trading_days: 30
    }));

    // Prepare stock colors
    const stocksWithColors = analyticsData.positions.map((position, index) => ({
      symbol: position.symbol,
      company_name: position.company_name,
      color: STOCK_COLORS[index % STOCK_COLORS.length]
    }));

    // Prepare stock value data for individual charts
    const stockValueData = (filteredData || []).map(item => {
      const result: any = { date: item.date };
      analyticsData.positions.forEach((position) => {
        // Use actual position data - no mock values
        result[position.symbol] = position.market_value;
        result[`${position.symbol}_pl`] = position.gain_loss;
      });
      return result;
    });

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
        return (
          <PortfolioValueChart
            data={chartData.portfolioData}
            currency={analyticsData!.portfolio.currency}
            isLarge={true}
            timePeriod={timePeriod}
          />
        );
      case 'portfolio-pl':
        return (
          <PortfolioPLChart
            data={chartData.portfolioData}
            currency={analyticsData!.portfolio.currency}
            isLarge={true}
            timePeriod={timePeriod}
          />
        );
      case 'stock-values':
        return (
          <StockValueChart
            data={chartData.filteredData}
            stocks={chartData.stocksWithColors}
            currency={analyticsData!.portfolio.currency}
            isLarge={true}
            timePeriod={timePeriod}
          />
        );
      case 'stock-pl':
        return (
          <StockPLChart
            data={chartData.filteredData}
            stocks={chartData.stocksWithColors}
            currency={analyticsData!.portfolio.currency}
            isLarge={true}
            timePeriod={timePeriod}
          />
        );
      case 'allocation':
        return (
          <AssetAllocationChart
            data={chartData.allocationData}
            currency={analyticsData!.portfolio.currency}
            isLarge={true}
          />
        );
      case 'performance-ranking':
        return (
          <PerformanceRankingChart
            data={chartData.rankingData}
            isLarge={true}
          />
        );
      default:
        return (
          <div className="chart-placeholder large">
            <div className="chart-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                <path d="M3 3v18h18"/>
                <path d="M7 16l4-4 4 4 6-6"/>
              </svg>
            </div>
            <p>Enlarged Chart View</p>
            <span className="chart-note">Chart not found</span>
          </div>
        );
    }
  };

  // Show portfolio required message for new users
  if (isNewUser) {
    return (
      <div className="page">
        <div className="page-header">
          <div className="header-content">
            <h1>Analytics</h1>
            <p className="page-subtitle">Comprehensive portfolio analysis and insights</p>
          </div>
        </div>
        
        <div className="empty-state-full glass">
          <div className="empty-state-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9,22 9,12 15,12 15,22"/>
            </svg>
          </div>
          <h3>Create a Portfolio First</h3>
          <p>You need to create a portfolio and add transactions before viewing analytics.</p>
          
          <div className="empty-state-actions">
            <Link to="/portfolios" className="btn btn-primary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="16"/>
                <line x1="8" y1="12" x2="16" y2="12"/>
              </svg>
              Create Portfolio
            </Link>
            <Link to="/" className="btn btn-outline">
              Back to Dashboard
            </Link>
          </div>
          
          <div className="help-section">
            <h4>Available Analytics:</h4>
            <ul>
              <li>Portfolio performance over time</li>
              <li>Asset allocation and diversification</li>
              <li>Risk metrics and volatility analysis</li>
              <li>Gain/loss tracking by stock and time period</li>
              <li>Benchmark comparison and correlation analysis</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page">
        <div className="loading-shimmer" style={{ height: '100vh' }}></div>
      </div>
    );
  }

  if (error || !analyticsData) {
    return (
      <div className="page">
        <div className="error-state">
          <div className="error-card glass">
            <h3>Unable to load analytics</h3>
            <p>{error || 'Analytics data not found'}</p>
            <div className="error-actions">
              <button onClick={() => navigate(`/portfolio/${portfolioId}/dashboard`)} className="btn btn-outline">
                Back to Dashboard
              </button>
              <button onClick={fetchAnalyticsData} className="btn btn-primary">
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page analytics-page">
      {/* Portfolio Context Header */}
      <div className="portfolio-context-header">
        <div className="breadcrumb">
          <Link to="/" className="breadcrumb-link">Main Menu</Link>
          <span className="breadcrumb-separator">›</span>
          <Link to={`/portfolio/${portfolioId}/dashboard`} className="breadcrumb-link">Portfolio</Link>
          <span className="breadcrumb-separator">›</span>
          <span className="breadcrumb-current">{analyticsData.portfolio.name}</span>
        </div>
        <div className="portfolio-meta">
          <span className="portfolio-currency">{analyticsData.portfolio.currency}</span>
          <span className="portfolio-created">Since {formatDateWithYear(analyticsData.portfolio.created_at)}</span>
        </div>
      </div>

      <div className="page-header">
        <div className="header-content">
          <div className="portfolio-title">
            <div className="portfolio-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 3v18h18"/>
                <path d="M7 16l4-4 4 4 6-6"/>
              </svg>
            </div>
            <div>
              <h1>{analyticsData.portfolio.name} Analytics</h1>
              <p className="page-subtitle">Comprehensive portfolio analysis and insights</p>
            </div>
          </div>
        </div>
        <div className="header-actions">
          <div className="time-period-selector">
            {(['1D', '1W', '30D', '1Y', 'ALL'] as const).map((period) => (
              <button
                key={period}
                className={`btn btn-outline btn-sm ${timePeriod === period ? 'active' : ''}`}
                onClick={() => setTimePeriod(period)}
              >
                {period === 'ALL' ? 'All Time' : period}
              </button>
            ))}
          </div>
          <Link to={`/portfolio/${portfolioId}/dashboard`} className="btn btn-outline">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9,22 9,12 15,12 15,22"/>
            </svg>
            Back to Dashboard
          </Link>
        </div>
      </div>

      {/* Analytics Dashboard Grid */}
      <div className="analytics-dashboard">
        {/* Row 1: Portfolio Value and P&L */}
        <div className="analytics-row">
          <div className="analytics-tile" onClick={() => setSelectedChart('portfolio-value')}>
            <div className="tile-header">
              <h3>Portfolio Value</h3>
              <div className="tile-value">
                {formatCurrency(analyticsData.portfolio.total_value || 0, analyticsData?.portfolio?.currency)}
              </div>
            </div>
            <div className="chart-container">
              {chartData && chartData.portfolioData && chartData.portfolioData.length > 0 ? (
                <PortfolioValueChart
                  data={chartData.portfolioData}
                  currency={analyticsData.portfolio.currency}
                  isLarge={false}
                  timePeriod={timePeriod}
                />
              ) : (
                <div className="chart-placeholder">
                  <div className="chart-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                      <path d="M3 3v18h18"/>
                      <path d="M7 16l4-4 4 4 6-6"/>
                    </svg>
                  </div>
                  <p>No data available</p>
                  <span className="chart-note">Portfolio performance data not found</span>
                </div>
              )}
            </div>
          </div>
          
          <div className="analytics-tile" onClick={() => setSelectedChart('portfolio-pl')}>
            <div className="tile-header">
              <h3>Portfolio P&L</h3>
              <div className={`tile-value ${(analyticsData.portfolio.gain_loss || 0) >= 0 ? 'positive' : 'negative'}`}>
                {formatCurrency(analyticsData.portfolio.gain_loss || 0, analyticsData?.portfolio?.currency)}
              </div>
            </div>
            <div className="chart-container">
              {chartData && chartData.portfolioData && chartData.portfolioData.length > 0 ? (
                <PortfolioPLChart
                  data={chartData.portfolioData}
                  currency={analyticsData.portfolio.currency}
                  isLarge={false}
                  timePeriod={timePeriod}
                />
              ) : (
                <div className="chart-placeholder">
                  <div className="chart-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                      <path d="M3 3v18h18"/>
                      <path d="M7 16l4-4 4 4 6-6"/>
                    </svg>
                  </div>
                  <p>No data available</p>
                  <span className="chart-note">Portfolio P&L data not found</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Row 2: Individual Stock Charts */}
        <div className="analytics-row">
          <div className="analytics-tile" onClick={() => setSelectedChart('stock-values')}>
            <div className="tile-header">
              <h3>Stock Values</h3>
              <div className="tile-subtitle">
                {analyticsData.positions.length} Active Positions
              </div>
            </div>
            <div className="chart-container">
              {chartData && chartData.filteredData && chartData.filteredData.length > 0 && chartData.stocksWithColors.length > 0 ? (
                <StockValueChart
                  data={chartData.filteredData}
                  stocks={chartData.stocksWithColors}
                  currency={analyticsData.portfolio.currency}
                  isLarge={false}
                  timePeriod={timePeriod}
                />
              ) : (
                <div className="chart-placeholder">
                  <div className="chart-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                      <path d="M3 3v18h18"/>
                      <path d="M7 16l4-4 4 4 6-6"/>
                    </svg>
                  </div>
                  <p>No data available</p>
                  <span className="chart-note">Stock performance data not found</span>
                </div>
              )}
            </div>
          </div>
          
          <div className="analytics-tile" onClick={() => setSelectedChart('stock-pl')}>
            <div className="tile-header">
              <h3>Stock P&L</h3>
              <div className="tile-subtitle">
                Performance by Stock
              </div>
            </div>
            <div className="chart-container">
              {chartData && chartData.filteredData && chartData.filteredData.length > 0 && chartData.stocksWithColors.length > 0 ? (
                <StockPLChart
                  data={chartData.filteredData}
                  stocks={chartData.stocksWithColors}
                  currency={analyticsData.portfolio.currency}
                  isLarge={false}
                  timePeriod={timePeriod}
                />
              ) : (
                <div className="chart-placeholder">
                  <div className="chart-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                      <path d="M3 3v18h18"/>
                      <path d="M7 16l4-4 4 4 6-6"/>
                    </svg>
                  </div>
                  <p>No data available</p>
                  <span className="chart-note">Stock P&L data not found</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Row 3: Asset Allocation and Performance Ranking */}
        <div className="analytics-row">
          <div className="analytics-tile" onClick={() => setSelectedChart('allocation')}>
            <div className="tile-header">
              <h3>Asset Allocation</h3>
              <div className="tile-subtitle">
                Distribution by Market Value
              </div>
            </div>
            <div className="chart-container">
              {chartData && chartData.allocationData && chartData.allocationData.length > 0 ? (
                <AssetAllocationChart
                  data={chartData.allocationData}
                  currency={analyticsData.portfolio.currency}
                  isLarge={false}
                />
              ) : (
                <div className="chart-placeholder">
                  <div className="chart-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                      <circle cx="12" cy="12" r="10"/>
                      <path d="M12 2a10 10 0 0 1 10 10"/>
                      <path d="M12 2a10 10 0 0 0 0 20"/>
                    </svg>
                  </div>
                  <p>No data available</p>
                  <span className="chart-note">No positions to display</span>
                </div>
              )}
            </div>
          </div>
          
          <div className="analytics-tile" onClick={() => setSelectedChart('performance-ranking')}>
            <div className="tile-header">
              <h3>Performance Ranking</h3>
              <div className="tile-subtitle">
                Average Daily % Performance
              </div>
            </div>
            <div className="chart-container">
              {chartData && chartData.rankingData && chartData.rankingData.length > 0 ? (
                <PerformanceRankingChart
                  data={chartData.rankingData}
                  isLarge={false}
                />
              ) : (
                <div className="chart-placeholder">
                  <div className="chart-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                      <path d="M3 12h18m-9-9v18"/>
                      <path d="M8 8l4 4 4-4"/>
                    </svg>
                  </div>
                  <p>No data available</p>
                  <span className="chart-note">No performance data to rank</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Modal for enlarged charts */}
      {selectedChart && (
        <div className="chart-modal-overlay" onClick={() => setSelectedChart(null)}>
          <div className="chart-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Chart Details</h2>
              <button className="modal-close" onClick={() => setSelectedChart(null)}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            <div className="modal-content">
              {chartData && renderEnlargedChart()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};