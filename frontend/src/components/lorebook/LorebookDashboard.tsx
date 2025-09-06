import React, { useEffect, useState } from 'react';
import { useLorebookStore } from '../../stores/lorebookStore';
import { Lorebook, LoreEntry } from '../../stores/lorebookStore';
import { LorebookGrid } from './LorebookGrid';
import { LorebookSearch } from './LorebookSearch';
import { LorebookBulkActions } from './LorebookBulkActions';
import { LorebookImport } from './LorebookImport';
import { ActiveLorebooks } from './ActiveLorebooks';

const LorebookDashboard: React.FC = () => {
  const store = useLorebookStore();
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');
  const [creationMode, setCreationMode] = useState<'single' | 'bulk' | 'import'>('single');
  const [editingLorebook, setEditingLorebook] = useState<Lorebook | null>(null);
  const [editingLorebookEntries, setEditingLorebookEntries] = useState<LoreEntry[]>([]);

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

  // Lorebooks are displayed as-is without sorting
  const sortedLorebooks = React.useMemo(() => {
    return store.lorebooks;
  }, [store.lorebooks]);

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

  const handleEditLorebook = async (lorebook: Lorebook) => {
    setEditingLorebook(lorebook);
    try {
      // Load the lorebook entries for editing using API directly
      const lorebookData = await fetch(`/lorebooks/${lorebook.id}`);
      if (lorebookData.ok) {
        const data = await lorebookData.json();
        setEditingLorebookEntries(data.entries || []);
      } else {
        setEditingLorebookEntries([]);
      }
    } catch (error) {
      console.error('Failed to load lorebook entries:', error);
      setEditingLorebookEntries([]);
    }
  };

  const handleUpdateLorebook = async () => {
    if (!editingLorebook) return;

    try {
      // Update lorebook metadata first
      await store.updateLorebookAction(editingLorebook.id, {
        name: editingLorebook.name,
        description: editingLorebook.description
      });

      // Handle entry operations
      // Get original entries to compare
      const originalEntries = editingLorebookEntries;

      // Load current entries from server for comparison
      const currentResponse = await fetch(`/lorebooks/${editingLorebook.id}`);
      if (!currentResponse.ok) {
        throw new Error('Failed to load current entries');
      }
      const currentData = await currentResponse.json();
      const serverEntries = currentData.entries || [];

      // Create maps for comparison
      const serverEntryMap = new Map(serverEntries.map((entry: LoreEntry) => [entry.id, entry]));
      const localEntryMap = new Map(originalEntries.map((entry: LoreEntry) => [entry.id, entry]));

      // Determine operations needed
      const toCreate: LoreEntry[] = [];
      const toUpdate: LoreEntry[] = [];
      const toDelete: number[] = [];

      // Find entries to create (no ID or temporary ID)
      for (const entry of editingLorebookEntries) {
        if (!entry.id || entry.id.toString().includes('.')) {
          // New entry or temporary ID
          toCreate.push(entry);
        } else {
          toUpdate.push(entry);
        }
      }

      // Find entries to delete (exist on server but not in local list)
      for (const serverEntry of serverEntries) {
        const stillExists = editingLorebookEntries.some(entry => entry.id === serverEntry.id);
        if (!stillExists) {
          toDelete.push(serverEntry.id);
        }
      }

      // Execute operations
      console.log('Entry operations:', { toCreate: toCreate.length, toUpdate: toUpdate.length, toDelete: toDelete.length });

      // Create new entries
      for (const entry of toCreate) {
        try {
          const newEntryData = {
            lorebook_id: editingLorebook.id,
            title: entry.title,
            content: entry.content,
            keywords: entry.keywords,
            secondary_keywords: entry.secondary_keywords,
            logic: entry.logic,
            trigger: entry.trigger,
            order: entry.order
          };

          await fetch('/lorebooks/entries', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newEntryData)
          });
        } catch (error) {
          console.error('Failed to create entry:', error);
        }
      }

      // Update existing entries
      for (const entry of toUpdate) {
        try {
          const updateData = {
            title: entry.title,
            content: entry.content,
            keywords: entry.keywords,
            secondary_keywords: entry.secondary_keywords,
            logic: entry.logic,
            trigger: entry.trigger,
            order: entry.order
          };

          await fetch(`/lorebooks/entries/${entry.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
          });
        } catch (error) {
          console.error('Failed to update entry:', error);
        }
      }

      // Delete removed entries
      for (const entryId of toDelete) {
        try {
          await fetch(`/lorebooks/entries/${entryId}`, {
            method: 'DELETE'
          });
        } catch (error) {
          console.error('Failed to delete entry:', error);
        }
      }

      // Refresh the lorebook list and close modal
      await store.fetchLorebooks();
      setEditingLorebook(null);
      setEditingLorebookEntries([]);

      console.log('Lorebook updated successfully');
    } catch (error) {
      console.error('Failed to update lorebook:', error);
    }
  };

  const handleCancelEdit = () => {
    setEditingLorebook(null);
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

      {/* Stats */}
      <div className="lorebook-stats">
        <span className="stats">
          {store.lorebooks.length} lorebooks, {store.lorebooks.reduce((sum, lb) => sum + lb.entry_count, 0)} total entries
        </span>
      </div>

      {/* Active Lorebooks for Chat Context */}
      <ActiveLorebooks lorebooks={store.lorebooks} />

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
            onEditLorebook={handleEditLorebook}
            onDeleteLorebook={(id) => {
              if (window.confirm('Delete this lorebook? This action cannot be undone.')) {
                store.deleteLorebookAction(id);
              }
            }}
            onCreateLorebook={handleCreateLorebook}
          />
        )}

        {/* Full Lorebook Editor Modal */}
        {editingLorebook && (
          <div className="modal-overlay">
            <div className="modal-content large-modal">
              <div className="modal-header">
                <h2>Edit Lorebook: {editingLorebook.name}</h2>
                <button className="close-btn" onClick={handleCancelEdit}>×</button>
              </div>
              <div className="modal-body">
                <div className="lorebook-editor">
                  {/* Lorebook Metadata */}
                  <div className="editor-section">
                    <h3>Lorebook Details</h3>
                    <div className="metadata-form">
                      <div className="form-row">
                        <div className="form-group">
                          <label htmlFor="edit-name">Name:</label>
                          <input
                            id="edit-name"
                            name="name"
                            type="text"
                            defaultValue={editingLorebook.name}
                            required
                            maxLength={255}
                            onChange={(e) => {
                              setEditingLorebook(prev => prev ? {...prev, name: e.target.value} : null);
                            }}
                          />
                        </div>
                        <div className="form-group">
                          <label htmlFor="edit-description">Description:</label>
                          <textarea
                            id="edit-description"
                            name="description"
                            rows={3}
                            defaultValue={editingLorebook.description || ''}
                            placeholder="Describe this lorebook..."
                            onChange={(e) => {
                              setEditingLorebook(prev => prev ? {...prev, description: e.target.value} : null);
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Lorebook Entries */}
                  <div className="editor-section">
                    <div className="section-header">
                      <h3>Lorebook Entries</h3>
                      <button
                        type="button"
                        className="primary"
                        onClick={() => {
                          const newEntry: LoreEntry = {
                            id: Date.now() + Math.random(), // Temporary ID
                            title: '',
                            content: '',
                            keywords: [],
                            secondary_keywords: [],
                            logic: 'AND ANY',
                            trigger: 100,
                            order: 0,
                            created_at: new Date().toISOString(),
                            updated_at: new Date().toISOString()
                          };
                          setEditingLorebookEntries([...editingLorebookEntries, newEntry]);
                        }}
                      >
                        + Add Entry
                      </button>
                    </div>

                    <div className="entries-editor">
                      {editingLorebookEntries.map((entry, index) => (
                        <div key={entry.id || index} className="entry-editor">
                          <div className="entry-header">
                            <input
                              type="text"
                              placeholder="Entry title..."
                              value={entry.title}
                              onChange={(e) => {
                                const updated = [...editingLorebookEntries];
                                updated[index] = {...entry, title: e.target.value};
                                setEditingLorebookEntries(updated);
                              }}
                            />
                            <div className="form-group">
                              <label>Trigger (%):</label>
                              <input
                                type="number"
                                min="0"
                                max="100"
                                value={entry.trigger}
                                onChange={(e) => {
                                  const updated = [...editingLorebookEntries];
                                  updated[index] = {...entry, trigger: parseInt(e.target.value) || 0};
                                  setEditingLorebookEntries(updated);
                                }}
                              />
                            </div>
                            <div className="form-group">
                              <label>Order:</label>
                              <input
                                type="number"
                                value={entry.order}
                                onChange={(e) => {
                                  const updated = [...editingLorebookEntries];
                                  updated[index] = {...entry, order: parseFloat(e.target.value) || 0};
                                  setEditingLorebookEntries(updated);
                                }}
                              />
                            </div>
                            <button
                              type="button"
                              className="delete-btn"
                              onClick={() => {
                                const updated = editingLorebookEntries.filter((_, i) => i !== index);
                                setEditingLorebookEntries(updated);
                              }}
                            >
                              ×
                            </button>
                          </div>

                          <div className="form-row">
                            <div className="form-group">
                              <label>Keywords:</label>
                              <input
                                type="text"
                                placeholder="keyword1, keyword2"
                                value={entry.keywords.join(', ')}
                                onChange={(e) => {
                                  const updated = [...editingLorebookEntries];
                                  updated[index] = {
                                    ...entry,
                                    keywords: e.target.value.split(',').map(k => k.trim()).filter(k => k)
                                  };
                                  setEditingLorebookEntries(updated);
                                }}
                              />
                            </div>
                            <div className="form-group">
                              <label>Logic:</label>
                              <select
                                value={entry.logic}
                                onChange={(e) => {
                                  const updated = [...editingLorebookEntries];
                                  updated[index] = {...entry, logic: e.target.value as any};
                                  setEditingLorebookEntries(updated);
                                }}
                              >
                                <option value="AND ANY">AND ANY</option>
                                <option value="AND ALL">AND ALL</option>
                                <option value="NOT ANY">NOT ANY</option>
                                <option value="NOT ALL">NOT ALL</option>
                              </select>
                            </div>
                            <div className="form-group">
                              <label>Secondary Keywords:</label>
                              <input
                                type="text"
                                placeholder="secondary1, secondary2"
                                value={entry.secondary_keywords.join(', ')}
                                onChange={(e) => {
                                  const updated = [...editingLorebookEntries];
                                  updated[index] = {
                                    ...entry,
                                    secondary_keywords: e.target.value.split(',').map(k => k.trim()).filter(k => k)
                                  };
                                  setEditingLorebookEntries(updated);
                                }}
                              />
                            </div>
                          </div>

                          <div className="form-group">
                            <label>Content:</label>
                            <textarea
                              rows={4}
                              placeholder="Entry content..."
                              value={entry.content}
                              onChange={(e) => {
                                const updated = [...editingLorebookEntries];
                                updated[index] = {...entry, content: e.target.value};
                                setEditingLorebookEntries(updated);
                              }}
                              required
                            />
                          </div>
                        </div>
                      ))}

                      {editingLorebookEntries.length === 0 && (
                        <div className="no-entries">
                          <p>No entries in this lorebook yet.</p>
                          <button
                            type="button"
                            className="primary"
                            onClick={() => {
                              const newEntry: LoreEntry = {
                                id: Date.now() + Math.random(),
                                title: '',
                                content: '',
                                keywords: [],
                                secondary_keywords: [],
                                logic: 'AND ANY',
                                trigger: 100,
                                order: 0,
                                created_at: new Date().toISOString(),
                                updated_at: new Date().toISOString()
                              };
                              setEditingLorebookEntries([newEntry]);
                            }}
                          >
                            Add First Entry
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="modal-actions">
                    <button
                      type="button"
                      className="primary"
                      onClick={handleUpdateLorebook}
                    >
                      Save All Changes
                    </button>
                    <button type="button" className="secondary" onClick={handleCancelEdit}>
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
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