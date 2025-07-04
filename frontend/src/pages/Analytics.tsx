import React from 'react';
import { Link } from 'react-router-dom';
import { usePortfolios } from '../hooks/usePortfolios';

export const Analytics: React.FC = () => {
  const { hasPortfolios, isNewUser } = usePortfolios();

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

  return (
    <div className="page">
      <div className="page-header">
        <h1>Analytics</h1>
        <p className="page-subtitle">Comprehensive portfolio analysis and insights</p>
      </div>
      
      <div className="coming-soon glass">
        <div className="coming-soon-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
            <path d="M3 3v18h18"/>
            <path d="M7 16l4-4 4 4 6-6"/>
          </svg>
        </div>
        <h2>Advanced Analytics</h2>
        <p>Detailed portfolio analytics including performance charts, asset allocation, risk metrics, and comparative analysis are coming soon.</p>
      </div>
    </div>
  );
};