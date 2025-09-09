"""Circuit execution engine for CoolChat.

This module provides the core execution engine for circuit-based prompt workflows.
It includes parsing, execution, validation, and integration with chat, lore, and RAG systems.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from .database import SessionLocal
from .models import Circuit, Character, LoreEntry
from .config import load_config
from .rag_service import get_rag_service
from .circuit_integrations import CircuitIntegrationAdapter

# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class NodeData:
    """Represents a node's data in the circuit."""
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any]
    label: Optional[str] = None


@dataclass
class Edge:
    """Represents an edge connecting nodes in the circuit."""
    id: str
    source: str
    target: str
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None


@dataclass
class CircuitData:
    """Parsed circuit data structure."""
    nodes: List[NodeData]
    edges: List[Edge]
    nodes_by_id: Dict[str, NodeData]
    edges_by_source: Dict[str, List[Edge]]
    edges_by_target: Dict[str, List[Edge]]


@dataclass
class ExecutionContext:
    """Context for circuit execution."""
    variables: Dict[str, Any]
    output: List[str]
    logs: List[Dict[str, Any]]
    current_node: Optional[NodeData] = None


class CircuitParser:
    """Parses serialized circuit definitions into executable structures."""

    @staticmethod
    def parse_circuit(data: Dict[str, Any]) -> CircuitData:
        """Parse raw circuit data into CircuitData structure."""
        nodes = []
        nodes_by_id = {}
        edges = []
        edges_by_source = {}
        edges_by_target = {}

        # Parse nodes
        for node_dict in data.get('nodes', []):
            node = NodeData(
                id=node_dict['id'],
                type=node_dict['type'],
                position=node_dict.get('position', {}),
                data=node_dict.get('data', {}),
                label=node_dict.get('data', {}).get('label')
            )
            nodes.append(node)
            nodes_by_id[node.id] = node

        # Parse edges
        for edge_dict in data.get('edges', []):
            edge = Edge(
                id=edge_dict['id'],
                source=edge_dict['source'],
                target=edge_dict['target'],
                source_handle=edge_dict.get('sourceHandle'),
                target_handle=edge_dict.get('targetHandle')
            )
            edges.append(edge)

            # Build lookup dictionaries
            if edge.source not in edges_by_source:
                edges_by_source[edge.source] = []
            edges_by_source[edge.source].append(edge)

            if edge.target not in edges_by_target:
                edges_by_target[edge.target] = []
            edges_by_target[edge.target].append(edge)

        return CircuitData(
            nodes=nodes,
            edges=edges,
            nodes_by_id=nodes_by_id,
            edges_by_source=edges_by_source,
            edges_by_target=edges_by_target
        )


class CircuitValidator:
    """Validates circuit structure and node configurations."""

    @staticmethod
    def validate_circuit(circuit_data: CircuitData) -> List[str]:
        """Validate the circuit structure and return list of errors."""
        errors = []

        # Check for unreachable nodes (no incoming edges except start nodes)
        start_nodes = []
        for node in circuit_data.nodes:
            if not circuit_data.edges_by_target.get(node.id):
                if node.type not in ['input_node', 'system_prompt', 'variable_processor']:
                    start_nodes.append(node)
                else:
                    start_nodes.append(node)
            else:
                # Has incoming edges
                pass

        # Must have at least one start node
        if not start_nodes:
            errors.append("Circuit must have at least one entry node")

        # Check for cycles (basic check)
        visited = set()
        rec_stack = set()

        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for edge in circuit_data.edges_by_source.get(node_id, []):
                target = edge.target
                if target not in visited and has_cycle(target):
                    return True
                elif target in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node in circuit_data.nodes:
            if node.id not in visited:
                if has_cycle(node.id):
                    errors.append("Circuit contains cycles (infinite loops)")
                    break

        # Validate node-specific configurations
        for node in circuit_data.nodes:
            errors.extend(CircuitValidator.validate_node(node))

        return errors

    @staticmethod
    def validate_node(node: NodeData) -> List[str]:
        """Validate a single node's configuration."""
        errors = []

        if node.type == 'conditional':
            if 'condition' not in node.data:
                errors.append(f"Node {node.id}: Conditional node missing 'condition' field")
            if 'true_path' not in node.data and 'false_path' not in node.data:
                errors.append(f"Node {node.id}: Conditional node must have at least one output path")

        elif node.type == 'llm_connector':
            if 'provider' not in node.data:
                errors.append(f"Node {node.id}: LLM connector node missing 'provider' field")
            if 'model' not in node.data:
                errors.append(f"Node {node.id}: LLM connector node missing 'model' field")

        elif node.type == 'prompt_builder':
            if not node.data.get('template'):
                errors.append(f"Node {node.id}: Prompt builder node missing template")

        return errors


