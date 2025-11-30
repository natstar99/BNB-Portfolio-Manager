import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { formatCurrency, formatPercent } from '../shared/formatters';
import { Portfolio, Position } from '../shared/types';

export const PortfolioDashboard: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const navigate = useNavigate();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingMarketData, setUpdatingMarketData] = useState(false);

  useEffect(() => {
    if (!portfolioId) {
      navigate('/');
      return;
    }
    fetchPortfolioData();
  }, [portfolioId, navigate]);

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      setError(null);

      const analyticsResponse = await fetch(`/api/portfolios/${portfolioId}/analytics`);
      if (!analyticsResponse.ok) {
        if (analyticsResponse.status === 404) {
          navigate('/');
          return;
        }
        throw new Error('Failed to fetch portfolio analytics');
      }

      const analyticsData = await analyticsResponse.json();

      if (analyticsData.success && analyticsData.data) {
        setPortfolio(analyticsData.data.portfolio);
        setPositions(analyticsData.data.positions || []);
      } else {
        throw new Error(analyticsData.error || 'Invalid response format');
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Portfolio data fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const updateMarketData = async () => {
    if (!portfolioId) return;

    try {
      setUpdatingMarketData(true);

      const response = await fetch(`/api/market-data/update-portfolio/${portfolioId}`, {
        method: 'POST'
      });

      const result = await response.json();

      if (result.success) {
        await fetchPortfolioData();
      } else {
        setError(result.error || 'Failed to update market data');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update market data');
    } finally {
      setUpdatingMarketData(false);
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
        <button onClick={() => navigate('/')}>Back to Portfolios</button>
        <button onClick={fetchPortfolioData}>Try Again</button>
      </div>
    );
  }

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>{portfolio.name}</h1>
        <button onClick={updateMarketData} disabled={updatingMarketData} className="btn btn-warning">
          {updatingMarketData ? 'Updating...' : 'Update Market Data'}
        </button>
      </div>

      {/* Portfolio Summary */}
      <h2>Summary</h2>
      <table className="table" style={{ marginBottom: '2rem' }}>
        <tbody>
          <tr>
            <td>Portfolio Value</td>
            <td>{formatCurrency(portfolio.total_value || 0, portfolio?.currency)}</td>
          </tr>
          <tr>
            <td>Total Cost</td>
            <td>{formatCurrency(portfolio.total_cost || 0, portfolio?.currency)}</td>
          </tr>
          <tr>
            <td>Total Return</td>
            <td className={(portfolio.total_pl || 0) > 0 ? 'metric-positive' : (portfolio.total_pl || 0) < 0 ? 'metric-negative' : 'metric-zero'}>
              {formatCurrency(portfolio.total_pl || 0, portfolio?.currency)} ({formatPercent(portfolio.total_pl_percent || 0)})
            </td>
          </tr>
          <tr>
            <td>Day Change</td>
            <td className={(portfolio.day_change || 0) > 0 ? 'metric-positive' : (portfolio.day_change || 0) < 0 ? 'metric-negative' : 'metric-zero'}>
              {formatCurrency(portfolio.day_change || 0, portfolio?.currency)} ({formatPercent(portfolio.day_change_percent || 0)})
            </td>
          </tr>
          <tr>
            <td>Active Positions</td>
            <td>{portfolio.stock_count || 0}</td>
          </tr>
        </tbody>
      </table>

      {/* Positions */}
      <h2>Positions</h2>
      {positions.length === 0 ? (
        <p>No positions yet. <Link to={`/portfolio/${portfolioId}/import`}>Import transactions</Link> to get started.</p>
      ) : (
        <table className="table" style={{ marginBottom: '2rem' }}>
          <thead>
            <tr>
              <th>Stock</th>
              <th>Units</th>
              <th>Avg. Cost</th>
              <th>Current Price</th>
              <th>Market Value</th>
              <th>Total Cost</th>
              <th>Gain/Loss</th>
              <th>%</th>
              <th>Day Change</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <tr key={position.id} onClick={() => navigate(`/portfolio/${portfolioId}/transactions?symbol=${position.symbol}`)} style={{ cursor: 'pointer' }}>
                <td>
                  <strong>{position.symbol}</strong>
                  <br />
                  <small>{position.company_name || 'Unknown Company'}</small>
                </td>
                <td>{position.quantity.toLocaleString()}</td>
                <td>{formatCurrency(position.avg_cost, portfolio?.currency)}</td>
                <td>{formatCurrency(position.current_price, portfolio?.currency)}</td>
                <td>{formatCurrency(position.market_value, portfolio?.currency)}</td>
                <td>{formatCurrency(position.avg_cost * position.quantity, portfolio?.currency)}</td>
                <td className={position.gain_loss > 0 ? 'metric-positive' : position.gain_loss < 0 ? 'metric-negative' : 'metric-zero'}>
                  {formatCurrency(position.gain_loss, portfolio?.currency)}
                </td>
                <td className={position.gain_loss_percent > 0 ? 'metric-positive' : position.gain_loss_percent < 0 ? 'metric-negative' : 'metric-zero'}>
                  {formatPercent(position.gain_loss_percent)}
                </td>
                <td className={position.day_change > 0 ? 'metric-positive' : position.day_change < 0 ? 'metric-negative' : 'metric-zero'}>
                  {formatCurrency(position.day_change, portfolio?.currency)}
                  <br />
                  <small>{formatPercent(position.day_change_percent)}</small>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
