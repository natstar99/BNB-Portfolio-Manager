import React, { useState, useCallback } from 'react';

interface FileUploadProps {
  onFileUpload: (fileData: {
    file: File;
    filename: string;
    totalRows: number;
    columns: string[];
    sampleData: any[];
    detectedMapping: { [key: string]: string };
  }) => void;
  loading: boolean;
  error: string | null;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onFileUpload, loading, error }) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  }, []);

  const handleFile = async (file: File) => {
    // Validate file type
    const validExtensions = ['.csv', '.xlsx', '.xls'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!validExtensions.includes(fileExtension)) {
      setUploadError('Please select a CSV or Excel file (.csv, .xlsx, .xls)');
      return;
    }

    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      setUploadError('File size must be less than 10MB');
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      // Analyze file structure
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/import/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to analyze file');
      }

      const data = await response.json();
      
      if (data.success && data.data) {
        onFileUpload({
          file,
          filename: data.data.filename,
          totalRows: data.data.total_rows,
          columns: data.data.columns,
          sampleData: data.data.sample_data,
          detectedMapping: data.data.detected_mapping,
        });
      } else {
        throw new Error(data.error || 'Failed to analyze file');
      }
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="file-upload-section">
      <div className="upload-instructions glass">
        <div className="instructions-header">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14,2 14,8 20,8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10,9 9,9 8,9"/>
          </svg>
          <h3>Upload Transaction Data</h3>
        </div>
        
        <div className="instructions-content">
          <p>Upload a CSV or Excel file containing your transaction data. The file should include:</p>
          <ul>
            <li><strong>Date</strong> - Transaction date</li>
            <li><strong>Stock Symbol</strong> - Ticker symbol (e.g., AAPL, MSFT)</li>
            <li><strong>Transaction Type</strong> - BUY, SELL, DIVIDEND, etc.</li>
            <li><strong>Quantity</strong> - Number of shares</li>
            <li><strong>Price</strong> - Price per share</li>
            <li><strong>Total Value</strong> - Total transaction value (optional)</li>
          </ul>
          
          <div className="file-requirements">
            <h4>File Requirements:</h4>
            <ul>
              <li>Supported formats: CSV, Excel (.xlsx, .xls)</li>
              <li>Maximum file size: 10MB</li>
              <li>First row should contain column headers</li>
            </ul>
          </div>
        </div>
      </div>

      <div 
        className={`file-upload-area ${dragActive ? 'drag-active' : ''} ${uploading ? 'uploading' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="fileInput"
          accept=".csv,.xlsx,.xls"
          onChange={handleChange}
          disabled={uploading}
          style={{ display: 'none' }}
        />
        
        <div className="upload-content">
          {uploading ? (
            <>
              <div className="upload-spinner">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12a9 9 0 11-6.219-8.56"/>
                </svg>
              </div>
              <h3>Analyzing file...</h3>
              <p>Please wait while we process your file</p>
            </>
          ) : (
            <>
              <div className="upload-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17,8 12,3 7,8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
              </div>
              <h3>Drop your file here</h3>
              <p>or click to browse and select a file</p>
              <label htmlFor="fileInput" className="btn btn-primary">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17,8 12,3 7,8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                Choose File
              </label>
            </>
          )}
        </div>
      </div>

      {(uploadError || error) && (
        <div className="upload-error">
          <div className="error-card">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <span>{uploadError || error}</span>
          </div>
        </div>
      )}

      <div className="upload-tips glass">
        <h4>Tips for best results:</h4>
        <div className="tips-grid">
          <div className="tip">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 11H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h4l5 4V7l-5 4z"/>
              <path d="M22 9s-1-2-3-2-3 2-3 2"/>
            </svg>
            <span>Use standard column names like "Date", "Symbol", "Type" for automatic detection</span>
          </div>
          <div className="tip">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            <span>Use consistent date format (YYYY-MM-DD recommended)</span>
          </div>
          <div className="tip">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
            </svg>
            <span>Remove any summary rows or extra headers</span>
          </div>
          <div className="tip">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
            </svg>
            <span>Stock symbols should match Yahoo Finance format (e.g., AAPL, CBA.AX)</span>
          </div>
        </div>
      </div>
    </div>
  );
};