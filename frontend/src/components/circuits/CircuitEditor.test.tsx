import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { CircuitEditor } from './CircuitEditor';
import { useCircuitStore } from '../../stores/circuitStore';

// Mock the circuitStore
vi.mock('../../stores/circuitStore', () => ({
  useCircuitStore: vi.fn()
}));

// Mock ReactFlow to avoid canvas rendering issues in tests
vi.mock('reactflow', async () => {
  const actual = await vi.importActual('reactflow');
  return {
    ...actual,
    ReactFlow: ({ children, ...props }: any) => (
      <div data-testid="react-flow-mock" {...props}>
        {children}
      </div>
    ),
    Controls: () => <div data-testid="controls">Controls</div>,
    MiniMap: () => <div data-testid="minimap">MiniMap</div>,
    ReactFlowProvider: ({ children }: any) => <div data-testid="react-flow-provider">{children}</div>,
    addEdge: vi.fn((...args) => ({ ...args[0], id: 'new-edge' })),
    useNodesState: vi.fn(() => [[], vi.fn()]),
    useEdgesState: vi.fn(() => [[], vi.fn()]),
  };
});

describe('CircuitEditor', () => {
  const mockCircuitStore = {
    circuits: [
      { id: 1, name: 'Test Circuit 1', description: 'First test circuit', data: { nodes: [], edges: [] } },
      { id: 2, name: 'Test Circuit 2', description: 'Second test circuit', data: { nodes: [], edges: [] } }
    ],
    current: null,
    fetchCircuits: vi.fn(),
    saveCircuit: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useCircuitStore as any).mockReturnValue(mockCircuitStore);
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it('renders CircuitEditor with title and toolbar', () => {
    render(
      <CircuitEditor />
    );

    expect(screen.getByText('Circuits')).toBeInTheDocument();
    expect(screen.getByText('+ New Circuit')).toBeInTheDocument();
    expect(screen.getByText('Save Circuit')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '+ New Circuit' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Save Circuit' })).toBeDisabled();
  });
});