import React, { useState, useEffect } from 'react';
import { usePortfolios } from '../hooks/usePortfolios';
import { Portfolio } from '../shared/types';
import '../styles/settings.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

export const Settings: React.FC = () => {
  const { portfolios, loading: portfoliosLoading, refetch: refreshPortfolios } = usePortfolios();
  const [currencies, setCurrencies] = useState<string[]>([]);
  const [loadingCurrencies, setLoadingCurrencies] = useState(true);
  const [editingPortfolio, setEditingPortfolio] = useState<number | null>(null);
  const [selectedCurrency, setSelectedCurrency] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    fetchCurrencies();
  }, []);

  const fetchCurrencies = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/currencies`);
      const data = await response.json();
      if (data.success) {
        setCurrencies(data.data.currencies);
      }
    } catch (error) {
      console.error('Failed to fetch currencies:', error);
    } finally {
      setLoadingCurrencies(false);
    }
  };

  const handleEditPortfolio = (portfolio: Portfolio) => {
    setEditingPortfolio(portfolio.id);
    setSelectedCurrency(portfolio.currency || 'USD');
    setMessage(null);
  };

  const handleCancelEdit = () => {
    setEditingPortfolio(null);
    setSelectedCurrency('');
    setMessage(null);
  };

  const handleSaveCurrency = async (portfolioId: number) => {
    setSaving(true);
    setMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/portfolios/${portfolioId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          currency: selectedCurrency
        })
      });

      const data = await response.json();

      if (data.success) {
        setMessage({ type: 'success', text: 'Portfolio base currency updated successfully' });
        setEditingPortfolio(null);
        await refreshPortfolios();
      } else {
        setMessage({ type: 'error', text: data.message || 'Failed to update currency' });
      }
    } catch (error) {
      console.error('Failed to update portfolio currency:', error);
      setMessage({ type: 'error', text: 'Failed to update portfolio currency' });
    } finally {
      setSaving(false);
    }
  };

  if (portfoliosLoading || loadingCurrencies) {
    return (
      <div className="page">
        <div className="page-header">
          <h1>Settings</h1>
          <p className="page-subtitle">Configure your portfolio preferences</p>
        </div>
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Settings</h1>
        <p className="page-subtitle">Configure your portfolio preferences</p>
      </div>

      {message && (
        <div className={`message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="settings-content">
        <section className="settings-section glass">
          <div className="settings-section-header">
            <h2>Portfolio Currency Settings</h2>
            <p>Set the base currency for each portfolio. All portfolio values and analytics will be displayed in this currency.</p>
          </div>

          {portfolios.length === 0 ? (
            <div className="empty-state">
              <p>No portfolios found. Create a portfolio first to configure currency settings.</p>
            </div>
          ) : (
            <div className="portfolio-currency-list">
              {portfolios.map((portfolio) => (
                <div key={portfolio.id} className="portfolio-currency-item">
                  <div className="portfolio-info">
                    <h3>{portfolio.name}</h3>
                    {portfolio.description && (
                      <p className="portfolio-description">{portfolio.description}</p>
                    )}
                  </div>

                  {editingPortfolio === portfolio.id ? (
                    <div className="currency-edit-controls">
                      <select
                        value={selectedCurrency}
                        onChange={(e) => setSelectedCurrency(e.target.value)}
                        className="currency-select"
                        disabled={saving}
                      >
                        {currencies.map((currency) => (
                          <option key={currency} value={currency}>
                            {currency}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => handleSaveCurrency(portfolio.id)}
                        className="btn btn-primary btn-sm"
                        disabled={saving}
                      >
                        {saving ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="btn btn-secondary btn-sm"
                        disabled={saving}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="currency-display-controls">
                      <span className="current-currency">{portfolio.currency || 'USD'}</span>
                      <button
                        onClick={() => handleEditPortfolio(portfolio)}
                        className="btn btn-secondary btn-sm"
                      >
                        Change Currency
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="settings-section glass">
          <div className="settings-section-header">
            <h2>Currency Information</h2>
            <p>Multi-currency support allows you to track international stocks and automatically convert values to your portfolio's base currency.</p>
          </div>
          <div className="info-content">
            <ul>
              <li><strong>Exchange Rates:</strong> Historical exchange rates are fetched from Yahoo Finance</li>
              <li><strong>Transaction Processing:</strong> Each transaction is converted using the rate from the transaction date</li>
              <li><strong>Supported Currencies:</strong> {currencies.length} currencies available</li>
              <li><strong>Automatic Conversion:</strong> Stock currencies are determined during stock verification</li>
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
};