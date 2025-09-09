import { create } from 'zustand';
import { API_BASE } from '../api';

export interface Circuit {
  id?: number;
  name: string;
  description?: string;
  data: {
    nodes?: any[];
    edges?: any[];
  };
}

interface CircuitState {
  circuits: Circuit[];
  current?: Circuit;
  fetchCircuits: () => Promise<void>;
  saveCircuit: (c: Circuit) => Promise<void>;
}

export const useCircuitStore = create<CircuitState>((set, get) => ({
  circuits: [],
  async fetchCircuits() {
    const res = await fetch(`${API_BASE}/circuits/`);
    const data = await res.json();
    set({ circuits: data });
  },
  async saveCircuit(circuit) {
    const res = await fetch(`${API_BASE}/circuits/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(circuit),
    });
    if (!res.ok) throw new Error('Failed to save');
    const saved = await res.json();
    set({ circuits: [...get().circuits, saved], current: saved });
  },
}));
