import React, { useState, useEffect } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { usePortfolios } from '../hooks/usePortfolios';
import '../styles/transactions.css';

interface Transaction {
  id: number;
  portfolio_id: number;
  portfolio_name: string;
  symbol: string;
  action: 'buy' | 'sell';
  quantity: number;
  price: number;
  total_amount: number;
  fees: number;
  date: string;
  notes?: string;
  verified: boolean;
  currency: string;
}

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



export const Transactions: React.FC = () => {
  const { portfolios, hasPortfolios, isNewUser } = usePortfolios();
  const location = useLocation();
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [selectedPortfolio, setSelectedPortfolio] = useState<string>('all');
  const [selectedAction, setSelectedAction] = useState<string>('all');
  const [searchSymbol, setSearchSymbol] = useState('');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  
  
  // Add Transaction
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTransaction, setNewTransaction] = useState({
    portfolio_id: portfolioId || (portfolios.length === 1 ? portfolios[0].id.toString() : ''),
    symbol: '',
    action: 'buy' as 'buy' | 'sell',
    quantity: '',
    price: '',
    fees: '0',
    date: new Date().toISOString().split('T')[0],
    notes: ''
  });

  useEffect(() => {
    if (hasPortfolios) {
      fetchTransactions();
    } else {
      setLoading(false);
    }
  }, [hasPortfolios]); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle URL parameters for pre-filtering and portfolio context
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const symbolParam = searchParams.get('symbol');
    
    if (symbolParam) {
      setSearchSymbol(symbolParam);
    }
    
    // Set portfolio filter when on portfolio-specific page
    if (portfolioId) {
      setSelectedPortfolio(portfolioId);
    }
  }, [location.search, portfolioId]);

  // Update new transaction portfolio when context changes
  useEffect(() => {
    if (portfolioId || (portfolios.length === 1 && portfolios[0])) {
      setNewTransaction(prev => ({
        ...prev,
        portfolio_id: portfolioId || portfolios[0].id.toString()
      }));
    }
  }, [portfolioId, portfolios]);

  const fetchTransactions = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Build API URL with portfolio context if available
      let apiUrl = '/api/transactions';
      const params = new URLSearchParams();
      
      if (portfolioId) {
        params.append('portfolio_id', portfolioId);
      }
      
      if (params.toString()) {
        apiUrl += `?${params.toString()}`;
      }
      
      const response = await fetch(apiUrl);
      if (!response.ok) {
        throw new Error('Failed to fetch transactions');
      }
      
      const data = await response.json();
      setTransactions(data.transactions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Transaction fetch error:', err);
    } finally {
      setLoading(false);
    }
  };



  const handleAddTransaction = async () => {
    if (!newTransaction.portfolio_id || !newTransaction.symbol || !newTransaction.quantity || !newTransaction.price) {
      alert('Please fill in all required fields');
      return;
    }
    
    try {
      const response = await fetch('/api/transactions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...newTransaction,
          quantity: parseFloat(newTransaction.quantity),
          price: parseFloat(newTransaction.price),
          fees: parseFloat(newTransaction.fees) || 0,
          portfolio_id: parseInt(newTransaction.portfolio_id),
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to add transaction');
      }
      
      // Refresh transactions
      fetchTransactions();
      setShowAddModal(false);
      setNewTransaction({
        portfolio_id: portfolioId || (portfolios.length === 1 ? portfolios[0].id.toString() : ''),
        symbol: '',
        action: 'buy',
        quantity: '',
        price: '',
        fees: '0',
        date: new Date().toISOString().split('T')[0],
        notes: ''
      });
      
    } catch (err) {
      console.error('Add transaction error:', err);
      alert('Failed to add transaction. Please try again.');
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

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  // Filter transactions
  const filteredTransactions = transactions.filter(transaction => {
    if (selectedPortfolio !== 'all' && transaction.portfolio_id !== parseInt(selectedPortfolio)) {
      return false;
    }
    if (selectedAction !== 'all' && transaction.action !== selectedAction) {
      return false;
    }
    if (searchSymbol && !transaction.symbol.toLowerCase().includes(searchSymbol.toLowerCase())) {
      return false;
    }
    if (dateRange.start && transaction.date < dateRange.start) {
      return false;
    }
    if (dateRange.end && transaction.date > dateRange.end) {
      return false;
    }
    return true;
  });

  // Show portfolio required message for new users
  if (isNewUser) {
    return (
      <div className="page">
        <div className="page-header">
          <div className="header-content">
            <h1>Transactions</h1>
            <p className="page-subtitle">View and manage your trading history</p>
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
          <p>You need to create a portfolio before you can import or add transactions.</p>
          
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
            <h4>What you can do with transactions:</h4>
            <ul>
              <li>Import trading history from CSV or Excel files</li>
              <li>Manually add individual buy/sell transactions</li>
              <li>Track performance across multiple portfolios</li>
              <li>Export transaction data for tax reporting</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  if (error && transactions.length === 0) {
    return (
      <div className="page">
        <div className="page-header">
          <h1>Transactions</h1>
        </div>
        <div className="error-state">
          <div className="error-card glass">
            <h3>Unable to load transactions</h3>
            <p>{error}</p>
            <button onClick={fetchTransactions} className="btn btn-primary">
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Get current portfolio information if we're in portfolio context
  const currentPortfolio = portfolioId ? portfolios.find(p => p.id === parseInt(portfolioId)) : null;

  return (
    <div className="page">
      {/* Portfolio Context Header - only show when in portfolio context */}
      {portfolioId && currentPortfolio && (
        <div className="portfolio-context-header">
          <div className="breadcrumb">
            <Link to="/" className="breadcrumb-link">Main Menu</Link>
            <span className="breadcrumb-separator">›</span>
            <Link to={`/portfolio/${portfolioId}/dashboard`} className="breadcrumb-link">Portfolio</Link>
            <span className="breadcrumb-separator">›</span>
            <span className="breadcrumb-current">{currentPortfolio.name}</span>
          </div>
          <div className="portfolio-meta">
            <span className="portfolio-currency">{currentPortfolio.currency}</span>
            <span className="portfolio-created">Since {formatDate(currentPortfolio.created_at)}</span>
          </div>
        </div>
      )}

      <div className="page-header">
        <div className="header-content">
          <div>
            <h1>Transactions</h1>
            <p className="page-subtitle">View and manage your trading history</p>
          </div>
          <div className="header-actions">
            <button 
              onClick={() => setShowAddModal(true)}
              className="btn btn-primary"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="16"/>
                <line x1="8" y1="12" x2="16" y2="12"/>
              </svg>
              Add Transaction
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-section glass">
        <div className="filters-grid">
          
          <div className="filter-group">
            <label className="filter-label">Action</label>
            <select 
              value={selectedAction}
              onChange={(e) => setSelectedAction(e.target.value)}
              className="filter-select"
            >
              <option value="all">All Actions</option>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </div>
          
          <div className="filter-group">
            <label className="filter-label">Symbol</label>
            <input
              type="text"
              value={searchSymbol}
              onChange={(e) => setSearchSymbol(e.target.value)}
              placeholder="Search symbol..."
              className="filter-input"
            />
          </div>
          
          <div className="filter-group">
            <label className="filter-label">From Date</label>
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
              className="filter-input"
            />
          </div>
          
          <div className="filter-group">
            <label className="filter-label">To Date</label>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
              className="filter-input"
            />
          </div>
          
          <div className="filter-group">
            <button 
              onClick={() => {
                setSelectedAction('all');
                setSearchSymbol('');
                setDateRange({ start: '', end: '' });
              }}
              className="btn btn-outline btn-sm"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="transactions-section">
        <div className="section-header">
          <h3>Transaction History</h3>
          <span className="transaction-count">
            {filteredTransactions.length} of {transactions.length} transactions
          </span>
        </div>
        
        <div className="transactions-table-container glass">
          {loading ? (
            <div className="loading-shimmer" style={{ height: '400px' }}></div>
          ) : filteredTransactions.length === 0 ? (
            <div className="empty-state">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                <path d="M7 7h10v10"/>
                <path d="M7 17 17 7"/>
              </svg>
              <h4>No transactions found</h4>
              <p>
                {transactions.length === 0 
                  ? 'Start by adding your first transaction or importing from a file'
                  : 'Try adjusting your filters to see more transactions'
                }
              </p>
              {transactions.length === 0 && (
                <div className="empty-actions">
                  <button onClick={() => setShowAddModal(true)} className="btn btn-primary">
                    Add Transaction
                  </button>
                  <Link to="/dashboard" className="btn btn-outline">
                    Go to Dashboard
                  </Link>
                </div>
              )}
            </div>
          ) : (
            <div className="transactions-table">
              <div className="table-header">
                <div className="header-cell date">Date</div>
                <div className="header-cell symbol">Symbol</div>
                <div className="header-cell action">Action</div>
                <div className="header-cell quantity">Quantity</div>
                <div className="header-cell price">Price</div>
                <div className="header-cell total">Total</div>
                <div className="header-cell currency">Currency</div>
                <div className="header-cell actions">Actions</div>
              </div>
              
              <div className="table-body">
                {filteredTransactions.map((transaction) => (
                  <div key={transaction.id} className="table-row">
                    <div className="table-cell date" data-label="Date">
                      {formatDate(transaction.date)}
                    </div>
                    
                    <div className="table-cell symbol" data-label="Symbol">
                      <div className="symbol-info">
                        <div className="symbol-icon">
                          {transaction.symbol.substring(0, 2)}
                        </div>
                        <span className="symbol-text">{transaction.symbol}</span>
                      </div>
                    </div>
                    
                    <div className="table-cell action" data-label="Action">
                      <span className={`action-badge ${transaction.action}`}>
                        {transaction.action.toUpperCase()}
                      </span>
                    </div>
                    
                    <div className="table-cell quantity" data-label="Quantity">
                      {transaction.quantity.toLocaleString()}
                    </div>
                    
                    <div className="table-cell price" data-label="Price">
                      {formatCurrency(transaction.price)}
                    </div>
                    
                    <div className="table-cell total" data-label="Total">
                      {formatCurrency(transaction.total_amount)}
                    </div>
                    
                    <div className="table-cell currency" data-label="Currency">
                      {transaction.currency}
                    </div>
                    
                    <div className="table-cell actions" data-label="Actions">
                      <button className="btn-icon" title="Edit transaction">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                      </button>
                      <button className="btn-icon" title="Delete transaction">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3,6 5,6 21,6"/>
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>


      {/* Add Transaction Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal glass" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add Transaction</h3>
              <button 
                onClick={() => setShowAddModal(false)}
                className="btn-icon"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            
            <div className="modal-body">
              <div className="form-grid">
                {/* Portfolio automatically determined from context */}
                {portfolioId && currentPortfolio && (
                  <div className="form-group">
                    <label className="form-label">Portfolio</label>
                    <div className="portfolio-context-display">
                      <span className="portfolio-name">{currentPortfolio.name}</span>
                      <span className="portfolio-currency">({currentPortfolio.currency})</span>
                    </div>
                  </div>
                )}
                
                {!portfolioId && portfolios.length > 1 && (
                  <div className="form-group">
                    <label className="form-label">Portfolio *</label>
                    <select
                      value={newTransaction.portfolio_id}
                      onChange={(e) => setNewTransaction({ ...newTransaction, portfolio_id: e.target.value })}
                      className="form-input"
                    >
                      <option value="">Select Portfolio</option>
                      {portfolios.map(portfolio => (
                        <option key={portfolio.id} value={portfolio.id.toString()}>
                          {portfolio.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                
                <div className="form-group">
                  <label className="form-label">Symbol *</label>
                  <input
                    type="text"
                    value={newTransaction.symbol}
                    onChange={(e) => setNewTransaction({ ...newTransaction, symbol: e.target.value.toUpperCase() })}
                    placeholder="e.g., AAPL"
                    className="form-input"
                  />
                </div>
                
                <div className="form-group">
                  <label className="form-label">Action *</label>
                  <select
                    value={newTransaction.action}
                    onChange={(e) => setNewTransaction({ ...newTransaction, action: e.target.value as 'buy' | 'sell' })}
                    className="form-input"
                  >
                    <option value="buy">Buy</option>
                    <option value="sell">Sell</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label className="form-label">Quantity *</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={newTransaction.quantity}
                    onChange={(e) => setNewTransaction({ ...newTransaction, quantity: e.target.value })}
                    placeholder="0"
                    className="form-input"
                  />
                </div>
                
                <div className="form-group">
                  <label className="form-label">Price *</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={newTransaction.price}
                    onChange={(e) => setNewTransaction({ ...newTransaction, price: e.target.value })}
                    placeholder="0.00"
                    className="form-input"
                  />
                </div>
                
                <div className="form-group">
                  <label className="form-label">Fees</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={newTransaction.fees}
                    onChange={(e) => setNewTransaction({ ...newTransaction, fees: e.target.value })}
                    placeholder="0.00"
                    className="form-input"
                  />
                </div>
                
                <div className="form-group">
                  <label className="form-label">Date *</label>
                  <input
                    type="date"
                    value={newTransaction.date}
                    onChange={(e) => setNewTransaction({ ...newTransaction, date: e.target.value })}
                    className="form-input"
                  />
                </div>
                
                <div className="form-group full-width">
                  <label className="form-label">Notes</label>
                  <textarea
                    rows={2}
                    value={newTransaction.notes}
                    onChange={(e) => setNewTransaction({ ...newTransaction, notes: e.target.value })}
                    placeholder="Optional notes about this transaction"
                    className="form-input"
                  />
                </div>
              </div>
            </div>
            
            <div className="modal-footer">
              <button 
                onClick={() => setShowAddModal(false)}
                className="btn btn-outline"
              >
                Cancel
              </button>
              <button 
                onClick={handleAddTransaction}
                className="btn btn-primary"
                disabled={!newTransaction.portfolio_id || !newTransaction.symbol || !newTransaction.quantity || !newTransaction.price}
              >
                Add Transaction
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};