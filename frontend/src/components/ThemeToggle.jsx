import React from 'react';
import { Sun, Moon } from 'lucide-react';

export default function ThemeToggle({ theme, onToggle }) {
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      className="theme-toggle-btn"
      onClick={onToggle}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} theme`}
      title={`Switch to ${isDark ? 'light' : 'dark'} theme`}
    >
      <div className={`theme-icon-wrapper ${isDark ? 'is-dark' : 'is-light'}`}>
        {isDark ? (
          <Moon size={16} className="theme-icon moon" />
        ) : (
          <Sun size={16} className="theme-icon sun" />
        )}
      </div>
      <span className="theme-toggle-label">{isDark ? 'Dark' : 'Light'}</span>
    </button>
  );
}
