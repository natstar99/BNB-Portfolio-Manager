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
}

interface StockAssignment {
  instrument_code: string;
  market_key: string;
  yahoo_symbol: string;
  name?: string;
  currency?: string;
  verification_status: 'pending' | 'verified' | 'failed' | 'inactive';
  drp_enabled: boolean;
  notes?: string;
  current_price?: number;
  market_cap_formatted?: string;
  sector?: string;
  industry?: string;
  exchange?: string;
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
  const [selectedStocks, setSelectedStocks] = useState<Set<string>>(new Set());
  const [showMarketModal, setShowMarketModal] = useState(false);
  const [marketSearchQuery, setMarketSearchQuery] = useState('');
  const [showStockModal, setShowStockModal] = useState(false);
  const [selectedStock, setSelectedStock] = useState<StockAssignment | null>(null);

  // Get unique stocks that need market assignment
  const newStocks = validationResults?.new_stock_symbols || [];

  useEffect(() => {
    fetchMarkets();
    initializeStockAssignments();
  }, []);

  // Update selectedStock when stockAssignments changes
  useEffect(() => {
    if (selectedStock && stockAssignments.length > 0) {
      const updatedStock = stockAssignments.find(s => s.instrument_code === selectedStock.instrument_code);
      if (updatedStock) {
        setSelectedStock(updatedStock);
      }
    }
  }, [stockAssignments, selectedStock?.instrument_code]);

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
    const assignments: StockAssignment[] = newStocks.map((stock: string | any) => {
      // Handle both string (new stocks) and object (existing stocks) formats
      if (typeof stock === 'string') {
        // New stock - initialize with defaults
        return {
          instrument_code: stock,
          market_key: '',
          yahoo_symbol: stock,
          verification_status: 'pending' as const,
          drp_enabled: false,
        };
      } else {
        // Existing stock - use actual database values
        return {
          instrument_code: stock.instrument_code,
          market_key: stock.market_key?.toString() || '',
          yahoo_symbol: stock.yahoo_symbol,
          name: stock.name,
          currency: stock.currency,
          verification_status: stock.verification_status || 'pending',
          drp_enabled: stock.drp_enabled || false,
          current_price: stock.current_price,
          market_cap_formatted: stock.market_cap ? `$${stock.market_cap.toLocaleString()}` : undefined,
          sector: stock.sector,
          industry: stock.industry,
          exchange: stock.exchange,
        };
      }
    });
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

