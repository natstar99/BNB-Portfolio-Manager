import React from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { ThemeToggle } from './ui/ThemeToggle';
import { usePortfolios } from '../hooks/usePortfolios';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { portfolioId } = useParams();
  const { portfolios, selectedPortfolio, selectPortfolio, hasPortfolios, isNewUser, loading } = usePortfolios();
  
  // Determine if we're in portfolio context
  const isInPortfolioContext = location.pathname.startsWith('/portfolio/');
  const currentPortfolio = portfolios.find(p => p.id === parseInt(portfolioId || '0'));

  // Main Menu navigation (when not in portfolio context)
  const mainMenuNavigation = [
    { 
      name: 'Home', 
      href: '/', 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9,22 9,12 15,12 15,22"/>
        </svg>
      )
    },
    { 
      name: 'Settings', 
      href: '/settings', 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="3"/>
          <path d="M12 1v6m0 6v6"/>
          <path d="M1 12h6m6 0h6"/>
        </svg>
      )
    },
    { 
      name: 'Stock Database', 
      href: '/stocks', 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
        </svg>
      )
    }
  ];

  // Portfolio context navigation (when in portfolio context)
  const portfolioNavigation = portfolioId ? [
    { 
      name: 'Dashboard', 
      href: `/portfolio/${portfolioId}/dashboard`, 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="7" height="7"/>
          <rect x="14" y="3" width="7" height="7"/>
          <rect x="14" y="14" width="7" height="7"/>
          <rect x="3" y="14" width="7" height="7"/>
        </svg>
      )
    },
    { 
      name: 'Transactions', 
      href: `/portfolio/${portfolioId}/transactions`, 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14,2 14,8 20,8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10,9 9,9 8,9"/>
        </svg>
      )
    },
    { 
      name: 'Import', 
      href: `/portfolio/${portfolioId}/import`, 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17,8 12,3 7,8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
      )
    },
    { 
      name: 'Stocks', 
      href: `/portfolio/${portfolioId}/stocks`, 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
        </svg>
      )
    }
  ] : [];

  // Choose navigation based on context
  const navigation = (isInPortfolioContext && portfolioId) ? portfolioNavigation : mainMenuNavigation;

  return (
    <div className="layout">
      {/* Top Navigation */}
      <header className="top-nav glass">
        <div className="nav-container">
          {/* Logo */}
          <Link to="/" className="logo">
            <div className="logo-icon">
              <svg width="28" height="28" viewBox="0 0 100 100" fill="none">
                <circle cx="50" cy="50" r="45" fill="url(#logoGradient)" />
                <path d="M30 35 L45 50 L70 25" stroke="white" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M30 55 L45 70 L70 45" stroke="white" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
                <defs>
                  <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="var(--color-primary)" />
                    <stop offset="100%" stopColor="var(--color-secondary)" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div className="logo-text">
              <h1>BNB Portfolio</h1>
              <span>Bear No Bears</span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="nav-links">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`nav-link ${isActive ? 'active' : ''}`}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span className="nav-text">{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Portfolio Context Indicator */}
          {isInPortfolioContext && currentPortfolio && (
            <div className="portfolio-context">
              <div className="portfolio-indicator">
                <div className="portfolio-icon">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                  </svg>
                </div>
                <span className="portfolio-name">{currentPortfolio.name}</span>
              </div>
              <Link to="/" className="btn-switch-portfolio">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="9,10 4,15 9,20"/>
                  <path d="M20,4 L20,7 A4,4 0 0,1 16,11 L4,11"/>
                </svg>
              </Link>
            </div>
          )}

          {/* User Actions */}
          <div className="nav-actions">
            <ThemeToggle />
            <div className="user-menu">
              <div className="user-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        <div className="content-container">
          {children}
        </div>
      </main>
    </div>
  );
};