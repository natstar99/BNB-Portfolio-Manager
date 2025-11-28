import React, { useState, useEffect } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { usePortfolios } from '../hooks/usePortfolios';
import { formatCurrency, formatDateWithYear } from '../shared/formatters';
import { Transaction } from '../shared/types';

export const Transactions: React.FC = () => {
  const { portfolios, hasPortfolios, isNewUser } = usePortfolios();
  const location = useLocation();
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
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

  // Handle URL parameters
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const symbolParam = searchParams.get('symbol');
    if (symbolParam) {
      setSearchSymbol(symbolParam);
    }
  }, [location.search]);

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

  // Filter transactions
  const filteredTransactions = transactions.filter(transaction => {
    if (selectedAction !== 'all' && transaction.action !== selectedAction) {
      return false;
    }
    if (searchSymbol && transaction.symbol && !transaction.symbol.toLowerCase().includes(searchSymbol.toLowerCase())) {
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

  if (isNewUser) {
    return (
      <div className="page">
        <h1>Transactions</h1>
        <p>You need to create a portfolio before you can add transactions.</p>
        <Link to="/">Create Portfolio</Link>
      </div>
    );
  }

  if (error && transactions.length === 0) {
    return (
      <div className="page">
        <h1>Transactions</h1>
        <p>{error}</p>
        <button onClick={fetchTransactions}>Try Again</button>
      </div>
    );
  }

  const currentPortfolio = portfolioId ? portfolios.find(p => p.id === parseInt(portfolioId)) : null;

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Transactions</h1>
        <button onClick={() => setShowAddModal(true)}>Add Transaction</button>
      </div>

      {/* Filters */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        <div>
          <label>Action</label>
          <select value={selectedAction} onChange={(e) => setSelectedAction(e.target.value)}>
            <option value="all">All Actions</option>
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
          </select>
        </div>

        <div>
          <label>Symbol</label>
          <input
            type="text"
            value={searchSymbol}
            onChange={(e) => setSearchSymbol(e.target.value)}
            placeholder="Search symbol..."
          />
        </div>

        <div>
          <label>From Date</label>
          <input
            type="date"
            value={dateRange.start}
            onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
          />
        </div>

        <div>
          <label>To Date</label>
          <input
            type="date"
            value={dateRange.end}
            onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
          />
        </div>
      </div>

      <button
        onClick={() => {
          setSelectedAction('all');
          setSearchSymbol('');
          setDateRange({ start: '', end: '' });
        }}
        style={{ marginBottom: '2rem' }}
      >
        Clear Filters
      </button>

      {/* Transactions Table */}
      <h2>Transaction History</h2>
      <p>{filteredTransactions.length} of {transactions.length} transactions</p>

      {loading ? (
        <p>Loading...</p>
      ) : filteredTransactions.length === 0 ? (
        <p>{transactions.length === 0 ? 'No transactions yet. Add your first transaction.' : 'No transactions match your filters.'}</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Symbol</th>
              <th>Action</th>
              <th>Quantity</th>
              <th>Price</th>
              <th>Total</th>
              <th>Currency</th>
            </tr>
          </thead>
          <tbody>
            {filteredTransactions.map((transaction) => (
              <tr key={transaction.id}>
                <td>{formatDateWithYear(transaction.date)}</td>
                <td>
                  <strong>{transaction.symbol || 'Unknown'}</strong>
                </td>
                <td>
                  <span className={transaction.action === 'buy' ? 'positive' : 'negative'}>
                    {transaction.action?.toUpperCase() || 'UNKNOWN'}
                  </span>
                </td>
                <td>{transaction.quantity.toLocaleString()}</td>
                <td>{formatCurrency(transaction.price)}</td>
                <td>{formatCurrency(transaction.total_amount || 0)}</td>
                <td>{transaction.currency}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Add Transaction Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Add Transaction</h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
              {!portfolioId && portfolios.length > 1 && (
                <div>
                  <label>Portfolio *</label>
                  <select
                    value={newTransaction.portfolio_id}
                    onChange={(e) => setNewTransaction({ ...newTransaction, portfolio_id: e.target.value })}
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

              {portfolioId && currentPortfolio && (
                <div>
                  <label>Portfolio</label>
                  <p>{currentPortfolio.name} ({currentPortfolio.currency})</p>
                </div>
              )}

              <div>
                <label>Symbol *</label>
                <input
                  type="text"
                  value={newTransaction.symbol}
                  onChange={(e) => setNewTransaction({ ...newTransaction, symbol: e.target.value.toUpperCase() })}
                  placeholder="e.g., AAPL"
                />
              </div>

              <div>
                <label>Action *</label>
                <select
                  value={newTransaction.action}
                  onChange={(e) => setNewTransaction({ ...newTransaction, action: e.target.value as 'buy' | 'sell' })}
                >
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                </select>
              </div>

              <div>
                <label>Quantity *</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={newTransaction.quantity}
                  onChange={(e) => setNewTransaction({ ...newTransaction, quantity: e.target.value })}
                  placeholder="0"
                />
              </div>

              <div>
                <label>Price *</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={newTransaction.price}
                  onChange={(e) => setNewTransaction({ ...newTransaction, price: e.target.value })}
                  placeholder="0.00"
                />
              </div>

              <div>
                <label>Fees</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={newTransaction.fees}
                  onChange={(e) => setNewTransaction({ ...newTransaction, fees: e.target.value })}
                  placeholder="0.00"
                />
              </div>

              <div>
                <label>Date *</label>
                <input
                  type="date"
                  value={newTransaction.date}
                  onChange={(e) => setNewTransaction({ ...newTransaction, date: e.target.value })}
                />
              </div>

              <div style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <textarea
                  rows={2}
                  value={newTransaction.notes}
                  onChange={(e) => setNewTransaction({ ...newTransaction, notes: e.target.value })}
                  placeholder="Optional notes"
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', justifyContent: 'flex-end' }}>
              <button onClick={() => setShowAddModal(false)}>Cancel</button>
              <button
                onClick={handleAddTransaction}
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
