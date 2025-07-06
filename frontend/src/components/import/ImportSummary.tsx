import React, { useState, useEffect } from 'react';

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
  const [currentStep, setCurrentStep] = useState(0);
  const [stepProgress, setStepProgress] = useState({
    processing: false,
    creating: false,
    importing: false,
    updating: false
  });
  
  // State to prevent multiple simultaneous imports
  const [hasStartedImport, setHasStartedImport] = useState(false);
  
  // Auto-start import when component mounts (Step 5 auto-start)
  useEffect(() => {
    if (!importing && !importResults && !error && !hasStartedImport) {
      setHasStartedImport(true);
      handleImport();
    }
  }, []);

  const simulateProgressSteps = () => {
    // Step 1: Processing file
    setCurrentStep(0);
    setStepProgress(prev => ({ ...prev, processing: true }));
    
    setTimeout(() => {
      // Step 2: Creating stocks
      setCurrentStep(1);
      setStepProgress(prev => ({ ...prev, creating: true }));
      
      setTimeout(() => {
        // Step 3: Importing transactions
        setCurrentStep(2);
        setStepProgress(prev => ({ ...prev, importing: true }));
        
        setTimeout(() => {
          // Step 4: Updating positions
          setCurrentStep(3);
          setStepProgress(prev => ({ ...prev, updating: true }));
        }, 1500);
      }, 1500);
    }, 1000);
  };

  const handleImport = async () => {
    if (!file || importing) return; // Prevent duplicate calls

    setImporting(true);
    setError(null);
    
    // Start progress simulation
    simulateProgressSteps();

    try {
      // No file upload needed - process staged transactions
      const response = await fetch('/api/import/transactions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          portfolio_id: portfolioId
        }),
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
              <div className={`step ${currentStep >= 0 ? 'active' : ''} ${stepProgress.processing ? 'completed' : ''}`}>
                <div className="step-icon">
                  {stepProgress.processing ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="20,6 9,17 4,12"/>
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14,2 14,8 20,8"/>
                    </svg>
                  )}
                </div>
                <span>Processing file...</span>
              </div>
              <div className={`step ${currentStep >= 1 ? 'active' : ''} ${stepProgress.creating ? 'completed' : ''}`}>
                <div className="step-icon">
                  {stepProgress.creating ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="20,6 9,17 4,12"/>
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
                    </svg>
                  )}
                </div>
                <span>Creating stocks...</span>
              </div>
              <div className={`step ${currentStep >= 2 ? 'active' : ''} ${stepProgress.importing ? 'completed' : ''}`}>
                <div className="step-icon">
                  {stepProgress.importing ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="20,6 9,17 4,12"/>
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9 11H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h4l5 4V7l-5 4z"/>
                      <path d="M22 9s-1-2-3-2-3 2-3 2"/>
                    </svg>
                  )}
                </div>
                <span>Importing transactions...</span>
              </div>
              <div className={`step ${currentStep >= 3 ? 'active' : ''} ${stepProgress.updating ? 'completed' : ''}`}>
                <div className="step-icon">
                  {stepProgress.updating ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="20,6 9,17 4,12"/>
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                      <line x1="8" y1="21" x2="16" y2="21"/>
                      <line x1="12" y1="17" x2="12" y2="21"/>
                    </svg>
                  )}
                </div>
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
                <div className="result-value">{importResults.summary?.verified_transactions_found || 0}</div>
                <div className="result-label">Verified Transactions Found</div>
              </div>
              <div className="result-card">
                <div className="result-value">{importResults.summary?.transactions_imported || 0}</div>
                <div className="result-label">Transactions Imported Successfully</div>
              </div>
              <div className="result-card">
                <div className="result-value">{importResults.summary?.actual_import_errors || 0}</div>
                <div className="result-label">Import Errors</div>
              </div>
              <div className="result-card success-rate">
                <div className="result-value">
                  {importResults.summary?.verified_transactions_found > 0 
                    ? Math.round((importResults.summary.transactions_imported / importResults.summary.verified_transactions_found) * 100)
                    : 0}%
                </div>
                <div className="result-label">Success Rate</div>
              </div>
            </div>
          </div>

          <div className="import-log-detail">
            <h3>Import Log:</h3>
            <div className="log-summary">
              <div className="log-item success">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20,6 9,17 4,12"/>
                </svg>
                <span>{importResults.summary?.transactions_imported || 0} transactions imported for {importResults.summary?.stocks_with_transactions || 0} verified stocks</span>
              </div>
              {importResults.summary?.unverified_transactions > 0 && (
                <div className="log-item info">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="m9,12 2,2 4,-4"/>
                  </svg>
                  <span>{importResults.summary.unverified_transactions} transactions remain in staging area with unverified stocks</span>
                </div>
              )}
              {importResults.summary?.actual_import_errors > 0 && (
                <div className="log-item error">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                  </svg>
                  <span>{importResults.summary.actual_import_errors} actual import errors occurred</span>
                </div>
              )}
            </div>
          </div>

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

  // This component now auto-starts the import - no pre-import summary needed
  // If we get here, something went wrong
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
          <h2>Preparing Import...</h2>
          <p>Setting up your transaction import, please wait.</p>
        </div>
      </div>
    </div>
  );
};