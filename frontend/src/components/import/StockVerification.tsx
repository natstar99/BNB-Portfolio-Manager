import React, { useState, useEffect } from 'react';

interface StockVerificationProps {
  validationResults: any;
  portfolioId: number;
  onStockVerification: (verificationResults: any) => void;
}

interface MarketCode {
  market_key: string;
  market_or_index: string;
  market_suffix: string;
  country: string;
  description: string;
}

interface StockAssignment {
  instrument_code: string;
  market_key: string;
  yahoo_symbol: string;
  name?: string;
  currency?: string;
  verification_status: 'pending' | 'verified' | 'failed' | 'delisted';
  drp_enabled: boolean;
  notes?: string;
}

export const StockVerification: React.FC<StockVerificationProps> = ({
  validationResults,
  portfolioId,
  onStockVerification,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [markets, setMarkets] = useState<MarketCode[]>([]);
  const [stockAssignments, setStockAssignments] = useState<StockAssignment[]>([]);
  const [verifying, setVerifying] = useState<string | null>(null);

  // Get unique stocks that need market assignment
  const newStocks = validationResults?.new_stock_symbols || [];

  useEffect(() => {
    fetchMarkets();
    initializeStockAssignments();
  }, []);

  const fetchMarkets = async () => {
    try {
      const response = await fetch('/api/import/markets');
      if (!response.ok) {
        throw new Error('Failed to fetch market codes');
      }
      const data = await response.json();
      setMarkets(data.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load markets');
    }
  };

  const initializeStockAssignments = () => {
    const assignments: StockAssignment[] = newStocks.map((stock: string) => ({
      instrument_code: stock,
      market_key: '',
      yahoo_symbol: stock,
      verification_status: 'pending' as const,
      drp_enabled: false,
    }));
    setStockAssignments(assignments);
  };

  const updateStockAssignment = (instrumentCode: string, field: keyof StockAssignment, value: any) => {
    setStockAssignments(prev => prev.map(stock => {
      if (stock.instrument_code === instrumentCode) {
        const updated = { ...stock, [field]: value };
        
        // Auto-update Yahoo symbol when market changes
        if (field === 'market_key' && value) {
          const market = markets.find(m => m.market_key === value);
          if (market) {
            updated.yahoo_symbol = `${instrumentCode}${market.market_suffix || ''}`;
            updated.verification_status = 'pending'; // Reset status when market changes
            updated.name = undefined;
            updated.currency = undefined;
          }
        }
        
        return updated;
      }
      return stock;
    }));
  };

  const verifyStock = async (instrumentCode: string) => {
    const stock = stockAssignments.find(s => s.instrument_code === instrumentCode);
    if (!stock || !stock.market_key) {
      setError('Please select a market before verifying');
      return;
    }

    setVerifying(instrumentCode);
    setError(null);

    try {
      const response = await fetch('/api/import/assign-markets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stock_assignments: [{
            instrument_code: instrumentCode,
            market_key: stock.market_key,
          }],
        }),
      });

      if (!response.ok) {
        throw new Error('Verification failed');
      }

      const data = await response.json();
      const result = data.data.results[0];

      if (result.success) {
        updateStockAssignment(instrumentCode, 'verification_status', 'verified');
        updateStockAssignment(instrumentCode, 'name', result.name);
        updateStockAssignment(instrumentCode, 'currency', result.currency);
      } else {
        updateStockAssignment(instrumentCode, 'verification_status', 'failed');
        setError(`Verification failed for ${instrumentCode}: ${result.error}`);
      }
    } catch (err) {
      updateStockAssignment(instrumentCode, 'verification_status', 'failed');
      setError(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setVerifying(null);
    }
  };

  const verifyAllStocks = async () => {
    const stocksToVerify = stockAssignments.filter(s => s.market_key && s.verification_status === 'pending');
    
    if (stocksToVerify.length === 0) {
      setError('No stocks ready for verification');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/import/assign-markets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stock_assignments: stocksToVerify.map(stock => ({
            instrument_code: stock.instrument_code,
            market_key: stock.market_key,
          })),
        }),
      });

      if (!response.ok) {
        throw new Error('Batch verification failed');
      }

      const data = await response.json();
      
      // Update all stocks with verification results
      data.data.results.forEach((result: any) => {
        if (result.success) {
          updateStockAssignment(result.instrument_code, 'verification_status', 'verified');
          updateStockAssignment(result.instrument_code, 'name', result.name);
          updateStockAssignment(result.instrument_code, 'currency', result.currency);
        } else {
          updateStockAssignment(result.instrument_code, 'verification_status', 'failed');
        }
      });

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Batch verification failed');
    } finally {
      setLoading(false);
    }
  };

  const markAsDelisted = (instrumentCode: string) => {
    updateStockAssignment(instrumentCode, 'verification_status', 'delisted');
  };

  const canProceed = () => {
    return stockAssignments.every(stock => 
      stock.verification_status === 'verified' || stock.verification_status === 'delisted'
    );
  };

  const handleProceed = () => {
    const verificationResults = {
      stockAssignments,
      summary: {
        total: stockAssignments.length,
        verified: stockAssignments.filter(s => s.verification_status === 'verified').length,
        delisted: stockAssignments.filter(s => s.verification_status === 'delisted').length,
        failed: stockAssignments.filter(s => s.verification_status === 'failed').length,
      },
    };
    onStockVerification(verificationResults);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'verified':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-success">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22,4 12,14.01 9,11.01"/>
          </svg>
        );
      case 'failed':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-error">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
        );
      case 'delisted':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-warning">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 8v4"/>
            <path d="M12 16h.01"/>
          </svg>
        );
      default:
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-secondary">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
        );
    }
  };

  if (newStocks.length === 0) {
    return (
      <div className="stock-verification-section">
        <div className="no-new-stocks glass">
          <div className="success-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>
          </div>
          <h3>No New Stocks to Verify</h3>
          <p>All stocks in your transaction data already exist in the portfolio.</p>
          <button className="btn btn-primary" onClick={handleProceed}>
            Proceed to Import
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="stock-verification-section">
      {/* Header */}
      <div className="verification-header glass">
        <div className="header-content">
          <h3>Verify New Stocks</h3>
          <p>Assign markets to new stocks and verify them with Yahoo Finance</p>
        </div>
        <div className="header-actions">
          <button 
            onClick={verifyAllStocks}
            disabled={loading || stockAssignments.filter(s => s.market_key && s.verification_status === 'pending').length === 0}
            className="btn btn-primary"
          >
            {loading ? 'Verifying...' : 'Verify All Pending'}
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-message glass">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <span>{error}</span>
          <button onClick={() => setError(null)} className="btn-close">×</button>
        </div>
      )}

      {/* Stock Assignment Table */}
      <div className="stock-assignment-table glass">
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Market</th>
              <th>Yahoo Symbol</th>
              <th>Stock Name</th>
              <th>Currency</th>
              <th>DRP</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {stockAssignments.map(stock => (
              <tr key={stock.instrument_code}>
                <td className="ticker-cell">
                  <span className="ticker-code">{stock.instrument_code}</span>
                </td>
                <td className="market-cell">
                  <select
                    value={stock.market_key}
                    onChange={(e) => updateStockAssignment(stock.instrument_code, 'market_key', e.target.value)}
                    className="market-select"
                  >
                    <option value="">Select Market</option>
                    {markets.map(market => (
                      <option key={market.market_key} value={market.market_key}>
                        {market.market_or_index} ({market.country})
                      </option>
                    ))}
                  </select>
                </td>
                <td className="yahoo-symbol-cell">
                  <span className="yahoo-symbol">{stock.yahoo_symbol}</span>
                </td>
                <td className="stock-name-cell">
                  <span className="stock-name">{stock.name || '-'}</span>
                </td>
                <td className="currency-cell">
                  <span className="currency">{stock.currency || '-'}</span>
                </td>
                <td className="drp-cell">
                  <input
                    type="checkbox"
                    checked={stock.drp_enabled}
                    onChange={(e) => updateStockAssignment(stock.instrument_code, 'drp_enabled', e.target.checked)}
                    className="drp-checkbox"
                  />
                </td>
                <td className="status-cell">
                  <div className="status-indicator">
                    {getStatusIcon(stock.verification_status)}
                    <span className={`status-text ${stock.verification_status}`}>
                      {stock.verification_status.charAt(0).toUpperCase() + stock.verification_status.slice(1)}
                    </span>
                  </div>
                </td>
                <td className="actions-cell">
                  <div className="action-menu">
                    <button
                      onClick={() => verifyStock(stock.instrument_code)}
                      disabled={!stock.market_key || verifying === stock.instrument_code || stock.verification_status === 'verified'}
                      className="btn btn-sm btn-outline"
                    >
                      {verifying === stock.instrument_code ? 'Verifying...' : 'Verify'}
                    </button>
                    <button
                      onClick={() => markAsDelisted(stock.instrument_code)}
                      disabled={stock.verification_status === 'delisted'}
                      className="btn btn-sm btn-secondary"
                    >
                      Mark Delisted
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary and Actions */}
      <div className="verification-summary">
        <div className="summary-stats">
          <div className="stat-item">
            <span className="stat-label">Total Stocks:</span>
            <span className="stat-value">{stockAssignments.length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Verified:</span>
            <span className="stat-value text-success">{stockAssignments.filter(s => s.verification_status === 'verified').length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Pending:</span>
            <span className="stat-value text-warning">{stockAssignments.filter(s => s.verification_status === 'pending').length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Delisted:</span>
            <span className="stat-value text-secondary">{stockAssignments.filter(s => s.verification_status === 'delisted').length}</span>
          </div>
        </div>

        <div className="proceed-actions">
          {canProceed() ? (
            <div className="success-state">
              <p className="action-message">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                  <polyline points="22,4 12,14.01 9,11.01"/>
                </svg>
                All stocks are ready for import. Proceed to final import step.
              </p>
              <button className="btn btn-primary btn-large" onClick={handleProceed}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="9,18 15,12 9,6"/>
                </svg>
                Proceed to Import Transactions
              </button>
            </div>
          ) : (
            <div className="pending-state">
              <p className="action-message">
                Please verify all stocks or mark them as delisted before proceeding.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};