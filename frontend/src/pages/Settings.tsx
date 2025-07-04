import React from 'react';

export const Settings: React.FC = () => {
  return (
    <div className="page">
      <div className="page-header">
        <h1>Settings</h1>
        <p className="page-subtitle">Configure your portfolio preferences</p>
      </div>
      
      <div className="coming-soon glass">
        <div className="coming-soon-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v6m0 6v6"/>
            <path d="M1 12h6m6 0h6"/>
          </svg>
        </div>
        <h2>Settings & Preferences</h2>
        <p>Comprehensive settings including currency preferences, tax calculation methods, display options, and data export features are coming soon.</p>
      </div>
    </div>
  );
};