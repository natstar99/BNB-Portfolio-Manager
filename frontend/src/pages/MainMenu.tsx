import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { usePortfolios } from '../hooks/usePortfolios';
import '../styles/main-menu.css';

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
}

export const MainMenu: React.FC = () => {
  const { portfolios, createPortfolio, deletePortfolio, loading, error } = usePortfolios();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newPortfolioName, setNewPortfolioName] = useState('');
  const [newPortfolioDescription, setNewPortfolioDescription] = useState('');

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
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const handleCreatePortfolio = async () => {
    if (!newPortfolioName.trim()) return;
    
    try {
      await createPortfolio(
        newPortfolioName.trim(), 
        'USD', 
        newPortfolioDescription.trim() || undefined
      );
      setNewPortfolioName('');
      setNewPortfolioDescription('');
      setShowCreateModal(false);
    } catch (err) {
      console.error('Failed to create portfolio:', err);
      alert('Failed to create portfolio. Please try again.');
    }
  };

  const totalPortfolioValue = portfolios.reduce((sum, portfolio) => sum + (portfolio.total_value || 0), 0);
  const totalGainLoss = portfolios.reduce((sum, portfolio) => sum + (portfolio.gain_loss || 0), 0);

  return (
    <div className="main-menu">
      {/* Hero Section */}
      <div className="hero-section">
        <div className="hero-content">
          <div className="hero-text">
            <h1>Welcome to BNB Portfolio Manager</h1>
            <p className="hero-subtitle">
              Your comprehensive investment portfolio management solution
            </p>
          </div>
          <div className="hero-stats">
            <div className="stat-card">
              <div className="stat-value">{portfolios.length}</div>
              <div className="stat-label">Active Portfolios</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{formatCurrency(totalPortfolioValue)}</div>
              <div className="stat-label">Total Value</div>
            </div>
            <div className="stat-card">
              <div className={`stat-value ${totalGainLoss >= 0 ? 'positive' : 'negative'}`}>
                {formatCurrency(totalGainLoss)}
              </div>
              <div className="stat-label">Total Gain/Loss</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Quick Actions */}
        <div className="quick-actions-section">
          <div className="section-header">
            <h2>Quick Actions</h2>
          </div>
          <div className="quick-actions">
            <button 
              onClick={() => setShowCreateModal(true)}
              className="action-card primary"
            >
              <div className="action-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="16"/>
                  <line x1="8" y1="12" x2="16" y2="12"/>
                </svg>
              </div>
              <h3>Create Portfolio</h3>
              <p>Start a new investment portfolio</p>
            </button>

            <Link to="/settings" className="action-card">
              <div className="action-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M12 1v6m0 6v6"/>
                  <path d="M1 12h6m6 0h6"/>
                </svg>
              </div>
              <h3>Settings</h3>
              <p>Configure app preferences</p>
            </Link>

            <div className="action-card disabled">
              <div className="action-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
                </svg>
              </div>
              <h3>Market News</h3>
              <p>Coming soon</p>
            </div>
          </div>
        </div>

        {/* Portfolios Section */}
        <div className="portfolios-section">
          <div className="section-header">
            <h2>Your Portfolios</h2>
            <p className="section-subtitle">
              {portfolios.length === 0 
                ? "Create your first portfolio to get started" 
                : `Manage ${portfolios.length} portfolio${portfolios.length !== 1 ? 's' : ''}`
              }
            </p>
          </div>

          {loading ? (
            <div className="portfolios-grid">
              {[1, 2, 3].map(i => (
                <div key={i} className="portfolio-card loading">
                  <div className="loading-shimmer" style={{ height: '200px' }}></div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="error-state">
              <div className="error-card">
                <h3>Unable to load portfolios</h3>
                <p>{error}</p>
                <button className="btn btn-primary">Try Again</button>
              </div>
            </div>
          ) : portfolios.length === 0 ? (
            <div className="empty-portfolios">
              <div className="empty-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                  <polyline points="9,22 9,12 15,12 15,22"/>
                </svg>
              </div>
              <h3>No portfolios yet</h3>
              <p>Create your first portfolio to start tracking your investments</p>
              <button 
                onClick={() => setShowCreateModal(true)}
                className="btn btn-primary btn-lg"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="16"/>
                  <line x1="8" y1="12" x2="16" y2="12"/>
                </svg>
                Create Your First Portfolio
              </button>
            </div>
          ) : (
            <div className="portfolios-grid">
              {portfolios.map((portfolio) => (
                <Link 
                  key={portfolio.id} 
                  to={`/portfolio/${portfolio.id}/dashboard`} 
                  className="portfolio-card"
                >
                  <div className="portfolio-header">
                    <div className="portfolio-icon">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                        <polyline points="9,22 9,12 15,12 15,22"/>
                      </svg>
                    </div>
                    <h3>{portfolio.name}</h3>
                    <p className="portfolio-meta">
                      Created {formatDate(portfolio.created_at)}
                    </p>
                  </div>
                  
                  <div className="portfolio-metrics">
                    <div className="metric">
                      <span className="label">Value</span>
                      <span className="value">
                        {portfolio.total_value ? formatCurrency(portfolio.total_value) : '$0.00'}
                      </span>
                    </div>
                    <div className="metric">
                      <span className="label">Gain/Loss</span>
                      <span className={`value ${portfolio.gain_loss ? (portfolio.gain_loss >= 0 ? 'positive' : 'negative') : ''}`}>
                        {portfolio.gain_loss ? formatCurrency(portfolio.gain_loss) : '$0.00'}
                      </span>
                    </div>
                    <div className="metric">
                      <span className="label">Positions</span>
                      <span className="value">{portfolio.stock_count || 0}</span>
                    </div>
                  </div>

                  <div className="portfolio-actions">
                    <span className="action-text">Click to manage →</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Portfolio Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal glass" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create New Portfolio</h3>
              <button 
                onClick={() => setShowCreateModal(false)}
                className="btn-icon"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">Portfolio Name *</label>
                <input
                  type="text"
                  className="form-input"
                  value={newPortfolioName}
                  onChange={(e) => setNewPortfolioName(e.target.value)}
                  placeholder="e.g., Growth Portfolio, Dividend Stocks"
                  maxLength={100}
                />
              </div>
              
              <div className="form-group">
                <label className="form-label">Description (Optional)</label>
                <textarea
                  className="form-input"
                  rows={3}
                  value={newPortfolioDescription}
                  onChange={(e) => setNewPortfolioDescription(e.target.value)}
                  placeholder="Brief description of this portfolio's strategy or purpose"
                  maxLength={500}
                />
              </div>
            </div>
            
            <div className="modal-footer">
              <button 
                onClick={() => setShowCreateModal(false)}
                className="btn btn-outline"
              >
                Cancel
              </button>
              <button 
                onClick={handleCreatePortfolio}
                className="btn btn-primary"
                disabled={!newPortfolioName.trim()}
              >
                Create Portfolio
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};