import React, { useState, useEffect } from 'react';
import { usePortfolios } from '../hooks/usePortfolios';
import { Portfolio } from '../shared/types';

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
        setMessage({ type: 'success', text: 'Portfolio currency updated successfully' });
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
        <h1>Settings</h1>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Settings</h1>
      <p>Configure your portfolio preferences</p>

      {message && (
        <div className={`message ${message.type}`} style={{ padding: '1rem', marginBottom: '1rem' }}>
          {message.text}
        </div>
      )}

      <h2>Portfolio Currency Settings</h2>
      <p>Set the base currency for each portfolio.</p>

      {portfolios.length === 0 ? (
        <p>No portfolios found. Create a portfolio first.</p>
      ) : (
        <table className="table" style={{ marginBottom: '2rem' }}>
          <thead>
            <tr>
              <th>Portfolio</th>
              <th>Currency</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {portfolios.map((portfolio) => (
              <tr key={portfolio.id}>
                <td>
                  <strong>{portfolio.name}</strong>
                  {portfolio.description && <br />}
                  {portfolio.description && <small>{portfolio.description}</small>}
                </td>
                <td>
                  {editingPortfolio === portfolio.id ? (
                    <select
                      value={selectedCurrency}
                      onChange={(e) => setSelectedCurrency(e.target.value)}
                      disabled={saving}
                    >
                      {currencies.map((currency) => (
                        <option key={currency} value={currency}>
                          {currency}
                        </option>
                      ))}
                    </select>
                  ) : (
                    portfolio.currency || 'USD'
                  )}
                </td>
                <td>
                  {editingPortfolio === portfolio.id ? (
                    <>
                      <button
                        onClick={() => handleSaveCurrency(portfolio.id)}
                        disabled={saving}
                        style={{ marginRight: '0.5rem' }}
                      >
                        {saving ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        disabled={saving}
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <button onClick={() => handleEditPortfolio(portfolio)}>
                      Change Currency
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>Currency Information</h2>
      <ul>
        <li>Exchange rates are fetched from Yahoo Finance</li>
        <li>Transactions are converted using the rate from the transaction date</li>
        <li>Supported currencies: {currencies.length} available</li>
        <li>Stock currencies are determined during stock verification</li>
      </ul>
    </div>
  );
};
