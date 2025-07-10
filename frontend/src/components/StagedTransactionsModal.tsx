import React, { useState, useEffect } from 'react';
import '../styles/staged-transactions-modal.css';

interface StagedTransaction {
  id: number;
  portfolio_id: number;
  raw_date: number;
  raw_instrument_code: string;
  raw_transaction_type: string;
  raw_quantity: number;
  raw_price: number;
  raw_import_timestamp: string;
  processed_flag: boolean;
}

interface StagedTransactionsModalProps {
  portfolioId: number;
  isOpen: boolean;
  onClose: () => void;
}

export const StagedTransactionsModal: React.FC<StagedTransactionsModalProps> = ({
  portfolioId,
  isOpen,
  onClose,
}) => {
  const [transactions, setTransactions] = useState<StagedTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchStagedTransactions();
    }
  }, [isOpen, portfolioId]);

  const fetchStagedTransactions = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/portfolios/${portfolioId}/staged-transactions`);
      const data = await response.json();
      
      if (data.success) {
        setTransactions(data.data.transactions);
      } else {
        setError(data.error || 'Failed to fetch staged transactions');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch staged transactions');
    } finally {
      setLoading(false);
    }
  };

  const processTransactions = async () => {
    setProcessing(true);
    setError(null);
    
    try {
      const response = await fetch('/api/import/transactions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          portfolio_id: portfolioId
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Refresh the staged transactions list
        await fetchStagedTransactions();
        // Show success message
        alert(`Successfully processed ${data.summary.transactions_imported} transactions!`);
      } else {
        setError(data.error || 'Failed to process transactions');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process transactions');
    } finally {
      setProcessing(false);
    }
  };

  const formatDate = (rawDate: number) => {
    const dateStr = rawDate.toString();
    if (dateStr.length === 8) {
      return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
    }
    return dateStr;
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="staged-transactions-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Staged Transactions</h3>
          <button onClick={onClose} className="modal-close">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        
        <div className="modal-body">
          {loading && (
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p>Loading staged transactions...</p>
            </div>
          )}

          {error && (
            <div className="error-message">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && (
            <>
              <div className="transactions-header">
                <div className="transaction-count">
                  <span>{transactions.length} unprocessed transactions</span>
                </div>
                {transactions.length > 0 && (
                  <button
                    onClick={processTransactions}
                    disabled={processing}
                    className="btn btn-primary"
                  >
                    {processing ? 'Processing...' : 'Process All Transactions'}
                  </button>
                )}
              </div>

              {transactions.length === 0 ? (
                <div className="no-transactions">
                  <p>No staged transactions found for this portfolio.</p>
                  <p>Import some transaction data to see them here.</p>
                </div>
              ) : (
                <div className="transactions-table-container">
                  <table className="transactions-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Stock</th>
                        <th>Type</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Total Value</th>
                        <th>Import Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((transaction) => (
                        <tr key={transaction.id}>
                          <td>{formatDate(transaction.raw_date)}</td>
                          <td>{transaction.raw_instrument_code}</td>
                          <td>
                            <span className={`transaction-type ${transaction.raw_transaction_type.toLowerCase()}`}>
                              {transaction.raw_transaction_type}
                            </span>
                          </td>
                          <td>{transaction.raw_quantity.toLocaleString()}</td>
                          <td>${transaction.raw_price.toFixed(2)}</td>
                          <td>${(transaction.raw_quantity * transaction.raw_price).toFixed(2)}</td>
                          <td>{formatTimestamp(transaction.raw_import_timestamp)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
        
        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-outline">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};