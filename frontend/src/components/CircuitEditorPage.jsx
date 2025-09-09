import React from 'react';
import { CircuitEditor } from './circuits/CircuitEditor';
import { CircuitEditor2 } from './circuits/CircuitEditor2';

export function CircuitEditor1Page() {
  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      color: 'var(--text)',
      padding: '2rem'
    }}>
      <h1>Circuit Editor 1 (Original)</h1>
      <div style={{ marginTop: '2rem' }}>
        <CircuitEditor />
      </div>
    </div>
  );
}

export function CircuitEditor2Page() {
  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      color: 'var(--text)',
      padding: '2rem'
    }}>
      <h1>Circuit Editor 2 (New)</h1>
      <div style={{ marginTop: '2rem' }}>
        <CircuitEditor2 />
      </div>
    </div>
  );
}