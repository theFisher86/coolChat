import React, { useState, useEffect } from 'react';
import { LoreEntry, useLorebookStore } from '../../stores/lorebookStore';
import { LoreEntryEditorModal } from './LoreEntryEditorModal';

export interface LoreEntryManagerProps {
  onEntryClick?: (entry: LoreEntry) => void;
}

export const LoreEntryManager: React.FC<LoreEntryManagerProps> = ({
  onEntryClick
}) => {
  const store = useLorebookStore();
  const [selectedEntry, setSelectedEntry] = useState<LoreEntry | null>(null);
  const [bulkSelectedIds, setBulkSelectedIds] = useState<Set<number>>(new Set());
  const [sortBy, setSortBy] = useState<'title' | 'created' | 'updated' | 'trigger' | 'order'>('order');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [filterText, setFilterText] = useState('');
  const [currentPage, setCurrentPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);

  useEffect(() => {
    // Refresh entries when selected lorebook changes
    if (store.selectedLorebook) {
      store.refreshLoreEntries();
    }
  }, [store.selectedLorebook?.id]); // Use specific property to avoid infinite loop

  const entries = React.useMemo(() => {
    let filtered = store.loreEntries;

    // Text filter
    if (filterText) {
      const text = filterText.toLowerCase();
      filtered = filtered.filter(entry =>
        entry.title?.toLowerCase().includes(text) ||
        entry.content?.toLowerCase().includes(text) ||
        entry.keywords?.some(kw => kw.toLowerCase().includes(text)) ||
        entry.secondary_keywords?.some(kw => kw.toLowerCase().includes(text))
      );
    }

    // Sorting
    filtered = filtered.sort((a, b) => {
      let aValue: any, bValue: any;

      switch (sortBy) {
        case 'title':
          aValue = a.title?.toLowerCase() || '';
          bValue = b.title?.toLowerCase() || '';
          break;
        case 'created':
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case 'updated':
          aValue = new Date(a.updated_at).getTime();
          bValue = new Date(b.updated_at).getTime();
          break;
        case 'trigger':
          aValue = a.trigger || 0;
          bValue = b.trigger || 0;
          break;
        case 'order':
          aValue = a.order || 0;
          bValue = b.order || 0;
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [store.loreEntries, filterText, sortBy, sortDirection]);

  // Pagination
  const paginatedEntries = React.useMemo(() => {
    const start = currentPage * pageSize;
    return entries.slice(start, start + pageSize);
  }, [entries, currentPage, pageSize]);

  const totalPages = Math.ceil(entries.length / pageSize);

  const handleSort = (field: typeof sortBy) => {
    if (sortBy === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortDirection('desc');
    }
  };

  const handleEntrySelect = (entry: LoreEntry, event: React.MouseEvent) => {
    if (event.ctrlKey || event.metaKey) {
      // Bulk select with Ctrl/Cmd
      setBulkSelectedIds(prev => {
        const newSet = new Set(prev);
        if (newSet.has(entry.id)) {
          newSet.delete(entry.id);
        } else {
          newSet.add(entry.id);
        }
        return newSet;
      });
    } else {
      // Single select
      if (bulkSelectedIds.size > 0) {
        // Clear bulk selection if clicking without modifier
        setBulkSelectedIds(new Set([entry.id]));
      } else {
        setSelectedEntry(entry);
        onEntryClick?.(entry);
      }
    }
  };

  const handleEditEntry = (entry: LoreEntry) => {
    setSelectedEntry(entry);
    store.setShowEditor(true, entry);
  };

  const handleCreateEntry = () => {
    setSelectedEntry(null);
    store.setShowEditor(true, null);
  };

  const handleDeleteEntry = async (entry: LoreEntry) => {
    if (window.confirm(`Delete "${entry.title || 'Untitled Entry'}"? This action cannot be undone.`)) {
      try {
        await store.deleteLoreEntryAction(entry.id);
        setBulkSelectedIds(prev => {
          const newSet = new Set(prev);
          newSet.delete(entry.id);
          return newSet;
        });
      } catch (error) {
        console.error('Failed to delete entry:', error);
      }
    }
  };

  const handleBulkDelete = async () => {
    if (bulkSelectedIds.size === 0) return;

    if (window.confirm(`Delete ${bulkSelectedIds.size} selected entries? This action cannot be undone.`)) {
      try {
        await store.bulkDeleteEntries();
        setBulkSelectedIds(new Set());
      } catch (error) {
        console.error('Failed to delete entries:', error);
      }
    }
  };

  const clearFilters = () => {
    setFilterText('');
    setCurrentPage(0);
  };

  const clearSelection = () => {
    setBulkSelectedIds(new Set());
    setSelectedEntry(null);
  };

  if (!store.selectedLorebook) {
    return (
      <div className="lore-entry-manager no-selection">
        <div className="empty-state">
          <div className="empty-icon">📖</div>
          <h3>No Lorebook Selected</h3>
          <p>Select a lorebook from the list to manage its entries.</p>
        </div>
      </div>
    );
  }

  if (store.entryLoading && store.loreEntries.length === 0) {
    return (
      <div className="lore-entry-manager loading">
        <div className="loading-spinner" />
        <p>Loading entries...</p>
      </div>
    );
  }

  return (
    <div className="lore-entry-manager">
      <div className="entry-manager-header">
        <div className="entry-info">
          <h2>{store.selectedLorebook.name} - {store.loreEntries.length} entries</h2>
          {bulkSelectedIds.size > 0 && (
            <span className="bulk-select-count">
              {bulkSelectedIds.size} selected
            </span>
          )}
        </div>
        <div className="header-actions">
          <input
            type="text"
            placeholder="Filter entries..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="filter-input"
          />
          {filterText && (
            <button onClick={clearFilters} className="clear-filter-btn">
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Bulk Actions */}
      {bulkSelectedIds.size > 0 && (
        <div className="bulk-actions-bar">
          <button
            onClick={handleBulkDelete}
            className="bulk-delete-btn"
          >
            🗑️ Delete Selected ({bulkSelectedIds.size})
          </button>
          <button
            onClick={clearSelection}
            className="cancel-bulk-btn"
          >
            Cancel Selection
          </button>
        </div>
      )}

      {/* Sort Controls */}
      <div className="sort-controls">
        <span>Sort by:</span>
        {(['title', 'created', 'updated', 'trigger', 'order'] as const).map(field => (
          <button
            key={field}
            className={`sort-btn ${sortBy === field ? 'active' : ''}`}
            onClick={() => handleSort(field)}
          >
            {field.charAt(0).toUpperCase() + field.slice(1)}
            {sortBy === field && (
              <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
            )}
          </button>
        ))}
      </div>

      {/* Entry Table */}
      <div className="entry-table-container">
        <table className="entry-table">
          <thead>
            <tr>
              <th className="checkbox-col">
                <input
                  type="checkbox"
                  checked={bulkSelectedIds.size === paginatedEntries.length && paginatedEntries.length > 0}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setBulkSelectedIds(new Set(paginatedEntries.map(entry => entry.id)));
                    } else {
                      clearSelection();
                    }
                  }}
                />
              </th>
              <th>Title</th>
              <th>Keywords</th>
              <th>Logic</th>
              <th>Trigger</th>
              <th>Order</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedEntries.map(entry => (
              <tr
                key={entry.id}
                className={`${bulkSelectedIds.has(entry.id) ? 'selected' : ''} ${selectedEntry?.id === entry.id ? 'active' : ''}`}
                onClick={(e) => handleEntrySelect(entry, e)}
              >
                <td className="checkbox-col">
                  <input
                    type="checkbox"
                    checked={bulkSelectedIds.has(entry.id)}
                    onChange={(e) => {
                      e.stopPropagation();
                      handleEntrySelect(entry, { ...e, ctrlKey: true } as any);
                    }}
                  />
                </td>
                <td className="title-col">
                  {entry.title || 'Untitled'}
                  {entry.title && (
                    <div className="content-preview">
                      {entry.content?.substring(0, 50)}...
                    </div>
                  )}
                </td>
                <td className="keywords-col">
                  {(entry.keywords || []).slice(0, 3).join(', ')}
                  {(entry.keywords || []).length > 3 && ` +${(entry.keywords || []).length - 3}`}
                  {(entry.secondary_keywords || []).length > 0 && (
                    <div className="secondary-keywords">
                      {(entry.secondary_keywords || []).slice(0, 2).join(', ')}
                      {(entry.secondary_keywords || []).length > 2 && '...'}
                    </div>
                  )}
                </td>
                <td className="logic-col">{entry.logic || 'AND ANY'}</td>
                <td className="trigger-col">{entry.trigger || 100}%</td>
                <td className="order-col">{entry.order || 0}</td>
                <td className="updated-col">
                  {new Date(entry.updated_at).toLocaleDateString()}
                </td>
                <td className="actions-col">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEditEntry(entry);
                    }}
                    title="Edit entry"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteEntry(entry);
                    }}
                    title="Delete entry"
                    className="delete-btn"
                  >
                    🗑️
                  </button>
                </td>
              </tr>
            ))}

            {/* Empty State */}
            {paginatedEntries.length === 0 && (
              <tr>
                <td colSpan={8} className="empty-table">
                  {filterText ? (
                    <div className="no-filter-results">
                      <p>No entries match your filter "{filterText}"</p>
                      <button onClick={clearFilters}>Clear filter</button>
                    </div>
                  ) : (
                    <div className="no-entries">
                      <p>No entries in this lorebook yet</p>
                      <button onClick={handleCreateEntry} className="primary">
                        Create First Entry
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="entry-pagination">
          <div className="page-info">
            Showing {currentPage * pageSize + 1}-{Math.min((currentPage + 1) * pageSize, entries.length)}
            of {entries.length} entries
          </div>
          <div className="page-controls">
            <button
              disabled={currentPage === 0}
              onClick={() => setCurrentPage(0)}
            >
              ⟪
            </button>
            <button
              disabled={currentPage === 0}
              onClick={() => setCurrentPage(currentPage - 1)}
            >
              ‹
            </button>
            <span className="current-page">
              Page {currentPage + 1} of {totalPages}
            </span>
            <button
              disabled={currentPage === totalPages - 1}
              onClick={() => setCurrentPage(currentPage + 1)}
            >
              ›
            </button>
            <button
              disabled={currentPage === totalPages - 1}
              onClick={() => setCurrentPage(totalPages - 1)}
            >
              ⟫
            </button>
          </div>
          <div className="page-size-selector">
            <label>Show:</label>
            <select value={pageSize} onChange={(e) => {
              setPageSize(parseInt(e.target.value, 10));
              setCurrentPage(0);
            }}>
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      )}

      {/* Add Entry Button */}
      <div className="add-entry-fab">
        <button onClick={handleCreateEntry} className="fab-btn" title="Create new entry">
          +
        </button>
      </div>

      {/* Editor Modal */}
      <LoreEntryEditorModal
        entry={store.editingEntry}
        isOpen={store.showEditor}
        onClose={() => store.setShowEditor(false)}
        onSave={async (data) => {
          if (store.editingEntry) {
            await store.updateLoreEntryAction(store.editingEntry.id, data);
          } else {
            await store.createLoreEntryAction(data);
          }
        }}
      />
    </div>
  );
};