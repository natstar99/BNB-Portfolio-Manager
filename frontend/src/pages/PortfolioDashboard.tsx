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

      // Fetch portfolio details
      const portfolioResponse = await fetch(`/api/portfolios/${portfolioId}`);
      if (!portfolioResponse.ok) {
        if (portfolioResponse.status === 404) {
          navigate('/');
          return;
        }
        throw new Error('Failed to fetch portfolio');
      }
      
      const portfolioData = await portfolioResponse.json();
      setPortfolio(portfolioData.data);

      // Fetch portfolio positions
      try {
        const positionsResponse = await fetch(`/api/portfolios/${portfolioId}/positions`);
        if (positionsResponse.ok) {
          const positionsData = await positionsResponse.json();
          setPositions(positionsData.data?.positions || []);
        }
      } catch (positionsErr) {
        console.log('Positions endpoint not available yet');
      }

      // Fetch recent transactions for this portfolio
      try {
        const transactionsResponse = await fetch(`/api/transactions?portfolio_id=${portfolioId}&limit=5`);
        if (transactionsResponse.ok) {
          const transactionsData = await transactionsResponse.json();
          setRecentTransactions(transactionsData.transactions || []);
        }
      } catch (transactionsErr) {
        console.log('Transactions endpoint returned error');
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
      currency: 'USD',
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
          <span className="breadcrumb-current">{portfolio.name}</span>
        </div>
        <div className="portfolio-selector-inline">
          <Link to="/" className="btn btn-outline btn-sm">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5m7-7l-7 7 7 7"/>
            </svg>
            Switch Portfolio
          </Link>
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
              <p className="page-subtitle">Portfolio Dashboard • {portfolio.currency}</p>
            </div>
          </div>
        </div>
        <div className="header-actions">
          <Link to={`/portfolio/${portfolioId}/transactions`} className="btn btn-outline">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
            </svg>
            View Transactions
          </Link>
          <Link to={`/portfolio/${portfolioId}/transactions/new`} className="btn btn-primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="16"/>
              <line x1="8" y1="12" x2="16" y2="12"/>
            </svg>
            Add Transaction
          </Link>
        </div>
      </div>

      {/* Portfolio Metrics */}
      <div className="metrics-section">
        <div className="metrics-grid">
          <MetricCard
            title="Portfolio Value"
            value={formatCurrency(portfolio.total_value || 0)}
            change={portfolio.day_change ? {
              value: portfolio.day_change,
              percentage: portfolio.day_change_percent || 0,
              isPositive: portfolio.day_change >= 0
            } : undefined}
            icon={
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
              </svg>
            }
          />

          <MetricCard
            title="Total Gain/Loss"
            value={formatCurrency(portfolio.gain_loss || 0)}
            change={portfolio.gain_loss ? {
              value: portfolio.gain_loss,
              percentage: portfolio.gain_loss_percent || 0,
              isPositive: portfolio.gain_loss >= 0
            } : undefined}
            icon={
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
              </svg>
            }
          />

          <MetricCard
            title="Total Cost"
            value={formatCurrency(portfolio.total_cost || 0)}
            icon={
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="1" y="3" width="15" height="13"/>
                <path d="m16 8 2-2 2 2"/>
                <path d="M21 14V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2z"/>
              </svg>
            }
          />

          <MetricCard
            title="Positions"
            value={portfolio.stock_count?.toString() || '0'}
            icon={
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
            }
          />
        </div>
      </div>

      {/* Top Holdings */}
      <div className="dashboard-section">
        <div className="section-header">
          <h2>Top Holdings</h2>
          <Link to={`/portfolio/${portfolioId}/positions`} className="btn btn-outline btn-sm">
            View All Positions
          </Link>
        </div>
        
        <div className="holdings-preview glass">
          {positions.length === 0 ? (
            <div className="empty-state">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
              <h3>No positions yet</h3>
              <p>Start building your portfolio by adding stocks</p>
              <Link to={`/portfolio/${portfolioId}/transactions/new`} className="btn btn-primary">
                Add First Position
              </Link>
            </div>
          ) : (
            <div className="holdings-list">
              {positions.slice(0, 5).map((position) => (
                <div key={position.id} className="holding-item">
                  <div className="holding-symbol">
                    <div className="symbol-icon">
                      {position.symbol.substring(0, 2).toUpperCase()}
                    </div>
                    <div className="holding-details">
                      <span className="symbol-text">{position.symbol}</span>
                      <span className="company-name">
                        {position.company_name || 'Unknown Company'}
                      </span>
                    </div>
                  </div>
                  <div className="holding-metrics">
                    <div className="metric-item">
                      <span className="metric-label">Value</span>
                      <span className="metric-value">{formatCurrency(position.market_value)}</span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">Gain/Loss</span>
                      <span className={`metric-value ${position.gain_loss >= 0 ? 'positive' : 'negative'}`}>
                        {formatCurrency(position.gain_loss)}
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">%</span>
                      <span className={`metric-value ${position.gain_loss_percent >= 0 ? 'positive' : 'negative'}`}>
                        {formatPercent(position.gain_loss_percent)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="dashboard-section">
        <div className="section-header">
          <h2>Recent Transactions</h2>
          <Link to={`/portfolio/${portfolioId}/transactions`} className="btn btn-outline btn-sm">
            View All
          </Link>
        </div>
        
        <div className="transactions-card glass">
          {recentTransactions.length === 0 ? (
            <div className="empty-state">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                <circle cx="12" cy="12" r="10"/>
                <path d="M8 12h8"/>
              </svg>
              <h3>No transactions yet</h3>
              <p>Your transaction history will appear here</p>
              <Link to={`/portfolio/${portfolioId}/transactions/new`} className="btn btn-primary">
                Add First Transaction
              </Link>
            </div>
          ) : (
            <div className="transactions-list">
              {recentTransactions.map((transaction, index) => (
                <div key={transaction.id || index} className="transaction-item">
                  <div className="transaction-symbol">
                    <div className="symbol-icon">
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

      {/* Quick Actions */}
      <div className="dashboard-section">
        <div className="section-header">
          <h2>Quick Actions</h2>
        </div>
        
        <div className="quick-actions">
          <Link to={`/portfolio/${portfolioId}/transactions/new`} className="action-card glass">
            <div className="action-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="16"/>
                <line x1="8" y1="12" x2="16" y2="12"/>
              </svg>
            </div>
            <h3>Add Transaction</h3>
            <p>Record a new buy/sell transaction</p>
          </Link>

          <Link to={`/portfolio/${portfolioId}/import`} className="action-card glass">
            <div className="action-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10,9 9,9 8,9"/>
              </svg>
            </div>
            <h3>Import Data</h3>
            <p>Upload CSV or Excel files</p>
          </Link>

          <Link to={`/portfolio/${portfolioId}/analytics`} className="action-card glass">
            <div className="action-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 3v18h18"/>
                <path d="M7 16l4-4 4 4 6-6"/>
              </svg>
            </div>
            <h3>View Analytics</h3>
            <p>Analyze portfolio performance</p>
          </Link>
        </div>
      </div>
    </div>
  );
};