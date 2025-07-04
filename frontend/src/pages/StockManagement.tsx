import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { StockManagement as StockManagementComponent } from '../components/stocks/StockManagement';
import '../styles/stock-management.css';
import '../styles/stock-editor.css';
import '../styles/bulk-stock-actions.css';

export const StockManagement: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();

  if (!portfolioId) {
    return (
      <div className="page">
        <div className="page-header">
          <div className="header-content">
            <h1>Error</h1>
            <p className="page-subtitle">Invalid portfolio ID</p>
          </div>
        </div>
        <div className="error-message">
          <p>Please select a portfolio first.</p>
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
          <Link to={`/portfolio/${portfolioId}/dashboard`} className="breadcrumb-link">
            Portfolio Dashboard
          </Link>
          <span className="breadcrumb-separator">›</span>
          <span className="breadcrumb-current">Stock Management</span>
        </div>
      </div>

      <div className="page-header">
        <div className="header-content">
          <div className="portfolio-title">
            <div className="portfolio-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
              </svg>
            </div>
            <div>
              <h1>Stock Management</h1>
              <p className="page-subtitle">Manage and verify stock symbols in your portfolio</p>
            </div>
          </div>
        </div>
        <div className="header-actions">
          <Link 
            to={`/portfolio/${portfolioId}/import`}
            className="btn btn-outline"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10,9 9,9 8,9"/>
            </svg>
            Import Transactions
          </Link>
          <button className="btn btn-primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>
            Verify All Pending
          </button>
        </div>
      </div>
      
      <div className="page-content">
        <StockManagementComponent />
      </div>
    </div>
  );
};