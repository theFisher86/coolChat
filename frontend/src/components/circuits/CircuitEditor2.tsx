import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useCircuitStore } from '../../stores/circuitStore';
import ReactFlow, { Node, Edge, addEdge, Connection, useNodesState, useEdgesState, Controls, MiniMap, Handle, Position } from 'reactflow';
import 'reactflow/dist/style.css';
import './CircuitEditor.css';

// Block connector configurations
const blockConfigs = {
  logic: {
    inputs: ['input1'],
    outputs: ['output'],
    label: 'Logic Block'
  },
  content: {
    inputs: ['text', 'source'],
    outputs: ['result'],
    label: 'Content Block'
  },
  flow: {
    inputs: ['trigger'],
    outputs: ['next', 'branched'],
    label: 'Flow Block'
  },
  integration: {
    inputs: ['request', 'params'],
    outputs: ['response', 'success', 'error'],
    label: 'Integration Block'
  }
};

// Block components with dynamic connectors
const BlockNode = ({ data }: any) => {
  const config = blockConfigs[data.type] || { inputs: [], outputs: [], label: 'Unknown Block' };
  const totalConnectors = Math.max(config.inputs.length, config.outputs.length, 1);
  const blockHeight = 80 + (totalConnectors * 20); // Base height + space for connectors

  // Calculate connector spacing
  const getConnectorTop = (index: number, total: number) => {
    const start = 20;
    const spacing = (blockHeight - 40) / Math.max(total - 1, 1);
    return start + (index * spacing);
  };

  return (
    <div
      className={`circuit-block circuit-${data.type}`}
      style={{ height: blockHeight, minHeight: 100 }}
    >
      {/* Input connectors (left side) */}
      {config.inputs.map((inputName, index) => (
        <Handle
          key={`input-${inputName}`}
          id={`input-${inputName}`}
          type="target"
          position={Position.Left}
          style={{
            background: '#10b981',
            border: '2px solid #059669',
            width: 12,
            height: 12,
            borderRadius: '50%',
            position: 'absolute',
            left: -6,
            top: getConnectorTop(index, config.inputs.length) - 6
          }}
          title={`Input: ${inputName}`}
        />
      ))}

      {/* Output connectors (right side) */}
      {config.outputs.map((outputName, index) => (
        <Handle
          key={`output-${outputName}`}
          id={`output-${outputName}`}
          type="source"
          position={Position.Right}
          style={{
            background: '#f59e0b',
            border: '2px solid #d97706',
            width: 12,
            height: 12,
            borderRadius: '50%',
            position: 'absolute',
            right: -6,
            top: getConnectorTop(index, config.outputs.length) - 6
          }}
          title={`Output: ${outputName}`}
        />
      ))}

      {/* Block content */}
      <div className="block-content" style={{
        padding: '8px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <span className="block-icon" style={{ fontSize: '16px', marginBottom: '4px' }}>
          {data.icon}
        </span>
        <span style={{
          fontSize: '12px',
          fontWeight: 'bold',
          textAlign: 'center',
          wordBreak: 'break-word'
        }}>
          {config.label}
        </span>
        <span style={{
          fontSize: '10px',
          opacity: 0.7,
          marginTop: '2px'
        }}>
          {totalConnectors} connections
        </span>
      </div>
    </div>
  );
};

const nodeTypes = {
  logic: BlockNode,
  content: BlockNode,
  flow: BlockNode,
  integration: BlockNode,
};

export const CircuitEditor2: React.FC = () => {
  const { circuits, current, fetchCircuits, saveCircuit } = useCircuitStore();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', description: '' });

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  useEffect(() => {
    fetchCircuits().catch(err => {
      console.error('Failed to fetch circuits:', err);
    });
  }, [fetchCircuits]);

  const deleteSelectedNode = useCallback(() => {
    if (!selectedNode) return;
    setNodes((nodes) => nodes.filter((node) => node.id !== selectedNode.id));
    setEdges((edges) => edges.filter(edge => edge.source !== selectedNode.id && edge.target !== selectedNode.id));
    setSelectedNode(null);
  }, [selectedNode, setNodes, setEdges]);

  useEffect(() => {
    if (current) {
      setNodes((current.data as any).nodes || []);
      setEdges((current.data as any).edges || []);
      setSelectedNode(null);
    }
  }, [current, setNodes, setEdges]);

  // Handle keyboard events for deleting nodes
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Delete' && selectedNode) {
        event.preventDefault();
        deleteSelectedNode();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedNode, deleteSelectedNode]);

  const onConnect = useCallback((params: Connection) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  const onDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const nodeType = event.dataTransfer.getData('nodeType');
    if (!nodeType) return;
    const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect();
    if (!reactFlowBounds) return;
    const blocksize = 100;
    const position = {
      x: event.clientX - reactFlowBounds.left - blocksize / 2,
      y: event.clientY - reactFlowBounds.top - blocksize / 2,
    };
    const config = blockConfigs[nodeType] || { inputs: [], outputs: [], label: 'Unknown Block' };
    const newNode: Node = {
      id: `${nodeType}-${Date.now()}`,
      type: nodeType,
      position,
      data: {
        label: config.label,
        type: nodeType,
        icon: getIconForType(nodeType),
        inputs: config.inputs,
        outputs: config.outputs
      },
    };
    setNodes((nds) => nds.concat(newNode));
  }, [setNodes]);

  const onDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => event.preventDefault(), []);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => setSelectedNode(node), []);

  const getIconForType = (type: string) => {
    const icons: Record<string, string> = { logic: '🌟', content: '📖', flow: '↗️', integration: '🔗' };
    return icons[type] || '⚡';
  };

  const onSave = () => {
    if (!current) return;
    saveCircuit({ ...current, data: { nodes, edges } }).catch(err => console.error('Failed to save:', err));
  };

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
        <span className="title">Circuits2</span>
        <div className="toolbar-actions">
          <button
            className="secondary"
            onClick={() => setShowCreateForm(true)}
            title="Create new circuit"
          >
            + New Circuit
          </button>
          <button
            className="secondary"
            onClick={onSave}
            disabled={!current}
            title="Save circuit"
          >
            Save Circuit
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
            {(['logic', 'content', 'flow', 'integration'] as const).map(type => (
              <div
                key={type}
                className={`palette-item circuit-${type}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('nodeType', type)}
              >
                <span className="block-icon">{getIconForType(type)}</span>
                <span>{type.charAt(0).toUpperCase() + type.slice(1)} Block</span>
              </div>
            ))}
          </div>
        </aside>

        <main className="canvas panel">
          <div className="canvas-header">
            {!current && circuits.length > 0 && <span className="muted">Select a circuit to view/edit</span>}
            {circuits.length === 0 && <span className="muted">No circuits available. Create your first circuit!</span>}
          </div>

          {circuits.length > 0 && !current && (
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
              {/* Instructions for circuit editing:
               * How to use the circuit editor:
               * 1. Drag blocks from the Block Palette onto the canvas
               * 2. Notice the color-coded connectors:
               *    - GREEN connectors on the LEFT are INPUTS (data flows IN)
               *    - ORANGE connectors on the RIGHT are OUTPUTS (data flows OUT)
               * 3. Click and drag from an OUTPUT connector to an INPUT connector to connect blocks
               * 4. Blocks automatically expand taller to accommodate more connectors
               * 5. Click on a node to select it and view its properties in the properties panel
               * 6. Delete nodes by:
               *    - Pressing the Delete key when a node is selected
               *    - Clicking the "Delete Node" button in the properties panel
               * 7. Use the Controls panel for zoom/pan and MiniMap for overview navigation
               */}
              <div style={{ height: '400px', position: 'relative' }}>
                <div ref={reactFlowWrapper} style={{ height: '100%' }}>
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                    onNodeClick={onNodeClick}
                    nodeTypes={nodeTypes}
                    fitView
                  >
                    <Controls />
                    <MiniMap />
                  </ReactFlow>
                </div>
              </div>
            </div>
          )}
        </main>

        <aside className="properties panel">
          <h4>Properties</h4>
          {current ? (
            <div className="properties-content">
              {!selectedNode ? (
                <>
                  <div className="property-item">
                    <strong>Name:</strong> {current.name}
                  </div>
                  {current.description && (
                    <div className="property-item">
                      <strong>Description:</strong> {current.description}
                    </div>
                  )}
                  <div className="property-item">
                    <strong>Nodes:</strong> {nodes.length}
                  </div>
                  <div className="property-item">
                    <strong>Edges:</strong> {edges.length}
                  </div>
                </>
              ) : (
                <>
                  <div className="property-item">
                    <strong>Label:</strong> {selectedNode.data.label}
                  </div>
                  <div className="property-item">
                    <strong>Type:</strong> {selectedNode.data.type}
                  </div>
                  <div className="property-item">
                    <strong>ID:</strong> {selectedNode.id}
                  </div>
                  <div className="property-item">
                    <strong>Position:</strong> ({Math.round(selectedNode.position.x)}, {Math.round(selectedNode.position.y)})
                  </div>
                  <div className="property-item">
                    <button
                      className="secondary delete-btn"
                      onClick={deleteSelectedNode}
                      title="Delete selected node (or press Delete key)"
                      style={{ marginTop: '8px', width: '100%' }}
                    >
                      🗑️ Delete Node
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="muted">No circuit selected</div>
          )}
        </aside>
      </div>
    </div>
  );
};