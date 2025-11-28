import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';

export const ThemeToggle = () => {
  const { theme, setTheme } = useTheme();

  return (
    <select
      value={theme}
      onChange={(e) => setTheme(e.target.value as 'light' | 'dark' | 'pipboy' | 'plain' | 'terminal')}
      style={{
        background: 'var(--color-surface)',
        color: 'var(--color-text-primary)',
        border: '1px solid var(--color-border)',
        padding: '0.5rem',
        borderRadius: '4px'
      }}
    >
      <option value="light">Light</option>
      <option value="dark">Dark</option>
      <option value="pipboy">Pipboy</option>
      <option value="terminal">Terminal</option>
      <option value="plain">Plain</option>
    </select>
  );
};
