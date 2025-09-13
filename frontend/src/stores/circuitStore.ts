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

// Prompt type associations for circuit integration
export type PromptType = 'main' | 'tool_call' | 'lore_suggest' | 'image_summary';

interface PromptCircuitAssociation {
  promptType: PromptType;
  circuitId?: number;
  circuitName?: string;
}

interface CircuitModalState {
  isOpen: boolean;
  promptType?: PromptType;
  selectedCircuitId?: number;
}

interface CircuitState {
  circuits: Circuit[];
  current?: Circuit;
  executionResult?: CircuitExecutionResponse;
  isExecuting: boolean;
  // New properties for settings integration
  modalState: CircuitModalState;
  promptCircuitAssociations: Record<PromptType, PromptCircuitAssociation>;
  // Actions
  fetchCircuits: () => Promise<void>;
  saveCircuit: (c: Circuit) => Promise<void>;
  executeCircuit: (circuitId: number, contextData?: Record<string, any>) => Promise<CircuitExecutionResponse>;
  // New actions for settings integration
  openCircuitModal: (promptType: PromptType, circuitId?: number) => void;
  closeCircuitModal: () => void;
  setPromptCircuitAssociation: (promptType: PromptType, circuitId?: number, circuitName?: string) => void;
  getPromptCircuitAssociation: (promptType: PromptType) => PromptCircuitAssociation | undefined;
}

export const useCircuitStore = create<CircuitState>((set, get) => ({
  circuits: [],
  isExecuting: false,
  // Initialize new properties
  modalState: {
    isOpen: false,
  },
  promptCircuitAssociations: {
    main: { promptType: 'main' },
    tool_call: { promptType: 'tool_call' },
    lore_suggest: { promptType: 'lore_suggest' },
    image_summary: { promptType: 'image_summary' },
  },
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
  // New actions for settings integration
  openCircuitModal(promptType, circuitId) {
    set({
      modalState: {
        isOpen: true,
        promptType,
        selectedCircuitId: circuitId,
      }
    });
  },
  closeCircuitModal() {
    set({
      modalState: {
        isOpen: false,
      }
    });
  },
  setPromptCircuitAssociation(promptType, circuitId, circuitName) {
    const associations = get().promptCircuitAssociations;
    const circuits = get().circuits;
    const circuit = circuits.find(c => c.id === circuitId);

    set({
      promptCircuitAssociations: {
        ...associations,
        [promptType]: {
          promptType,
          circuitId,
          circuitName: circuitName || circuit?.name,
        }
      }
    });
  },
  getPromptCircuitAssociation(promptType) {
    return get().promptCircuitAssociations[promptType];
  },
}));
