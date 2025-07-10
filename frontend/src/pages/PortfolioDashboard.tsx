import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { MetricCard } from '../components/ui/MetricCard';
import '../styles/dashboard.css';

interface Portfolio {
  id: number;
  name: string;
  currency: string;
  created_at: string;
  stock_count: number;
  total_value?: number;
  total_cost?: number;
  gain_loss?: number;
  gain_loss_percent?: number;
  day_change?: number;
  day_change_percent?: number;
}

interface Position {
  id: number;
  symbol: string;
  company_name?: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  gain_loss: number;
  gain_loss_percent: number;
  day_change: number;
  day_change_percent: number;
}

interface RecentTransaction {
  id: number;
  symbol: string;
  action: string;
  quantity: number;
  price: number;
  date: string;
}

export const PortfolioDashboard: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const navigate = useNavigate();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [recentTransactions, setRecentTransactions] = useState<RecentTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [portfolioSettings, setPortfolioSettings] = useState({
    accounting_method: 'fifo',
    base_currency: 'USD'
  });

  useEffect(() => {
    if (!portfolioId) {
      navigate('/');
      return;
    }
    fetchPortfolioData();
  }, [portfolioId, navigate]);

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch comprehensive portfolio analytics data in one call
      const analyticsResponse = await fetch(`/api/portfolios/${portfolioId}/analytics`);
      if (!analyticsResponse.ok) {
        if (analyticsResponse.status === 404) {
          navigate('/');
          return;
        }
        throw new Error('Failed to fetch portfolio analytics');
      }
      
      const analyticsData = await analyticsResponse.json();
      console.log('Analytics data received:', analyticsData); // Debug logging
      
      if (analyticsData.success && analyticsData.data) {
        // Set portfolio data with metrics
        setPortfolio(analyticsData.data.portfolio);
        
        // Set positions data
        setPositions(analyticsData.data.positions || []);
        
        // Set recent transactions data
        setRecentTransactions(analyticsData.data.recent_transactions || []);
        
        console.log('Dashboard data set:', {
          portfolio: analyticsData.data.portfolio,
          positions: analyticsData.data.positions?.length || 0,
          transactions: analyticsData.data.recent_transactions?.length || 0
        });
      } else {
        throw new Error(analyticsData.error || 'Invalid response format');
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Portfolio data fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: portfolio?.currency || 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number | null | undefined): string => {
    if (value === null || value === undefined || isNaN(value)) {
      return '0.00%';
    }
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="page">
        <div className="loading-shimmer" style={{ height: '100vh' }}></div>
      </div>
    );
  }

  if (error || !portfolio) {
    return (
      <div className="page">
        <div className="error-state">
          <div className="error-card glass">
            <h3>Unable to load portfolio</h3>
            <p>{error || 'Portfolio not found'}</p>
            <div className="error-actions">
              <button onClick={() => navigate('/')} className="btn btn-outline">
                Back to Main Menu
              </button>
              <button onClick={fetchPortfolioData} className="btn btn-primary">
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      {/* Portfolio Context Header */}
      <div className="portfolio-context-header">
        <div className="breadcrumb">
          <Link to="/" className="breadcrumb-link">Main Menu</Link>
          <span className="breadcrumb-separator">›</span>
          <Link to={`/portfolio/${portfolioId}/dashboard`} className="breadcrumb-link">Portfolio</Link>
          <span className="breadcrumb-separator">›</span>
          <span className="breadcrumb-current">{portfolio.name}</span>
        </div>
        <div className="portfolio-meta">
          <span className="portfolio-currency">{portfolio.currency}</span>
          <span className="portfolio-created">Since {formatDate(portfolio.created_at)}</span>
        </div>
      </div>

      <div className="page-header">
        <div className="header-content">
          <div className="portfolio-title">
            <div className="portfolio-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9,22 9,12 15,12 15,22"/>
              </svg>
            </div>
            <div>
              <h1>{portfolio.name}</h1>
              <p className="page-subtitle">Portfolio Dashboard</p>
            </div>
          </div>
        </div>
        <div className="header-actions">
          <Link to={`/portfolio/${portfolioId}/stocks`} className="btn btn-outline">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
            </svg>
            Manage Stocks
          </Link>
          <Link to={`/portfolio/${portfolioId}/import`} className="btn btn-outline">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17,8 12,3 7,8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Import Data
          </Link>
          <button onClick={() => setShowSettingsModal(true)} className="btn btn-primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
            Settings
          </button>
        </div>
      </div>

      {/* Portfolio Overview */}
      <div className="dashboard-section">
        <div className="section-header">
          <h2>Portfolio Overview</h2>
          <div className="portfolio-actions">
            <Link to="/" className="btn btn-outline btn-sm">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 12H5m7-7l-7 7 7 7"/>
              </svg>
              Switch Portfolio
            </Link>
          </div>
        </div>
        
        <div className="portfolio-summary-card glass">
          <div className="summary-content">
            <div className="summary-item">
              <div className="summary-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                </svg>
              </div>
              <div className="summary-details">
                <span className="summary-label">Portfolio Value</span>
                <span className="summary-value">{formatCurrency(portfolio.total_value || 0)}</span>
                {portfolio.day_change !== undefined && (
                  <span className={`summary-change ${portfolio.day_change >= 0 ? 'positive' : 'negative'}`}>
                    {portfolio.day_change >= 0 ? '+' : ''}{formatCurrency(portfolio.day_change)} ({formatPercent(portfolio.day_change_percent || 0)})
                  </span>
                )}
              </div>
            </div>

            <div className="summary-item">
              <div className="summary-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="1" y="3" width="15" height="13"/>
                  <path d="m16 8 2-2 2 2"/>
                  <path d="M21 14V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2z"/>
                </svg>
              </div>
              <div className="summary-details">
                <span className="summary-label">Total Cost</span>
                <span className="summary-value">{formatCurrency(portfolio.total_cost || 0)}</span>
              </div>
            </div>

            <div className="summary-item">
              <div className="summary-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
                </svg>
              </div>
              <div className="summary-details">
                <span className="summary-label">Total Return</span>
                <span className={`summary-value ${(portfolio.gain_loss || 0) >= 0 ? 'positive' : 'negative'}`}>
                  {formatCurrency(portfolio.gain_loss || 0)}
                </span>
                {portfolio.gain_loss_percent !== undefined && (
                  <span className={`summary-change ${(portfolio.gain_loss_percent || 0) >= 0 ? 'positive' : 'negative'}`}>
                    {formatPercent(portfolio.gain_loss_percent)}
                  </span>
                )}
              </div>
            </div>

            <div className="summary-item">
              <div className="summary-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                  <line x1="8" y1="21" x2="16" y2="21"/>
                  <line x1="12" y1="17" x2="12" y2="21"/>
                </svg>
              </div>
              <div className="summary-details">
                <span className="summary-label">Active Positions</span>
                <span className="summary-value">{portfolio.stock_count || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Portfolio Positions Table */}
      <div className="dashboard-section">
        <div className="section-header">
          <h2>Portfolio Positions</h2>
          <div className="header-actions-secondary">
            <Link to={`/portfolio/${portfolioId}/transactions/new`} className="btn btn-outline btn-sm">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14m-7-7h14"/>
              </svg>
              Add New
            </Link>
            <Link to={`/portfolio/${portfolioId}/positions`} className="btn btn-outline btn-sm">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
              Detailed View
            </Link>
          </div>
        </div>
        
        <div className="positions-table-container">
          {positions.length === 0 ? (
            <div className="empty-state-table">
              <div className="empty-content">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                  <line x1="8" y1="21" x2="16" y2="21"/>
                  <line x1="12" y1="17" x2="12" y2="21"/>
                </svg>
                <h3>No positions yet</h3>
                <p>Start building your portfolio by importing transactions or adding stocks manually</p>
                <div className="empty-actions">
                  <Link to={`/portfolio/${portfolioId}/import`} className="btn btn-primary">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="17,8 12,3 7,8"/>
                      <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                    Import Transactions
                  </Link>
                  <Link to={`/portfolio/${portfolioId}/stocks`} className="btn btn-outline">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
                    </svg>
                    Manage Stocks
                  </Link>
                </div>
              </div>
            </div>
          ) : (
            <div className="positions-table glass">
              <table className="table">
                <thead>
                  <tr>
                    <th>Stock</th>
                    <th>Units Owned</th>
                    <th>Avg. Cost</th>
                    <th>Current Price</th>
                    <th>Market Value</th>
                    <th>Total Cost</th>
                    <th>Gain/Loss</th>
                    <th>%</th>
                    <th>Day Change</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((position) => (
                    <tr key={position.id} className="position-row" onClick={() => navigate(`/portfolio/${portfolioId}/transactions?symbol=${position.symbol}`)}>
                      <td className="stock-cell">
                        <div className="stock-info">
                          <div className="symbol-icon">
                            {position.symbol.substring(0, 2).toUpperCase()}
                          </div>
                          <div className="stock-details">
                            <span className="symbol">{position.symbol}</span>
                            <span className="company-name">{position.company_name || 'Unknown Company'}</span>
                          </div>
                        </div>
                      </td>
                      <td className="units-cell">
                        <span className="units">{position.quantity.toLocaleString()}</span>
                      </td>
                      <td className="avg-cost-cell">
                        <span className="price">{formatCurrency(position.avg_cost)}</span>
                      </td>
                      <td className="current-price-cell">
                        <span className="price">{formatCurrency(position.current_price)}</span>
                      </td>
                      <td className="market-value-cell">
                        <span className="value">{formatCurrency(position.market_value)}</span>
                      </td>
                      <td className="total-cost-cell">
                        <span className="value">{formatCurrency(position.avg_cost * position.quantity)}</span>
                      </td>
                      <td className="gain-loss-cell">
                        <span className={`gain-loss ${position.gain_loss >= 0 ? 'positive' : 'negative'}`}>
                          {formatCurrency(position.gain_loss)}
                        </span>
                      </td>
                      <td className="percentage-cell">
                        <span className={`percentage ${position.gain_loss_percent >= 0 ? 'positive' : 'negative'}`}>
                          {formatPercent(position.gain_loss_percent)}
                        </span>
                      </td>
                      <td className="day-change-cell">
                        <div className="day-change">
                          <span className={`change-value ${position.day_change >= 0 ? 'positive' : 'negative'}`}>
                            {formatCurrency(position.day_change)}
                          </span>
                          <span className={`change-percent ${position.day_change_percent >= 0 ? 'positive' : 'negative'}`}>
                            {formatPercent(position.day_change_percent)}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Two-Column Layout */}
      <div className="dashboard-two-column">
        {/* Recent Activity */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Recent Transactions</h2>
            <Link to={`/portfolio/${portfolioId}/transactions`} className="btn btn-outline btn-sm">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
              </svg>
              View All
            </Link>
          </div>
          
          <div className="transactions-card glass">
            {recentTransactions.length === 0 ? (
              <div className="empty-state-compact">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M8 12h8"/>
                </svg>
                <h4>No transactions yet</h4>
                <p>Your transaction history will appear here</p>
              </div>
            ) : (
              <div className="transactions-list">
                {recentTransactions.slice(0, 4).map((transaction, index) => (
                  <div key={transaction.id || index} className="transaction-item-compact">
                    <div className="transaction-symbol">
                      <div className="symbol-icon-small">
                        {transaction.symbol?.substring(0, 2).toUpperCase() || 'N/A'}
                      </div>
                      <div className="transaction-details">
                        <span className="symbol-text">{transaction.symbol || 'Unknown'}</span>
                        <span className="transaction-type">
                          {transaction.action || 'Unknown'} • {transaction.quantity || 0} shares
                        </span>
                      </div>
                    </div>
                    <div className="transaction-value">
                      <span className="price">{formatCurrency(transaction.price || 0)}</span>
                      <span className="date">{formatDate(transaction.date || new Date().toISOString())}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Performance Preview */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Performance Overview</h2>
            <Link to={`/portfolio/${portfolioId}/analytics`} className="btn btn-outline btn-sm">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 3v18h18"/>
                <path d="M7 16l4-4 4 4 6-6"/>
              </svg>
              Detailed Analytics
            </Link>
          </div>
          
          <div className="performance-card glass">
            {portfolio.total_value && portfolio.total_cost ? (
              <div className="performance-content">
                {/* Performance Metrics */}
                <div className="performance-metrics">
                  <div className="performance-metric">
                    <span className="metric-label">Total Return</span>
                    <span className={`metric-value ${(portfolio.gain_loss || 0) >= 0 ? 'positive' : 'negative'}`}>
                      {formatCurrency(portfolio.gain_loss || 0)}
                    </span>
                    <span className={`metric-percentage ${(portfolio.gain_loss_percent || 0) >= 0 ? 'positive' : 'negative'}`}>
                      {formatPercent(portfolio.gain_loss_percent || 0)}
                    </span>
                  </div>
                  <div className="performance-metric">
                    <span className="metric-label">Day Change</span>
                    <span className={`metric-value ${(portfolio.day_change || 0) >= 0 ? 'positive' : 'negative'}`}>
                      {formatCurrency(portfolio.day_change || 0)}
                    </span>
                    <span className={`metric-percentage ${(portfolio.day_change_percent || 0) >= 0 ? 'positive' : 'negative'}`}>
                      {formatPercent(portfolio.day_change_percent || 0)}
                    </span>
                  </div>
                </div>

                {/* Placeholder for Chart */}
                <div className="chart-placeholder">
                  <div className="chart-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                      <path d="M3 3v18h18"/>
                      <path d="M7 16l4-4 4 4 6-6"/>
                    </svg>
                  </div>
                  <p>Performance chart coming soon</p>
                  <span className="chart-note">Historical data visualization will be available here</span>
                </div>

                {/* Quick Stats */}
                <div className="quick-stats">
                  <div className="stat-item">
                    <span className="stat-label">Positions</span>
                    <span className="stat-value">{portfolio.stock_count || 0}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Invested</span>
                    <span className="stat-value">{formatCurrency(portfolio.total_cost || 0)}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Current Value</span>
                    <span className="stat-value">{formatCurrency(portfolio.total_value || 0)}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="empty-state-compact">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                  <path d="M3 3v18h18"/>
                  <path d="M7 16l4-4 4 4 6-6"/>
                </svg>
                <h4>No performance data yet</h4>
                <p>Performance metrics will appear once you have positions</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      {showSettingsModal && (
        <div className="modal-overlay" onClick={() => setShowSettingsModal(false)}>
          <div className="modal glass" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Portfolio Settings</h3>
              <button 
                onClick={() => setShowSettingsModal(false)}
                className="btn-icon"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            
            <div className="modal-body">
              <div className="settings-section">
                <h4>Accounting Method</h4>
                <p className="setting-description">
                  Choose how gains/losses are calculated when you sell positions
                </p>
                <div className="radio-group">
                  <label className="radio-option">
                    <input 
                      type="radio" 
                      name="accounting_method" 
                      value="fifo"
                      checked={portfolioSettings.accounting_method === 'fifo'}
                      onChange={(e) => setPortfolioSettings({...portfolioSettings, accounting_method: e.target.value})}
                    />
                    <span className="radio-label">
                      <strong>FIFO</strong> - First In, First Out
                      <small>Sell oldest shares first</small>
                    </span>
                  </label>
                  <label className="radio-option">
                    <input 
                      type="radio" 
                      name="accounting_method" 
                      value="lifo"
                      checked={portfolioSettings.accounting_method === 'lifo'}
                      onChange={(e) => setPortfolioSettings({...portfolioSettings, accounting_method: e.target.value})}
                    />
                    <span className="radio-label">
                      <strong>LIFO</strong> - Last In, First Out
                      <small>Sell newest shares first</small>
                    </span>
                  </label>
                  <label className="radio-option">
                    <input 
                      type="radio" 
                      name="accounting_method" 
                      value="hifo"
                      checked={portfolioSettings.accounting_method === 'hifo'}
                      onChange={(e) => setPortfolioSettings({...portfolioSettings, accounting_method: e.target.value})}
                    />
                    <span className="radio-label">
                      <strong>HIFO</strong> - Highest In, First Out
                      <small>Sell highest cost shares first</small>
                    </span>
                  </label>
                </div>
              </div>

              <div className="settings-section">
                <h4>Base Currency</h4>
                <p className="setting-description">
                  Currency used for portfolio value calculations and display
                </p>
                <select 
                  value={portfolioSettings.base_currency}
                  onChange={(e) => setPortfolioSettings({...portfolioSettings, base_currency: e.target.value})}
                  className="form-input"
                >
                  <option value="USD">USD - US Dollar</option>
                  <option value="EUR">EUR - Euro</option>
                  <option value="GBP">GBP - British Pound</option>
                  <option value="CAD">CAD - Canadian Dollar</option>
                  <option value="AUD">AUD - Australian Dollar</option>
                  <option value="JPY">JPY - Japanese Yen</option>
                </select>
              </div>
            </div>
            
            <div className="modal-footer">
              <button 
                onClick={() => setShowSettingsModal(false)}
                className="btn btn-outline"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  // TODO: Save settings to backend
                  console.log('Saving settings:', portfolioSettings);
                  setShowSettingsModal(false);
                }}
                className="btn btn-primary"
              >
                Save Settings
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};