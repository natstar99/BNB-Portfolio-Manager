import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: {
    value: number;
    percentage: number;
    isPositive: boolean;
  };
  icon?: React.ReactNode;
  className?: string;
  loading?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  icon,
  className = '',
  loading = false
}) => {
  if (loading) {
    return (
      <div className={`metric-card loading-shimmer ${className}`}>
        <div style={{ height: '120px' }}></div>
      </div>
    );
  }

  return (
    <div className={`metric-card ${className}`}>
      <div className="metric-header">
        <span className="metric-label">{title}</span>
        {icon && <span className="metric-icon">{icon}</span>}
      </div>
      
      <div className="metric-value">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      
      {change && (
        <div className={`metric-change ${change.isPositive ? 'positive' : 'negative'}`}>
          <span className="change-indicator">
            {change.isPositive ? '↗' : '↘'}
          </span>
          <span className="change-value">
            {Math.abs(change.value || 0).toLocaleString()} ({Math.abs(change.percentage || 0).toFixed(2)}%)
          </span>
        </div>
      )}
    </div>
  );
};