import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { BulkStockActions } from './BulkStockActions';
import { StockEditor } from './StockEditor';

interface Stock {
  id: number;
  symbol: string;
  name: string | null;
  market: string | null;
  yahoo_symbol: string | null;
  verification_status: 'pending' | 'verified' | 'inactive' | 'error';
  verification_error: string | null;
  created_at: string;
  updated_at: string;
  transaction_count: number;
  current_price: number | null;
  last_updated: string | null;
}

interface Market {
  code: string;
  name: string;
  suffix: string;
  country: string;
  timezone: string;
}

export const StockManagement: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStocks, setSelectedStocks] = useState<number[]>([]);
  const [bulkAction, setBulkAction] = useState<string>('');
  const [filter, setFilter] = useState<'all' | 'pending' | 'verified' | 'inactive' | 'error'>('all');
  const [editingStock, setEditingStock] = useState<Stock | null>(null);

  useEffect(() => {
    loadStocks();
    loadMarkets();
  }, [portfolioId]);

  const loadStocks = async () => {
    try {
      const response = await fetch(`/api/portfolio/${portfolioId}/stocks`);
      if (!response.ok) {
        throw new Error('Failed to load stocks');
      }
      const data = await response.json();
      setStocks(data.stocks || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stocks');
    } finally {
      setLoading(false);
    }
  };

  const loadMarkets = async () => {
    try {
      const response = await fetch('/api/markets');
      if (!response.ok) {
        throw new Error('Failed to load markets');
      }
      const data = await response.json();
      setMarkets(data.markets || []);
    } catch (err) {
      console.error('Failed to load markets:', err);
    }
  };

  const handleStockSelection = (stockId: number) => {
    setSelectedStocks(prev => 
      prev.includes(stockId) 
        ? prev.filter(id => id !== stockId)
        : [...prev, stockId]
    );
  };

  const handleSelectAll = () => {
    const filteredStocks = getFilteredStocks();
    const allSelected = filteredStocks.every(stock => selectedStocks.includes(stock.id));
    
    if (allSelected) {
      setSelectedStocks([]);
    } else {
      setSelectedStocks(filteredStocks.map(stock => stock.id));
    }
  };

  const handleBulkAction = async () => {
    if (!bulkAction || selectedStocks.length === 0) return;

    try {
      const response = await fetch(`/api/portfolio/${portfolioId}/stocks/bulk-action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: bulkAction,
          stock_ids: selectedStocks,
        }),
      });

      if (!response.ok) {
        throw new Error('Bulk action failed');
      }

      await loadStocks();
      setSelectedStocks([]);
      setBulkAction('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk action failed');
    }
  };

  const handleSingleVerification = async (stockId: number) => {
    try {
      const response = await fetch(`/api/portfolio/${portfolioId}/stocks/${stockId}/verify`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Stock verification failed');
      }

      await loadStocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Stock verification failed');
    }
  };

  const handleBulkVerify = async (stockIds: number[]) => {
    try {
      const response = await fetch(`/api/portfolio/${portfolioId}/stocks/bulk-verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ stock_ids: stockIds }),
      });

      if (!response.ok) {
        throw new Error('Bulk verification failed');
      }

      await loadStocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk verification failed');
    }
  };

  const handleBulkMarkDelisted = async (stockIds: number[]) => {
    try {
      const response = await fetch(`/api/portfolio/${portfolioId}/stocks/bulk-inactive`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ stock_ids: stockIds }),
      });

      if (!response.ok) {
        throw new Error('Bulk mark inactive failed');
      }

      await loadStocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk mark inactive failed');
    }
  };

  const handleBulkReset = async (stockIds: number[]) => {
    try {
      const response = await fetch(`/api/portfolio/${portfolioId}/stocks/bulk-reset`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ stock_ids: stockIds }),
      });

      if (!response.ok) {
        throw new Error('Bulk reset failed');
      }

      await loadStocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk reset failed');
    }
  };

  const handleStockEdit = (stock: Stock) => {
    setEditingStock(stock);
  };

  const handleStockSave = async (updatedStock: Partial<Stock>) => {
    if (!editingStock) return;

    try {
      const response = await fetch(`/api/portfolio/${portfolioId}/stocks/${editingStock.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatedStock),
      });

      if (!response.ok) {
        throw new Error('Failed to update stock');
      }

      await loadStocks();
      setEditingStock(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update stock');
    }
  };

  const getFilteredStocks = () => {
    if (filter === 'all') return stocks;
    return stocks.filter(stock => stock.verification_status === filter);
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
      case 'pending':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-warning">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
        );
      case 'inactive':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-error">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
        );
      case 'error':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-error">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        );
      default:
        return null;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'verified': return 'Verified';
      case 'pending': return 'Pending';
      case 'inactive': return 'Inactive';
      case 'error': return 'Error';
      default: return 'Unknown';
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'verified': return 'status-verified';
      case 'pending': return 'status-pending';
      case 'inactive': return 'status-inactive';
      case 'error': return 'status-error';
      default: return '';
    }
  };

  const filteredStocks = getFilteredStocks();

  if (loading) {
    return (
      <div className="stock-management-loading">
        <div className="loading-spinner">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 12a9 9 0 11-6.219-8.56"/>
          </svg>
        </div>
        <h3>Loading Stock Data...</h3>
        <p>Please wait while we load your stock information</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="stock-management-error">
        <div className="error-card">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <div className="error-content">
            <h3>Error Loading Stocks</h3>
            <p>{error}</p>
            <button onClick={loadStocks} className="btn btn-primary">
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="stock-management">
      <div className="stock-management-header">
        <div className="header-content">
          <h2>Stock Management</h2>
          <p>Manage and verify stock symbols in your portfolio</p>
        </div>
        
        <div className="header-stats">
          <div className="stat-card">
            <div className="stat-value">{stocks.length}</div>
            <div className="stat-label">Total Stocks</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stocks.filter(s => s.verification_status === 'verified').length}</div>
            <div className="stat-label">Verified</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stocks.filter(s => s.verification_status === 'pending').length}</div>
            <div className="stat-label">Pending</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stocks.filter(s => s.verification_status === 'error').length}</div>
            <div className="stat-label">Errors</div>
          </div>
        </div>
      </div>

      <div className="stock-management-controls">
        <div className="filter-controls">
          <label className="filter-label">Filter by status:</label>
          <select 
            value={filter} 
            onChange={(e) => setFilter(e.target.value as any)}
            className="filter-select"
          >
            <option value="all">All Stocks</option>
            <option value="pending">Pending Verification</option>
            <option value="verified">Verified</option>
            <option value="inactive">Inactive</option>
            <option value="error">Errors</option>
          </select>
        </div>

      </div>

      <BulkStockActions
        selectedStocks={selectedStocks}
        totalStocks={filteredStocks.length}
        onBulkVerify={handleBulkVerify}
        onBulkMarkDelisted={handleBulkMarkDelisted}
        onBulkReset={handleBulkReset}
        onClearSelection={() => setSelectedStocks([])}
        loading={loading}
      />

      <div className="stock-table-container">
        <table className="stock-table">
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  checked={filteredStocks.length > 0 && filteredStocks.every(stock => selectedStocks.includes(stock.id))}
                  onChange={handleSelectAll}
                />
              </th>
              <th>Symbol</th>
              <th>Name</th>
              <th>Market</th>
              <th>Yahoo Symbol</th>
              <th>Status</th>
              <th>Transactions</th>
              <th>Current Price</th>
              <th>Last Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredStocks.map(stock => (
              <tr key={stock.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedStocks.includes(stock.id)}
                    onChange={() => handleStockSelection(stock.id)}
                  />
                </td>
                <td>
                  <div className="stock-symbol">
                    <span className="symbol-text">{stock.symbol}</span>
                  </div>
                </td>
                <td>
                  <div className="stock-name">
                    {stock.name || <span className="no-data">No name</span>}
                  </div>
                </td>
                <td>
                  <div className="stock-market">
                    {stock.market || <span className="no-data">Not set</span>}
                  </div>
                </td>
                <td>
                  <div className="yahoo-symbol">
                    {stock.yahoo_symbol || <span className="no-data">Not set</span>}
                  </div>
                </td>
                <td>
                  <div className={`stock-status ${getStatusClass(stock.verification_status)}`}>
                    {getStatusIcon(stock.verification_status)}
                    <span className="status-label">{getStatusLabel(stock.verification_status)}</span>
                    {stock.verification_error && (
                      <div className="status-error" title={stock.verification_error}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="10"/>
                          <path d="M12 16v-4"/>
                          <path d="M12 8h.01"/>
                        </svg>
                      </div>
                    )}
                  </div>
                </td>
                <td>
                  <div className="transaction-count">
                    {stock.transaction_count}
                  </div>
                </td>
                <td>
                  <div className="current-price">
                    {stock.current_price !== null ? (
                      <span className="price-value">${stock.current_price.toFixed(2)}</span>
                    ) : (
                      <span className="no-data">No price</span>
                    )}
                  </div>
                </td>
                <td>
                  <div className="last-updated">
                    {stock.last_updated ? (
                      <span className="date-value">
                        {new Date(stock.last_updated).toLocaleDateString()}
                      </span>
                    ) : (
                      <span className="no-data">Never</span>
                    )}
                  </div>
                </td>
                <td>
                  <div className="stock-actions">
                    {stock.verification_status === 'pending' && (
                      <button
                        onClick={() => handleSingleVerification(stock.id)}
                        className="btn btn-sm btn-primary"
                        title="Verify this stock"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                          <polyline points="22,4 12,14.01 9,11.01"/>
                        </svg>
                      </button>
                    )}
                    <button
                      onClick={() => handleStockEdit(stock)}
                      className="btn btn-sm btn-outline"
                      title="Edit stock details"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredStocks.length === 0 && (
          <div className="no-stocks">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
            </svg>
            <h3>No stocks found</h3>
            <p>
              {filter === 'all' 
                ? 'No stocks have been created yet. Import some transactions to get started.'
                : `No stocks with status "${filter}" found.`
              }
            </p>
          </div>
        )}
      </div>

      {editingStock && (
        <StockEditor
          stock={editingStock}
          markets={markets}
          onSave={handleStockSave}
          onCancel={() => setEditingStock(null)}
          onVerify={handleSingleVerification}
          loading={loading}
        />
      )}
    </div>
  );
};