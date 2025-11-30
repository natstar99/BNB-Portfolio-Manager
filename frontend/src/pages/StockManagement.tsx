import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { StagedTransactionsModal } from '../components/StagedTransactionsModal';

interface Stock {
  stock_key: number;
  portfolio_key: number;
  instrument_code: string;
  yahoo_symbol: string;
  name: string;
  market_key: number | null;
  sector: string | null;
  industry: string | null;
  exchange: string | null;
  currency: string | null;
  country: string | null;
  market_cap: number | null;
  verification_status: 'pending' | 'verified' | 'inactive' | 'failed';
  drp_enabled: boolean;
  current_price: number | null;
  last_updated: string | null;
}

interface Market {
  market_key: number;
  market_or_index: string;
  market_suffix: string;
}

export const StockManagement: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStocks, setSelectedStocks] = useState<Set<number>>(new Set());
  const [verifying, setVerifying] = useState<number | null>(null);
  const [showStagedTransactions, setShowStagedTransactions] = useState(false);
  const [filter, setFilter] = useState<'all' | 'pending' | 'verified' | 'inactive' | 'failed'>('all');
  const [bulkAssigningMarket, setBulkAssigningMarket] = useState(false);
  const [bulkVerifying, setBulkVerifying] = useState(false);
  const [selectedMarketForBulk, setSelectedMarketForBulk] = useState<string>('');
  const [markingInactive, setMarkingInactive] = useState<number | null>(null);

  useEffect(() => {
    if (portfolioId) {
      fetchPortfolioStocks();
      fetchMarkets();
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
        setStocks(data.data.new_stock_symbols || []);
      } else {
        throw new Error(data.error || 'Failed to fetch portfolio stocks');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch portfolio stocks');
    } finally {
      setLoading(false);
    }
  };

  const fetchMarkets = async () => {
    try {
      const response = await fetch('/api/import/markets');
      if (!response.ok) {
        throw new Error('Failed to fetch markets');
      }
      const data = await response.json();
      setMarkets(data.data || []);
    } catch (err) {
      console.error('Failed to load markets:', err);
    }
  };

  const handleMarketChange = async (stock: Stock, marketKey: string) => {
    if (!marketKey) return;

    const market = markets.find(m => m.market_key.toString() === marketKey);
    if (!market) return;

    const yahoo_symbol = `${stock.instrument_code}${market.market_suffix || ''}`;

    // Update locally
    setStocks(prev => prev.map(s =>
      s.stock_key === stock.stock_key
        ? { ...s, market_key: parseInt(marketKey), yahoo_symbol, verification_status: 'pending' as const }
        : s
    ));

    // Update backend
    try {
      await fetch(`/api/import/save-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          portfolioId: parseInt(portfolioId!),
          stockAssignments: [{
            instrument_code: stock.instrument_code,
            market_key: marketKey,
            yahoo_symbol,
            name: stock.name,
            verification_status: 'pending',
            drp_enabled: stock.drp_enabled
          }]
        })
      });
    } catch (err) {
      console.error('Failed to update market:', err);
    }
  };

  const verifyStock = async (stock: Stock) => {
    if (!stock.market_key) {
      setError('Please select a market before verifying');
      return;
    }

    setVerifying(stock.stock_key);
    setError(null);

    try {
      const response = await fetch('/api/import/assign-markets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stock_assignments: [{
            instrument_code: stock.instrument_code,
            market_key: stock.market_key.toString()
          }]
        })
      });

      if (!response.ok) {
        throw new Error('Verification failed');
      }

      const data = await response.json();
      const result = data.data.results[0];

      if (result.success) {
        // Update stock with verification results
        setStocks(prev => prev.map(s =>
          s.stock_key === stock.stock_key
            ? {
                ...s,
                verification_status: 'verified' as const,
                name: result.name || s.name,
                currency: result.currency || s.currency,
                current_price: result.current_price || s.current_price,
                sector: result.sector || s.sector,
                industry: result.industry || s.industry,
                exchange: result.exchange || s.exchange
              }
            : s
        ));

        // Save to backend
        await fetch(`/api/import/save-verification`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            portfolioId: parseInt(portfolioId!),
            stockAssignments: [{
              instrument_code: stock.instrument_code,
              market_key: stock.market_key.toString(),
              yahoo_symbol: stock.yahoo_symbol,
              name: result.name,
              currency: result.currency,
              verification_status: 'verified',
              drp_enabled: stock.drp_enabled,
              current_price: result.current_price,
              sector: result.sector,
              industry: result.industry,
              exchange: result.exchange
            }]
          })
        });
      } else {
        setStocks(prev => prev.map(s =>
          s.stock_key === stock.stock_key
            ? { ...s, verification_status: 'failed' as const }
            : s
        ));
        setError(`Verification failed for ${stock.instrument_code}: ${result.error}`);
      }
    } catch (err) {
      setStocks(prev => prev.map(s =>
        s.stock_key === stock.stock_key
          ? { ...s, verification_status: 'failed' as const }
          : s
      ));
      setError(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setVerifying(null);
    }
  };

  const handleDRPChange = async (stock: Stock, enabled: boolean) => {
    setStocks(prev => prev.map(s =>
      s.stock_key === stock.stock_key
        ? { ...s, drp_enabled: enabled }
        : s
    ));

    // Update backend
    try {
      await fetch(`/api/import/save-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          portfolioId: parseInt(portfolioId!),
          stockAssignments: [{
            instrument_code: stock.instrument_code,
            market_key: stock.market_key?.toString() || '',
            yahoo_symbol: stock.yahoo_symbol,
            name: stock.name,
            verification_status: stock.verification_status,
            drp_enabled: enabled
          }]
        })
      });
    } catch (err) {
      console.error('Failed to update DRP:', err);
    }
  };

  const toggleStockSelection = (stockKey: number) => {
    setSelectedStocks(prev => {
      const newSet = new Set(prev);
      if (newSet.has(stockKey)) {
        newSet.delete(stockKey);
      } else {
        newSet.add(stockKey);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    const filteredStocks = getFilteredStocks();
    if (selectedStocks.size === filteredStocks.length) {
      setSelectedStocks(new Set());
    } else {
      setSelectedStocks(new Set(filteredStocks.map(s => s.stock_key)));
    }
  };

  const bulkAssignMarket = async () => {
    if (!selectedMarketForBulk || selectedStocks.size === 0) return;

    setBulkAssigningMarket(true);
    setError(null);

    const market = markets.find(m => m.market_key.toString() === selectedMarketForBulk);
    if (!market) return;

    try {
      const stocksToUpdate = stocks.filter(s => selectedStocks.has(s.stock_key));
      const assignments = stocksToUpdate.map(stock => ({
        instrument_code: stock.instrument_code,
        market_key: selectedMarketForBulk,
        yahoo_symbol: `${stock.instrument_code}${market.market_suffix || ''}`,
        name: stock.name,
        verification_status: 'pending',
        drp_enabled: stock.drp_enabled
      }));

      // Update locally
      setStocks(prev => prev.map(s => {
        if (selectedStocks.has(s.stock_key)) {
          return {
            ...s,
            market_key: parseInt(selectedMarketForBulk),
            yahoo_symbol: `${s.instrument_code}${market.market_suffix || ''}`,
            verification_status: 'pending' as const
          };
        }
        return s;
      }));

      // Update backend
      await fetch(`/api/import/save-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          portfolioId: parseInt(portfolioId!),
          stockAssignments: assignments
        })
      });

      setSelectedStocks(new Set());
      setSelectedMarketForBulk('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk market assignment failed');
    } finally {
      setBulkAssigningMarket(false);
    }
  };

  const markStockInactive = async (stock: Stock) => {
    setMarkingInactive(stock.stock_key);
    setError(null);

    try {
      // Update locally
      setStocks(prev => prev.map(s =>
        s.stock_key === stock.stock_key
          ? { ...s, verification_status: 'inactive' as const }
          : s
      ));

      // Update backend
      await fetch(`/api/import/save-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          portfolioId: parseInt(portfolioId!),
          stockAssignments: [{
            instrument_code: stock.instrument_code,
            market_key: stock.market_key?.toString() || '',
            yahoo_symbol: stock.yahoo_symbol,
            name: stock.name,
            verification_status: 'inactive',
            drp_enabled: stock.drp_enabled
          }]
        })
      });
    } catch (err) {
      console.error('Failed to mark as inactive:', err);
      setError(err instanceof Error ? err.message : 'Failed to mark as inactive');
    } finally {
      setMarkingInactive(null);
    }
  };

  const bulkMarkInactive = async () => {
    if (selectedStocks.size === 0) return;

    try {
      const stocksToMarkInactive = stocks.filter(s => selectedStocks.has(s.stock_key));

      // Update locally
      setStocks(prev => prev.map(s =>
        selectedStocks.has(s.stock_key)
          ? { ...s, verification_status: 'inactive' as const }
          : s
      ));

      // Update backend
      await fetch(`/api/import/save-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          portfolioId: parseInt(portfolioId!),
          stockAssignments: stocksToMarkInactive.map(stock => ({
            instrument_code: stock.instrument_code,
            market_key: stock.market_key?.toString() || '',
            yahoo_symbol: stock.yahoo_symbol,
            name: stock.name,
            verification_status: 'inactive',
            drp_enabled: stock.drp_enabled
          }))
        })
      });

      setSelectedStocks(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to mark as inactive');
    }
  };

  const bulkVerifyStocks = async () => {
    if (selectedStocks.size === 0) return;

    setBulkVerifying(true);
    setError(null);

    try {
      const stocksToVerify = stocks.filter(s =>
        selectedStocks.has(s.stock_key) &&
        s.market_key &&
        s.verification_status === 'pending'
      );

      if (stocksToVerify.length === 0) {
        setError('No pending stocks with markets assigned to verify');
        setBulkVerifying(false);
        return;
      }

      const response = await fetch('/api/import/assign-markets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stock_assignments: stocksToVerify.map(stock => ({
            instrument_code: stock.instrument_code,
            market_key: stock.market_key!.toString()
          }))
        })
      });

      if (!response.ok) {
        throw new Error('Bulk verification failed');
      }

      const data = await response.json();

      // Build assignments array from verification results
      const allAssignments: any[] = [];

      // Process results for stocks that were verified
      for (const result of data.data.results) {
        const stock = stocksToVerify.find(s => s.instrument_code === result.instrument_code);
        if (!stock) continue;

        if (result.success) {
          allAssignments.push({
            instrument_code: stock.instrument_code,
            market_key: stock.market_key!.toString(),
            yahoo_symbol: stock.yahoo_symbol,
            name: result.name,
            currency: result.currency,
            verification_status: 'verified',
            drp_enabled: stock.drp_enabled,
            current_price: result.current_price,
            sector: result.sector,
            industry: result.industry,
            exchange: result.exchange
          });
        } else {
          allAssignments.push({
            instrument_code: stock.instrument_code,
            market_key: stock.market_key!.toString(),
            yahoo_symbol: stock.yahoo_symbol,
            name: stock.name,
            verification_status: 'failed',
            drp_enabled: stock.drp_enabled
          });
        }
      }

      console.log('Bulk verify - assignments to save:', allAssignments);

      // Save ALL verification results to backend FIRST
      if (allAssignments.length > 0) {
        const saveResponse = await fetch(`/api/import/save-verification`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            portfolioId: parseInt(portfolioId!),
            stockAssignments: allAssignments
          })
        });

        if (!saveResponse.ok) {
          const errorData = await saveResponse.json();
          console.error('Failed to save bulk verification:', errorData);
          throw new Error(errorData.error || 'Failed to save verification results');
        }

        const saveData = await saveResponse.json();
        console.log('Bulk verify - save successful:', saveData);
      } else {
        console.warn('Bulk verify - no assignments to save');
      }

      // Update UI state after successful save
      setStocks(prev => prev.map(s => {
        const result = data.data.results.find((r: any) => r.instrument_code === s.instrument_code);

        if (result && result.success) {
          return {
            ...s,
            verification_status: 'verified' as const,
            name: result.name || s.name,
            currency: result.currency || s.currency,
            current_price: result.current_price || s.current_price,
            sector: result.sector || s.sector,
            industry: result.industry || s.industry,
            exchange: result.exchange || s.exchange
          };
        } else if (result && !result.success) {
          return {
            ...s,
            verification_status: 'failed' as const
          };
        }
        return s;
      }));

      setSelectedStocks(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk verification failed');
    } finally {
      setBulkVerifying(false);
    }
  };

  const getFilteredStocks = () => {
    if (filter === 'all') return stocks;
    return stocks.filter(stock => stock.verification_status === filter);
  };

  const filteredStocks = getFilteredStocks();

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

  const pendingCount = stocks.filter(s => s.verification_status === 'pending').length;

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header">
        <div className="header-content">
          <h1>Stock Management</h1>
          <p className="page-subtitle">Manage and verify stock symbols in your portfolio</p>
        </div>
        <div className="header-actions">
          <button
            onClick={() => setShowStagedTransactions(true)}
            className="btn btn-warning"
          >
            View Staged Transactions
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <div className="metric-label">Total Stocks</div>
          <div className="metric-value">{stocks.length}</div>
        </div>
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <div className="metric-label">Verified</div>
          <div className="metric-value text-success">{stocks.filter(s => s.verification_status === 'verified').length}</div>
        </div>
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <div className="metric-label">Pending</div>
          <div className="metric-value text-warning">{pendingCount}</div>
        </div>
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <div className="metric-label">Failed</div>
          <div className="metric-value text-error">{stocks.filter(s => s.verification_status === 'failed').length}</div>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedStocks.size > 0 && (
        <div className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <div style={{ fontWeight: 600 }}>
              {selectedStocks.size} stock{selectedStocks.size !== 1 ? 's' : ''} selected
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <label>Assign Market:</label>
              <select
                value={selectedMarketForBulk}
                onChange={(e) => setSelectedMarketForBulk(e.target.value)}
                style={{ padding: '0.5rem', minWidth: '200px' }}
              >
                <option value="">Select Market</option>
                {markets.map(market => (
                  <option key={market.market_key} value={market.market_key}>
                    {market.market_or_index}
                  </option>
                ))}
              </select>
              <button
                onClick={bulkAssignMarket}
                disabled={!selectedMarketForBulk || bulkAssigningMarket}
                className="btn btn-primary"
              >
                {bulkAssigningMarket ? 'Assigning...' : 'Assign to Selected'}
              </button>
            </div>
            <button
              onClick={bulkVerifyStocks}
              disabled={bulkVerifying}
              className="btn btn-primary"
            >
              {bulkVerifying ? 'Verifying...' : 'Verify Selected'}
            </button>
            <button
              onClick={bulkMarkInactive}
              className="btn btn-warning"
            >
              Mark Selected as Inactive
            </button>
            <button
              onClick={() => setSelectedStocks(new Set())}
              className="btn btn-outline"
            >
              Clear Selection
            </button>
          </div>
        </div>
      )}

      {/* Filter */}
      <div style={{ marginBottom: '1rem' }}>
        <label style={{ marginRight: '0.5rem' }}>Filter by status:</label>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as any)}
          style={{ padding: '0.5rem', minWidth: '200px' }}
        >
          <option value="all">All Stocks ({stocks.length})</option>
          <option value="pending">Pending Verification ({stocks.filter(s => s.verification_status === 'pending').length})</option>
          <option value="verified">Verified ({stocks.filter(s => s.verification_status === 'verified').length})</option>
          <option value="inactive">Inactive ({stocks.filter(s => s.verification_status === 'inactive').length})</option>
          <option value="failed">Failed ({stocks.filter(s => s.verification_status === 'failed').length})</option>
        </select>
      </div>

      {/* Table */}
      <div className="card" style={{ overflow: 'auto' }}>
        <table className="table" style={{ width: '100%', minWidth: '1200px' }}>
          <thead>
            <tr>
              <th style={{ width: '40px' }}>
                <input
                  type="checkbox"
                  checked={filteredStocks.length > 0 && selectedStocks.size === filteredStocks.length}
                  onChange={toggleSelectAll}
                />
              </th>
              <th>Ticker</th>
              <th>Name</th>
              <th>Market</th>
              <th>Yahoo Symbol</th>
              <th>Currency</th>
              <th>Price</th>
              <th>DRP</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredStocks.map(stock => (
              <tr key={stock.stock_key}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedStocks.has(stock.stock_key)}
                    onChange={() => toggleStockSelection(stock.stock_key)}
                  />
                </td>
                <td style={{ fontWeight: 600 }}>{stock.instrument_code}</td>
                <td>{stock.name}</td>
                <td>
                  <select
                    value={stock.market_key?.toString() || ''}
                    onChange={(e) => handleMarketChange(stock, e.target.value)}
                    style={{ width: '100%', padding: '0.25rem' }}
                  >
                    <option value="">Select Market</option>
                    {markets.map(market => (
                      <option key={market.market_key} value={market.market_key}>
                        {market.market_or_index}
                      </option>
                    ))}
                  </select>
                </td>
                <td>{stock.yahoo_symbol}</td>
                <td>{stock.currency || '-'}</td>
                <td>{stock.current_price ? `$${stock.current_price.toFixed(2)}` : '-'}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={stock.drp_enabled}
                    onChange={(e) => handleDRPChange(stock, e.target.checked)}
                  />
                </td>
                <td className={`status-${stock.verification_status}`}>
                  {stock.verification_status.charAt(0).toUpperCase() + stock.verification_status.slice(1)}
                </td>
                <td>
                  <div style={{ display: 'flex', gap: '0.25rem' }}>
                    {stock.verification_status === 'pending' && stock.market_key && (
                      <button
                        onClick={() => verifyStock(stock)}
                        disabled={verifying === stock.stock_key}
                        className="btn btn-sm btn-primary"
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.875rem' }}
                      >
                        {verifying === stock.stock_key ? 'Verifying...' : 'Verify'}
                      </button>
                    )}
                    {(stock.verification_status === 'pending' || stock.verification_status === 'failed') && (
                      <button
                        onClick={() => markStockInactive(stock)}
                        disabled={markingInactive === stock.stock_key}
                        className="btn btn-warning"
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.875rem' }}
                        title="Mark as inactive (delisted/not traded)"
                      >
                        {markingInactive === stock.stock_key ? 'Marking...' : 'Inactive'}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredStocks.length === 0 && (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
            <p>No stocks found with status "{filter}"</p>
          </div>
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
