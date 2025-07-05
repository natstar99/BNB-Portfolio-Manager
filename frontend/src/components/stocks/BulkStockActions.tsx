import React, { useState } from 'react';

interface BulkActionsProps {
  selectedStocks: number[];
  totalStocks: number;
  onBulkVerify: (stockIds: number[]) => Promise<void>;
  onBulkMarkDelisted: (stockIds: number[]) => Promise<void>;
  onBulkReset: (stockIds: number[]) => Promise<void>;
  onClearSelection: () => void;
  loading?: boolean;
}

export const BulkStockActions: React.FC<BulkActionsProps> = ({
  selectedStocks,
  totalStocks,
  onBulkVerify,
  onBulkMarkDelisted,
  onBulkReset,
  onClearSelection,
  loading = false,
}) => {
  const [action, setAction] = useState<'verify' | 'inactive' | 'reset' | ''>('');
  const [executing, setExecuting] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);

  const handleActionSelect = (selectedAction: 'verify' | 'inactive' | 'reset') => {
    setAction(selectedAction);
    setShowConfirmation(true);
  };

  const executeAction = async () => {
    if (!action || selectedStocks.length === 0) return;

    setExecuting(true);
    try {
      switch (action) {
        case 'verify':
          await onBulkVerify(selectedStocks);
          break;
        case 'inactive':
          await onBulkMarkDelisted(selectedStocks);
          break;
        case 'reset':
          await onBulkReset(selectedStocks);
          break;
      }
      onClearSelection();
      setShowConfirmation(false);
      setAction('');
    } catch (error) {
      console.error('Bulk action failed:', error);
    } finally {
      setExecuting(false);
    }
  };

  const cancelAction = () => {
    setShowConfirmation(false);
    setAction('');
  };

  const getActionDescription = () => {
    switch (action) {
      case 'verify':
        return {
          title: 'Verify Selected Stocks',
          description: `This will attempt to verify ${selectedStocks.length} stock${selectedStocks.length !== 1 ? 's' : ''} by checking their symbols against Yahoo Finance. Verified stocks will have their information updated.`,
          icon: (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>
          ),
          confirmText: 'Verify Stocks',
          confirmClass: 'btn-primary'
        };
      case 'inactive':
        return {
          title: 'Mark as Inactive',
          description: `This will mark ${selectedStocks.length} stock${selectedStocks.length !== 1 ? 's' : ''} as inactive. Inactive stocks will no longer be verified against Yahoo Finance.`,
          icon: (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
          ),
          confirmText: 'Mark as Inactive',
          confirmClass: 'btn-warning'
        };
      case 'reset':
        return {
          title: 'Reset Verification Status',
          description: `This will reset the verification status of ${selectedStocks.length} stock${selectedStocks.length !== 1 ? 's' : ''} back to "pending". This allows you to re-verify them later.`,
          icon: (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="1,4 1,10 7,10"/>
              <path d="M3.51,15a9,9 0 1,0 2.13-9.36L1,10"/>
            </svg>
          ),
          confirmText: 'Reset Status',
          confirmClass: 'btn-outline'
        };
      default:
        return null;
    }
  };

  if (selectedStocks.length === 0) {
    return null;
  }

  if (showConfirmation) {
    const actionInfo = getActionDescription();
    if (!actionInfo) return null;

    return (
      <div className="bulk-actions-confirmation">
        <div className="confirmation-content">
          <div className="confirmation-header">
            {actionInfo.icon}
            <h3>{actionInfo.title}</h3>
          </div>
          <p className="confirmation-description">{actionInfo.description}</p>
          <div className="confirmation-actions">
            <button
              onClick={cancelAction}
              className="btn btn-outline"
              disabled={executing}
            >
              Cancel
            </button>
            <button
              onClick={executeAction}
              className={`btn ${actionInfo.confirmClass}`}
              disabled={executing}
            >
              {executing ? (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 12a9 9 0 11-6.219-8.56"/>
                  </svg>
                  Processing...
                </>
              ) : (
                actionInfo.confirmText
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bulk-actions-panel">
      <div className="selection-info">
        <div className="selection-count">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22,4 12,14.01 9,11.01"/>
          </svg>
          <span>
            {selectedStocks.length} of {totalStocks} stock{selectedStocks.length !== 1 ? 's' : ''} selected
          </span>
        </div>
        <button
          onClick={onClearSelection}
          className="clear-selection-btn"
          disabled={loading}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
          Clear
        </button>
      </div>

      <div className="bulk-action-buttons">
        <button
          onClick={() => handleActionSelect('verify')}
          className="bulk-action-btn verify-btn"
          disabled={loading}
          title="Verify selected stocks against Yahoo Finance"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22,4 12,14.01 9,11.01"/>
          </svg>
          Verify All
        </button>

        <button
          onClick={() => handleActionSelect('inactive')}
          className="bulk-action-btn inactive-btn"
          disabled={loading}
          title="Mark selected stocks as inactive"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          Mark Inactive
        </button>

        <button
          onClick={() => handleActionSelect('reset')}
          className="bulk-action-btn reset-btn"
          disabled={loading}
          title="Reset verification status to pending"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="1,4 1,10 7,10"/>
            <path d="M3.51,15a9,9 0 1,0 2.13-9.36L1,10"/>
          </svg>
          Reset Status
        </button>
      </div>
    </div>
  );
};