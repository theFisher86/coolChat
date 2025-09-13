import React, { useState, useEffect } from 'react';
import { useCircuitStore, PromptType, Circuit } from '../../stores/circuitStore';
import { API_BASE } from '../../api';
import './CircuitEditor.css';

interface CircuitModalProps {
  isOpen: boolean;
  promptType: PromptType;
  onClose: () => void;
  onSave: (circuitId: number, circuitName: string) => void;
}

const getPromptTypeDisplayName = (type: PromptType): string => {
  const displayNames = {
    main: 'Main System Prompt',
    tool_call: 'Tool Call Prompt',
    lore_suggest: 'Lorebook Suggestion Prompt',
    image_summary: 'Image Generation Prompt',
  };
  return displayNames[type] || type;
};

export const CircuitModal: React.FC<CircuitModalProps> = ({
  isOpen,
  promptType,
  onClose,
  onSave,
}) => {
  const { circuits, fetchCircuits, modalState } = useCircuitStore();
  const [selectedCircuitId, setSelectedCircuitId] = useState<number | undefined>();
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [newCircuitName, setNewCircuitName] = useState('');
  const [newCircuitDescription, setNewCircuitDescription] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchCircuits().catch(err => console.error('Failed to fetch circuits:', err));
    }
  }, [isOpen, fetchCircuits]);

  useEffect(() => {
    if (isOpen && modalState.selectedCircuitId) {
      setSelectedCircuitId(modalState.selectedCircuitId);
    }
  }, [isOpen, modalState.selectedCircuitId]);

  const handleSave = () => {
    if (selectedCircuitId) {
      const circuit = circuits.find(c => c.id === selectedCircuitId);
      if (circuit) {
        onSave(selectedCircuitId, circuit.name);
        onClose();
      }
    }
  };

  const handleCreateAndSelect = async () => {
    if (!newCircuitName.trim()) return;

    try {
      const newCircuit = {
        name: `${getPromptTypeDisplayName(promptType)} - ${newCircuitName.trim()}`,
        description: newCircuitDescription.trim() || `Circuit for ${getPromptTypeDisplayName(promptType)}`,
        data: { nodes: [], edges: [] }
      };

      const response = await fetch(`${API_BASE}/circuits/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCircuit),
      });

      if (!response.ok) throw new Error('Failed to create circuit');

      const savedCircuit = await response.json();

      // Update circuits list
      const updatedCircuits = [...circuits, savedCircuit];
      useCircuitStore.setState({ circuits: updatedCircuits });

      // Select the new circuit
      setSelectedCircuitId(savedCircuit.id);
      setIsCreatingNew(false);
      setNewCircuitName('');
      setNewCircuitDescription('');
    } catch (error) {
      console.error('Failed to create circuit:', error);
      alert('Failed to create circuit: ' + (error as Error).message);
    }
  };

  const handleCancel = () => {
    setSelectedCircuitId(undefined);
    setIsCreatingNew(false);
    setNewCircuitName('');
    setNewCircuitDescription('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content circuit-modal" onClick={(e) => e.stopPropagation()}>
        <h3>Select Circuit for {getPromptTypeDisplayName(promptType)}</h3>

        <div className="circuit-selection">
          <div className="section">
            <h4>Available Circuits</h4>
            <div className="circuit-list">
              {circuits.length === 0 ? (
                <div className="empty-state">
                  <p>No circuits available. Create your first circuit below.</p>
                </div>
              ) : (
                circuits.map((circuit: Circuit) => (
                  <div
                    key={circuit.id}
                    className={`circuit-item ${selectedCircuitId === circuit.id ? 'selected' : ''}`}
                    onClick={() => setSelectedCircuitId(circuit.id)}
                  >
                    <div className="circuit-info">
                      <span className="circuit-name">{circuit.name}</span>
                      {circuit.description && (
                        <span className="circuit-description">{circuit.description}</span>
                      )}
                    </div>
                    <div className="selection-indicator">
                      {selectedCircuitId === circuit.id && '✓'}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="section">
            <div className="create-new-header">
              <h4>Create New Circuit</h4>
              <button
                className="secondary small"
                onClick={() => setIsCreatingNew(!isCreatingNew)}
              >
                {isCreatingNew ? 'Cancel' : '+ Create New'}
              </button>
            </div>

            {isCreatingNew && (
              <div className="create-form">
                <div className="form-group">
                  <label>Circuit Name:</label>
                  <input
                    type="text"
                    value={newCircuitName}
                    onChange={(e) => setNewCircuitName(e.target.value)}
                    placeholder="Enter circuit name..."
                    autoFocus
                  />
                </div>
                <div className="form-group">
                  <label>Description (optional):</label>
                  <textarea
                    value={newCircuitDescription}
                    onChange={(e) => setNewCircuitDescription(e.target.value)}
                    placeholder="Enter circuit description..."
                    rows={3}
                  />
                </div>
                <div className="form-actions">
                  <button
                    onClick={handleCreateAndSelect}
                    disabled={!newCircuitName.trim()}
                  >
                    Create & Select
                  </button>
                  <button
                    className="secondary"
                    onClick={() => setIsCreatingNew(false)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="modal-actions">
          <button
            onClick={handleSave}
            disabled={!selectedCircuitId}
          >
            Save Selection
          </button>
          <button className="secondary" onClick={handleCancel}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};