import React, { useState } from 'react';

interface ImportSummaryProps {
  file: File | null;
  columnMapping: { [key: string]: string };
  dateFormat: string;
  validationResults: any;
  portfolioId: number;
  onImport: (importResults: any) => void;
  onComplete: () => void;
}

export const ImportSummary: React.FC<ImportSummaryProps> = ({
  file,
  columnMapping,
  dateFormat,
  validationResults,
  portfolioId,
  onImport,
  onComplete,
}) => {
  const [importing, setImporting] = useState(false);
  const [importResults, setImportResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleImport = async () => {
    if (!file) return;

    setImporting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('portfolio_id', portfolioId.toString());
      formData.append('column_mapping', JSON.stringify(columnMapping));
      formData.append('date_format', dateFormat);

      const response = await fetch('/api/import/transactions', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      
      if (data.success) {
        setImportResults(data);
        onImport(data);
      } else {
        throw new Error(data.error || 'Import failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  if (importing) {
    return (
      <div className="import-summary-section">
        <div className="import-loading">
          <div className="loading-animation">
            <div className="loading-spinner">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12a9 9 0 11-6.219-8.56"/>
              </svg>
            </div>
            <div className="loading-steps">
              <div className="step active">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14,2 14,8 20,8"/>
                </svg>
                <span>Processing file...</span>
              </div>
              <div className="step">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
                </svg>
                <span>Creating stocks...</span>
              </div>
              <div className="step">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 11H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h4l5 4V7l-5 4z"/>
                  <path d="M22 9s-1-2-3-2-3 2-3 2"/>
                </svg>
                <span>Importing transactions...</span>
              </div>
              <div className="step">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                  <line x1="8" y1="21" x2="16" y2="21"/>
                  <line x1="12" y1="17" x2="12" y2="21"/>
                </svg>
                <span>Updating positions...</span>
              </div>
            </div>
          </div>
          <h3>Importing Transactions...</h3>
          <p>Please wait while we process your transaction data</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="import-summary-section">
        <div className="import-error">
          <div className="error-card">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <div className="error-content">
              <h3>Import Failed</h3>
              <p>{error}</p>
              <div className="error-actions">
                <button onClick={handleImport} className="btn btn-primary">
                  Try Again
                </button>
                <button onClick={() => setError(null)} className="btn btn-outline">
                  Back to Summary
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (importResults) {
    return (
      <div className="import-summary-section">
        <div className="import-success">
          <div className="success-header">
            <div className="success-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22,4 12,14.01 9,11.01"/>
              </svg>
            </div>
            <h2>Import Completed Successfully!</h2>
            <p>Your transactions have been imported and are ready for use.</p>
          </div>

          <div className="import-results">
            <div className="results-grid">
              <div className="result-card">
                <div className="result-value">{importResults.summary?.successful_imports || 0}</div>
                <div className="result-label">Transactions Imported</div>
              </div>
              <div className="result-card">
                <div className="result-value">{importResults.summary?.stocks_created || 0}</div>
                <div className="result-label">New Stocks Created</div>
              </div>
              <div className="result-card">
                <div className="result-value">{importResults.summary?.validation_errors || 0}</div>
                <div className="result-label">Validation Errors</div>
              </div>
              <div className="result-card">
                <div className="result-value">{importResults.summary?.import_errors || 0}</div>
                <div className="result-label">Import Errors</div>
              </div>
            </div>
          </div>

          {importResults.details?.import_errors && importResults.details.import_errors.length > 0 && (
            <div className="import-errors-detail">
              <h3>Import Issues:</h3>
              <div className="errors-list">
                {importResults.details.import_errors.slice(0, 5).map((error: string, index: number) => (
                  <div key={index} className="error-item">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10"/>
                      <line x1="15" y1="9" x2="9" y2="15"/>
                      <line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                    <span>{error}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="next-steps">
            <h3>What's Next?</h3>
            <div className="steps-grid">
              <div className="next-step">
                <div className="step-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
                  </svg>
                </div>
                <div className="step-content">
                  <h4>Verify Stock Information</h4>
                  <p>Review and verify any unrecognized stock symbols in the Stock Management section.</p>
                </div>
              </div>
              <div className="next-step">
                <div className="step-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 3v18h18"/>
                    <path d="M7 16l4-4 4 4 6-6"/>
                  </svg>
                </div>
                <div className="step-content">
                  <h4>Review Portfolio Analytics</h4>
                  <p>Check your updated portfolio performance and analytics dashboard.</p>
                </div>
              </div>
              <div className="next-step">
                <div className="step-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14,2 14,8 20,8"/>
                  </svg>
                </div>
                <div className="step-content">
                  <h4>Review Transaction History</h4>
                  <p>View and manage your imported transactions in the Transactions section.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="completion-actions">
            <button onClick={onComplete} className="btn btn-primary btn-lg">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9,22 9,12 15,12 15,22"/>
              </svg>
              Go to Portfolio Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Pre-import summary
  return (
    <div className="import-summary-section">
      <div className="import-ready">
        <div className="ready-header">
          <div className="ready-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 11H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h4l5 4V7l-5 4z"/>
              <path d="M22 9s-1-2-3-2-3 2-3 2"/>
            </svg>
          </div>
          <h2>Ready to Import</h2>
          <p>Review the summary below and click "Start Import" to begin the import process.</p>
        </div>

        <div className="import-summary-card glass">
          <h3>Import Summary</h3>
          <div className="summary-details">
            <div className="detail-row">
              <span className="detail-label">File:</span>
              <span className="detail-value">{file?.name}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Total Rows:</span>
              <span className="detail-value">{validationResults.total_rows}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Valid Transactions:</span>
              <span className="detail-value success">{validationResults.valid_rows}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Unique Stocks:</span>
              <span className="detail-value">{validationResults.unique_instruments}</span>
            </div>
            {validationResults.validation_errors > 0 && (
              <div className="detail-row">
                <span className="detail-label">Validation Errors:</span>
                <span className="detail-value error">{validationResults.validation_errors}</span>
              </div>
            )}
          </div>
        </div>

        <div className="import-warning glass">
          <div className="warning-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </div>
          <div className="warning-content">
            <h4>Before You Import</h4>
            <ul>
              <li>Make sure you have reviewed all validation results</li>
              <li>Unverified stocks will be created with "pending" status</li>
              <li>You can verify stock information later in Stock Management</li>
              <li>This import cannot be undone - consider backing up your data</li>
            </ul>
          </div>
        </div>

        <div className="import-actions">
          <button onClick={handleImport} className="btn btn-primary btn-lg">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17,8 12,3 7,8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Start Import ({validationResults.valid_rows} transactions)
          </button>
        </div>
      </div>
    </div>
  );
};