import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FileUpload } from '../components/import/FileUpload';
import { ColumnMapping } from '../components/import/ColumnMapping';
import { DataPreview } from '../components/import/DataPreview';
import { ImportSummary } from '../components/import/ImportSummary';
import { StockVerification } from '../components/import/StockVerification';

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
      title: '1. Upload File',
      completed: Boolean(importData.file),
      current: currentStep === 0,
    },
    {
      key: 'mapping',
      title: '2. Map Columns',
      completed: Object.keys(importData.columnMapping).length > 0,
      current: currentStep === 1,
    },
    {
      key: 'confirm',
      title: '3. Confirm Transactions',
      completed: Boolean(importData.validationResults?.confirmed),
      current: currentStep === 2,
    },
    {
      key: 'verify',
      title: '4. Verify Stocks',
      completed: Boolean(importData.validationResults?.stocksVerified),
      current: currentStep === 3,
    },
    {
      key: 'import',
      title: '5. Import',
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
  };

  const handleConfirmTransactions = () => {
    setImportData(prev => ({
      ...prev,
      validationResults: { ...prev.validationResults, confirmed: true }
    }));
    setCurrentStep(3);
  };

  const handleStockVerification = (verificationResults: any) => {
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
    return <div className="page"><p>Loading...</p></div>;
  }

  if (error || !portfolio) {
    return (
      <div className="page">
        <h1>Error</h1>
        <p>{error || 'Portfolio not found'}</p>
        <button onClick={() => navigate('/')}>Back to Main Menu</button>
      </div>
    );
  }

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1>Import Transactions</h1>
          <p>Portfolio: {portfolio.name}</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <a
            href="/api/import/template"
            download="bnb_transactions_template.csv"
          >
            Download Template
          </a>
          {importData.file && (
            <button onClick={resetImport}>Start Over</button>
          )}
        </div>
      </div>

      {/* Step Indicator */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          {steps.map((step, index) => (
            <button
              key={step.key}
              onClick={() => canProceedToStep(index) && setCurrentStep(index)}
              className={step.current ? 'active' : ''}
              disabled={!canProceedToStep(index)}
              style={{
                opacity: canProceedToStep(index) ? 1 : 0.5,
                cursor: canProceedToStep(index) ? 'pointer' : 'not-allowed'
              }}
            >
              {step.completed ? '✓ ' : ''}{step.title}
            </button>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div>
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
