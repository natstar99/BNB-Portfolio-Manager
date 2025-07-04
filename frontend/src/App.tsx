import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { Layout } from './components/Layout';
import { MainMenu } from './pages/MainMenu';
import { PortfolioDashboard } from './pages/PortfolioDashboard';
import { Analytics } from './pages/Analytics';
import { Transactions } from './pages/Transactions';
import { TransactionImport } from './pages/TransactionImport';
import { StockManagement } from './pages/StockManagement';
import { Settings } from './pages/Settings';
import './styles/globals.css';
import './styles/layout.css';
import './App.css';

function App() {
  return (
    <ThemeProvider>
      <Router>
        <div className="App">
          <Layout>
            <Routes>
              {/* Main Menu - Portfolio Selection */}
              <Route path="/" element={<MainMenu />} />
              
              {/* Portfolio-Specific Routes */}
              <Route path="/portfolio/:portfolioId/dashboard" element={<PortfolioDashboard />} />
              <Route path="/portfolio/:portfolioId/transactions" element={<Transactions />} />
              <Route path="/portfolio/:portfolioId/analytics" element={<Analytics />} />
              <Route path="/portfolio/:portfolioId/import" element={<TransactionImport />} />
              <Route path="/portfolio/:portfolioId/stocks" element={<StockManagement />} />
              <Route path="/portfolio/:portfolioId/positions" element={<div className="page"><div className="page-header"><div className="header-content"><h1>Positions</h1><p className="page-subtitle">View and manage your portfolio positions</p></div></div><div className="coming-soon"><div className="coming-soon-icon"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg></div><h2>Portfolio Positions</h2><p>This section will show detailed position information and allow portfolio management.</p></div></div>} />
              
              {/* Global Routes */}
              <Route path="/settings" element={<Settings />} />
              
              {/* Legacy Routes - Redirect to Main Menu */}
              <Route path="/portfolios" element={<MainMenu />} />
              <Route path="/dashboard" element={<MainMenu />} />
              <Route path="/transactions" element={<MainMenu />} />
              <Route path="/analytics" element={<MainMenu />} />
              
              {/* Stocks Management (Global) */}
              <Route path="/stocks" element={<div className="page"><div className="page-header"><div className="header-content"><h1>Stock Database</h1><p className="page-subtitle">Manage your stock database and corporate actions</p></div></div><div className="coming-soon"><div className="coming-soon-icon"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/></svg></div><h2>Stock Management</h2><p>This section will allow you to manage your stock database, handle stock splits, dividends, and verify stock data with Yahoo Finance.</p></div></div>} />
            </Routes>
          </Layout>
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;