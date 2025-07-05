import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { FileUpload } from '../components/import/FileUpload';
import { ColumnMapping } from '../components/import/ColumnMapping';
import { DataPreview } from '../components/import/DataPreview';
import { ImportSummary } from '../components/import/ImportSummary';
import { StockVerification } from '../components/import/StockVerification';
import '../styles/transaction-import.css';

export interface ImportData {
  file: File | null;
  filename: string;
  totalRows: number;
  columns: string[];
  sampleData: any[];
  columnMapping: { [key: string]: string };
  dateFormat: string;
  validationResults: any;
  importResults: any;
}

export interface ImportStep {
  key: string;
  title: string;
  description: string;
  completed: boolean;
  current: boolean;
}

const REQUIRED_FIELDS = [
  { key: 'date', label: 'Date', required: true },
  { key: 'instrument_code', label: 'Stock Symbol', required: true },
  { key: 'transaction_type', label: 'Transaction Type', required: true },
  { key: 'quantity', label: 'Quantity', required: true },
  { key: 'price', label: 'Price', required: true },
  { key: 'total_value', label: 'Total Value', required: false },
];

export const TransactionImport: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const navigate = useNavigate();
  
  const [portfolio, setPortfolio] = useState<any>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [importData, setImportData] = useState<ImportData>({
    file: null,
    filename: '',
    totalRows: 0,
    columns: [],
    sampleData: [],
    columnMapping: {},
    dateFormat: 'YYYY-MM-DD',
    validationResults: null,
    importResults: null,
  });

  const steps: ImportStep[] = [
    {
      key: 'upload',
      title: 'Upload File',
      description: 'Select CSV or Excel file containing transactions',
      completed: Boolean(importData.file),
      current: currentStep === 0,
    },
    {
      key: 'mapping',
      title: 'Map Columns',
      description: 'Map your file columns to required fields',
      completed: Object.keys(importData.columnMapping).length > 0,
      current: currentStep === 1,
    },
    {
      key: 'confirm',
      title: 'Confirm Transactions',
      description: 'Review and confirm your transaction data',
      completed: Boolean(importData.validationResults?.confirmed),
      current: currentStep === 2,
    },
    {
      key: 'verify',
      title: 'Verify Stocks',
      description: 'Assign markets and verify new stocks',
      completed: Boolean(importData.validationResults?.stocksVerified),
      current: currentStep === 3,
    },
    {
      key: 'import',
      title: 'Import Transactions',
      description: 'Process verified stocks to portfolio',
      completed: Boolean(importData.importResults?.success),
      current: currentStep === 4,
    },
  ];

  useEffect(() => {
    if (!portfolioId) {
      navigate('/');
      return;
    }
    fetchPortfolio();
  }, [portfolioId, navigate]);

  const fetchPortfolio = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/portfolios/${portfolioId}`);
      if (!response.ok) {
        if (response.status === 404) {
          navigate('/');
          return;
        }
        throw new Error('Failed to fetch portfolio');
      }
      const data = await response.json();
      setPortfolio(data.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (fileData: {
    file: File;
    filename: string;
    totalRows: number;
    columns: string[];
    sampleData: any[];
    detectedMapping: { [key: string]: string };
  }) => {
    setImportData(prev => ({
      ...prev,
      file: fileData.file,
      filename: fileData.filename,
      totalRows: fileData.totalRows,
      columns: fileData.columns,
      sampleData: fileData.sampleData,
      columnMapping: fileData.detectedMapping,
    }));
    setCurrentStep(1);
  };

  const handleMappingComplete = (mapping: { [key: string]: string }, dateFormat: string) => {
    setImportData(prev => ({ ...prev, columnMapping: mapping, dateFormat }));
    setCurrentStep(2);
  };

  const handleValidation = (validationResults: any) => {
    setImportData(prev => ({ ...prev, validationResults }));
    // NO auto-advancement - user must click "Confirm Transactions" button
  };

  const handleConfirmTransactions = () => {
    // Mark transactions as confirmed and proceed to stock verification
    setImportData(prev => ({ 
      ...prev, 
      validationResults: { ...prev.validationResults, confirmed: true }
    }));
    setCurrentStep(3);
  };

  const handleStockVerification = (verificationResults: any) => {
    // Mark stocks as verified and proceed to final import
    setImportData(prev => ({ 
      ...prev, 
      validationResults: { ...prev.validationResults, stocksVerified: true }
    }));
    setCurrentStep(4);
  };

  const handleImport = (importResults: any) => {
    setImportData(prev => ({ ...prev, importResults }));
  };

  const resetImport = () => {
    setImportData({
      file: null,
      filename: '',
      totalRows: 0,
      columns: [],
      sampleData: [],
      columnMapping: {},
      dateFormat: 'YYYY-MM-DD',
      validationResults: null,
      importResults: null,
    });
    setCurrentStep(0);
    setError(null);
  };

  const canProceedToStep = (stepIndex: number): boolean => {
    switch (stepIndex) {
      case 1: return Boolean(importData.file);
      case 2: return Object.keys(importData.columnMapping).length > 0;
      case 3: return Boolean(importData.validationResults?.confirmed);
      case 4: return Boolean(importData.validationResults?.stocksVerified);
      default: return true;
    }
  };

  if (loading) {
    return (
      <div className="page">
        <div className="loading-shimmer" style={{ height: '100vh' }}></div>
      </div>
    );
  }

  if (error || !portfolio) {
    return (
      <div className="page">
        <div className="error-state">
          <div className="error-card glass">
            <h3>Unable to load portfolio</h3>
            <p>{error || 'Portfolio not found'}</p>
            <Link to="/" className="btn btn-primary">Back to Main Menu</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      {/* Portfolio Context Header */}
      <div className="portfolio-context-header">
        <div className="breadcrumb">
          <Link to="/" className="breadcrumb-link">Main Menu</Link>
          <span className="breadcrumb-separator">›</span>
          <Link to={`/portfolio/${portfolioId}/dashboard`} className="breadcrumb-link">
            {portfolio.name}
          </Link>
          <span className="breadcrumb-separator">›</span>
          <span className="breadcrumb-current">Import Transactions</span>
        </div>
      </div>

      <div className="page-header">
        <div className="header-content">
          <div className="portfolio-title">
            <div className="portfolio-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10,9 9,9 8,9"/>
              </svg>
            </div>
            <div>
              <h1>Import Transactions</h1>
              <p className="page-subtitle">Upload and import transaction data to {portfolio.name}</p>
            </div>
          </div>
        </div>
        <div className="header-actions">
          <a 
            href="/api/import/template" 
            download="bnb_transactions_template.csv"
            className="btn btn-outline"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7,10 12,15 17,10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Download Template
          </a>
          {importData.file && (
            <button onClick={resetImport} className="btn btn-outline">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="1,4 1,10 7,10"/>
                <path d="M3.51,15a9,9 0 1,0 2.13-9.36L1,10"/>
              </svg>
              Start Over
            </button>
          )}
        </div>
      </div>

      {/* Step Indicator */}
      <div className="import-steps">
        {steps.map((step, index) => (
          <div 
            key={step.key} 
            className={`step ${step.completed ? 'completed' : ''} ${step.current ? 'current' : ''}`}
            onClick={() => canProceedToStep(index) && setCurrentStep(index)}
          >
            <div className="step-indicator">
              {step.completed ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20,6 9,17 4,12"/>
                </svg>
              ) : (
                <span>{index + 1}</span>
              )}
            </div>
            <div className="step-content">
              <h3>{step.title}</h3>
              <p>{step.description}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Step Content */}
      <div className="import-content">
        {currentStep === 0 && (
          <FileUpload
            onFileUpload={handleFileUpload}
            loading={loading}
            error={error}
          />
        )}

        {currentStep === 1 && importData.file && (
          <ColumnMapping
            columns={importData.columns}
            sampleData={importData.sampleData}
            requiredFields={REQUIRED_FIELDS}
            detectedMapping={importData.columnMapping}
            onMappingComplete={handleMappingComplete}
          />
        )}

        {currentStep === 2 && importData.file && importData.columnMapping && (
          <DataPreview
            file={importData.file}
            columnMapping={importData.columnMapping}
            dateFormat={importData.dateFormat}
            portfolioId={parseInt(portfolioId!)}
            onValidation={handleValidation}
            onConfirm={handleConfirmTransactions}
          />
        )}

        {currentStep === 3 && importData.validationResults && (
          <StockVerification
            validationResults={importData.validationResults}
            portfolioId={parseInt(portfolioId!)}
            onStockVerification={handleStockVerification}
          />
        )}

        {currentStep === 4 && importData.validationResults && (
          <ImportSummary
            file={importData.file}
            columnMapping={importData.columnMapping}
            dateFormat={importData.dateFormat}
            validationResults={importData.validationResults}
            portfolioId={parseInt(portfolioId!)}
            onImport={handleImport}
            onComplete={() => navigate(`/portfolio/${portfolioId}/dashboard`)}
          />
        )}
      </div>
    </div>
  );
};