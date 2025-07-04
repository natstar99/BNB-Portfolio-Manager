import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme, isDark } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="theme-toggle"
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      <div className="theme-toggle-track">
        <div className={`theme-toggle-thumb ${isDark ? 'dark' : 'light'}`}>
          {isDark ? '🌙' : '☀️'}
        </div>
      </div>
    </button>
  );
};

// Add these styles to your CSS
const styles = `
.theme-toggle {
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-xs);
}

.theme-toggle-track {
  width: 50px;
  height: 26px;
  background: var(--glass-background);
  border: 1px solid var(--color-border);
  border-radius: 13px;
  position: relative;
  transition: all var(--transition-normal);
  backdrop-filter: var(--glass-backdrop);
}

.theme-toggle-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  position: absolute;
  top: 2px;
  transition: all var(--transition-normal);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  box-shadow: var(--shadow-sm);
}

.theme-toggle-thumb.light {
  left: 2px;
}

.theme-toggle-thumb.dark {
  left: 26px;
}

.theme-toggle:hover .theme-toggle-track {
  background: var(--color-surface-secondary);
}
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style');
  styleSheet.textContent = styles;
  document.head.appendChild(styleSheet);
}