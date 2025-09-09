import React, { useEffect, useState } from 'react';
import { useCircuitStore } from '../../stores/circuitStore';
import './CircuitEditor.css';

export const CircuitEditor: React.FC = () => {
  const { circuits, current, fetchCircuits, saveCircuit } = useCircuitStore();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', description: '' });

  useEffect(() => {
    fetchCircuits().catch(err => {
      console.error('Failed to fetch circuits:', err);
    });
  }, [fetchCircuits]);

  const handleCreateCircuit = async () => {
    if (!createForm.name.trim()) return;

    try {
      const newCircuit = {
        name: createForm.name.trim(),
        description: createForm.description.trim(),
        data: { nodes: [], edges: [] }
      };

      await saveCircuit(newCircuit);
      setCreateForm({ name: '', description: '' });
      setShowCreateForm(false);
    } catch (err) {
      console.error('Failed to create circuit:', err);
    }
  };

  return (
    <div className="circuit-editor">
      <div className="toolbar panel">
        <span className="title">Circuits</span>
        <div className="toolbar-actions">
          <button
            className="secondary"
            onClick={() => setShowCreateForm(true)}
            title="Create new circuit"
          >
            + New Circuit
          </button>
        </div>
      </div>

      {showCreateForm && (
        <div className="create-form-overlay">
          <div className="create-form-modal panel">
            <h3>Create New Circuit</h3>
            <div className="form-group">
              <label htmlFor="circuit-name">Name:</label>
              <input
                id="circuit-name"
                type="text"
                value={createForm.name}
                onChange={(e) => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter circuit name..."
              />
            </div>
            <div className="form-group">
              <label htmlFor="circuit-description">Description (optional):</label>
              <textarea
                id="circuit-description"
                value={createForm.description}
                onChange={(e) => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Enter circuit description..."
                rows={3}
              />
            </div>
            <div className="form-actions">
              <button onClick={handleCreateCircuit} disabled={!createForm.name.trim()}>
                Create Circuit
              </button>
              <button
                className="secondary"
                onClick={() => {
                  setShowCreateForm(false);
                  setCreateForm({ name: '', description: '' });
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="editor-body">
        <aside className="block-palette panel">
          <h4>Block Palette</h4>
          <div className="palette-items">
            <div className="palette-item" draggable>
              <span className="block-icon">🔗</span>
              <span>Input</span>
            </div>
            <div className="palette-item" draggable>
              <span className="block-icon">⚡</span>
              <span>Output</span>
            </div>
            <div className="palette-item" draggable>
              <span className="block-icon">↗️</span>
              <span>AND Gate</span>
            </div>
            <div className="palette-item" draggable>
              <span className="block-icon">⊻</span>
              <span>OR Gate</span>
            </div>
            <div className="palette-item" draggable>
              <span className="block-icon">🔔</span>
              <span>NOT Gate</span>
            </div>
          </div>
        </aside>

        <main className="canvas panel">
          <div className="canvas-header">
            {!current && circuits.length > 0 && <span className="muted">Select a circuit to view/edit</span>}
            {circuits.length === 0 && <span className="muted">No circuits available. Create your first circuit!</span>}
          </div>

          {circuits.length > 0 && (
            <div className="circuits-list">
              {circuits.map((circuit) => (
                <div
                  key={circuit.id}
                  className={`circuit-item ${current?.id === circuit.id ? 'active' : ''}`}
                  onClick={() => useCircuitStore.setState({ current: circuit })}
                >
                  <span className="circuit-name">{circuit.name}</span>
                  {circuit.description && (
                    <span className="circuit-description">{circuit.description}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {current && (
            <div className="circuit-canvas">
              <h3>{current.name}</h3>
              <div className="canvas-grid">
                <div className="muted" style={{ textAlign: 'center', padding: '2rem' }}>
                  Canvas for {current.name}<br />
                  Circuit editing features coming soon...
                </div>
              </div>
            </div>
          )}
        </main>

        <aside className="properties panel">
          <h4>Properties</h4>
          {current ? (
            <div className="properties-content">
              <div className="property-item">
                <strong>Name:</strong> {current.name}
              </div>
              {current.description && (
                <div className="property-item">
                  <strong>Description:</strong> {current.description}
                </div>
              )}
              <div className="property-item">
                <strong>Nodes:</strong> {(current.data.nodes?.length || 0)}
              </div>
              <div className="property-item">
                <strong>Edges:</strong> {(current.data.edges?.length || 0)}
              </div>
            </div>
          ) : (
            <div className="muted">No circuit selected</div>
          )}
        </aside>
      </div>
    </div>
  );
};
