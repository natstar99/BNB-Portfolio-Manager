import React, { useState, useEffect, useRef } from 'react';
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
}

interface Portfolio {
  id: number;
  name: string;
}

interface ImportProgress {
  total: number;
  processed: number;
  errors: number;
  status: 'idle' | 'analyzing' | 'preview' | 'processing' | 'completed' | 'error';
}

interface FileAnalysis {
  filename: string;
  total_rows: number;
  columns: string[];
  detected_mapping: Record<string, string>;
  sample_data: Record<string, any>[];
}

interface ColumnMapping {
  date: string;
  instrument_code: string;
  transaction_type: string;
  quantity: string;
  price: string;
  total_value?: string;
}

const DATE_FORMATS = [
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (2024-01-15)' },
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (01/15/2024)' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (15/01/2024)' },
  { value: 'DD-MM-YYYY', label: 'DD-MM-YYYY (15-01-2024)' },
  { value: 'MM-DD-YYYY', label: 'MM-DD-YYYY (01-15-2024)' },
  { value: 'YYYYMMDD', label: 'YYYYMMDD (20240115)' },
  { value: 'DD-MMM-YYYY', label: 'DD-MMM-YYYY (15-Jan-2024)' },
  { value: 'MMM DD, YYYY', label: 'MMM DD, YYYY (Jan 15, 2024)' }
];

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
  
  // Import/Export
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [fileAnalysis, setFileAnalysis] = useState<FileAnalysis | null>(null);
  const [columnMapping, setColumnMapping] = useState<ColumnMapping>({
    date: '',
    instrument_code: '',
    transaction_type: '',
    quantity: '',
    price: '',
    total_value: ''
  });
  const [selectedDateFormat, setSelectedDateFormat] = useState('YYYY-MM-DD');
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string>('');
  const [importProgress, setImportProgress] = useState<ImportProgress>({
    total: 0,
    processed: 0,
    errors: 0,
    status: 'idle'
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Add Transaction
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTransaction, setNewTransaction] = useState({
    portfolio_id: '',
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


  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const validTypes = [
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      ];
      
      if (validTypes.includes(file.type) || file.name.endsWith('.csv') || file.name.endsWith('.xlsx')) {
        setImportFile(file);
        await analyzeFile(file);
      } else {
        alert('Please select a CSV or Excel file');
        event.target.value = '';
      }
    }
  };

  const analyzeFile = async (file: File) => {
    try {
      setImportProgress({ total: 0, processed: 0, errors: 0, status: 'analyzing' });
      
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/import/analyze', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Failed to analyze file');
      }
      
      const result = await response.json();
      if (result.success) {
        setFileAnalysis(result.data);
        
        // Auto-populate column mapping from detected mapping
        const detected = result.data.detected_mapping;
        setColumnMapping({
          date: detected.date || '',
          instrument_code: detected.instrument_code || detected.symbol || '',
          transaction_type: detected.transaction_type || detected.action || '',
          quantity: detected.quantity || '',
          price: detected.price || '',
          total_value: detected.total_value || detected.total || ''
        });
        
        setImportProgress({ total: 0, processed: 0, errors: 0, status: 'preview' });
      } else {
        throw new Error(result.error || 'Analysis failed');
      }
    } catch (err) {
      console.error('File analysis error:', err);
      setImportProgress({ total: 0, processed: 0, errors: 0, status: 'error' });
      alert('Failed to analyze file. Please check the format and try again.');
    }
  };

  const resetImportState = () => {
    setImportFile(null);
    setFileAnalysis(null);
    setColumnMapping({
      date: '',
      instrument_code: '',
      transaction_type: '',
      quantity: '',
      price: '',
      total_value: ''
    });
    setSelectedDateFormat('YYYY-MM-DD');
    setSelectedPortfolioId('');
    setImportProgress({ total: 0, processed: 0, errors: 0, status: 'idle' });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleImport = async () => {
    if (!importFile || !selectedPortfolioId) {
      alert('Please select a portfolio and ensure all required fields are mapped');
      return;
    }
    
    // Validate required column mappings
    if (!columnMapping.date || !columnMapping.instrument_code || !columnMapping.transaction_type || 
        !columnMapping.quantity || !columnMapping.price) {
      alert('Please map all required columns: Date, Stock Ticker, Action, Quantity, and Price');
      return;
    }
    
    const formData = new FormData();
    formData.append('file', importFile);
    formData.append('portfolio_id', selectedPortfolioId);
    formData.append('column_mapping', JSON.stringify(columnMapping));
    formData.append('date_format', selectedDateFormat);
    
    try {
      setImportProgress({ total: 0, processed: 0, errors: 0, status: 'processing' });
      
      const response = await fetch('/api/import/transactions', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Import failed');
      }
      
      const result = await response.json();
      if (result.success) {
        setImportProgress({
          total: result.total || 0,
          processed: result.processed || 0,
          errors: result.errors || 0,
          status: 'completed'
        });
        
        // Refresh transactions
        fetchTransactions();
        
        // Close modal after delay
        setTimeout(() => {
          setShowImportModal(false);
          resetImportState();
        }, 3000);
      } else {
        throw new Error(result.error || 'Import failed');
      }
      
    } catch (err) {
      setImportProgress(prev => ({ ...prev, status: 'error' }));
      console.error('Import error:', err);
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
        portfolio_id: '',
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

  const handleExport = () => {
    const params = new URLSearchParams();
    if (selectedPortfolio !== 'all') params.append('portfolio_id', selectedPortfolio);
    if (selectedAction !== 'all') params.append('action', selectedAction);
    if (searchSymbol) params.append('symbol', searchSymbol);
    if (dateRange.start) params.append('start_date', dateRange.start);
    if (dateRange.end) params.append('end_date', dateRange.end);
    
    window.open(`/api/transactions/export?${params.toString()}`, '_blank');
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

  return (
    <div className="page">
      <div className="page-header">
        <div className="header-content">
          <div>
            <h1>Transactions</h1>
            <p className="page-subtitle">View and manage your trading history</p>
          </div>
          <div className="header-actions">
            <button 
              onClick={() => setShowImportModal(true)}
              className="btn btn-outline"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="12" y1="11" x2="12" y2="17"/>
                <polyline points="9,14 12,17 15,14"/>
              </svg>
              Import
            </button>
            <button 
              onClick={handleExport}
              className="btn btn-outline"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7,10 12,15 17,10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              Export
            </button>
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
                  <button onClick={() => setShowImportModal(true)} className="btn btn-outline">
                    Import File
                  </button>
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

      {/* Import Modal */}
      {showImportModal && (
        <div className="modal-overlay" onClick={() => { setShowImportModal(false); resetImportState(); }}>
          <div className="modal glass import-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Import Transactions</h3>
              <button 
                onClick={() => { setShowImportModal(false); resetImportState(); }}
                className="btn-icon"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            
            <div className="modal-body">
              {/* Step 1: File Selection */}
              {importProgress.status === 'idle' && (
                <>
                  <div className="import-info">
                    <h4>Step 1: Select File</h4>
                    <p>Upload a CSV or Excel file containing your transaction data</p>
                    
                    <div className="supported-formats">
                      <strong>Supported formats:</strong> CSV, Excel (.xlsx, .xls)
                    </div>
                  </div>
                  
                  <div className="file-upload">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv,.xlsx,.xls"
                      onChange={handleFileSelect}
                      style={{ display: 'none' }}
                    />
                    <button 
                      onClick={() => fileInputRef.current?.click()}
                      className="btn btn-outline file-select-btn"
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14,2 14,8 20,8"/>
                        <line x1="12" y1="11" x2="12" y2="17"/>
                        <polyline points="9,14 12,17 15,14"/>
                      </svg>
                      Choose File
                    </button>
                  </div>
                </>
              )}

              {/* Analyzing Status */}
              {importProgress.status === 'analyzing' && (
                <div className="import-progress">
                  <h4>Analyzing File...</h4>
                  <div className="loading-spinner"></div>
                  <p>Reading file structure and detecting columns</p>
                </div>
              )}
              
              {/* Step 2: Preview and Configuration */}
              {importProgress.status === 'preview' && fileAnalysis && (
                <>
                  <div className="import-step">
                    <h4>Step 2: Configure Import</h4>
                    <p>Review the data preview and configure column mapping</p>
                  </div>

                  {/* File Info */}
                  <div className="file-info glass-inner">
                    <h5>📁 File Information</h5>
                    <div className="file-details">
                      <span><strong>File:</strong> {fileAnalysis.filename}</span>
                      <span><strong>Rows:</strong> {fileAnalysis.total_rows} transactions</span>
                      <span><strong>Columns:</strong> {fileAnalysis.columns.length}</span>
                    </div>
                  </div>

                  {/* Portfolio Selection */}
                  <div className="config-section glass-inner">
                    <h5>🎯 Target Portfolio</h5>
                    <select
                      value={selectedPortfolioId}
                      onChange={(e) => setSelectedPortfolioId(e.target.value)}
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

                  {/* Column Mapping */}
                  <div className="config-section glass-inner">
                    <h5>🔗 Column Mapping</h5>
                    <div className="column-mapping-grid">
                      <div className="mapping-field">
                        <label>Date Column *</label>
                        <select
                          value={columnMapping.date}
                          onChange={(e) => setColumnMapping({...columnMapping, date: e.target.value})}
                          className="form-input"
                        >
                          <option value="">Select column</option>
                          {fileAnalysis.columns.map(col => (
                            <option key={col} value={col}>{col}</option>
                          ))}
                        </select>
                      </div>

                      <div className="mapping-field">
                        <label>Stock Ticker Column *</label>
                        <select
                          value={columnMapping.instrument_code}
                          onChange={(e) => setColumnMapping({...columnMapping, instrument_code: e.target.value})}
                          className="form-input"
                        >
                          <option value="">Select column</option>
                          {fileAnalysis.columns.map(col => (
                            <option key={col} value={col}>{col}</option>
                          ))}
                        </select>
                      </div>

                      <div className="mapping-field">
                        <label>Action Column *</label>
                        <select
                          value={columnMapping.transaction_type}
                          onChange={(e) => setColumnMapping({...columnMapping, transaction_type: e.target.value})}
                          className="form-input"
                        >
                          <option value="">Select column</option>
                          {fileAnalysis.columns.map(col => (
                            <option key={col} value={col}>{col}</option>
                          ))}
                        </select>
                      </div>

                      <div className="mapping-field">
                        <label>Quantity Column *</label>
                        <select
                          value={columnMapping.quantity}
                          onChange={(e) => setColumnMapping({...columnMapping, quantity: e.target.value})}
                          className="form-input"
                        >
                          <option value="">Select column</option>
                          {fileAnalysis.columns.map(col => (
                            <option key={col} value={col}>{col}</option>
                          ))}
                        </select>
                      </div>

                      <div className="mapping-field">
                        <label>Price Column *</label>
                        <select
                          value={columnMapping.price}
                          onChange={(e) => setColumnMapping({...columnMapping, price: e.target.value})}
                          className="form-input"
                        >
                          <option value="">Select column</option>
                          {fileAnalysis.columns.map(col => (
                            <option key={col} value={col}>{col}</option>
                          ))}
                        </select>
                      </div>

                      <div className="mapping-field">
                        <label>Total Column</label>
                        <select
                          value={columnMapping.total_value}
                          onChange={(e) => setColumnMapping({...columnMapping, total_value: e.target.value})}
                          className="form-input"
                        >
                          <option value="">Select column (optional)</option>
                          {fileAnalysis.columns.map(col => (
                            <option key={col} value={col}>{col}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Date Format Selection */}
                  <div className="config-section glass-inner">
                    <h5>📅 Date Format</h5>
                    <select
                      value={selectedDateFormat}
                      onChange={(e) => setSelectedDateFormat(e.target.value)}
                      className="form-input"
                    >
                      {DATE_FORMATS.map(format => (
                        <option key={format.value} value={format.value}>
                          {format.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Data Preview */}
                  {fileAnalysis.sample_data.length > 0 && (
                    <div className="config-section glass-inner">
                      <h5>👁️ Data Preview (First 3 rows)</h5>
                      <div className="data-preview-table">
                        <div className="preview-table-header">
                          {fileAnalysis.columns.map(col => (
                            <div key={col} className="preview-header-cell">{col}</div>
                          ))}
                        </div>
                        {fileAnalysis.sample_data.slice(0, 3).map((row, index) => (
                          <div key={index} className="preview-table-row">
                            {fileAnalysis.columns.map(col => (
                              <div key={col} className="preview-table-cell">
                                {row[col]?.toString() || ''}
                              </div>
                            ))}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
              
              {/* Processing Status */}
              {importProgress.status === 'processing' && (
                <div className="import-progress">
                  <h4>Processing Transactions...</h4>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill"
                      style={{ 
                        width: importProgress.total > 0 
                          ? `${(importProgress.processed / importProgress.total) * 100}%` 
                          : '0%' 
                      }}
                    ></div>
                  </div>
                  <p>
                    Processed {importProgress.processed} of {importProgress.total} transactions
                  </p>
                </div>
              )}
              
              {/* Completion Status */}
              {importProgress.status === 'completed' && (
                <div className="import-result success">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22,4 12,14.01 9,11.01"/>
                  </svg>
                  <h4>Import Completed Successfully!</h4>
                  <p>
                    Successfully imported {importProgress.processed} transactions
                    {importProgress.errors > 0 && ` with ${importProgress.errors} errors`}
                  </p>
                </div>
              )}
              
              {/* Error Status */}
              {importProgress.status === 'error' && (
                <div className="import-result error">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                  </svg>
                  <h4>Import Failed</h4>
                  <p>There was an error processing your file. Please check the format and try again.</p>
                  <button 
                    onClick={resetImportState}
                    className="btn btn-outline btn-sm"
                    style={{ marginTop: '10px' }}
                  >
                    Try Again
                  </button>
                </div>
              )}
            </div>
            
            {/* Modal Footer - Show appropriate buttons based on status */}
            {(importProgress.status === 'idle' || importProgress.status === 'preview') && (
              <div className="modal-footer">
                <button 
                  onClick={() => { setShowImportModal(false); resetImportState(); }}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                {importProgress.status === 'preview' && (
                  <button 
                    onClick={handleImport}
                    className="btn btn-primary"
                    disabled={!selectedPortfolioId || !columnMapping.date || !columnMapping.instrument_code || !columnMapping.transaction_type || !columnMapping.quantity || !columnMapping.price}
                  >
                    Import {fileAnalysis?.total_rows || 0} Transactions
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

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