class CircuitExecutor:
    """Executes circuit logic step by step."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()
        self.rag_service = get_rag_service(db=self.db)
        self.integrator = CircuitIntegrationAdapter(db=self.db, rag_service=self.rag_service)

    def execute_circuit(
        self,
        circuit: Circuit,
        inputs: Dict[str, Any],
        character_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a circuit with given inputs."""
        start_time = datetime.now(timezone.utc)

        try:
            # Parse circuit
            circuit_data = CircuitParser.parse_circuit(circuit.data)

            # Validate circuit
            validation_errors = CircuitValidator.validate_circuit(circuit_data)
            if validation_errors:
                raise ValueError(f"Circuit validation failed: {'; '.join(validation_errors)}")

            # Initialize execution context
            context = ExecutionContext(
                variables=dict(inputs),  # Copy inputs
                output=[],
                logs=[]
            )

            # Log execution start
            self._log_event(context, "EXECUTE_CIRCUIT", {
                "circuit_id": circuit.id,
                "inputs": inputs,
                "start_time": start_time.isoformat()
            })

            # Find start nodes (nodes with no incoming edges)
            start_nodes = [
                node for node in circuit_data.nodes
                if node.id not in circuit_data.edges_by_target
            ]

            # Execute from start nodes
            executed_nodes = set()
            for start_node in start_nodes:
                self._execute_node(start_node, circuit_data, context, executed_nodes, character_id)

            # Log execution end
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._log_event(context, "EXECUTE_CIRCUIT_COMPLETE", {
                "execution_ms": execution_time,
                "output": "\n".join(context.output),
                "variable_count": len(context.variables)
            })

            return {
                "success": True,
                "output": "\n".join(context.output),
                "variables": context.variables,
                "execution_ms": execution_time,
                "logs": context.logs
            }

        except Exception as e:
            # Log error
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.error(f"Circuit execution failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "execution_ms": execution_time,
                "output": "",
                "variables": {},
                "logs": []
            }

    def _execute_node(
        self,
        node: NodeData,
        circuit_data: CircuitData,
        context: ExecutionContext,
        executed_nodes: set,
        character_id: Optional[int] = None
    ) -> None:
        """Execute a single node in the circuit."""
        if node.id in executed_nodes:
            return

        executed_nodes.add(node.id)
        context.current_node = node

        start_node_time = datetime.now(timezone.utc)

        try:
            # Log node execution start
            self._log_event(context, "EXECUTE_NODE_START", {
                "node_id": node.id,
                "node_type": node.type,
                "node_label": node.label
            })

            # Execute based on node type
            result = self._execute_node_logic(node, context, character_id)

            # Handle execution result
            if isinstance(result, dict):
                if result.get('output'):
                    context.output.append(result['output'])
                if result.get('variables'):
                    context.variables.update(result['variables'])

            # Find next nodes and execute them
            outgoing_edges = circuit_data.edges_by_source.get(node.id, [])
            for edge in outgoing_edges:
                next_node = circuit_data.nodes_by_id.get(edge.target)
                if next_node:
                    # Check if this edge should be followed (for conditionals)
                    if self._should_follow_edge(edge, node, context):
                        self._execute_node(next_node, circuit_data, context, executed_nodes, character_id)

            # Log node execution end
            execution_time = (datetime.now(timezone.utc) - start_node_time).total_seconds() * 1000
            self._log_event(context, "EXECUTE_NODE_COMPLETE", {
                "node_id": node.id,
                "execution_ms": execution_time,
                "result": str(result)[:200] if result else None
            })

        except Exception as e:
            # Log node error and continue
            execution_time = (datetime.now(timezone.utc) - start_node_time).total_seconds() * 1000
            self._log_event(context, "EXECUTE_NODE_ERROR", {
                "node_id": node.id,
                "error": str(e),
                "execution_ms": execution_time
            }, "ERROR")
            logger.error(f"Node {node.id} execution failed: {str(e)}", exc_info=True)

    def _execute_node_logic(
        self,
        node: NodeData,
        context: ExecutionContext,
        character_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute the logic for a specific node type."""
        node_type = node.type

        if node_type == 'input_node':
            # Just pass through variables
            return {"variables": context.variables}

        elif node_type == 'variable_processor':
            return self._process_variable_node(node, context)

        elif node_type == 'conditional':
            return self._process_conditional_node(node, context)

        elif node_type == 'prompt_builder':
            return self._process_prompt_builder_node(node, context)

        elif node_type == 'llm_connector':
            return self._process_llm_connector_node(node, context, character_id)

        elif node_type == 'output_node':
            return {"output": node.data.get('template', '')}

        elif node_type == 'system_prompt':
            # Add system prompt to context
            system_prompt = node.data.get('text', '')
            context.variables['system_prompt'] = system_prompt
            return {"output": system_prompt}

        elif node_type == 'lore_injection':
            return self._process_lore_injection_node(node, context)

        # Default: pass through
        return {"variables": context.variables}

    def _process_variable_node(self, node: NodeData, context: ExecutionContext) -> Dict[str, Any]:
        """Process variable processor node."""
        operation = node.data.get('operation', 'set')
        var_name = node.data.get('variable_name', '')
        value = node.data.get('value', '')

        if operation == 'set':
            context.variables[var_name] = value
        elif operation == 'append':
            if var_name in context.variables:
                context.variables[var_name] += value
            else:
                context.variables[var_name] = value
        elif operation == 'get':
            # Just ensure variable exists
            pass

        return {"variables": {var_name: context.variables.get(var_name)}}

    def _process_conditional_node(self, node: NodeData, context: ExecutionContext) -> Dict[str, Any]:
        """Process conditional node."""
        condition = node.data.get('condition', '')
        # Simple evaluation - can be extended
        result = self._evaluate_condition(condition, context.variables)
        context.variables['condition_result'] = result
        return {"variables": {"condition_result": result}}

    def _process_prompt_builder_node(self, node: NodeData, context: ExecutionContext) -> Dict[str, Any]:
        """Process prompt builder node."""
        template = node.data.get('template', '')
        # Simple variable substitution
        for var_name, var_value in context.variables.items():
            template = template.replace('{{' + var_name + '}}', str(var_value))

        context.variables['prompt'] = template
        return {"output": template, "variables": {"prompt": template}}

    def _process_llm_connector_node(
        self,
        node: NodeData,
        context: ExecutionContext,
        character_id: Optional[int]
    ) -> Dict[str, Any]:
        """Process LLM connector node."""
        provider = node.data.get('provider', 'openai')
        model = node.data.get('model', 'gpt-4')
        prompt = context.variables.get('prompt', '')

        if not prompt:
            raise ValueError("No prompt available for LLM connector")

        # Call integration adapter
        response = self.integrator.call_llm(provider, model, prompt, character_id)

        context.variables['llm_response'] = response
        return {"output": response, "variables": {"llm_response": response}}

    def _process_lore_injection_node(self, node: NodeData, context: ExecutionContext) -> Dict[str, Any]:
        """Process lore injection node."""
        keywords = node.data.get('keywords', [])
        limit = node.data.get('limit', 5)

        # Get relevant lore entries
        lore_entries = self.integrator.query_lore(keywords, limit)

        # Inject into prompt
        lore_text = "\n".join([f"[{entry['keyword']}]: {entry['content']}" for entry in lore_entries])
        context.variables['lore_injection'] = lore_text
        return {"output": lore_text, "variables": {"lore_injection": lore_text}}

    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """Simple condition evaluation."""
        # Very basic implementation - can be enhanced with proper expression parser
        if '==' in condition:
            left, right = condition.split('==', 1)
            left = left.strip()
            right = right.strip()
            # Check if it's a variable
            if left in variables:
                return variables[left] == right.strip('"').strip("'")
            else:
                return left == right
        return True  # Default to true

    def _should_follow_edge(self, edge: Edge, node: NodeData, context: ExecutionContext) -> bool:
        """Determine if an edge should be followed based on node results."""
        if node.type == 'conditional':
            target_handle = edge.target_handle
            if target_handle == 'true':
                return bool(context.variables.get('condition_result', False))
            elif target_handle == 'false':
                return not bool(context.variables.get('condition_result', False))
            else:
                return True

        # Default: follow all edges
        return True

    def _log_event(
        self,
        context: ExecutionContext,
        event: str,
        details: Dict[str, Any],
        level: str = "INFO"
    ) -> None:
        """Add an event to the execution logs."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            "node_id": context.current_node.id if context.current_node else None,
            "details": details
        }
        context.logs.append(log_entry)