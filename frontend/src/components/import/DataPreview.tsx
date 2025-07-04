import React, { useState, useEffect } from 'react';

interface DataPreviewProps {
  file: File;
  columnMapping: { [key: string]: string };
  dateFormat: string;
  portfolioId: number;
  onValidation: (validationResults: any) => void;
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
}) => {
  const [validating, setValidating] = useState(false);
  const [validationResults, setValidationResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const dateFormats = [
    { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (2023-12-31)' },
    { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (12/31/2023)' },
    { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (31/12/2023)' },
    { value: 'DD-MM-YYYY', label: 'DD-MM-YYYY (31-12-2023)' },
    { value: 'MM-DD-YYYY', label: 'MM-DD-YYYY (12-31-2023)' },
    { value: 'YYYYMMDD', label: 'YYYYMMDD (20231231)' },
    { value: 'DD-MMM-YYYY', label: 'DD-MMM-YYYY (31-Dec-2023)' },
    { value: 'MMM DD, YYYY', label: 'MMM DD, YYYY (Dec 31, 2023)' },
  ];

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

      const response = await fetch('/api/import/validate', {
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
          <h3>Validating Data...</h3>
          <p>Checking data format and verifying stock symbols</p>
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
              <h3>Validation Error</h3>
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
      {/* Date Format Display */}
      <div className="date-format-section glass">
        <div className="section-header">
          <h3>Date Format Configuration</h3>
          <p>Using date format: <strong>{dateFormats.find(f => f.value === dateFormat)?.label || dateFormat}</strong></p>
        </div>
      </div>

      {/* Validation Summary */}
      <div className="validation-summary glass">
        <div className="summary-header">
          <h3>Transaction Summary</h3>
          {getValidationStatusIcon(validationResults.validation_errors?.length > 0)}
        </div>
        
        <div className="summary-stats">
          <div className="stat-card">
            <div className="stat-value">{validationResults.total_rows}</div>
            <div className="stat-label">Total Rows</div>
          </div>
          <div className="stat-card success">
            <div className="stat-value">{validationResults.valid_rows}</div>
            <div className="stat-label">Valid Rows</div>
          </div>
          <div className="stat-card error">
            <div className="stat-value">{validationResults.validation_errors?.length || 0}</div>
            <div className="stat-label">Errors</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{validationResults.unique_instruments}</div>
            <div className="stat-label">Unique Stocks</div>
          </div>
        </div>
      </div>

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

      {/* Column Mapping Summary */}
      <div className="mapping-summary glass">
        <h3>Column Mapping Used</h3>
        <div className="mapping-grid">
          {Object.entries(validationResults.column_mapping).map(([field, column]) => (
            <div key={field} className="mapping-item">
              <span className="field-name">{field}</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9,18 15,12 9,6"/>
              </svg>
              <span className="column-name">{String(column)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="preview-actions">
        {validationResults.valid_rows > 0 ? (
          <div className="success-actions">
            <p className="action-message">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22,4 12,14.01 9,11.01"/>
              </svg>
              Ready to import {validationResults.valid_rows} valid transaction{validationResults.valid_rows !== 1 ? 's' : ''}
            </p>
            <button 
              onClick={() => onValidation(validationResults)}
              className="btn btn-primary"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9,18 15,12 9,6"/>
              </svg>
              Proceed to Import
            </button>
          </div>
        ) : (
          <div className="error-actions">
            <p className="action-message error">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
              No valid transactions found. Please fix the errors and try again.
            </p>
            <button onClick={validateData} className="btn btn-outline">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="1,4 1,10 7,10"/>
                <path d="M3.51,15a9,9 0 1,0 2.13-9.36L1,10"/>
              </svg>
              Retry Validation
            </button>
          </div>
        )}
      </div>
    </div>
  );
};