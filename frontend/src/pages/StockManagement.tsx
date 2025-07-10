import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { StockVerification } from '../components/import/StockVerification';
import { StagedTransactionsModal } from '../components/StagedTransactionsModal';
import '../styles/transaction-import.css';

export const StockManagement: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const [validationResults, setValidationResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showStagedTransactions, setShowStagedTransactions] = useState(false);

  useEffect(() => {
    if (portfolioId) {
      fetchPortfolioStocks();
    }
  }, [portfolioId]);

  const fetchPortfolioStocks = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/portfolios/${portfolioId}/stocks/for-verification`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch portfolio stocks');
      }
      
      const data = await response.json();
      if (data.success) {
        setValidationResults(data.data.validation_results);
      } else {
        throw new Error(data.error || 'Failed to fetch portfolio stocks');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch portfolio stocks');
    } finally {
      setLoading(false);
    }
  };

  const handleStockVerification = (verificationResults: any) => {
    // Handle the verification results - could redirect or show success message
    console.log('Stock verification completed:', verificationResults);
    // Optionally refresh the data
    fetchPortfolioStocks();
  };

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

  if (loading) {
    return (
      <div className="page">
        <div className="page-content">
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Loading portfolio stocks...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <div className="page-content">
          <div className="error-container">
            <h3>Error Loading Stocks</h3>
            <p>{error}</p>
            <button onClick={fetchPortfolioStocks} className="btn btn-primary">
              Try Again
            </button>
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
          <button 
            onClick={() => setShowStagedTransactions(true)}
            className="btn btn-outline"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10,9 9,9 8,9"/>
            </svg>
            View Staged Transactions
          </button>
        </div>
      </div>
      
      <div className="page-content">
        {validationResults && (
          <StockVerification
            validationResults={validationResults}
            portfolioId={parseInt(portfolioId)}
            onStockVerification={handleStockVerification}
            context="management"
          />
        )}
      </div>

      {/* Staged Transactions Modal */}
      <StagedTransactionsModal
        portfolioId={parseInt(portfolioId || '0')}
        isOpen={showStagedTransactions}
        onClose={() => setShowStagedTransactions(false)}
      />
    </div>
  );
};