import React, { useState, useEffect } from 'react';

interface RequiredField {
  key: string;
  label: string;
  required: boolean;
}

interface ColumnMappingProps {
  columns: string[];
  sampleData: any[];
  requiredFields: RequiredField[];
  detectedMapping: { [key: string]: string };
  onMappingComplete: (mapping: { [key: string]: string }, dateFormat: string) => void;
}

export const ColumnMapping: React.FC<ColumnMappingProps> = ({
  columns,
  sampleData,
  requiredFields,
  detectedMapping,
  onMappingComplete,
}) => {
  const [mapping, setMapping] = useState<{ [key: string]: string }>(detectedMapping);
  const [errors, setErrors] = useState<string[]>([]);
  const [selectedDateFormat, setSelectedDateFormat] = useState<string>('YYYY-MM-DD');

  const dateFormats = [
    { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (2023-12-25)', example: '2023-12-25' },
    { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (12/25/2023)', example: '12/25/2023' },
    { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (25/12/2023)', example: '25/12/2023' },
    { value: 'DD-MM-YYYY', label: 'DD-MM-YYYY (25-12-2023)', example: '25-12-2023' },
    { value: 'MM-DD-YYYY', label: 'MM-DD-YYYY (12-25-2023)', example: '12-25-2023' },
    { value: 'YYYYMMDD', label: 'YYYYMMDD (20231225)', example: '20231225' },
    { value: 'DD-MMM-YYYY', label: 'DD-MMM-YYYY (25-Dec-2023)', example: '25-Dec-2023' },
    { value: 'MMM DD, YYYY', label: 'MMM DD, YYYY (Dec 25, 2023)', example: 'Dec 25, 2023' },
  ];

  useEffect(() => {
    setMapping(detectedMapping);
  }, [detectedMapping]);

  const handleMappingChange = (fieldKey: string, columnName: string) => {
    setMapping(prev => ({
      ...prev,
      [fieldKey]: columnName,
    }));
  };

  const validateMapping = (): boolean => {
    const newErrors: string[] = [];
    
    // Check required fields
    requiredFields.forEach(field => {
      if (field.required && (!mapping[field.key] || mapping[field.key] === '')) {
        newErrors.push(`${field.label} is required`);
      }
    });

    // Check for duplicate mappings
    const usedColumns = Object.values(mapping).filter(col => col !== '');
    const duplicates = usedColumns.filter((col, index) => usedColumns.indexOf(col) !== index);
    if (duplicates.length > 0) {
      newErrors.push(`Column${duplicates.length > 1 ? 's' : ''} ${duplicates.join(', ')} mapped multiple times`);
    }

    setErrors(newErrors);
    return newErrors.length === 0;
  };

  // Compute validation state without side effects for render
  const isValidMapping = (): boolean => {
    // Check required fields
    const hasRequiredFields = requiredFields.every(field => 
      !field.required || (mapping[field.key] && mapping[field.key] !== '')
    );

    // Check for duplicate mappings
    const usedColumns = Object.values(mapping).filter(col => col !== '');
    const hasDuplicates = usedColumns.length !== new Set(usedColumns).size;

    return hasRequiredFields && !hasDuplicates;
  };

  const handleContinue = () => {
    if (validateMapping()) {
      onMappingComplete(mapping, selectedDateFormat);
    }
  };

  const getSampleValue = (columnName: string): string => {
    if (!columnName || sampleData.length === 0) return '';
    const firstRow = sampleData[0];
    return firstRow[columnName]?.toString() || '';
  };

  const getFieldIcon = (fieldKey: string) => {
    switch (fieldKey) {
      case 'date':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
        );
      case 'instrument_code':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
          </svg>
        );
      case 'transaction_type':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 11H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h4l5 4V7l-5 4z"/>
            <path d="M22 9s-1-2-3-2-3 2-3 2"/>
          </svg>
        );
      case 'quantity':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
        );
      case 'price':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
          </svg>
        );
      case 'total_value':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="1" y="3" width="15" height="13"/>
            <path d="m16 8 2-2 2 2"/>
            <path d="M21 14V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2z"/>
          </svg>
        );
      default:
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M8 12h8"/>
          </svg>
        );
    }
  };

  return (
    <div className="column-mapping-section">
      <div className="mapping-header glass">
        <div className="header-content">
          <h3>Map Your Columns</h3>
          <p>Map the columns from your file to the required transaction fields. Required fields are marked with an asterisk (*).</p>
        </div>
        <div className="mapping-stats">
          <div className="stat">
            <span className="stat-label">File Columns</span>
            <span className="stat-value">{columns.length}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Required Fields</span>
            <span className="stat-value">{requiredFields.filter(f => f.required).length}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Mapped</span>
            <span className="stat-value">
              {Object.values(mapping).filter(v => v !== '').length}
            </span>
          </div>
        </div>
      </div>

      {errors.length > 0 && (
        <div className="mapping-errors">
          <div className="error-card">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <div className="error-content">
              <h4>Mapping Issues:</h4>
              <ul>
                {errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      <div className="mapping-grid">
        <div className="required-fields">
          <h4>Required Fields</h4>
          <div className="fields-list">
            {requiredFields.map(field => (
              <div key={field.key} className="field-mapping">
                <div className="field-info">
                  <div className="field-header">
                    {getFieldIcon(field.key)}
                    <span className="field-label">
                      {field.label}
                      {field.required && <span className="required">*</span>}
                    </span>
                  </div>
                  <select
                    value={mapping[field.key] || ''}
                    onChange={(e) => handleMappingChange(field.key, e.target.value)}
                    className={`field-select ${field.required && !mapping[field.key] ? 'error' : ''}`}
                  >
                    <option value="">-- Select Column --</option>
                    {columns.map(column => (
                      <option key={column} value={column}>
                        {column}
                      </option>
                    ))}
                  </select>
                </div>
                
                {mapping[field.key] && (
                  <div className="sample-preview">
                    <span className="sample-label">Sample:</span>
                    <span className="sample-value">
                      {getSampleValue(mapping[field.key]) || 'No data'}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="file-preview">
          <h4>File Preview</h4>
          <div className="preview-table">
            <table>
              <thead>
                <tr>
                  {columns.map(column => (
                    <th key={column} className={Object.values(mapping).includes(column) ? 'mapped' : ''}>
                      {column}
                      {Object.values(mapping).includes(column) && (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="20,6 9,17 4,12"/>
                        </svg>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sampleData.slice(0, 3).map((row, index) => (
                  <tr key={index}>
                    {columns.map(column => (
                      <td key={column}>
                        {row[column]?.toString() || ''}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {mapping['date'] && (
        <div className="date-format-section glass">
          <h4>Date Format Configuration</h4>
          <p>Select the format that matches your date column ({mapping['date']})</p>
          
          <div className="date-format-grid">
            {dateFormats.map(format => (
              <label key={format.value} className={`date-format-option ${selectedDateFormat === format.value ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="dateFormat"
                  value={format.value}
                  checked={selectedDateFormat === format.value}
                  onChange={(e) => setSelectedDateFormat(e.target.value)}
                />
                <div className="format-content">
                  <div className="format-label">{format.label}</div>
                  <div className="format-example">Example: {format.example}</div>
                </div>
              </label>
            ))}
          </div>
          
          {mapping['date'] && (
            <div className="date-preview">
              <strong>Your date sample:</strong> {getSampleValue(mapping['date'])}
            </div>
          )}
        </div>
      )}

      <div className="mapping-actions">
        <button className="btn btn-error" onClick={() => window.history.back()}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15,18 9,12 15,6"/>
          </svg>
          Return to Previous Step
        </button>
        <button 
          onClick={handleContinue}
          className="btn btn-primary"
          disabled={!isValidMapping()}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9,18 15,12 9,6"/>
          </svg>
          Continue to Preview
        </button>
      </div>

      <div className="mapping-tips glass">
        <h4>Column Mapping Tips:</h4>
        <div className="tips-list">
          <div className="tip">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 11H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h4l5 4V7l-5 4z"/>
              <path d="M22 9s-1-2-3-2-3 2-3 2"/>
            </svg>
            <strong>Transaction Type:</strong> Should contain values like BUY, SELL, DIVIDEND, SPLIT
          </div>
          <div className="tip">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            <strong>Date:</strong> Accepts various formats (YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY)
          </div>
          <div className="tip">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
            <strong>Price & Quantity:</strong> Should be numeric values (decimals allowed)
          </div>
          <div className="tip">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
            </svg>
            <strong>Stock Symbol:</strong> Use standard ticker symbols (e.g., AAPL for Apple)
          </div>
        </div>
      </div>
    </div>
  );
};