import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { usePortfolios } from '../hooks/usePortfolios';
import { formatCurrency } from '../shared/formatters';

export const MainMenu = () => {
  const { portfolios, createPortfolio, loading, error } = usePortfolios();
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState('');

  const handleCreate = async () => {
    if (!name.trim()) return;
    await createPortfolio(name.trim(), 'USD');
    setName('');
    setShowModal(false);
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <main>
      <h1>Portfolios</h1>

      {/* Actions */}
      <div style={{marginBottom: '2rem'}}>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          Create Portfolio
        </button>
      </div>

      {/* Portfolio List */}
      {portfolios.length === 0 ? (
        <p>No portfolios yet. Create one to get started.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Value</th>
              <th>P/L</th>
              <th>Positions</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {portfolios.map(p => (
              <tr key={p.id}>
                <td>{p.name}</td>
                <td>{formatCurrency(p.total_value || 0)}</td>
                <td className={(p.total_pl || 0) >= 0 ? 'positive' : 'negative'}>
                  {formatCurrency(p.total_pl || 0)}
                </td>
                <td>{p.stock_count || 0}</td>
                <td>
                  <Link to={`/portfolio/${p.id}/dashboard`}>Open</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Create Modal */}
      {showModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          onClick={() => setShowModal(false)}
        >
          <div
            className="card"
            style={{minWidth: '400px', padding: '2rem'}}
            onClick={e => e.stopPropagation()}
          >
            <h3>Create Portfolio</h3>

            <label className="form-label">Name</label>
            <input
              className="form-input"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="My Portfolio"
            />

            <div style={{marginTop: '1rem', display: 'flex', gap: '1rem'}}>
              <button className="btn-secondary" onClick={() => setShowModal(false)}>
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleCreate}
                disabled={!name.trim()}
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
};