  const toggleStockSelection = (instrumentCode: string) => {
    setSelectedStocks(prev => {
      const newSet = new Set(prev);
      if (newSet.has(instrumentCode)) {
        newSet.delete(instrumentCode);
      } else {
        newSet.add(instrumentCode);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    if (selectedStocks.size === stockAssignments.length) {
      setSelectedStocks(new Set());
    } else {
      setSelectedStocks(new Set(stockAssignments.map(s => s.instrument_code)));
    }
  };

  const assignMarketToSelected = (marketKey: string) => {
    const market = markets.find(m => m.market_key.toString() === marketKey);
    if (!market) return;

    setStockAssignments(prev => prev.map(stock => {
      if (selectedStocks.has(stock.instrument_code)) {
        return {
          ...stock,
          market_key: marketKey,
          yahoo_symbol: `${stock.instrument_code}${market.market_suffix || ''}`,
          verification_status: 'pending' as const,
          name: undefined,
          currency: undefined
        };
      }
      return stock;
    }));
    
    setSelectedStocks(new Set());
    setShowMarketModal(false);
    setMarketSearchQuery('');
  };

  const filteredMarkets = markets.filter(market => 
    market.market_or_index.toLowerCase().includes(marketSearchQuery.toLowerCase()) ||
    market.market_suffix?.toLowerCase().includes(marketSearchQuery.toLowerCase())
  );

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
        updateStockAssignment(instrumentCode, 'current_price', result.current_price);
        updateStockAssignment(instrumentCode, 'market_cap_formatted', result.market_cap_formatted);
        updateStockAssignment(instrumentCode, 'sector', result.sector);
        updateStockAssignment(instrumentCode, 'industry', result.industry);
        updateStockAssignment(instrumentCode, 'exchange', result.exchange);
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

  const canVerifySelected = (): boolean => {
    return Array.from(selectedStocks).every(instrumentCode => {
      const stock = stockAssignments.find(s => s.instrument_code === instrumentCode);
      return stock && stock.market_key && stock.verification_status === 'pending';
    });
  };

  const bulkVerifySelected = async () => {
    const stocksToVerify = stockAssignments.filter(s => 
      selectedStocks.has(s.instrument_code) && 
      s.market_key && 
      s.verification_status === 'pending'
    );
    
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
        throw new Error('Bulk verification failed');
      }

      const data = await response.json();
      
      // Update all stocks with verification results
      data.data.results.forEach((result: any) => {
        if (result.success) {
          updateStockAssignment(result.instrument_code, 'verification_status', 'verified');
          updateStockAssignment(result.instrument_code, 'name', result.name);
          updateStockAssignment(result.instrument_code, 'currency', result.currency);
          updateStockAssignment(result.instrument_code, 'current_price', result.current_price);
          updateStockAssignment(result.instrument_code, 'market_cap_formatted', result.market_cap_formatted);
          updateStockAssignment(result.instrument_code, 'sector', result.sector);
          updateStockAssignment(result.instrument_code, 'industry', result.industry);
          updateStockAssignment(result.instrument_code, 'exchange', result.exchange);
        } else {
          updateStockAssignment(result.instrument_code, 'verification_status', 'failed');
        }
      });

      // Clear selection after verification
      setSelectedStocks(new Set());

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk verification failed');
    } finally {
      setLoading(false);
    }
  };

  const bulkMarkAsInactive = () => {
    selectedStocks.forEach(instrumentCode => {
      updateStockAssignment(instrumentCode, 'verification_status', 'inactive');
    });
    
    // Clear selection after marking as inactive
    setSelectedStocks(new Set());
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
          updateStockAssignment(result.instrument_code, 'current_price', result.current_price);
          updateStockAssignment(result.instrument_code, 'market_cap_formatted', result.market_cap_formatted);
          updateStockAssignment(result.instrument_code, 'sector', result.sector);
          updateStockAssignment(result.instrument_code, 'industry', result.industry);
          updateStockAssignment(result.instrument_code, 'exchange', result.exchange);
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

  const markAsInactive = (instrumentCode: string) => {
    updateStockAssignment(instrumentCode, 'verification_status', 'inactive');
  };


  const handleProceed = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/import/save-verification', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          portfolioId: portfolioId,
          stockAssignments: stockAssignments,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to save verification results');
      }

      const data = await response.json();
      
      if (data.success) {
        // Call the original callback with results
        const verificationResults = {
          stockAssignments,
          summary: {
            total: stockAssignments.length,
            verified: stockAssignments.filter(s => s.verification_status === 'verified').length,
            inactive: stockAssignments.filter(s => s.verification_status === 'inactive').length,
            failed: stockAssignments.filter(s => s.verification_status === 'failed').length,
          },
          saveResults: data,
        };
        onStockVerification(verificationResults);
      } else {
        setError(data.error || 'Failed to save verification results');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save verification results');
    } finally {
      setLoading(false);
    }
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
      case 'inactive':
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

      {/* Bulk Market Assignment */}
      <div className="bulk-assignment-section glass">
        <div className="bulk-header">
          <div className="selection-controls">
            <label className="select-all-control">
              <input
                type="checkbox"
                checked={selectedStocks.size === stockAssignments.length && stockAssignments.length > 0}
                onChange={toggleSelectAll}
                className="select-all-checkbox"
              />
              <span>Select All ({selectedStocks.size} of {stockAssignments.length})</span>
            </label>
          </div>
          <div className="bulk-actions">
            <button
              onClick={() => setShowMarketModal(true)}
              disabled={selectedStocks.size === 0}
              className="btn btn-primary"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1"/>
              </svg>
              Assign Market to Selected ({selectedStocks.size})
            </button>
            <button
              onClick={bulkVerifySelected}
              disabled={selectedStocks.size === 0 || !canVerifySelected()}
              className="btn btn-secondary"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22,4 12,14.01 9,11.01"/>
              </svg>
              Verify Selected ({selectedStocks.size})
            </button>
            <button
              onClick={bulkMarkAsInactive}
              disabled={selectedStocks.size === 0}
              className="btn btn-warning"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 8v4"/>
                <path d="M12 16h.01"/>
              </svg>
              Mark as Inactive ({selectedStocks.size})
            </button>
          </div>
        </div>
      </div>

      {/* Stock Assignment Table */}
      <div className="stock-assignment-table glass">
        <table>
          <thead>
            <tr>
              <th className="select-column">Select</th>
              <th>Ticker</th>
              <th>Market</th>
              <th>Yahoo Symbol</th>
              <th>Stock Name</th>
              <th>Currency</th>
              <th>DRP</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {stockAssignments.map(stock => (
              <tr 
                key={stock.instrument_code} 
                className={selectedStocks.has(stock.instrument_code) ? 'selected' : ''}
                onClick={() => toggleStockSelection(stock.instrument_code)}
                onDoubleClick={() => {
                  setSelectedStock(stock);
                  setShowStockModal(true);
                }}
                style={{ cursor: 'pointer' }}
                title="Click to select, double-click to edit stock details"
              >
                <td className="select-cell">
                  <input
                    type="checkbox"
                    checked={selectedStocks.has(stock.instrument_code)}
                    onChange={() => toggleStockSelection(stock.instrument_code)}
                    onClick={(e) => e.stopPropagation()}
                    className="stock-select-checkbox"
                  />
                </td>
                <td className="ticker-cell">
                  <span className="ticker-code">{stock.instrument_code}</span>
                </td>
                <td className="market-cell">
                  <span className="market-name">
                    {stock.market_key ? 
                      markets.find(m => m.market_key.toString() === stock.market_key)?.market_or_index || 'Unknown Market'
                      : 'Not Assigned'
                    }
                  </span>
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
                    onClick={(e) => e.stopPropagation()}
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Market Assignment Modal */}
      {showMarketModal && (
        <div className="modal-overlay" onClick={() => setShowMarketModal(false)}>
          <div className="market-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Assign Market to Selected Stocks ({selectedStocks.size})</h3>
              <button
                onClick={() => setShowMarketModal(false)}
                className="modal-close"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            
            <div className="modal-body">
              <div className="search-section">
                <label className="search-label">Search Markets</label>
                <input
                  type="text"
                  value={marketSearchQuery}
                  onChange={(e) => setMarketSearchQuery(e.target.value)}
                  placeholder="Search by market name or suffix..."
                  className="search-input"
                  autoFocus
                />
              </div>
              
              <div className="markets-list">
                {filteredMarkets.map(market => (
                  <div
                    key={market.market_key}
                    onClick={() => assignMarketToSelected(market.market_key.toString())}
                    className="market-option"
                  >
                    <div className="market-info">
                      <div className="market-name">{market.market_or_index}</div>
                      <div className="market-details">
                        {market.market_suffix && (
                          <span className="market-suffix">Suffix: {market.market_suffix}</span>
                        )}
                      </div>
                    </div>
                    <div className="select-arrow">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="9,18 15,12 9,6"/>
                      </svg>
                    </div>
                  </div>
                ))}
                {filteredMarkets.length === 0 && (
                  <div className="no-markets">
                    <p>No markets found matching your search</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stock Detail Modal */}
      {showStockModal && selectedStock && (
        <div className="modal-overlay" onClick={() => setShowStockModal(false)}>
          <div className="stock-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Stock Details - {selectedStock.instrument_code}</h3>
              <button
                onClick={() => setShowStockModal(false)}
                className="modal-close"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            
            <div className="modal-body">
              <div className="stock-detail-grid">
                <div className="detail-row">
                  <label>Ticker:</label>
                  <span>{selectedStock.instrument_code}</span>
                </div>
                <div className="detail-row">
                  <label>Yahoo Symbol:</label>
                  <span>{selectedStock.yahoo_symbol}</span>
                </div>
                <div className="detail-row">
                  <label>Market:</label>
                  <span>
                    {selectedStock.market_key ? 
                      markets.find(m => m.market_key.toString() === selectedStock.market_key)?.market_or_index || 'Unknown Market'
                      : 'Not Assigned'
                    }
                  </span>
                </div>
                <div className="detail-row">
                  <label>Stock Name:</label>
                  <span>{selectedStock.name || 'Not verified'}</span>
                </div>
                <div className="detail-row">
                  <label>Currency:</label>
                  <span>{selectedStock.currency || 'Not verified'}</span>
                </div>
                <div className="detail-row">
                  <label>Current Price:</label>
                  <span>{selectedStock.current_price ? `${selectedStock.currency || 'USD'} ${selectedStock.current_price.toFixed(2)}` : 'Not verified'}</span>
                </div>
                <div className="detail-row">
                  <label>Market Cap:</label>
                  <span>{selectedStock.market_cap_formatted || 'Not verified'}</span>
                </div>
                <div className="detail-row">
                  <label>Sector:</label>
                  <span>{selectedStock.sector || 'Not verified'}</span>
                </div>
                <div className="detail-row">
                  <label>Industry:</label>
                  <span>{selectedStock.industry || 'Not verified'}</span>
                </div>
                <div className="detail-row">
                  <label>Exchange:</label>
                  <span>{selectedStock.exchange || 'Not verified'}</span>
                </div>
                <div className="detail-row">
                  <label>Status:</label>
                  <div className="status-indicator">
                    {getStatusIcon(selectedStock.verification_status)}
                    <span className={`status-text ${selectedStock.verification_status}`}>
                      {selectedStock.verification_status.charAt(0).toUpperCase() + selectedStock.verification_status.slice(1)}
                    </span>
                  </div>
                </div>
                <div className="detail-row">
                  <label>DRP Enabled:</label>
                  <input
                    type="checkbox"
                    checked={selectedStock.drp_enabled}
                    onChange={(e) => {
                      const updatedStock = { ...selectedStock, drp_enabled: e.target.checked };
                      setSelectedStock(updatedStock);
                      updateStockAssignment(selectedStock.instrument_code, 'drp_enabled', e.target.checked);
                    }}
                    className="drp-checkbox"
                  />
                </div>
              </div>
            </div>
            
            <div className="modal-footer">
              <div className="modal-actions">
                <button
                  onClick={() => {
                    verifyStock(selectedStock.instrument_code);
                  }}
                  disabled={!selectedStock.market_key || verifying === selectedStock.instrument_code || selectedStock.verification_status === 'verified'}
                  className="btn btn-primary"
                >
                  {verifying === selectedStock.instrument_code ? 'Verifying...' : 'Verify Stock'}
                </button>
                <button
                  onClick={() => {
                    const newStatus: 'pending' | 'inactive' = selectedStock.verification_status === 'inactive' ? 'pending' : 'inactive';
                    updateStockAssignment(selectedStock.instrument_code, 'verification_status', newStatus);
                    const updatedStock = { ...selectedStock, verification_status: newStatus };
                    setSelectedStock(updatedStock);
                  }}
                  className="btn btn-secondary"
                >
                  {selectedStock.verification_status === 'inactive' ? 'Mark as Pending' : 'Mark as Inactive'}
                </button>
                <button
                  onClick={() => setShowStockModal(false)}
                  className="btn btn-outline"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
            <span className="stat-label">Inactive:</span>
            <span className="stat-value text-secondary">{stockAssignments.filter(s => s.verification_status === 'inactive').length}</span>
          </div>
        </div>

        <div className="proceed-actions">
          <div className="save-state">
            <p className="action-message">
              Click to persist changes. Historical data will be collected for all verified stocks. Stocks with Pending, Inactive and Failed status will remain in the staging area for this portfolio.
            </p>
            <div className="proceed-buttons">
              <button className="btn btn-error" onClick={() => window.history.back()}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15,18 9,12 15,6"/>
                </svg>
                Return to Previous Step
              </button>
              <button className="btn btn-primary btn-large" onClick={handleProceed} disabled={loading}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                  <polyline points="17,21 17,13 7,13 7,21"/>
                  <polyline points="7,3 7,8 15,8"/>
                </svg>
                {loading ? 'Saving...' : 'Save and Import into Portfolio'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};