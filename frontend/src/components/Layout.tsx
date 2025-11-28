import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ThemeToggle } from './ui/ThemeToggle';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  // Extract portfolioId from pathname
  const pathMatch = location.pathname.match(/^\/portfolio\/(\d+)/);
  const portfolioId = pathMatch ? pathMatch[1] : null;

  // Determine if we're in portfolio context
  const isInPortfolioContext = location.pathname.startsWith('/portfolio/');

  // Portfolio context navigation
  const portfolioNavigation = portfolioId ? [
    { name: 'Portfolios', href: '/' },
    { name: 'Summary', href: `/portfolio/${portfolioId}/dashboard` },
    { name: 'Manage Stocks', href: `/portfolio/${portfolioId}/stocks` },
    { name: 'Transactions', href: `/portfolio/${portfolioId}/transactions` },
    { name: 'Charts', href: `/portfolio/${portfolioId}/analytics` },
    { name: 'Import Data', href: `/portfolio/${portfolioId}/import` },
    { name: 'Settings', href: '/settings' }
  ] : [];

  // Main Menu navigation (when not in portfolio context)
  const mainMenuNavigation = [
    { name: 'Portfolios', href: '/' },
    { name: 'Settings', href: '/settings' }
  ];

  // Choose navigation based on context
  const navigation = (isInPortfolioContext && portfolioId) ? portfolioNavigation : mainMenuNavigation;

  return (
    <div className="layout">
      {/* Top Navigation */}
      <header className="top-nav glass">
        <div className="nav-container">
          {/* Logo */}
          <div className="logo">
            <span style={{fontSize: '14px', fontWeight: '600'}}>BNB PORTFOLIO MANAGER</span>
          </div>

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
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* Theme Toggle */}
          <div className="nav-actions">
            <ThemeToggle />
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