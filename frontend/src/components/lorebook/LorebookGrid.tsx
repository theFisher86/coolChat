import React, { useState } from 'react';
import { Lorebook } from '../../stores/lorebookStore';
import './LorebookStyles.css';

interface LorebookGridProps {
  lorebooks: Lorebook[];
  viewMode: 'cards' | 'table';
  selectedLorebookId?: number;
  onSelectLorebook: (lorebook: Lorebook | null) => void;
  onEditLorebook: (lorebook: Lorebook) => void;
  onDeleteLorebook: (id: number) => void;
  onCreateLorebook: (data: Partial<Lorebook>) => void;
}

export const LorebookGrid: React.FC<LorebookGridProps> = ({
  lorebooks,
  viewMode,
  selectedLorebookId,
  onSelectLorebook,
  onEditLorebook,
  onDeleteLorebook,
  onCreateLorebook
}) => {
  const [quickCreateName, setQuickCreateName] = useState('');
  const [quickCreateDesc, setQuickCreateDesc] = useState('');

  const handleQuickCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickCreateName.trim()) return;

    await onCreateLorebook({
      name: quickCreateName,
      description: quickCreateDesc,
      entries: []
    } as any);

    setQuickCreateName('');
    setQuickCreateDesc('');
  };

  if (lorebooks.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">📚</div>
        <h3>No Lorebooks Yet</h3>
        <p>Create your first lorebook to get started with organizing your game world.</p>

        {/* Quick Create Form */}
        <form onSubmit={handleQuickCreate} className="quick-create-form">
          <input
            type="text"
            placeholder="Lorebook name"
            value={quickCreateName}
            onChange={(e) => setQuickCreateName(e.target.value)}
            required
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={quickCreateDesc}
            onChange={(e) => setQuickCreateDesc(e.target.value)}
          />
          <button type="submit" className="primary">Create Lorebook</button>
        </form>
      </div>
    );
  }

  if (viewMode === 'table') {
    return (
      <div className="lorebook-table-container">
        <table className="lorebook-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
              <th>Entries</th>
              <th>Last Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {lorebooks.map((lorebook) => (
              <tr
                key={lorebook.id}
                className={selectedLorebookId === lorebook.id ? 'selected' : ''}
                onClick={() => onSelectLorebook(lorebook)}
              >
                <td className="lorebook-name">{lorebook.name}</td>
                <td className="lorebook-description">{lorebook.description || '—'}</td>
                <td className="entry-count">{lorebook.entry_count}</td>
                <td className="updated-at">
                  {new Date(lorebook.updated_at).toLocaleDateString()}
                </td>
                <td className="actions">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onEditLorebook(lorebook);
                    }}
                    title="Edit lorebook"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteLorebook(lorebook.id);
                    }}
                    title="Delete lorebook"
                    className="delete-btn"
                  >
                    🗑️
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Card view
  return (
    <div className="lorebook-grid">
      {lorebooks.map((lorebook) => (
        <LorebookCard
          key={lorebook.id}
          lorebook={lorebook}
          isSelected={selectedLorebookId === lorebook.id}
          onSelect={() => onSelectLorebook(lorebook)}
          onEdit={() => onEditLorebook(lorebook)}
          onDelete={() => onDeleteLorebook(lorebook.id)}
        />
      ))}

      {/* Quick Create Card */}
      <div className="lorebook-card quick-create-card">
        <div className="card-header">
          <div className="card-icon add-icon">➕</div>
          <h3>Create New</h3>
        </div>
        <div className="card-content">
          <form onSubmit={handleQuickCreate}>
            <input
              type="text"
              placeholder="Lorebook title"
              value={quickCreateName}
              onChange={(e) => setQuickCreateName(e.target.value)}
              required
            />
            <textarea
              placeholder="Brief description..."
              value={quickCreateDesc}
              onChange={(e) => setQuickCreateDesc(e.target.value)}
              rows={2}
            />
            <button type="submit" className="primary create-btn">
              Create Lorebook
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

interface LorebookCardProps {
  lorebook: Lorebook;
  isSelected: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

const LorebookCard: React.FC<LorebookCardProps> = ({
  lorebook,
  isSelected,
  onSelect,
  onEdit,
  onDelete
}) => {
  const [showActions, setShowActions] = useState(false);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) {
      return 'Today';
    } else if (diffDays === 2) {
      return 'Yesterday';
    } else if (diffDays <= 7) {
      return `${diffDays - 1} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  return (
    <div
      className={`lorebook-card ${isSelected ? 'selected' : ''} ${showActions ? 'show-actions' : ''}`}
      onClick={onSelect}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="card-header">
        <div className="card-icon">📚</div>
        <h3 className="card-title">{lorebook.name}</h3>
        <div className="card-actions">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            title="Edit lorebook"
          >
            ⚙️
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (window.confirm(`Delete "${lorebook.name}"?`)) {
                onDelete();
              }
            }}
            title="Delete lorebook"
            className="delete-btn"
          >
            🗑️
          </button>
        </div>
      </div>

      <div className="card-content">
        <p className="card-description">
          {lorebook.description || 'No description'}
        </p>
        <div className="card-stats">
          <div className="stat">
            <span className="stat-label">Entries:</span>
            <span className="stat-value">{lorebook.entry_count}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Updated:</span>
            <span className="stat-value">{formatDate(lorebook.updated_at)}</span>
          </div>
        </div>
      </div>

      {isSelected && (
        <div className="selection-indicator">
          ✓ Selected
        </div>
      )}
    </div>
  );
};