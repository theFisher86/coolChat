import React, { useState } from 'react';
import './LorebookStyles.css';

interface LorebookBulkActionsProps {
  selectedCount: number;
  onBulkDelete: () => Promise<void>;
  onBulkEdit: () => void;
  onClearSelection: () => void;
  onBulkTag?: (tag: string) => Promise<void>;
  onBulkMove?: (targetLorebookId: number) => Promise<void>;
}

export const LorebookBulkActions: React.FC<LorebookBulkActionsProps> = ({
  selectedCount,
  onBulkDelete,
  onBulkEdit,
  onClearSelection,
  onBulkTag,
  onBulkMove
}) => {
  const [bulkMode, setBulkMode] = useState<'idle' | 'editing' | 'deleting' | 'tagging'>('idle');
  const [tagInput, setTagInput] = useState('');

  if (selectedCount === 0) {
    return null;
  }

  const handleDelete = async () => {
    if (bulkMode !== 'deleting') {
      setBulkMode('deleting');
      return;
    }

    // Confirm deletion
    if (window.confirm(
      `Delete ${selectedCount} entry${selectedCount === 1 ? '' : 'ies'}? This action cannot be undone.`
    )) {
      try {
        await onBulkDelete();
        setBulkMode('idle');
      } catch (error) {
        console.error('Bulk delete failed:', error);
        setBulkMode('idle');
      }
    } else {
      setBulkMode('idle');
    }
  };

  const handleTagAdd = async () => {
    if (tagInput.trim() && onBulkTag) {
      try {
        await onBulkTag(tagInput.trim());
        setTagInput('');
      } catch (error) {
        console.error('Bulk tagging failed:', error);
      }
    }
  };

  const buttonClass = (mode: typeof bulkMode) =>
    bulkMode === mode ? 'active' : '';

  return (
    <div className="bulk-actions-panel">
      <div className="bulk-selection-info">
        <span className="selection-count">
          {selectedCount} entr{selectedCount === 1 ? 'y' : 'ies'} selected
        </span>
        <button
          onClick={onClearSelection}
          className="clear-selection-btn"
          title="Clear selection"
        >
          ✕
        </button>
      </div>

      <div className="bulk-action-buttons">
        {/* Bulk Actions */}
        <button
          onClick={() => setBulkMode('editing')}
          className={`bulk-action-btn edit-btn ${buttonClass('editing')}`}
          title="Bulk edit selected entries"
        >
          📝 Edit
        </button>

        {onBulkTag && (
          <button
            onClick={() => {}}
            className="bulk-action-btn tag-btn"
            title="Add tag to selected entries"
          >
            🏷️ Tag
          </button>
        )}

        {onBulkMove && (
          <button
            onClick={() => {}}
            className="bulk-action-btn move-btn"
            title="Move selected entries"
          >
            ↗️ Move
          </button>
        )}

        <button
          onClick={handleDelete}
          className={`bulk-action-btn delete-btn ${buttonClass('deleting')}`}
          title="Delete selected entries"
        >
          🗑️ {bulkMode === 'deleting' ? 'Confirm Delete' : 'Delete'}
        </button>
      </div>

      {/* Conditional Action Panels */}
      {bulkMode === 'editing' && (
        <BulkEditPanel
          selectedCount={selectedCount}
          onSave={() => {
            onBulkEdit();
            setBulkMode('idle');
          }}
          onCancel={() => setBulkMode('idle')}
        />
      )}

      {/* Tag Input */}
      {bulkMode === 'tagging' && onBulkTag && (
        <div className="bulk-tagging-panel">
          <div className="tag-input-group">
            <input
              type="text"
              placeholder="Add tag to selected entries..."
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleTagAdd();
                }
              }}
              autoFocus
            />
            <button
              onClick={handleTagAdd}
              disabled={!tagInput.trim()}
              className="add-tag-btn"
            >
              Add Tag
            </button>
            <button
              onClick={() => {
                setBulkMode('idle');
                setTagInput('');
              }}
              className="cancel-tag-btn"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Confirm Delete */}
      {bulkMode === 'deleting' && (
        <div className="bulk-delete-confirm">
          <div className="confirm-message">
            This will permanently delete {selectedCount} selected entr{selectedCount === 1 ? 'y' : 'ies'}.
            This action cannot be undone.
          </div>
          <div className="confirm-actions">
            <button
              onClick={handleDelete}
              className="confirm-delete-btn danger"
            >
              Yes, Delete All
            </button>
            <button
              onClick={() => setBulkMode('idle')}
              className="cancel-delete-btn"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

interface BulkEditPanelProps {
  selectedCount: number;
  onSave: () => void;
  onCancel: () => void;
}

const BulkEditPanel: React.FC<BulkEditPanelProps> = ({
  selectedCount,
  onSave,
  onCancel
}) => {
  const [field, setField] = useState<'logic' | 'trigger' | 'order' | 'addKeyword' | 'removeKeyword'>('logic');
  const [value, setValue] = useState<any>('');

  const handleSave = () => {
    // This would be passed up to the parent for actual state management
    onSave();
  };

  return (
    <div className="bulk-edit-panel">
      <div className="panel-header">
        <h3>Bulk Edit {selectedCount} Entr{selectedCount === 1 ? 'y' : 'ies'}</h3>
        <button onClick={onCancel} className="close-btn" title="Close bulk edit">×</button>
      </div>

      <div className="bulk-edit-content">
        {/* Field Selection */}
        <div className="field-selector">
          <label>Field to edit:</label>
          <select value={field} onChange={(e) => setField(e.target.value as typeof field)}>
            <option value="logic">Logic</option>
            <option value="trigger">Trigger</option>
            <option value="order">Order</option>
            <option value="addKeyword">Add Keyword</option>
            <option value="removeKeyword">Remove Keyword</option>
          </select>
        </div>

        {/* Value Input */}
        <div className="value-input">
          {field === 'logic' && (
            <select value={value || 'AND ANY'} onChange={(e) => setValue(e.target.value)}>
              <option value="AND ANY">AND ANY</option>
              <option value="AND ALL">AND ALL</option>
              <option value="NOT ANY">NOT ANY</option>
              <option value="NOT ALL">NOT ALL</option>
            </select>
          )}

          {field === 'trigger' && (
            <div className="range-input">
              <input
                type="range"
                min="0"
                max="100"
                step="10"
                value={value || 50}
                onChange={(e) => setValue(parseInt(e.target.value, 10))}
              />
              <span>{value || 50}%</span>
            </div>
          )}

          {field === 'order' && (
            <input
              type="number"
              value={value || 0}
              onChange={(e) => setValue(parseFloat(e.target.value))}
              step="0.1"
              placeholder="0.0"
            />
          )}

          {(field === 'addKeyword' || field === 'removeKeyword') && (
            <input
              type="text"
              value={value || ''}
              onChange={(e) => setValue(e.target.value)}
              placeholder="Enter keyword..."
            />
          )}
        </div>

        {/* Preview */}
        <div className="preview-section">
          <label>Preview:</label>
          <div className="preview-text">
            Set <strong>{field}</strong> to <strong>{value || 'value'}</strong> for selected entries
          </div>
        </div>
      </div>

      <div className="panel-actions">
        <button onClick={handleSave} className="primary">Apply Changes</button>
        <button onClick={onCancel} className="secondary">Cancel</button>
      </div>
    </div>
  );
};