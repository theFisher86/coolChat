import React, { useEffect } from 'react';
import { useCircuitStore } from '../../stores/circuitStore';
import './CircuitEditor.css';

export const CircuitEditor: React.FC = () => {
  const { circuits, current, fetchCircuits } = useCircuitStore();

  useEffect(() => {
    fetchCircuits();
  }, [fetchCircuits]);

  return (
    <div className="circuit-editor">
      <div className="toolbar panel">
        <span className="title">Circuits</span>
      </div>
      <div className="editor-body">
        <aside className="block-palette panel">Block Palette</aside>
        <main className="canvas panel">
          {current ? (
            <pre>{JSON.stringify(current.data, null, 2)}</pre>
          ) : (
            <div className="muted">Select or create a circuit</div>
          )}
        </main>
        <aside className="properties panel">Properties</aside>
      </div>
    </div>
  );
};
