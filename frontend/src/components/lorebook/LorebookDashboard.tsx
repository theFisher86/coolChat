import React, { useEffect, useState } from 'react';
import './LorebookStyles.css';
import { useLorebookStore } from '../../stores/lorebookStore';
import { Lorebook } from '../../stores/lorebookStore';
import { LorebookGrid } from './LorebookGrid';
import { LorebookSearch } from './LorebookSearch';
import { LorebookBulkActions } from './LorebookBulkActions';
import { LorebookImport } from './LorebookImport';

const LorebookDashboard: React.FC = () => {
  const store = useLorebookStore();
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');
  const [creationMode, setCreationMode] = useState<'single' | 'bulk' | 'import'>('single');
  const [sortBy, setSortBy] = useState<'name' | 'entries' | 'created' | 'updated'>('updated');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    // Load lorebooks on component mount
    console.log('[DEBUG] LorebookDashboard useEffect triggered, calling fetchLorebooks');
    store.fetchLorebooks();

    // Initialize from URL if applicable
    // const urlParams = new URLSearchParams(window.location.search);
    // const activeId = urlParams.get('active');
    // if (activeId) {
    //   const lb = store.lorebooks.find(lb => lb.id === parseInt(activeId));
    //   if (lb) store.selectLorebook(lb);
    // }
  }, []); // Remove store from dependencies to prevent infinite loop

  const handleSortChange = (field: typeof sortBy) => {
    if (sortBy === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortDirection('desc');
    }
  };

  const sortedLorebooks = React.useMemo(() => {
    const sorted = [...store.lorebooks].sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;

      switch (sortBy) {
        case 'name':
          aVal = a.name.toLowerCase();
          bVal = b.name.toLowerCase();
          break;
        case 'entries':
          aVal = a.entry_count;
          bVal = b.entry_count;
          break;
        case 'created':
          aVal = new Date(a.created_at).getTime();
          bVal = new Date(b.created_at).getTime();
          break;
        case 'updated':
          aVal = new Date(a.updated_at).getTime();
          bVal = new Date(b.updated_at).getTime();
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [store.lorebooks, sortBy, sortDirection]);

  const handleCreateLorebook = async (lorebookData: Partial<Lorebook>) => {
    try {
      await store.createLorebookAction(lorebookData as any);
      setCreationMode('single');
    } catch (error) {
      // Error handling
      console.error('Failed to create lorebook:', error);
    }
  };

  const handleBulkCreate = async (lorebooks: Partial<Lorebook>[]) => {
    for (const lb of lorebooks) {
      await handleCreateLorebook(lb);
    }
    setCreationMode('single');
  };

  const handleImport = async (file: File) => {
    try {
      await store.importLorebookAction(file);
      setCreationMode('single');
    } catch (error) {
      console.error('Import failed:', error);
    }
  };

  if (store.lorebookLoading && store.lorebooks.length === 0) {
    return (
      <div className="lorebook-dashboard loading">
        <div className="loading-spinner" />
        <p>Loading lorebooks...</p>
      </div>
    );
  }

  return (
    <div className="lorebook-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <h1>Lorebook Management</h1>
        <div className="dashboard-actions">
          <button
            className={`action-btn ${viewMode === 'cards' ? 'active' : ''}`}
            onClick={() => setViewMode('cards')}
          >
            📋 Cards
          </button>
          <button
            className={`action-btn ${viewMode === 'table' ? 'active' : ''}`}
            onClick={() => setViewMode('table')}
          >
            📊 Table
          </button>
          <div className="dropdown-menu">
            <button className="primary">+ Create</button>
            <div className="dropdown-content">
              <button onClick={() => setCreationMode('single')}>New Lorebook</button>
              <button onClick={() => setCreationMode('bulk')}>Bulk Create</button>
              <button onClick={() => setCreationMode('import')}>Import JSON</button>
            </div>
          </div>
        </div>
      </div>

      {/* Search Panel */}
      <LorebookSearch
        onSearch={(query) => store.searchLoreAction(query)}
        onClear={() => store.clearSearch()}
        isSearching={store.isSearching}
        searchResults={store.searchResults}
      />

      {/* Bulk Actions */}
      <LorebookBulkActions
        selectedCount={store.selectedEntries.size}
        onBulkDelete={() => store.bulkDeleteEntries()}
        onBulkEdit={() => { /* TODO: Implement bulk edit */ }}
        onClearSelection={() => store.clearSelection()}
      />

      {/* Sorting Controls */}
      <div className="sorting-controls">
        <span>Sort by:</span>
        {(['name', 'entries', 'created', 'updated'] as const).map((field) => (
          <button
            key={field}
            className={`sort-btn ${sortBy === field ? 'active' : ''}`}
            onClick={() => handleSortChange(field)}
          >
            {field.charAt(0).toUpperCase() + field.slice(1)}
            {sortBy === field && (
              <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
            )}
          </button>
        ))}
        <span className="stats">
          {store.lorebooks.length} lorebooks, {store.lorebooks.reduce((sum, lb) => sum + lb.entry_count, 0)} total entries
        </span>
      </div>

      {/* Main Content */}
      <div className="dashboard-content">
        {creationMode === 'import' ? (
          <LorebookImport
            onImport={handleImport}
            onCancel={() => setCreationMode('single')}
          />
        ) : creationMode === 'bulk' ? (
          <LorebookBulkCreation
            onCreate={handleBulkCreate}
            onCancel={() => setCreationMode('single')}
          />
        ) : (
          <LorebookGrid
            lorebooks={sortedLorebooks}
            viewMode={viewMode}
            onSelectLorebook={store.selectLorebook}
            selectedLorebookId={store.selectedLorebook?.id}
            onEditLorebook={(lorebook) => {
              // TODO: Open edit modal
              console.log('Edit lorebook:', lorebook);
            }}
            onDeleteLorebook={(id) => {
              if (window.confirm('Delete this lorebook? This action cannot be undone.')) {
                store.deleteLorebookAction(id);
              }
            }}
            onCreateLorebook={handleCreateLorebook}
          />
        )}
      </div>
    </div>
  );
};

// Simple inline component for bulk creation
const LorebookBulkCreation: React.FC<{
  onCreate: (lorebooks: Partial<Lorebook>[]) => Promise<void>;
  onCancel: () => void;
}> = ({ onCreate, onCancel }) => {
  const [bulkText, setBulkText] = useState('');

  const handleSubmit = async () => {
    const lines = bulkText.split('\n').filter(line => line.trim());
    const lorebooks = lines.map(line => ({
      name: line.trim(),
      description: '',
      entries: []
    }));

    await onCreate(lorebooks);
    setBulkText('');
  };

  return (
    <div className="bulk-creation-panel">
      <h3>Create Multiple Lorebooks</h3>
      <p>Enter one lorebook name per line:</p>
      <textarea
        value={bulkText}
        onChange={(e) => setBulkText(e.target.value)}
        placeholder="Fantasy World&#10;Sci-Fi Universe&#10;Historical Era"
        rows={6}
      />
      <div className="panel-actions">
        <button onClick={handleSubmit}>Create</button>
        <button className="secondary" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
};

export { LorebookDashboard };