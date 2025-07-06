import React, { useState, useEffect } from 'react';

interface DataPreviewProps {
  file: File;
  columnMapping: { [key: string]: string };
  dateFormat: string;
  portfolioId: number;
  onValidation: (validationResults: any) => void;
  onConfirm: () => void;
}

interface ValidationError {
  row: number;
  field: string;
  value: string;
  error: string;
}

interface StockVerification {
  symbol: string;
  exists: boolean;
  name?: string;
  current_price?: number;
  verification_error?: string;
}

export const DataPreview: React.FC<DataPreviewProps> = ({
  file,
  columnMapping,
  dateFormat,
  portfolioId,
  onValidation,
  onConfirm,
}) => {
  const [validating, setValidating] = useState(false);
  const [validationResults, setValidationResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [confirming, setConfirming] = useState(false);


  useEffect(() => {
    validateData();
  }, [dateFormat]);

  const validateData = async () => {
    setValidating(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('column_mapping', JSON.stringify(columnMapping));
      formData.append('date_format', dateFormat);
      formData.append('portfolio_id', portfolioId.toString());

      // Step 3a: Confirm transactions (validation only, no database changes)
      const response = await fetch('/api/import/confirm-transactions', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Validation failed');
      }

      const data = await response.json();
      
      if (data.success) {
        setValidationResults(data.data);
        onValidation(data.data);
      } else {
        throw new Error(data.error || 'Validation failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validation failed');
    } finally {
      setValidating(false);
    }
  };

  const confirmTransactions = async () => {
    setConfirming(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('column_mapping', JSON.stringify(columnMapping));
      formData.append('date_format', dateFormat);
      formData.append('portfolio_id', portfolioId.toString());

      // Step 3b: Stage transactions (save to STG_RAW_TRANSACTIONS)
      const response = await fetch('/api/import/stage-transactions', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to stage transactions');
      }

      const data = await response.json();
      
      if (data.success) {
        // Update validation results with staging confirmation data
        setValidationResults((prev: any) => ({
          ...prev,
          ...data.data,
          confirmed: true,
          staged: true
        }));
        
        // Call the onConfirm callback to proceed to next step
        onConfirm();
      } else {
        throw new Error(data.error || 'Failed to stage transactions');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stage transactions');
    } finally {
      setConfirming(false);
    }
  };

  const getValidationStatusIcon = (hasErrors: boolean) => {
    if (hasErrors) {
      return (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-error">
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
      );
    } else {
      return (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-success">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22,4 12,14.01 9,11.01"/>
        </svg>
      );
    }
  };

  const getStockStatusIcon = (verification: StockVerification) => {
    if (verification.exists) {
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-success">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22,4 12,14.01 9,11.01"/>
        </svg>
      );
    } else {
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-warning">
          <circle cx="12" cy="12" r="10"/>
          <path d="m9 12 2 2 4-4"/>
        </svg>
      );
    }
  };

  if (validating) {
    return (
      <div className="data-preview-section">
        <div className="validation-loading">
          <div className="loading-spinner">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12a9 9 0 11-6.219-8.56"/>
            </svg>
          </div>
          <h3>Confirming Data...</h3>
          <p>Checking data format and detecting duplicates</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="data-preview-section">
        <div className="validation-error">
          <div className="error-card">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <div className="error-content">
              <h3>Confirmation Error</h3>
              <p>{error}</p>
              <button onClick={validateData} className="btn btn-primary">
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!validationResults) return null;

  return (
    <div className="data-preview-section">
      {/* Column Mapping Summary */}
      <div className="column-mapping-summary glass">
        <div className="section-header">
          <h3>Column Mapping Applied</h3>
        </div>
        <div className="mapping-grid horizontal">
          {Object.entries(columnMapping).map(([field, column]) => (
            <div key={field} className="mapping-item">
              <span className="field-name">{field}</span>
              <span className="arrow">→</span>
              <span className="column-name">{column}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Transaction Confirmation Summary */}
      <div className="confirmation-summary glass">
        <div className="summary-header">
          <h3>Confirm Transaction Import - {validationResults.filename}</h3>
          {getValidationStatusIcon(validationResults.validation_errors?.length > 0)}
        </div>
        
        <div className="summary-stats">
          <div className="stat-card">
            <div className="stat-label">Total Rows</div>
            <div className="stat-value">{validationResults.total_rows}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">New Stocks</div>
            <div className="stat-value">{validationResults.new_stocks || 0}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">New Transactions</div>
            <div className="stat-value">{validationResults.new_transactions || validationResults.valid_rows}</div>
          </div>
        </div>


      </div>

      {/* Transaction Breakdown - View Details */}
      {validationResults.transaction_breakdown && Object.keys(validationResults.transaction_breakdown).length > 0 && (
        <div className="transaction-breakdown glass">
          <div className="breakdown-section">
            <div className="breakdown-header">
              <h3>View Details</h3>
              <button 
                onClick={() => setShowBreakdown(!showBreakdown)}
                className={`btn ${showBreakdown ? 'btn-secondary' : 'btn-primary'}`}
              >
                {showBreakdown ? 'Hide' : 'Show'} Transaction Breakdown
              </button>
            </div>
            
            {showBreakdown && (
              <div className="breakdown-table-container">
                <div className="breakdown-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Stock</th>
                        <th>Total Transactions</th>
                        <th>BUY</th>
                        <th>SELL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(validationResults.transaction_breakdown).map(([stock, breakdown]: [string, any]) => (
                        <tr key={stock}>
                          <td className="stock-code">{stock}</td>
                          <td className="total-transactions">{breakdown.total}</td>
                          <td className="buy-count">{breakdown.BUY || 0}</td>
                          <td className="sell-count">{breakdown.SELL || 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Validation Errors */}
      {validationResults.validation_errors && validationResults.validation_errors.length > 0 && (
        <div className="validation-errors glass">
          <div className="section-header">
            <h3>Data Issues</h3>
            <p>The following rows have validation errors that need to be fixed:</p>
          </div>
          <div className="errors-list">
            {validationResults.validation_errors.slice(0, 10).map((error: string, index: number) => (
              <div key={index} className="error-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="15" y1="9" x2="9" y2="15"/>
                  <line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
                <span>{error}</span>
              </div>
            ))}
            {validationResults.validation_errors.length > 10 && (
              <div className="more-errors">
                <span>And {validationResults.validation_errors.length - 10} more errors...</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stock Verification Results */}
      {validationResults.verification_results && Object.keys(validationResults.verification_results).length > 0 && (
        <div className="stock-verification glass">
          <div className="section-header">
            <h3>Stock Verification</h3>
            <p>Verification results for stocks found in your data:</p>
          </div>
          <div className="stocks-list">
            {Object.entries(validationResults.verification_results).map(([symbol, verification]: [string, any]) => (
              <div key={symbol} className="stock-item">
                <div className="stock-info">
                  {getStockStatusIcon(verification)}
                  <div className="stock-details">
                    <span className="stock-symbol">{symbol}</span>
                    <span className="stock-name">
                      {verification.exists ? verification.name || 'Verified' : 'Not found on Yahoo Finance'}
                    </span>
                  </div>
                </div>
                <div className="stock-status">
                  {verification.exists ? (
                    <span className="status verified">Verified</span>
                  ) : (
                    <span className="status unverified">Needs Verification</span>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          <div className="verification-note">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 16v-4"/>
              <path d="M12 8h.01"/>
            </svg>
            <p>
              Unverified stocks will be created with "pending" status. You can verify them later in the Stock Management section.
            </p>
          </div>
        </div>
      )}


      {/* Confirmation Actions */}
      <div className="confirmation-actions">
        {validationResults.validation_errors?.length > 0 ? (
          <div className="error-state">
            <p className="action-message error">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
              Please fix the validation errors before proceeding.
            </p>
            <div className="action-buttons">
              <button className="btn btn-error" onClick={() => window.history.back()}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15,18 9,12 15,6"/>
                </svg>
                Return to Previous Step
              </button>
            </div>
          </div>
        ) : (
          <div className="success-state">
            <p className="action-message">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22,4 12,14.01 9,11.01"/>
              </svg>
              Ready to stage {validationResults.valid_rows} valid transaction{validationResults.valid_rows !== 1 ? 's' : ''} for stock verification.
            </p>
            <div className="action-buttons">
              <button className="btn btn-error" onClick={() => window.history.back()}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15,18 9,12 15,6"/>
                </svg>
                Return to Previous Step
              </button>
              <button 
                className="btn btn-primary btn-large" 
                onClick={confirmTransactions}
                disabled={confirming}
              >
                {confirming ? (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin">
                      <path d="M21 12a9 9 0 11-6.219-8.56"/>
                    </svg>
                    Staging...
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="9,18 15,12 9,6"/>
                    </svg>
                    Stage Transactions
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};