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

export interface CircuitExecutionRequest {
  context_data?: Record<string, any>;
}

export interface CircuitExecutionResponse {
  execution_id: string;
  success: boolean;
  outputs: Record<string, any>;
  logs: string[];
  errors: string[];
}

interface CircuitState {
  circuits: Circuit[];
  current?: Circuit;
  executionResult?: CircuitExecutionResponse;
  isExecuting: boolean;
  fetchCircuits: () => Promise<void>;
  saveCircuit: (c: Circuit) => Promise<void>;
  executeCircuit: (circuitId: number, contextData?: Record<string, any>) => Promise<CircuitExecutionResponse>;
}

export const useCircuitStore = create<CircuitState>((set, get) => ({
  circuits: [],
  isExecuting: false,
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
  async executeCircuit(circuitId, contextData) {
    set({ isExecuting: true, executionResult: undefined });
    try {
      const res = await fetch(`${API_BASE}/circuits/${circuitId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_data: contextData }),
      });

      if (!res.ok) {
        throw new Error(`Execution failed: ${res.statusText}`);
      }

      const result: CircuitExecutionResponse = await res.json();
      set({ executionResult: result, isExecuting: false });
      return result;
    } catch (error) {
      const errorResult: CircuitExecutionResponse = {
        execution_id: '',
        success: false,
        outputs: {},
        logs: [],
        errors: [error instanceof Error ? error.message : 'Unknown error']
      };
      set({ executionResult: errorResult, isExecuting: false });
      throw error;
    }
  },
}));
