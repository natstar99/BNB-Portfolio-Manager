import React, { useState, useEffect } from 'react';

interface Stock {
  id: number;
  symbol: string;
  name: string | null;
  market: string | null;
  yahoo_symbol: string | null;
  verification_status: 'pending' | 'verified' | 'delisted' | 'error';
  verification_error: string | null;
  current_price: number | null;
}

interface Market {
  code: string;
  name: string;
  suffix: string;
  country: string;
  timezone: string;
}

interface StockEditorProps {
  stock: Stock;
  markets: Market[];
  onSave: (updatedStock: Partial<Stock>) => void;
  onCancel: () => void;
  onVerify: (stockId: number) => void;
  loading?: boolean;
}

export const StockEditor: React.FC<StockEditorProps> = ({
  stock,
  markets,
  onSave,
  onCancel,
  onVerify,
  loading = false,
}) => {
  const [formData, setFormData] = useState({
    symbol: stock.symbol || '',
    name: stock.name || '',
    market: stock.market || '',
    yahoo_symbol: stock.yahoo_symbol || '',
    verification_status: stock.verification_status,
  });
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<any>(null);

  useEffect(() => {
    // Auto-generate Yahoo symbol when market changes
    if (formData.market && formData.symbol) {
      const selectedMarket = markets.find(m => m.code === formData.market);
      if (selectedMarket) {
        const yahooSymbol = selectedMarket.suffix 
          ? `${formData.symbol}${selectedMarket.suffix}`
          : formData.symbol;
        setFormData(prev => ({
          ...prev,
          yahoo_symbol: yahooSymbol
        }));
      }
    }
  }, [formData.market, formData.symbol, markets]);

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: { [key: string]: string } = {};
    
    if (!formData.symbol.trim()) {
      newErrors.symbol = 'Stock symbol is required';
    } else if (!/^[A-Z0-9.-]+$/i.test(formData.symbol)) {
      newErrors.symbol = 'Invalid stock symbol format';
    }
    
    if (!formData.market) {
      newErrors.market = 'Market selection is required';
    }
    
    if (!formData.yahoo_symbol.trim()) {
      newErrors.yahoo_symbol = 'Yahoo symbol is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleVerifySymbol = async () => {
    if (!formData.yahoo_symbol.trim()) {
      setErrors(prev => ({
        ...prev,
        yahoo_symbol: 'Yahoo symbol is required for verification'
      }));
      return;
    }

    setVerifying(true);
    setVerificationResult(null);
    
    try {
      const response = await fetch('/api/stocks/verify-symbol', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          yahoo_symbol: formData.yahoo_symbol
        }),
      });

      const data = await response.json();
      
      if (response.ok) {
        setVerificationResult(data);
        if (data.exists) {
          // Auto-fill name if found
          if (data.name && !formData.name) {
            setFormData(prev => ({
              ...prev,
              name: data.name
            }));
          }
        }
      } else {
        setErrors(prev => ({
          ...prev,
          yahoo_symbol: data.error || 'Verification failed'
        }));
      }
    } catch (err) {
      setErrors(prev => ({
        ...prev,
        yahoo_symbol: 'Verification failed - check your connection'
      }));
    } finally {
      setVerifying(false);
    }
  };

  const handleSave = () => {
    if (!validateForm()) return;

    const updatedStock: Partial<Stock> = {
      symbol: formData.symbol.trim().toUpperCase(),
      name: formData.name.trim() || null,
      market: formData.market,
      yahoo_symbol: formData.yahoo_symbol.trim(),
      verification_status: verificationResult?.exists ? 'verified' : 'pending',
    };

    onSave(updatedStock);
  };

  const getMarketDisplayName = (market: Market) => {
    return `${market.name} (${market.country})`;
  };

  return (
    <div className="stock-editor-overlay">
      <div className="stock-editor-modal">
        <div className="stock-editor-header">
          <h3>Edit Stock Information</h3>
          <button onClick={onCancel} className="close-button">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div className="stock-editor-content">
          <div className="form-section">
            <div className="form-group">
              <label className="form-label">
                Stock Symbol *
                <span className="form-hint">Original symbol from your transaction data</span>
              </label>
              <input
                type="text"
                value={formData.symbol}
                onChange={(e) => handleInputChange('symbol', e.target.value.toUpperCase())}
                className={`form-input ${errors.symbol ? 'error' : ''}`}
                placeholder="e.g., AAPL, CBA"
                disabled={loading}
              />
              {errors.symbol && <span className="error-message">{errors.symbol}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">
                Company Name
                <span className="form-hint">Full company name (auto-filled during verification)</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className="form-input"
                placeholder="e.g., Apple Inc."
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label className="form-label">
                Market *
                <span className="form-hint">Select the stock exchange where this stock is listed</span>
              </label>
              <select
                value={formData.market}
                onChange={(e) => handleInputChange('market', e.target.value)}
                className={`form-select ${errors.market ? 'error' : ''}`}
                disabled={loading}
              >
                <option value="">Select Market</option>
                {markets.map(market => (
                  <option key={market.code} value={market.code}>
                    {getMarketDisplayName(market)}
                  </option>
                ))}
              </select>
              {errors.market && <span className="error-message">{errors.market}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">
                Yahoo Finance Symbol *
                <span className="form-hint">Symbol used by Yahoo Finance (auto-generated based on market)</span>
              </label>
              <div className="yahoo-symbol-input">
                <input
                  type="text"
                  value={formData.yahoo_symbol}
                  onChange={(e) => handleInputChange('yahoo_symbol', e.target.value)}
                  className={`form-input ${errors.yahoo_symbol ? 'error' : ''}`}
                  placeholder="e.g., AAPL, CBA.AX"
                  disabled={loading}
                />
                <button
                  onClick={handleVerifySymbol}
                  disabled={verifying || loading || !formData.yahoo_symbol.trim()}
                  className="verify-button"
                >
                  {verifying ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 12a9 9 0 11-6.219-8.56"/>
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                      <polyline points="22,4 12,14.01 9,11.01"/>
                    </svg>
                  )}
                  {verifying ? 'Verifying...' : 'Verify'}
                </button>
              </div>
              {errors.yahoo_symbol && <span className="error-message">{errors.yahoo_symbol}</span>}
            </div>

            {verificationResult && (
              <div className={`verification-result ${verificationResult.exists ? 'success' : 'error'}`}>
                <div className="result-header">
                  {verificationResult.exists ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                      <polyline points="22,4 12,14.01 9,11.01"/>
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10"/>
                      <line x1="15" y1="9" x2="9" y2="15"/>
                      <line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                  )}
                  <span className="result-title">
                    {verificationResult.exists ? 'Symbol Verified' : 'Symbol Not Found'}
                  </span>
                </div>
                
                {verificationResult.exists ? (
                  <div className="result-details">
                    <p><strong>Name:</strong> {verificationResult.name}</p>
                    {verificationResult.current_price && (
                      <p><strong>Current Price:</strong> ${verificationResult.current_price.toFixed(2)}</p>
                    )}
                    {verificationResult.market_cap && (
                      <p><strong>Market Cap:</strong> {verificationResult.market_cap}</p>
                    )}
                  </div>
                ) : (
                  <div className="result-details">
                    <p>This symbol was not found on Yahoo Finance. Please check the symbol or mark as delisted.</p>
                    <div className="not-found-actions">
                      <button 
                        onClick={() => handleInputChange('verification_status', 'delisted')}
                        className="btn btn-sm btn-outline"
                      >
                        Mark as Delisted
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="market-info-section">
            <h4>Market Information</h4>
            {formData.market && (
              <div className="market-details">
                {(() => {
                  const selectedMarket = markets.find(m => m.code === formData.market);
                  return selectedMarket ? (
                    <div className="market-card">
                      <div className="market-header">
                        <h5>{selectedMarket.name}</h5>
                        <span className="market-code">{selectedMarket.code}</span>
                      </div>
                      <div className="market-info">
                        <p><strong>Country:</strong> {selectedMarket.country}</p>
                        <p><strong>Timezone:</strong> {selectedMarket.timezone}</p>
                        <p><strong>Yahoo Suffix:</strong> {selectedMarket.suffix || 'None'}</p>
                      </div>
                    </div>
                  ) : (
                    <p className="no-market">Select a market to see details</p>
                  );
                })()}
              </div>
            )}
          </div>
        </div>

        <div className="stock-editor-actions">
          <button 
            onClick={onCancel}
            className="btn btn-outline"
            disabled={loading}
          >
            Cancel
          </button>
          <button 
            onClick={handleSave}
            className="btn btn-primary"
            disabled={loading || Object.keys(errors).length > 0}
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};